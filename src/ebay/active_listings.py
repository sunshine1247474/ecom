"""
eBay Active Listings Scanner
==============================
Fetches all active listings from the seller's eBay account with:
  - Title
  - Status (Active / Ended / Sold)
  - Current price
  - Views (hit count)
  - Watchers
  - Quantity available / sold
  - Time left
  - Listing URL
  - Item ID

Uses the eBay Trading API (GetMyeBaySelling) which is the most reliable
way to get watcher counts and view counts — the newer REST APIs do not
expose watchers.

Auth: requires EBAY_USER_TOKEN (obtained via get_ebay_token.py)
"""

from __future__ import annotations
import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import requests
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent.parent / ".env", override=True)

# ─────────────────────────────────────────────────────────────────────────────
# Data model
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ActiveListing:
    item_id:        str
    title:          str
    price:          float
    currency:       str
    quantity:       int
    quantity_sold:  int
    watchers:       int
    views:          int
    status:         str          # "Active", "Completed", etc.
    time_left:      str          # e.g. "P3DT2H15M" (ISO 8601 duration)
    time_left_human: str         # e.g. "3d 2h 15m"
    end_time:       Optional[datetime]
    listing_url:    str
    image_url:      str = ""
    condition:      str = ""
    extra:          dict = field(default_factory=dict)

    @property
    def days_left(self) -> Optional[float]:
        if self.end_time:
            delta = self.end_time - datetime.now(timezone.utc)
            return max(0.0, delta.total_seconds() / 86400)
        return None

    @property
    def is_ending_soon(self) -> bool:
        d = self.days_left
        return d is not None and d < 1.0


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _parse_iso_duration(duration: str) -> str:
    """Convert ISO 8601 duration (P3DT2H15M) to human-readable string."""
    if not duration:
        return ""
    import re
    pattern = r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?"
    m = re.match(pattern, duration)
    if not m:
        return duration
    days, hours, mins, secs = (int(x or 0) for x in m.groups())
    parts = []
    if days:  parts.append(f"{days}d")
    if hours: parts.append(f"{hours}h")
    if mins:  parts.append(f"{mins}m")
    if secs and not parts: parts.append(f"{secs}s")
    return " ".join(parts) or "< 1m"


def _parse_datetime(s: str) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def _xml_text(element, tag: str, ns: str = "") -> str:
    """Safely get text from an XML element."""
    if ns:
        tag = f"{{{ns}}}{tag}"
    el = element.find(tag)
    return el.text.strip() if el is not None and el.text else ""


def _xml_int(element, tag: str, ns: str = "") -> int:
    val = _xml_text(element, tag, ns)
    try:
        return int(val)
    except (ValueError, TypeError):
        return 0


def _xml_float(element, tag: str, ns: str = "") -> float:
    val = _xml_text(element, tag, ns)
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Trading API client
# ─────────────────────────────────────────────────────────────────────────────

NS = "urn:ebay:apis:eBLBaseComponents"

class EbayActiveListingsScanner:
    """
    Uses eBay Trading API → GetMyeBaySelling to fetch all active listings.
    Also calls GetItem for each listing to get view counts (HitCount).
    """

    def __init__(self):
        env = os.environ.get("EBAY_ENVIRONMENT", "sandbox").lower()
        if env == "production":
            self.api_url = "https://api.ebay.com/ws/api.dll"
        else:
            self.api_url = "https://api.sandbox.ebay.com/ws/api.dll"

        self.app_id   = os.environ.get("EBAY_APP_ID", "")
        self.dev_id   = os.environ.get("EBAY_DEV_ID", "")
        self.cert_id  = os.environ.get("EBAY_CERT_ID", "")
        self.token    = os.environ.get("EBAY_USER_TOKEN", "")

        if not self.token:
            raise RuntimeError(
                "EBAY_USER_TOKEN not set. Run: python get_ebay_token.py"
            )

    def _headers(self, call_name: str) -> dict:
        return {
            "X-EBAY-API-SITEID":       "0",
            "X-EBAY-API-COMPATIBILITY-LEVEL": "967",
            "X-EBAY-API-CALL-NAME":    call_name,
            "X-EBAY-API-APP-NAME":     self.app_id,
            "X-EBAY-API-DEV-NAME":     self.dev_id,
            "X-EBAY-API-CERT-NAME":    self.cert_id,
            "Content-Type":            "text/xml",
        }

    def _post(self, call_name: str, body_xml: str) -> ET.Element:
        xml = f"""<?xml version="1.0" encoding="utf-8"?>
<{call_name}Request xmlns="{NS}">
  <RequesterCredentials>
    <eBayAuthToken>{self.token}</eBayAuthToken>
  </RequesterCredentials>
  {body_xml}
</{call_name}Request>"""

        resp = requests.post(
            self.api_url,
            data=xml.encode("utf-8"),
            headers=self._headers(call_name),
            timeout=30,
        )
        resp.raise_for_status()
        root = ET.fromstring(resp.content)

        # Check for API-level errors
        ack = _xml_text(root, "Ack", NS)
        if ack not in ("Success", "Warning"):
            errors = root.findall(f"{{{NS}}}Errors")
            msg = "; ".join(
                _xml_text(e, "LongMessage", NS) or _xml_text(e, "ShortMessage", NS)
                for e in errors
            )
            raise RuntimeError(f"eBay API error ({call_name}): {msg}")

        return root

    # ── GetMyeBaySelling ──────────────────────────────────────────────────────

    def get_active_listings(self, page_size: int = 200) -> list[ActiveListing]:
        """Fetch all active listings using pagination."""
        all_listings: list[ActiveListing] = []
        page = 1

        while True:
            body = f"""
  <ActiveList>
    <Include>true</Include>
    <Pagination>
      <EntriesPerPage>{page_size}</EntriesPerPage>
      <PageNumber>{page}</PageNumber>
    </Pagination>
    <Sort>TimeLeft</Sort>
  </ActiveList>
  <DetailLevel>ReturnAll</DetailLevel>
"""
            root = self._post("GetMyeBaySelling", body)

            active_list = root.find(f"{{{NS}}}ActiveList")
            if active_list is None:
                break

            items_array = active_list.find(f"{{{NS}}}ItemArray")
            if items_array is None:
                break

            items = items_array.findall(f"{{{NS}}}Item")
            if not items:
                break

            for item in items:
                listing = self._parse_item(item)
                all_listings.append(listing)

            # Pagination check
            pagination = active_list.find(f"{{{NS}}}PaginationResult")
            if pagination is not None:
                total_pages = _xml_int(pagination, "TotalNumberOfPages", NS)
                if page >= total_pages:
                    break
            else:
                break

            page += 1

        return all_listings

    def _parse_item(self, item: ET.Element) -> ActiveListing:
        item_id = _xml_text(item, "ItemID", NS)
        title   = _xml_text(item, "Title", NS)

        # Price
        selling_status = item.find(f"{{{NS}}}SellingStatus")
        price     = 0.0
        currency  = "USD"
        qty_sold  = 0
        if selling_status is not None:
            current_price = selling_status.find(f"{{{NS}}}CurrentPrice")
            if current_price is not None:
                price    = float(current_price.text or 0)
                currency = current_price.get("currencyID", "USD")
            qty_sold = _xml_int(selling_status, "QuantitySold", NS)

        # Quantity
        quantity = _xml_int(item, "Quantity", NS)

        # Watchers
        watchers = _xml_int(item, "WatchCount", NS)

        # Views (HitCount) — may be 0 here, enriched by get_item_details
        views = _xml_int(item, "HitCount", NS)

        # Time left
        time_left = _xml_text(item, "TimeLeft", NS)
        time_left_human = _parse_iso_duration(time_left)

        # End time
        end_time_str = _xml_text(item, "EndTime", NS)
        end_time = _parse_datetime(end_time_str)

        # Listing URL
        listing_url = _xml_text(item, "ViewItemURL", NS)
        if not listing_url:
            listing_url = f"https://www.ebay.com/itm/{item_id}"

        # Image
        picture_details = item.find(f"{{{NS}}}PictureDetails")
        image_url = ""
        if picture_details is not None:
            image_url = _xml_text(picture_details, "GalleryURL", NS)

        # Condition
        condition = _xml_text(item, "ConditionDisplayName", NS)

        return ActiveListing(
            item_id=item_id,
            title=title,
            price=price,
            currency=currency,
            quantity=quantity,
            quantity_sold=qty_sold,
            watchers=watchers,
            views=views,
            status="Active",
            time_left=time_left,
            time_left_human=time_left_human,
            end_time=end_time,
            listing_url=listing_url,
            image_url=image_url,
            condition=condition,
        )

    # ── GetItem — enriches with HitCount ─────────────────────────────────────

    def enrich_with_views(self, listings: list[ActiveListing]) -> list[ActiveListing]:
        """
        Call GetItem for each listing to get accurate HitCount (views).
        Note: HitCount is only available if the seller enabled it in their account.
        This is done in batches to avoid rate limits.
        """
        for listing in listings:
            try:
                body = f"""
  <ItemID>{listing.item_id}</ItemID>
  <DetailLevel>ReturnAll</DetailLevel>
  <IncludeWatchCount>true</IncludeWatchCount>
"""
                root = self._post("GetItem", body)
                item = root.find(f"{{{NS}}}Item")
                if item is not None:
                    listing.views    = _xml_int(item, "HitCount", NS)
                    listing.watchers = _xml_int(item, "WatchCount", NS)
            except Exception:
                pass  # Keep existing values if enrichment fails

        return listings

    # ── Main entry point ──────────────────────────────────────────────────────

    def scan(self, enrich_views: bool = True) -> list[ActiveListing]:
        """
        Full scan: fetch all active listings + optionally enrich with view counts.
        Returns list sorted by watchers descending (most-watched first).
        """
        listings = self.get_active_listings()

        if enrich_views and listings:
            listings = self.enrich_with_views(listings)

        # Sort: ending soon first, then by watchers
        listings.sort(key=lambda x: (not x.is_ending_soon, -x.watchers))
        return listings


# ─────────────────────────────────────────────────────────────────────────────
# Quick CLI test
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    scanner = EbayActiveListingsScanner()
    print("Scanning active listings…")
    listings = scanner.scan(enrich_views=False)  # Set True for view counts (slower)

    if not listings:
        print("No active listings found.")
    else:
        print(f"\nFound {len(listings)} active listing(s):\n")
        print(f"{'#':<4} {'Title':<45} {'Price':>8} {'Watch':>6} {'Views':>6} {'Time Left':<12} {'URL'}")
        print("─" * 110)
        for i, l in enumerate(listings, 1):
            title = l.title[:43] + "…" if len(l.title) > 44 else l.title
            print(f"{i:<4} {title:<45} ${l.price:>7.2f} {l.watchers:>6} {l.views:>6} {l.time_left_human:<12} {l.listing_url}")
