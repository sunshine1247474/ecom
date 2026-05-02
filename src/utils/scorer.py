"""
Product Scorer
==============
Scores a product candidate on 5 dimensions and produces a final score
and decision (APPROVE / TEST / MONITOR / REJECT).

Scoring weights:
  margin_score      × 30
  demand_score      × 25
  competition_score × 15
  shipping_score    × 15
  risk_score        × 15  (subtracted)

Final score range: 0 – 100
  80+    → APPROVE
  60–79  → TEST
  40–59  → MONITOR
  <40    → REJECT
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass
class ScoreInput:
    # Margin
    net_margin_before_cashback: float   # percentage, e.g. 18.5

    # Demand (estimated monthly sold units on eBay)
    monthly_sold_estimate: int          # e.g. 25

    # Competition (number of active eBay listings for same keyword)
    active_listing_count: int           # e.g. 120

    # Shipping (weight in lbs)
    weight_lbs: float                   # e.g. 1.2

    # Risk flags
    is_branded: bool = False            # known brand / VeRO risk
    is_fragile: bool = False
    is_hazmat: bool = False
    is_regulated: bool = False          # medical, baby safety, etc.
    return_rate_high: bool = False      # category known for high returns


@dataclass
class ScoreResult:
    margin_score: int
    demand_score: int
    competition_score: int
    shipping_score: int
    risk_score: int
    final_score: float
    decision: str
    reason: str


def score_product(inp: ScoreInput) -> ScoreResult:
    # ── Margin score (1–5) ───────────────────────────────────────────────────
    m = inp.net_margin_before_cashback
    if m >= 25:
        margin_score = 5
    elif m >= 20:
        margin_score = 4
    elif m >= 15:
        margin_score = 3
    elif m >= 12:
        margin_score = 2
    elif m >= 8:
        margin_score = 1
    else:
        margin_score = 0

    # ── Demand score (1–5) ───────────────────────────────────────────────────
    s = inp.monthly_sold_estimate
    if s >= 100:
        demand_score = 5
    elif s >= 50:
        demand_score = 4
    elif s >= 20:
        demand_score = 3
    elif s >= 10:
        demand_score = 2
    elif s >= 3:
        demand_score = 1
    else:
        demand_score = 0

    # ── Competition score (1–5, fewer = better) ──────────────────────────────
    c = inp.active_listing_count
    if c <= 10:
        competition_score = 5
    elif c <= 30:
        competition_score = 4
    elif c <= 75:
        competition_score = 3
    elif c <= 150:
        competition_score = 2
    elif c <= 300:
        competition_score = 1
    else:
        competition_score = 0

    # ── Shipping score (1–5, lighter = better) ───────────────────────────────
    w = inp.weight_lbs
    if w <= 0.5:
        shipping_score = 5
    elif w <= 1.0:
        shipping_score = 4
    elif w <= 2.0:
        shipping_score = 3
    elif w <= 5.0:
        shipping_score = 2
    elif w <= 10.0:
        shipping_score = 1
    else:
        shipping_score = 0

    # ── Risk score (1–5, more risk = higher number = subtracted) ─────────────
    risk_points = 0
    if inp.is_branded:
        risk_points += 2
    if inp.is_fragile:
        risk_points += 1
    if inp.is_hazmat:
        risk_points += 3
    if inp.is_regulated:
        risk_points += 3
    if inp.return_rate_high:
        risk_points += 1
    risk_score = min(risk_points, 5)

    # ── Final score ──────────────────────────────────────────────────────────
    final_score = (
        margin_score * 30
        + demand_score * 25
        + competition_score * 15
        + shipping_score * 15
        - risk_score * 15
    )
    # Normalize to 0–100
    max_possible = 5 * (30 + 25 + 15 + 15)   # = 425
    final_score_pct = round(max(0, final_score) / max_possible * 100, 1)

    # ── Decision ─────────────────────────────────────────────────────────────
    reasons = []
    if margin_score == 0:
        reasons.append("margin below 8%")
    if demand_score == 0:
        reasons.append("very low demand")
    if inp.is_hazmat or inp.is_regulated:
        reasons.append("hazmat/regulated product")
    if inp.is_branded:
        reasons.append("brand/IP risk")

    if final_score_pct >= 80:
        decision = "✅ APPROVE"
        reason = "Strong across all dimensions."
    elif final_score_pct >= 60:
        decision = "🔵 TEST"
        reason = "Acceptable. Test with 2–5 units."
    elif final_score_pct >= 40:
        decision = "⚠️ MONITOR"
        reason = "Weak in: " + (", ".join(reasons) if reasons else "one or more areas") + "."
    else:
        decision = "❌ REJECT"
        reason = "Too risky or unprofitable: " + (", ".join(reasons) if reasons else "multiple issues") + "."

    return ScoreResult(
        margin_score=margin_score,
        demand_score=demand_score,
        competition_score=competition_score,
        shipping_score=shipping_score,
        risk_score=risk_score,
        final_score=final_score_pct,
        decision=decision,
        reason=reason,
    )
