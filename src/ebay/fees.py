"""
eBay Fee Engine
===============
Real eBay Final Value Fees (FVF) by category, as of 2024/2025.
Source: https://www.ebay.com/help/selling/fees-credits-invoices/selling-fees?id=4822

FVF is calculated on the TOTAL amount of the sale:
  item price + shipping charged to buyer + sales tax collected.

Promoted Listings (General) fee is charged only when a sale is made
after a click within the attribution window.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# eBay Final Value Fee table (percentage + fixed per-order fee)
# Format: (rate_up_to_7500, rate_above_7500, fixed_fee_per_order)
# ─────────────────────────────────────────────────────────────────────────────
EBAY_FVF_TABLE: dict[str, tuple[float, float, float]] = {
    # Category name                          : (rate%, rate_above_7500%, fixed_fee)
    "Books & Magazines":                       (14.95, 2.35, 0.30),
    "Business & Industrial":                   (11.70, 2.35, 0.30),
    "Clothing, Shoes & Accessories":           (15.00, 9.00, 0.30),
    "Coins & Paper Money":                     (13.25, 2.35, 0.30),
    "Collectibles":                            (13.25, 2.35, 0.30),
    "Consumer Electronics":                    (13.25, 2.35, 0.30),
    "Crafts":                                  (13.25, 2.35, 0.30),
    "Dolls & Bears":                           (13.25, 2.35, 0.30),
    "DVDs & Movies":                           (14.95, 2.35, 0.30),
    "eBay Motors - Parts & Accessories":       (10.00, 2.35, 0.30),
    "eBay Motors - Passenger Vehicles":        (3.00,  3.00, 0.00),  # flat $75 max
    "Entertainment Memorabilia":               (13.25, 2.35, 0.30),
    "Gift Cards & Coupons":                    (13.25, 2.35, 0.30),
    "Health & Beauty":                         (13.25, 2.35, 0.30),
    "Home & Garden":                           (13.25, 2.35, 0.30),
    "Jewelry & Watches":                       (15.00, 6.50, 0.30),
    "Music":                                   (14.95, 2.35, 0.30),
    "Musical Instruments & Gear":              (6.35,  2.35, 0.30),
    "Pet Supplies":                            (13.25, 2.35, 0.30),
    "Pottery & Glass":                         (13.25, 2.35, 0.30),
    "Real Estate":                             (1.00,  1.00, 0.00),
    "Specialty Services":                      (15.00, 2.35, 0.30),
    "Sporting Goods":                          (13.25, 2.35, 0.30),
    "Sports Mem, Cards & Fan Shop":            (13.25, 2.35, 0.30),
    "Stamps":                                  (13.25, 2.35, 0.30),
    "Tickets & Experiences":                   (13.25, 2.35, 0.30),
    "Toys & Hobbies":                          (13.25, 2.35, 0.30),
    "Travel":                                  (11.00, 2.35, 0.30),
    "Video Games & Consoles":                  (13.25, 2.35, 0.30),
    # Default fallback
    "Everything Else":                         (13.25, 2.35, 0.30),
}

# US state sales tax rates (approximate averages, 2024)
# eBay collects and remits marketplace facilitator tax in all US states.
# The seller does NOT pay this — the buyer pays it — but it IS included
# in the FVF base. We model it here for accurate FVF calculation.
US_STATE_TAX_RATES: dict[str, float] = {
    "AL": 0.09, "AK": 0.00, "AZ": 0.084, "AR": 0.095, "CA": 0.0875,
    "CO": 0.077, "CT": 0.0635, "DE": 0.00, "FL": 0.07, "GA": 0.072,
    "HI": 0.045, "ID": 0.06, "IL": 0.0875, "IN": 0.07, "IA": 0.07,
    "KS": 0.087, "KY": 0.06, "LA": 0.0952, "ME": 0.055, "MD": 0.06,
    "MA": 0.0625, "MI": 0.06, "MN": 0.0888, "MS": 0.07, "MO": 0.082,
    "MT": 0.00, "NE": 0.069, "NV": 0.082, "NH": 0.00, "NJ": 0.066,
    "NM": 0.076, "NY": 0.08, "NC": 0.0698, "ND": 0.0696, "OH": 0.072,
    "OK": 0.0898, "OR": 0.00, "PA": 0.06, "RI": 0.07, "SC": 0.075,
    "SD": 0.064, "TN": 0.0955, "TX": 0.0825, "UT": 0.072, "VT": 0.062,
    "VA": 0.057, "WA": 0.0986, "WV": 0.065, "WI": 0.054, "WY": 0.054,
    "DC": 0.06,
}


@dataclass
class FeeBreakdown:
    """Full breakdown of all fees and costs for one product."""
    # Inputs
    sale_price: float
    source_cost: float
    shipping_to_buyer: float = 0.0
    shipping_to_self: float = 0.0          # inbound / prep cost
    packaging_cost: float = 0.30
    category: str = "Everything Else"
    promoted_listing_rate: float = 0.07    # 7% default
    buyer_state: str = "TX"                # used for FVF base calc
    return_reserve_pct: float = 0.02       # 2% reserve for returns
    payment_fee_pct: float = 0.0           # Payoneer/PayPal if applicable
    cashback_expected: float = 0.0         # from cashback engine

    # Computed outputs (filled by calculate())
    sales_tax_on_sale: float = field(init=False, default=0.0)
    fvf_base: float = field(init=False, default=0.0)
    final_value_fee: float = field(init=False, default=0.0)
    promoted_listing_fee: float = field(init=False, default=0.0)
    return_reserve: float = field(init=False, default=0.0)
    payment_fee: float = field(init=False, default=0.0)
    total_fees: float = field(init=False, default=0.0)
    total_costs: float = field(init=False, default=0.0)
    gross_profit: float = field(init=False, default=0.0)
    net_profit_before_cashback: float = field(init=False, default=0.0)
    net_profit_after_cashback: float = field(init=False, default=0.0)
    net_margin_before_cashback: float = field(init=False, default=0.0)
    net_margin_after_cashback: float = field(init=False, default=0.0)
    decision: str = field(init=False, default="")

    def __post_init__(self):
        self.calculate()

    def calculate(self):
        """Run all fee and profit calculations."""
        tax_rate = US_STATE_TAX_RATES.get(self.buyer_state, 0.08)
        self.sales_tax_on_sale = round(self.sale_price * tax_rate, 4)

        # FVF base = item price + shipping charged + sales tax
        self.fvf_base = self.sale_price + self.shipping_to_buyer + self.sales_tax_on_sale

        # Look up FVF rate
        rate_low, rate_high, fixed = EBAY_FVF_TABLE.get(
            self.category, EBAY_FVF_TABLE["Everything Else"]
        )
        if self.fvf_base <= 7500:
            fvf_rate = rate_low / 100
        else:
            fvf_rate = rate_high / 100

        self.final_value_fee = round(self.fvf_base * fvf_rate + fixed, 4)
        self.promoted_listing_fee = round(
            self.sale_price * self.promoted_listing_rate, 4
        )
        self.return_reserve = round(self.sale_price * self.return_reserve_pct, 4)
        self.payment_fee = round(self.sale_price * self.payment_fee_pct, 4)

        self.total_fees = round(
            self.final_value_fee
            + self.promoted_listing_fee
            + self.return_reserve
            + self.payment_fee,
            4,
        )
        self.total_costs = round(
            self.source_cost
            + self.shipping_to_self
            + self.packaging_cost
            + self.total_fees,
            4,
        )

        self.gross_profit = round(self.sale_price - self.source_cost, 4)
        self.net_profit_before_cashback = round(
            self.sale_price - self.total_costs, 4
        )
        self.net_profit_after_cashback = round(
            self.net_profit_before_cashback + self.cashback_expected, 4
        )

        if self.sale_price > 0:
            self.net_margin_before_cashback = round(
                self.net_profit_before_cashback / self.sale_price * 100, 2
            )
            self.net_margin_after_cashback = round(
                self.net_profit_after_cashback / self.sale_price * 100, 2
            )

        # Decision logic
        if self.net_profit_before_cashback < 0:
            self.decision = "❌ REJECT — Loss before cashback"
        elif self.net_margin_before_cashback < 12:
            self.decision = "⚠️ MONITOR — Margin < 12%"
        elif self.net_profit_before_cashback < 3:
            self.decision = "⚠️ MONITOR — Profit < $3"
        elif self.net_margin_before_cashback >= 20:
            self.decision = "✅ APPROVE — Strong margin"
        else:
            self.decision = "🔵 TEST — Acceptable margin"

    def to_dict(self) -> dict:
        return {
            "Sale Price": f"${self.sale_price:.2f}",
            "Source Cost": f"${self.source_cost:.2f}",
            "Shipping (outbound)": f"${self.shipping_to_buyer:.2f}",
            "Shipping / Prep (inbound)": f"${self.shipping_to_self:.2f}",
            "Sales Tax on Sale (FVF base)": f"${self.sales_tax_on_sale:.2f}",
            "eBay Final Value Fee": f"${self.final_value_fee:.2f}",
            "Promoted Listing Fee": f"${self.promoted_listing_fee:.2f}",
            "Return Reserve (2%)": f"${self.return_reserve:.2f}",
            "Payment Fee": f"${self.payment_fee:.2f}",
            "Packaging / Prep": f"${self.packaging_cost:.2f}",
            "─── Total Fees": f"${self.total_fees:.2f}",
            "─── Total Costs": f"${self.total_costs:.2f}",
            "Net Profit (before cashback)": f"${self.net_profit_before_cashback:.2f}",
            "Net Margin (before cashback)": f"{self.net_margin_before_cashback:.1f}%",
            "Expected Cashback": f"${self.cashback_expected:.2f}",
            "Net Profit (after cashback)": f"${self.net_profit_after_cashback:.2f}",
            "Net Margin (after cashback)": f"{self.net_margin_after_cashback:.1f}%",
            "Decision": self.decision,
        }


def get_categories() -> list[str]:
    """Return sorted list of all eBay categories."""
    return sorted(EBAY_FVF_TABLE.keys())


def calculate_profit(
    sale_price: float,
    source_cost: float,
    category: str = "Everything Else",
    shipping_to_buyer: float = 0.0,
    shipping_to_self: float = 0.0,
    packaging_cost: float = 0.30,
    promoted_listing_rate: float = 0.07,
    buyer_state: str = "TX",
    return_reserve_pct: float = 0.02,
    cashback_expected: float = 0.0,
) -> FeeBreakdown:
    """Convenience wrapper — returns a full FeeBreakdown."""
    return FeeBreakdown(
        sale_price=sale_price,
        source_cost=source_cost,
        shipping_to_buyer=shipping_to_buyer,
        shipping_to_self=shipping_to_self,
        packaging_cost=packaging_cost,
        category=category,
        promoted_listing_rate=promoted_listing_rate,
        buyer_state=buyer_state,
        return_reserve_pct=return_reserve_pct,
        cashback_expected=cashback_expected,
    )
