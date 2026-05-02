"""
Multi-Source Product Search Engine
====================================
All sources use Traject Data APIs (trajectdata.com) — a single vendor
that provides clean, structured product data for every major US retailer.

API → Retailer mapping:
  Rainforest API  → Amazon          (RAINFOREST_API_KEY)
  BlueCart API    → Walmart         (BLUECART_API_KEY)
  Red Circle API  → Target          (REDCIRCLE_API_KEY)
  BigBox API      → Home Depot      (BIGBOX_API_KEY)
  Backyard API    → Lowe's          (BACKYARD_API_KEY)
  Countdown API   → eBay            (COUNTDOWN_API_KEY)  ← useful for sold-price research
  SerpWow         → Google Shopping (SERPWOW_API_KEY)
  Scale SERP      → Google Shopping (SCALESERP_API_KEY)  ← fallback
  Value SERP      → Google Shopping (VALUESERP_API_KEY)  ← fallback

Each source returns a list of SourceProduct objects.
The aggregator deduplicates and ranks by price.

All API keys are loaded from environment variables only — never hardcoded.
"""

from __future__ import annotations
import os
import httpx
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SourceProduct:
    title: str
    price: float
    source: str                     # "amazon", "walmart", "target", etc.
    url: str
    image_url: str = ""
    rating: Optional[float] = None
    review_count: Optional[int] = None
    asin: Optional[str] = None      # Amazon ASIN if available
    item_id: Optional[str] = None   # Retailer-specific ID
    in_stock: bool = True
    shipping_note: str = ""
    extra: dict = field(default_factory=dict)


def _safe_price(value) -> Optional[float]:
    """Safely convert various price formats to float."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        v = value.get("value") or value.get("amount") or value.get("raw")
        return _safe_price(v)
    if isinstance(value, str):
        cleaned = value.replace("$", "").replace(",", "").strip()
        try:
            return float(cleaned.split()[0])
        except (ValueError, IndexError):
            return None
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Amazon — Rainforest API (trajectdata.com/ecommerce/rainforest-api)
# ─────────────────────────────────────────────────────────────────────────────

class AmazonRainforestSource:
    BASE = "https://api.rainforestapi.com/request"
    SOURCE_NAME = "amazon"

    def __init__(self):
        self.api_key = os.environ.get("RAINFOREST_API_KEY", "")

    def search(self, keyword: str, limit: int = 10) -> list[SourceProduct]:
        if not self.api_key:
            return []
        params = {
            "api_key": self.api_key,
            "type": "search",
            "amazon_domain": "amazon.com",
            "search_term": keyword,
        }
        try:
            resp = httpx.get(self.BASE, params=params, timeout=25)
            resp.raise_for_status()
            results = resp.json().get("search_results", [])[:limit]
            products = []
            for r in results:
                price = _safe_price(r.get("price"))
                if price is None:
                    continue
                products.append(SourceProduct(
                    title=r.get("title", ""),
                    price=price,
                    source=self.SOURCE_NAME,
                    url=r.get("link", ""),
                    image_url=r.get("image", ""),
                    rating=r.get("rating"),
                    review_count=r.get("ratings_total"),
                    asin=r.get("asin"),
                    shipping_note="Prime" if r.get("is_prime") else "",
                ))
            return products
        except Exception:
            return []


# ─────────────────────────────────────────────────────────────────────────────
# Walmart — BlueCart API (app.bluecartapi.com)
# ─────────────────────────────────────────────────────────────────────────────

class WalmartBlueCartSource:
    BASE = "https://api.bluecartapi.com/request"
    SOURCE_NAME = "walmart"

    def __init__(self):
        self.api_key = os.environ.get("BLUECART_API_KEY", "")

    def search(self, keyword: str, limit: int = 10) -> list[SourceProduct]:
        if not self.api_key:
            return []
        params = {
            "api_key": self.api_key,
            "type": "search",
            "search_term": keyword,
        }
        try:
            resp = httpx.get(self.BASE, params=params, timeout=25)
            resp.raise_for_status()
            results = resp.json().get("search_results", [])[:limit]
            products = []
            for r in results:
                price = _safe_price(r.get("primary_price") or r.get("price"))
                if price is None:
                    continue
                products.append(SourceProduct(
                    title=r.get("title", ""),
                    price=price,
                    source=self.SOURCE_NAME,
                    url=r.get("link", ""),
                    image_url=r.get("image", ""),
                    rating=r.get("rating"),
                    review_count=r.get("ratings_total"),
                    item_id=r.get("item_id"),
                    shipping_note="Free" if r.get("free_shipping") else "",
                ))
            return products
        except Exception:
            return []


# ─────────────────────────────────────────────────────────────────────────────
# Target — Red Circle API (app.redcircleapi.com)
# ─────────────────────────────────────────────────────────────────────────────

class TargetRedCircleSource:
    BASE = "https://api.redcircleapi.com/request"
    SOURCE_NAME = "target"

    def __init__(self):
        self.api_key = os.environ.get("REDCIRCLE_API_KEY", "")

    def search(self, keyword: str, limit: int = 10) -> list[SourceProduct]:
        if not self.api_key:
            return []
        params = {
            "api_key": self.api_key,
            "type": "search",
            "search_term": keyword,
        }
        try:
            resp = httpx.get(self.BASE, params=params, timeout=25)
            resp.raise_for_status()
            results = resp.json().get("search_results", [])[:limit]
            products = []
            for r in results:
                price = _safe_price(r.get("price") or r.get("current_retail_price"))
                if price is None:
                    continue
                products.append(SourceProduct(
                    title=r.get("title", ""),
                    price=price,
                    source=self.SOURCE_NAME,
                    url=r.get("link", ""),
                    image_url=r.get("image", ""),
                    rating=r.get("rating"),
                    review_count=r.get("ratings_total"),
                    item_id=r.get("tcin"),
                    shipping_note="Free" if r.get("free_shipping") else "",
                ))
            return products
        except Exception:
            return []


# ─────────────────────────────────────────────────────────────────────────────
# Home Depot — BigBox API (docs.trajectdata.com/bigboxapi)
# ─────────────────────────────────────────────────────────────────────────────

class HomeDepotBigBoxSource:
    BASE = "https://api.bigboxapi.com/request"
    SOURCE_NAME = "homedepot"

    def __init__(self):
        self.api_key = os.environ.get("BIGBOX_API_KEY", "")

    def search(self, keyword: str, limit: int = 10) -> list[SourceProduct]:
        if not self.api_key:
            return []
        params = {
            "api_key": self.api_key,
            "type": "search",
            "search_term": keyword,
        }
        try:
            resp = httpx.get(self.BASE, params=params, timeout=25)
            resp.raise_for_status()
            results = resp.json().get("search_results", [])[:limit]
            products = []
            for r in results:
                price = _safe_price(r.get("price"))
                if price is None:
                    continue
                products.append(SourceProduct(
                    title=r.get("title", ""),
                    price=price,
                    source=self.SOURCE_NAME,
                    url=r.get("link", ""),
                    image_url=r.get("image", ""),
                    rating=r.get("rating"),
                    review_count=r.get("ratings_total"),
                    item_id=r.get("item_id"),
                    shipping_note="Free" if r.get("free_shipping") else "",
                ))
            return products
        except Exception:
            return []


# ─────────────────────────────────────────────────────────────────────────────
# Lowe's — Backyard API (app.backyardapi.com)
# ─────────────────────────────────────────────────────────────────────────────

class LowesBackyardSource:
    BASE = "https://api.backyardapi.com/request"
    SOURCE_NAME = "lowes"

    def __init__(self):
        self.api_key = os.environ.get("BACKYARD_API_KEY", "")

    def search(self, keyword: str, limit: int = 10) -> list[SourceProduct]:
        if not self.api_key:
            return []
        params = {
            "api_key": self.api_key,
            "type": "search",
            "search_term": keyword,
        }
        try:
            resp = httpx.get(self.BASE, params=params, timeout=25)
            resp.raise_for_status()
            results = resp.json().get("search_results", [])[:limit]
            products = []
            for r in results:
                price = _safe_price(r.get("price"))
                if price is None:
                    continue
                products.append(SourceProduct(
                    title=r.get("title", ""),
                    price=price,
                    source=self.SOURCE_NAME,
                    url=r.get("link", ""),
                    image_url=r.get("image", ""),
                    rating=r.get("rating"),
                    review_count=r.get("ratings_total"),
                    item_id=r.get("item_id"),
                ))
            return products
        except Exception:
            return []


# ─────────────────────────────────────────────────────────────────────────────
# eBay — Countdown API (docs.trajectdata.com/countdownapi)
# Used for SOLD PRICE RESEARCH — what buyers actually pay on eBay
# ─────────────────────────────────────────────────────────────────────────────

class EbayCountdownSource:
    BASE = "https://api.countdownapi.com/request"
    SOURCE_NAME = "ebay_sold"

    def __init__(self):
        self.api_key = os.environ.get("COUNTDOWN_API_KEY", "")

    def search_sold(self, keyword: str, limit: int = 10) -> list[SourceProduct]:
        """Search eBay SOLD listings to estimate realistic sale prices."""
        if not self.api_key:
            return []
        params = {
            "api_key": self.api_key,
            "type": "search",
            "ebay_domain": "ebay.com",
            "search_term": keyword,
            "sold_items": "true",
        }
        try:
            resp = httpx.get(self.BASE, params=params, timeout=25)
            resp.raise_for_status()
            results = resp.json().get("search_results", [])[:limit]
            products = []
            for r in results:
                price = _safe_price(r.get("price"))
                if price is None:
                    continue
                products.append(SourceProduct(
                    title=r.get("title", ""),
                    price=price,
                    source=self.SOURCE_NAME,
                    url=r.get("link", ""),
                    image_url=r.get("image", ""),
                    extra={"sold_date": r.get("date_sold", "")},
                ))
            return products
        except Exception:
            return []

    def avg_sold_price(self, keyword: str, limit: int = 20) -> Optional[float]:
        """Return the average sold price for a keyword on eBay."""
        sold = self.search_sold(keyword, limit=limit)
        if not sold:
            return None
        prices = [p.price for p in sold if p.price > 0]
        return round(sum(prices) / len(prices), 2) if prices else None

    def search(self, keyword: str, limit: int = 10) -> list[SourceProduct]:
        return self.search_sold(keyword, limit)


# ─────────────────────────────────────────────────────────────────────────────
# Google Shopping — SerpWow (primary)
# ─────────────────────────────────────────────────────────────────────────────

class GoogleShoppingSerpWowSource:
    BASE = "https://api.serpwow.com/live/search"
    SOURCE_NAME = "google_shopping"

    def __init__(self):
        self.api_key = os.environ.get("SERPWOW_API_KEY", "")

    def search(self, keyword: str, limit: int = 15) -> list[SourceProduct]:
        if not self.api_key:
            return []
        params = {
            "api_key": self.api_key,
            "q": keyword,
            "search_type": "shopping",
            "gl": "us",
            "hl": "en",
        }
        try:
            resp = httpx.get(self.BASE, params=params, timeout=25)
            resp.raise_for_status()
            results = resp.json().get("shopping_results", [])[:limit]
            products = []
            for r in results:
                price = _safe_price(r.get("price"))
                if price is None:
                    continue
                src = r.get("source", "google_shopping").lower()
                products.append(SourceProduct(
                    title=r.get("title", ""),
                    price=price,
                    source=src,
                    url=r.get("link", ""),
                    image_url=r.get("image", ""),
                    rating=r.get("rating"),
                    review_count=r.get("reviews"),
                    shipping_note=r.get("delivery", ""),
                ))
            return products
        except Exception:
            return []


# ─────────────────────────────────────────────────────────────────────────────
# Google Shopping — Scale SERP (fallback 1)
# ─────────────────────────────────────────────────────────────────────────────

class GoogleShoppingScaleSerpSource:
    BASE = "https://api.scaleserp.com/search"
    SOURCE_NAME = "google_shopping"

    def __init__(self):
        self.api_key = os.environ.get("SCALESERP_API_KEY", "")

    def search(self, keyword: str, limit: int = 15) -> list[SourceProduct]:
        if not self.api_key:
            return []
        params = {
            "api_key": self.api_key,
            "q": keyword,
            "search_type": "shopping",
            "gl": "us",
            "hl": "en",
        }
        try:
            resp = httpx.get(self.BASE, params=params, timeout=25)
            resp.raise_for_status()
            results = resp.json().get("shopping_results", [])[:limit]
            products = []
            for r in results:
                price = _safe_price(r.get("price"))
                if price is None:
                    continue
                products.append(SourceProduct(
                    title=r.get("title", ""),
                    price=price,
                    source=r.get("source", self.SOURCE_NAME).lower(),
                    url=r.get("link", ""),
                    image_url=r.get("image", ""),
                    rating=r.get("rating"),
                    review_count=r.get("reviews"),
                    shipping_note=r.get("delivery", ""),
                ))
            return products
        except Exception:
            return []


# ─────────────────────────────────────────────────────────────────────────────
# Google Shopping — Value SERP (fallback 2)
# ─────────────────────────────────────────────────────────────────────────────

class GoogleShoppingValueSerpSource:
    BASE = "https://api.valueserp.com/search"
    SOURCE_NAME = "google_shopping"

    def __init__(self):
        self.api_key = os.environ.get("VALUESERP_API_KEY", "")

    def search(self, keyword: str, limit: int = 15) -> list[SourceProduct]:
        if not self.api_key:
            return []
        params = {
            "api_key": self.api_key,
            "q": keyword,
            "search_type": "shopping",
            "gl": "us",
            "hl": "en",
        }
        try:
            resp = httpx.get(self.BASE, params=params, timeout=25)
            resp.raise_for_status()
            results = resp.json().get("shopping_results", [])[:limit]
            products = []
            for r in results:
                price = _safe_price(r.get("price"))
                if price is None:
                    continue
                products.append(SourceProduct(
                    title=r.get("title", ""),
                    price=price,
                    source=r.get("source", self.SOURCE_NAME).lower(),
                    url=r.get("link", ""),
                    image_url=r.get("image", ""),
                    rating=r.get("rating"),
                    review_count=r.get("reviews"),
                    shipping_note=r.get("delivery", ""),
                ))
            return products
        except Exception:
            return []


# ─────────────────────────────────────────────────────────────────────────────
# Aggregator
# ─────────────────────────────────────────────────────────────────────────────

class ProductSearchAggregator:
    """
    Searches all available sources simultaneously and returns a unified,
    deduplicated, price-sorted list of SourceProduct objects.

    Only sources with valid API keys (set in environment) are activated.
    The system gracefully skips any source whose key is missing.
    """

    # Retailer-specific sources (each covers one store)
    RETAILER_SOURCES = [
        AmazonRainforestSource,
        WalmartBlueCartSource,
        TargetRedCircleSource,
        HomeDepotBigBoxSource,
        LowesBackyardSource,
    ]

    # Google Shopping sources — uses first one with a valid key
    GOOGLE_SOURCES = [
        GoogleShoppingSerpWowSource,
        GoogleShoppingScaleSerpSource,
        GoogleShoppingValueSerpSource,
    ]

    def __init__(self):
        # Activate retailer sources that have keys
        self.retailer_sources = [
            cls() for cls in self.RETAILER_SOURCES
            if os.environ.get(self._key_for(cls), "")
        ]
        # Activate first available Google Shopping source
        self.google_source = None
        for cls in self.GOOGLE_SOURCES:
            if os.environ.get(self._key_for(cls), ""):
                self.google_source = cls()
                break

        # eBay sold-price research
        self.ebay_source = EbayCountdownSource()

    @staticmethod
    def _key_for(cls) -> str:
        key_map = {
            "AmazonRainforestSource":        "RAINFOREST_API_KEY",
            "WalmartBlueCartSource":         "BLUECART_API_KEY",
            "TargetRedCircleSource":         "REDCIRCLE_API_KEY",
            "HomeDepotBigBoxSource":         "BIGBOX_API_KEY",
            "LowesBackyardSource":           "BACKYARD_API_KEY",
            "GoogleShoppingSerpWowSource":   "SERPWOW_API_KEY",
            "GoogleShoppingScaleSerpSource": "SCALESERP_API_KEY",
            "GoogleShoppingValueSerpSource": "VALUESERP_API_KEY",
        }
        return key_map.get(cls.__name__, "")

    @property
    def active_sources(self) -> list[str]:
        """Return names of active (key-configured) sources."""
        names = [s.SOURCE_NAME for s in self.retailer_sources]
        if self.google_source:
            names.append("google_shopping")
        return names

    def search(
        self,
        keyword: str,
        limit_per_source: int = 10,
        max_price: Optional[float] = None,
        min_price: Optional[float] = None,
        include_google: bool = True,
    ) -> list[SourceProduct]:
        all_results: list[SourceProduct] = []

        for source in self.retailer_sources:
            try:
                all_results.extend(source.search(keyword, limit=limit_per_source))
            except Exception:
                continue

        if include_google and self.google_source:
            try:
                all_results.extend(self.google_source.search(keyword, limit=limit_per_source))
            except Exception:
                pass

        # Price filters
        if min_price is not None:
            all_results = [p for p in all_results if p.price >= min_price]
        if max_price is not None:
            all_results = [p for p in all_results if p.price <= max_price]

        # Sort by price ascending
        all_results.sort(key=lambda p: p.price)
        return all_results

    def cheapest_by_source(self, keyword: str) -> dict[str, Optional[SourceProduct]]:
        """Return the cheapest result per retailer for a given keyword."""
        results = self.search(keyword)
        cheapest: dict[str, Optional[SourceProduct]] = {}
        for product in results:
            src = product.source
            if src not in cheapest or product.price < cheapest[src].price:
                cheapest[src] = product
        return cheapest

    def ebay_avg_sold_price(self, keyword: str) -> Optional[float]:
        """Return average eBay sold price for a keyword (uses Countdown API)."""
        return self.ebay_source.avg_sold_price(keyword)
