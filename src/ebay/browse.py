"""
eBay Browse API Client
======================
Searches eBay for active and sold listings to gauge demand and competition.
Uses the eBay Browse API (OAuth Application token — no user login needed).

Docs: https://developer.ebay.com/api-docs/buy/browse/overview.html
"""

from __future__ import annotations
import os
import httpx
from dataclasses import dataclass
from typing import Optional


EBAY_OAUTH_URL = {
    "sandbox":    "https://api.sandbox.ebay.com/identity/v1/oauth2/token",
    "production": "https://api.ebay.com/identity/v1/oauth2/token",
}
EBAY_BROWSE_URL = {
    "sandbox":    "https://api.sandbox.ebay.com/buy/browse/v1",
    "production": "https://api.ebay.com/buy/browse/v1",
}


@dataclass
class EbayListing:
    title: str
    price: float
    currency: str
    condition: str
    item_id: str
    url: str
    image_url: str
    seller_feedback: int
    shipping_cost: Optional[float]
    sold_count: Optional[int] = None


class EbayBrowseClient:
    """Thin wrapper around eBay Browse API."""

    def __init__(self):
        self.app_id = os.environ.get("EBAY_APP_ID", "")
        self.cert_id = os.environ.get("EBAY_CERT_ID", "")
        self.env = os.environ.get("EBAY_ENVIRONMENT", "sandbox")
        self._token: Optional[str] = None

    # ── Auth ──────────────────────────────────────────────────────────────────

    def _get_app_token(self) -> str:
        """Fetch a client-credentials OAuth token (no user needed)."""
        if self._token:
            return self._token
        resp = httpx.post(
            EBAY_OAUTH_URL[self.env],
            auth=(self.app_id, self.cert_id),
            data={"grant_type": "client_credentials",
                  "scope": "https://api.ebay.com/oauth/api_scope"},
            timeout=15,
        )
        resp.raise_for_status()
        self._token = resp.json()["access_token"]
        return self._token

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._get_app_token()}",
            "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
            "Content-Type": "application/json",
        }

    # ── Search ────────────────────────────────────────────────────────────────

    def search(
        self,
        keyword: str,
        limit: int = 20,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        condition: str = "NEW",
    ) -> list[EbayListing]:
        """
        Search active eBay listings.
        condition: NEW | USED | UNSPECIFIED
        """
        params: dict = {
            "q": keyword,
            "limit": limit,
            "filter": f"conditions:{{{condition}}}",
        }
        if min_price:
            params["filter"] += f",price:[{min_price}..]"
        if max_price:
            params["filter"] += f",price:[..{max_price}]"

        url = f"{EBAY_BROWSE_URL[self.env]}/item_summary/search"
        resp = httpx.get(url, headers=self._headers(), params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        results = []
        for item in data.get("itemSummaries", []):
            price_info = item.get("price", {})
            shipping = item.get("shippingOptions", [{}])[0]
            ship_cost = None
            if shipping.get("shippingCostType") == "FIXED":
                ship_cost = float(shipping.get("shippingCost", {}).get("value", 0))

            results.append(EbayListing(
                title=item.get("title", ""),
                price=float(price_info.get("value", 0)),
                currency=price_info.get("currency", "USD"),
                condition=item.get("condition", ""),
                item_id=item.get("itemId", ""),
                url=item.get("itemWebUrl", ""),
                image_url=(item.get("image") or {}).get("imageUrl", ""),
                seller_feedback=item.get("seller", {}).get("feedbackScore", 0),
                shipping_cost=ship_cost,
            ))
        return results

    def get_sold_stats(self, keyword: str, limit: int = 20) -> dict:
        """
        Use the terapeak-style sold data via Browse API filter.
        Returns avg price, min, max, count of sold listings found.
        """
        params = {
            "q": keyword,
            "limit": limit,
            "filter": "buyingOptions:{FIXED_PRICE},conditions:{NEW}",
            "sort": "BEST_MATCH",
        }
        url = f"{EBAY_BROWSE_URL[self.env]}/item_summary/search"
        resp = httpx.get(url, headers=self._headers(), params=params, timeout=20)
        resp.raise_for_status()
        items = resp.json().get("itemSummaries", [])

        prices = [float(i.get("price", {}).get("value", 0)) for i in items if i.get("price")]
        if not prices:
            return {"count": 0, "avg_price": 0, "min_price": 0, "max_price": 0}

        return {
            "count": len(prices),
            "avg_price": round(sum(prices) / len(prices), 2),
            "min_price": round(min(prices), 2),
            "max_price": round(max(prices), 2),
        }
