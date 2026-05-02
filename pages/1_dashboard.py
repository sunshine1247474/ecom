"""
Dashboard Page
==============
Overview of all product candidates with KPI cards and charts.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.utils.database import get_all_products
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
st.title("📊 Dashboard")

products = get_all_products()

if not products:
    st.info("No products yet. Go to **Product Search** or **Profit Calculator** to add your first candidates.")
    st.stop()

df = pd.DataFrame(products)

# ── KPI row ───────────────────────────────────────────────────────────────────
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Candidates", len(df))
col2.metric("✅ Approved",  len(df[df["decision"].str.startswith("✅", na=False)]))
col3.metric("🔵 Test",       len(df[df["decision"].str.startswith("🔵", na=False)]))
col4.metric("⚠️ Monitor",   len(df[df["decision"].str.startswith("⚠️", na=False)]))
col5.metric("❌ Rejected",  len(df[df["decision"].str.startswith("❌", na=False)]))

st.markdown("---")

# ── Charts ────────────────────────────────────────────────────────────────────
c1, c2 = st.columns(2)

with c1:
    st.subheader("Decision Breakdown")
    decision_counts = df["decision"].value_counts().reset_index()
    decision_counts.columns = ["Decision", "Count"]
    fig = px.pie(decision_counts, names="Decision", values="Count",
                 color_discrete_sequence=px.colors.qualitative.Set2)
    st.plotly_chart(fig, use_container_width=True)

with c2:
    st.subheader("Margin Distribution (before cashback)")
    if "net_margin_before_cashback" in df.columns:
        fig2 = px.histogram(
            df.dropna(subset=["net_margin_before_cashback"]),
            x="net_margin_before_cashback",
            nbins=20,
            labels={"net_margin_before_cashback": "Net Margin %"},
            color_discrete_sequence=["#4C78A8"],
        )
        fig2.add_vline(x=12, line_dash="dash", line_color="red",
                       annotation_text="12% threshold")
        st.plotly_chart(fig2, use_container_width=True)

# ── Candidates table ──────────────────────────────────────────────────────────
st.subheader("All Candidates")

display_cols = [
    "id", "title", "source", "source_price", "sale_price",
    "net_margin_before_cashback", "final_score", "decision", "status"
]
available = [c for c in display_cols if c in df.columns]
st.dataframe(
    df[available].rename(columns={
        "net_margin_before_cashback": "Margin %",
        "final_score": "Score",
        "source_price": "Cost ($)",
        "sale_price": "Sale ($)",
    }),
    use_container_width=True,
    hide_index=True,
)

# ── Quick status update ───────────────────────────────────────────────────────
st.markdown("---")
st.subheader("Quick Status Update")
if "id" in df.columns:
    prod_id = st.selectbox("Select product ID", df["id"].tolist())
    new_status = st.selectbox("New status", ["candidate", "approved", "testing", "live", "rejected", "archived"])
    if st.button("Update Status"):
        from src.utils.database import update_status
        update_status(prod_id, new_status)
        st.success(f"Product {prod_id} updated to '{new_status}'. Refresh to see changes.")
