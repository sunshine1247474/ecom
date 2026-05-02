"""
Cashback Engine
===============
Models cashback/rebate programs realistically.

Key principle: cashback is NOT guaranteed. The engine calculates
an "expected value" by multiplying the advertised rate by several
probability factors. The result is used as a BONUS only — never
as a required component of profitability.

Supported programs:
  - Rakuten (rakuten.com)
  - TopCashback
  - RebatesMe
  - Capital One Shopping
  - Honey / PayPal Rewards
  - Credit card rewards (Chase, Amex, Citi, etc.)
  - Discounted gift cards (Raise, CardCash) — modeled separately

Reference rates are approximate as of 2024/2025 and should be
verified before use. Rates change frequently.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Known cashback rates by program and retailer (approximate, 2024/2025)
# Format: program → { retailer: (advertised_rate, tracking_reliability) }
# tracking_reliability: probability that the click/purchase is tracked
# ─────────────────────────────────────────────────────────────────────────────
CASHBACK_RATES: dict[str, dict[str, tuple[float, float]]] = {
    "rakuten": {
        "walmart":     (0.04, 0.85),
        "target":      (0.03, 0.85),
        "homedepot":   (0.03, 0.82),
        "lowes":       (0.04, 0.82),
        "bestbuy":     (0.02, 0.80),
        "macys":       (0.06, 0.85),
        "kohls":       (0.05, 0.85),
        "ebay":        (0.01, 0.80),
        "default":     (0.02, 0.75),
    },
    "topcashback": {
        "walmart":     (0.05, 0.80),
        "target":      (0.04, 0.80),
        "homedepot":   (0.04, 0.78),
        "lowes":       (0.05, 0.78),
        "bestbuy":     (0.03, 0.78),
        "default":     (0.03, 0.72),
    },
    "rebatesme": {
        "walmart":     (0.04, 0.78),
        "target":      (0.03, 0.78),
        "default":     (0.02, 0.70),
    },
    "capital_one_shopping": {
        "walmart":     (0.03, 0.88),
        "target":      (0.02, 0.88),
        "homedepot":   (0.02, 0.85),
        "default":     (0.015, 0.82),
    },
}

# Merchant approval probability (probability that the retailer pays out
# after tracking — excludes reseller activity, coupon conflicts, etc.)
MERCHANT_APPROVAL_PROB: dict[str, float] = {
    "walmart":   0.82,
    "target":    0.80,
    "homedepot": 0.78,
    "lowes":     0.78,
    "bestbuy":   0.75,
    "default":   0.70,
}

# Non-return probability (cashback is reversed if item is returned)
NON_RETURN_PROB: dict[str, float] = {
    "home_organization": 0.94,
    "kitchen":           0.91,
    "electronics":       0.82,
    "clothing":          0.75,
    "default":           0.88,
}

# Credit card reward rates (cash back categories)
CREDIT_CARD_RATES: dict[str, dict[str, float]] = {
    "chase_freedom_flex": {
        "grocery":       0.05,
        "gas":           0.05,
        "restaurant":    0.03,
        "default":       0.01,
    },
    "amex_blue_cash_preferred": {
        "grocery":       0.06,
        "gas":           0.03,
        "streaming":     0.06,
        "default":       0.01,
    },
    "citi_double_cash": {
        "default":       0.02,
    },
    "paypal_cashback": {
        "default":       0.015,
    },
}

# Discounted gift card discount rates (Raise.com / CardCash averages, 2024)
GIFT_CARD_DISCOUNTS: dict[str, float] = {
    "walmart":   0.04,   # ~4% off face value
    "target":    0.05,
    "homedepot": 0.06,
    "lowes":     0.07,
    "bestbuy":   0.05,
    "default":   0.03,
}


@dataclass
class CashbackResult:
    retailer: str
    purchase_amount: float
    product_category: str

    # Per-program results
    program_results: list[dict] = field(default_factory=list)

    # Best single program
    best_program: str = ""
    best_expected_value: float = 0.0
    best_advertised_rate: float = 0.0

    # Gift card bonus
    gift_card_discount: float = 0.0
    gift_card_expected_savings: float = 0.0

    # Credit card bonus
    best_cc_program: str = ""
    cc_reward_rate: float = 0.0
    cc_expected_value: float = 0.0

    # Combined best scenario
    combined_expected_savings: float = 0.0
    combined_as_pct: float = 0.0


def calculate_cashback(
    purchase_amount: float,
    retailer: str,
    product_category: str = "default",
    include_gift_cards: bool = True,
    include_credit_cards: bool = True,
) -> CashbackResult:
    """
    Calculate expected cashback from all available programs for a purchase.

    Args:
        purchase_amount: The price you pay to the retailer.
        retailer: e.g. "walmart", "target", "homedepot"
        product_category: e.g. "home_organization", "electronics"
        include_gift_cards: Whether to model discounted gift card savings.
        include_credit_cards: Whether to model credit card rewards.

    Returns:
        CashbackResult with per-program breakdown and best combined scenario.
    """
    result = CashbackResult(
        retailer=retailer.lower(),
        purchase_amount=purchase_amount,
        product_category=product_category,
    )

    non_return = NON_RETURN_PROB.get(product_category, NON_RETURN_PROB["default"])
    merchant_approval = MERCHANT_APPROVAL_PROB.get(retailer.lower(), MERCHANT_APPROVAL_PROB["default"])

    # ── Portal cashback programs ──────────────────────────────────────────────
    best_ev = 0.0
    best_prog = ""
    best_adv = 0.0

    for program, retailers in CASHBACK_RATES.items():
        retailer_rates = retailers.get(retailer.lower(), retailers.get("default", (0, 0)))
        advertised_rate, tracking_prob = retailer_rates

        expected_value = round(
            purchase_amount
            * advertised_rate
            * tracking_prob
            * merchant_approval
            * non_return,
            4,
        )

        result.program_results.append({
            "program": program,
            "advertised_rate_pct": round(advertised_rate * 100, 2),
            "tracking_reliability": round(tracking_prob * 100, 1),
            "merchant_approval_pct": round(merchant_approval * 100, 1),
            "non_return_pct": round(non_return * 100, 1),
            "expected_value": expected_value,
            "expected_rate_pct": round(expected_value / purchase_amount * 100, 2) if purchase_amount else 0,
        })

        if expected_value > best_ev:
            best_ev = expected_value
            best_prog = program
            best_adv = advertised_rate

    result.best_program = best_prog
    result.best_expected_value = best_ev
    result.best_advertised_rate = best_adv

    # ── Gift card discount ────────────────────────────────────────────────────
    if include_gift_cards:
        gc_rate = GIFT_CARD_DISCOUNTS.get(retailer.lower(), GIFT_CARD_DISCOUNTS["default"])
        # Gift card discount is near-guaranteed (just buying at a discount)
        # but we apply a small fraud/availability risk factor of 0.92
        result.gift_card_discount = gc_rate
        result.gift_card_expected_savings = round(purchase_amount * gc_rate * 0.92, 4)

    # ── Credit card rewards ───────────────────────────────────────────────────
    if include_credit_cards:
        best_cc_ev = 0.0
        best_cc_prog = ""
        best_cc_rate = 0.0
        for cc_name, categories in CREDIT_CARD_RATES.items():
            rate = categories.get(product_category, categories.get("default", 0.01))
            ev = round(purchase_amount * rate, 4)
            if ev > best_cc_ev:
                best_cc_ev = ev
                best_cc_prog = cc_name
                best_cc_rate = rate
        result.best_cc_program = best_cc_prog
        result.cc_reward_rate = best_cc_rate
        result.cc_expected_value = best_cc_ev

    # ── Combined best scenario ────────────────────────────────────────────────
    # Portal cashback + gift card discount + credit card rewards
    # (gift card and portal cashback can usually be stacked)
    result.combined_expected_savings = round(
        result.best_expected_value
        + result.gift_card_expected_savings
        + result.cc_expected_value,
        4,
    )
    if purchase_amount > 0:
        result.combined_as_pct = round(
            result.combined_expected_savings / purchase_amount * 100, 2
        )

    return result


def cashback_summary(result: CashbackResult) -> str:
    """Return a human-readable summary of the cashback result."""
    lines = [
        f"Purchase: ${result.purchase_amount:.2f} at {result.retailer.title()}",
        f"",
        f"Best portal:      {result.best_program.replace('_',' ').title()} "
        f"— advertised {result.best_advertised_rate*100:.1f}%, "
        f"expected ${result.best_expected_value:.2f}",
        f"Gift card saving: ${result.gift_card_expected_savings:.2f} "
        f"({result.gift_card_discount*100:.1f}% off face value)",
        f"Credit card:      {result.best_cc_program.replace('_',' ').title()} "
        f"— {result.cc_reward_rate*100:.1f}%, expected ${result.cc_expected_value:.2f}",
        f"",
        f"Combined expected savings: ${result.combined_expected_savings:.2f} "
        f"({result.combined_as_pct:.1f}% of purchase)",
    ]
    return "\n".join(lines)
