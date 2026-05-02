"""
Profit Calculator Page
======================
Interactive calculator with real eBay fee tables by category.
"""

import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.ebay.fees import calculate_profit, get_categories, US_STATE_TAX_RATES
from src.cashback.engine import calculate_cashback
from src.utils.scorer import score_product, ScoreInput
from src.utils.database import upsert_product
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(page_title="Profit Calculator", page_icon="🧮", layout="wide")
st.title("🧮 Profit Calculator")
st.markdown("Enter product details to calculate exact eBay profit with real fee tables.")

# ── Input form ────────────────────────────────────────────────────────────────
with st.form("calc_form"):
    st.subheader("Product Details")
    c1, c2 = st.columns(2)

    with c1:
        title = st.text_input("Product Title", placeholder="e.g. Bamboo Drawer Organizer Set")
        source = st.selectbox("Source / Retailer", ["walmart", "target", "homedepot", "lowes", "bestbuy", "other"])
        source_url = st.text_input("Source URL (optional)")
        source_price = st.number_input("Source Cost ($)", min_value=0.01, value=12.00, step=0.01)
        sale_price = st.number_input("eBay Sale Price ($)", min_value=0.01, value=24.99, step=0.01)

    with c2:
        category = st.selectbox("eBay Category", get_categories(), index=get_categories().index("Home & Garden"))
        buyer_state = st.selectbox("Buyer State (for FVF base)", sorted(US_STATE_TAX_RATES.keys()), index=sorted(US_STATE_TAX_RATES.keys()).index("TX"))
        shipping_out = st.number_input("Shipping to Buyer ($, 0 = free)", min_value=0.0, value=0.0, step=0.50)
        shipping_in = st.number_input("Inbound / Prep Cost ($)", min_value=0.0, value=0.0, step=0.50)
        packaging = st.number_input("Packaging Cost ($)", min_value=0.0, value=0.30, step=0.05)

    st.subheader("eBay Fees")
    c3, c4 = st.columns(2)
    with c3:
        promoted_rate = st.slider("Promoted Listing Rate (%)", 0, 20, 7) / 100
        return_reserve = st.slider("Return Reserve (%)", 0, 10, 2) / 100
    with c4:
        weight_lbs = st.number_input("Product Weight (lbs)", min_value=0.1, value=1.0, step=0.1)

    st.subheader("Risk Flags")
    rc1, rc2, rc3, rc4, rc5 = st.columns(5)
    is_branded = rc1.checkbox("Branded / VeRO Risk")
    is_fragile = rc2.checkbox("Fragile")
    is_hazmat = rc3.checkbox("Hazmat")
    is_regulated = rc4.checkbox("Regulated")
    return_rate_high = rc5.checkbox("High Return Rate")

    submitted = st.form_submit_button("Calculate", type="primary")

# ── Results ───────────────────────────────────────────────────────────────────
if submitted:
    fb = calculate_profit(
        sale_price=sale_price,
        source_cost=source_price,
        category=category,
        shipping_to_buyer=shipping_out,
        shipping_to_self=shipping_in,
        packaging_cost=packaging,
        promoted_listing_rate=promoted_rate,
        buyer_state=buyer_state,
        return_reserve_pct=return_reserve,
    )

    # Cashback
    cb = calculate_cashback(
        purchase_amount=source_price,
        retailer=source,
        product_category="home_organization",
    )
    fb.cashback_expected = cb.combined_expected_savings
    fb.calculate()  # recalculate with cashback

    # Score
    score = score_product(ScoreInput(
        net_margin_before_cashback=fb.net_margin_before_cashback,
        monthly_sold_estimate=20,  # placeholder — user fills in search page
        active_listing_count=50,
        weight_lbs=weight_lbs,
        is_branded=is_branded,
        is_fragile=is_fragile,
        is_hazmat=is_hazmat,
        is_regulated=is_regulated,
        return_rate_high=return_rate_high,
    ))

    # ── KPI row ───────────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Results")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Net Profit (before CB)", f"${fb.net_profit_before_cashback:.2f}",
              delta=f"{fb.net_margin_before_cashback:.1f}% margin")
    k2.metric("Expected Cashback", f"${fb.cashback_expected:.2f}",
              delta=f"{cb.combined_as_pct:.1f}% of cost")
    k3.metric("Net Profit (after CB)", f"${fb.net_profit_after_cashback:.2f}",
              delta=f"{fb.net_margin_after_cashback:.1f}% margin")
    k4.metric("Score", f"{score.final_score}/100", delta=score.decision)

    # ── Decision banner ───────────────────────────────────────────────────────
    decision_color = {
        "✅": "success", "🔵": "info", "⚠️": "warning", "❌": "error"
    }
    emoji = fb.decision[0] if fb.decision else "⚠️"
    banner = decision_color.get(emoji, "info")
    getattr(st, banner)(f"**{fb.decision}** — {score.reason}")

    # ── Fee breakdown table ───────────────────────────────────────────────────
    st.subheader("Full Fee Breakdown")
    breakdown = fb.to_dict()
    df_breakdown = pd.DataFrame(
        list(breakdown.items()), columns=["Item", "Value"]
    )
    st.dataframe(df_breakdown, use_container_width=True, hide_index=True)

    # ── Cashback breakdown ────────────────────────────────────────────────────
    st.subheader("Cashback Breakdown")
    cb_rows = []
    for p in cb.program_results:
        cb_rows.append({
            "Program": p["program"].replace("_", " ").title(),
            "Advertised %": f"{p['advertised_rate_pct']:.2f}%",
            "Tracking Reliability": f"{p['tracking_reliability']:.0f}%",
            "Merchant Approval": f"{p['merchant_approval_pct']:.0f}%",
            "Expected Value": f"${p['expected_value']:.2f}",
            "Expected %": f"{p['expected_rate_pct']:.2f}%",
        })
    cb_rows.append({
        "Program": "🎁 Gift Card Discount",
        "Advertised %": f"{cb.gift_card_discount*100:.1f}%",
        "Tracking Reliability": "92%",
        "Merchant Approval": "—",
        "Expected Value": f"${cb.gift_card_expected_savings:.2f}",
        "Expected %": f"{cb.gift_card_discount*100*0.92:.2f}%",
    })
    cb_rows.append({
        "Program": f"💳 {cb.best_cc_program.replace('_',' ').title()}",
        "Advertised %": f"{cb.cc_reward_rate*100:.1f}%",
        "Tracking Reliability": "99%",
        "Merchant Approval": "—",
        "Expected Value": f"${cb.cc_expected_value:.2f}",
        "Expected %": f"{cb.cc_reward_rate*100:.2f}%",
    })
    st.dataframe(pd.DataFrame(cb_rows), use_container_width=True, hide_index=True)

    # ── Save to DB ────────────────────────────────────────────────────────────
    st.markdown("---")
    if st.button("💾 Save to Candidates"):
        pid = upsert_product({
            "title": title,
            "keyword": title,
            "category": category,
            "source": source,
            "source_url": source_url,
            "source_price": source_price,
            "sale_price": sale_price,
            "shipping_out": shipping_out,
            "shipping_in": shipping_in,
            "packaging_cost": packaging,
            "promoted_rate": promoted_rate,
            "buyer_state": buyer_state,
            "weight_lbs": weight_lbs,
            "is_branded": int(is_branded),
            "is_fragile": int(is_fragile),
            "is_hazmat": int(is_hazmat),
            "is_regulated": int(is_regulated),
            "return_rate_high": int(return_rate_high),
            "net_margin_before_cashback": fb.net_margin_before_cashback,
            "net_profit_before_cashback": fb.net_profit_before_cashback,
            "cashback_expected": fb.cashback_expected,
            "net_profit_after_cashback": fb.net_profit_after_cashback,
            "final_score": score.final_score,
            "decision": fb.decision,
            "status": "candidate",
        })
        st.success(f"Saved as candidate #{pid}. View in the Candidates page.")
