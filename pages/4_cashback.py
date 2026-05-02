"""
Cashback Analyzer Page
======================
Model realistic cashback from all programs for a given purchase.
"""

import streamlit as st
import pandas as pd
import plotly.bar_polar as bp
import plotly.express as px
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.cashback.engine import (
    calculate_cashback, cashback_summary,
    CASHBACK_RATES, GIFT_CARD_DISCOUNTS, CREDIT_CARD_RATES,
    NON_RETURN_PROB,
)
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(page_title="Cashback Analyzer", page_icon="💰", layout="wide")
st.title("💰 Cashback Analyzer")
st.markdown("""
Model **realistic cashback** from portals (Rakuten, TopCashback, RebatesMe),
discounted gift cards (Raise, CardCash), and credit card rewards.

> **Key principle:** Cashback is modeled as an *expected value*, not a guarantee.
> The system multiplies the advertised rate by tracking reliability, merchant approval
> probability, and non-return probability to give you a realistic number.
""")

# ── Input ─────────────────────────────────────────────────────────────────────
with st.form("cb_form"):
    c1, c2, c3 = st.columns(3)
    with c1:
        retailer = st.selectbox(
            "Retailer",
            ["walmart", "target", "homedepot", "lowes", "bestbuy", "other"],
        )
        purchase_amount = st.number_input("Purchase Amount ($)", min_value=0.01, value=20.00, step=0.01)
    with c2:
        product_category = st.selectbox(
            "Product Category",
            list(NON_RETURN_PROB.keys()),
        )
        include_gift_cards = st.checkbox("Include Gift Card Discount", value=True)
    with c3:
        include_credit_cards = st.checkbox("Include Credit Card Rewards", value=True)
        st.markdown("")
        submitted = st.form_submit_button("Analyze Cashback", type="primary")

if submitted:
    result = calculate_cashback(
        purchase_amount=purchase_amount,
        retailer=retailer,
        product_category=product_category,
        include_gift_cards=include_gift_cards,
        include_credit_cards=include_credit_cards,
    )

    # ── KPI row ───────────────────────────────────────────────────────────────
    st.markdown("---")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Best Portal", result.best_program.replace("_", " ").title(),
              delta=f"${result.best_expected_value:.2f} expected")
    k2.metric("Gift Card Saving", f"${result.gift_card_expected_savings:.2f}",
              delta=f"{result.gift_card_discount*100:.1f}% off face value")
    k3.metric("Credit Card Reward", f"${result.cc_expected_value:.2f}",
              delta=result.best_cc_program.replace("_", " ").title())
    k4.metric("Combined Expected Savings", f"${result.combined_expected_savings:.2f}",
              delta=f"{result.combined_as_pct:.1f}% of purchase")

    st.info(cashback_summary(result))

    # ── Portal comparison chart ───────────────────────────────────────────────
    st.subheader("Portal Comparison")
    portal_rows = []
    for p in result.program_results:
        portal_rows.append({
            "Program": p["program"].replace("_", " ").title(),
            "Advertised %": p["advertised_rate_pct"],
            "Expected %": p["expected_rate_pct"],
            "Expected $": p["expected_value"],
        })
    df_portals = pd.DataFrame(portal_rows)

    fig = px.bar(
        df_portals,
        x="Program",
        y=["Advertised %", "Expected %"],
        barmode="group",
        title="Advertised vs. Expected Cashback Rate",
        color_discrete_sequence=["#4C78A8", "#F58518"],
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Full breakdown table ──────────────────────────────────────────────────
    st.subheader("Full Breakdown")
    all_rows = []
    for p in result.program_results:
        all_rows.append({
            "Program": p["program"].replace("_", " ").title(),
            "Type": "Portal",
            "Advertised Rate": f"{p['advertised_rate_pct']:.2f}%",
            "Tracking Reliability": f"{p['tracking_reliability']:.0f}%",
            "Merchant Approval": f"{p['merchant_approval_pct']:.0f}%",
            "Non-Return Prob": f"{100 - (1 - NON_RETURN_PROB.get(product_category, 0.88)) * 100:.0f}%",
            "Expected Value": f"${p['expected_value']:.2f}",
        })
    all_rows.append({
        "Program": "Gift Card (Raise/CardCash)",
        "Type": "Gift Card",
        "Advertised Rate": f"{result.gift_card_discount*100:.1f}%",
        "Tracking Reliability": "92%",
        "Merchant Approval": "N/A",
        "Non-Return Prob": "N/A",
        "Expected Value": f"${result.gift_card_expected_savings:.2f}",
    })
    all_rows.append({
        "Program": result.best_cc_program.replace("_", " ").title(),
        "Type": "Credit Card",
        "Advertised Rate": f"{result.cc_reward_rate*100:.1f}%",
        "Tracking Reliability": "99%",
        "Merchant Approval": "N/A",
        "Non-Return Prob": "N/A",
        "Expected Value": f"${result.cc_expected_value:.2f}",
    })
    st.dataframe(pd.DataFrame(all_rows), use_container_width=True, hide_index=True)

    # ── Stacking explanation ──────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Can You Stack These?")
    st.markdown("""
| Combination | Stackable? | Notes |
|:---|:---|:---|
| Portal cashback + Credit card | ✅ Usually yes | Pay with your cashback credit card through the portal |
| Gift card + Portal cashback | ✅ Usually yes | Buy a discounted gift card, then use it via portal link |
| Gift card + Credit card | ⚠️ Sometimes | Some cards don't earn rewards on gift card purchases |
| Two portals at once | ❌ No | Only one portal click counts per purchase |
""")
