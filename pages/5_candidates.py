"""
Candidates Page
===============
Full CRUD management of product candidates.
"""

import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.utils.database import get_all_products, update_status, delete_product
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(page_title="Candidates", page_icon="📋", layout="wide")
st.title("📋 Product Candidates")

# ── Filter bar ────────────────────────────────────────────────────────────────
col1, col2 = st.columns([2, 1])
with col1:
    status_filter = st.multiselect(
        "Filter by status",
        ["candidate", "approved", "testing", "live", "rejected", "archived"],
        default=["candidate", "approved", "testing"],
    )
with col2:
    min_score = st.slider("Minimum Score", 0, 100, 0)

products = get_all_products()
if not products:
    st.info("No candidates yet. Use the Profit Calculator or Product Search to add products.")
    st.stop()

df = pd.DataFrame(products)

# Apply filters
if status_filter:
    df = df[df["status"].isin(status_filter)]
if min_score > 0 and "final_score" in df.columns:
    df = df[df["final_score"] >= min_score]

st.markdown(f"Showing **{len(df)}** products.")

# ── Display table ─────────────────────────────────────────────────────────────
display_cols = [
    "id", "title", "source", "source_price", "sale_price",
    "net_margin_before_cashback", "cashback_expected",
    "net_profit_after_cashback", "final_score", "decision", "status",
]
available = [c for c in display_cols if c in df.columns]

st.dataframe(
    df[available].rename(columns={
        "source_price":                 "Cost ($)",
        "sale_price":                   "Sale ($)",
        "net_margin_before_cashback":   "Margin %",
        "cashback_expected":            "CB ($)",
        "net_profit_after_cashback":    "Net Profit ($)",
        "final_score":                  "Score",
    }),
    use_container_width=True,
    hide_index=True,
)

# ── Bulk actions ──────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("Actions")
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown("**Update Status**")
    prod_id = st.number_input("Product ID", min_value=1, step=1, key="upd_id")
    new_status = st.selectbox(
        "New Status",
        ["candidate", "approved", "testing", "live", "rejected", "archived"],
        key="upd_status",
    )
    if st.button("Update", key="btn_update"):
        update_status(int(prod_id), new_status)
        st.success(f"Product {prod_id} → {new_status}")
        st.rerun()

with c2:
    st.markdown("**Delete Product**")
    del_id = st.number_input("Product ID to Delete", min_value=1, step=1, key="del_id")
    if st.button("🗑️ Delete", key="btn_delete", type="secondary"):
        delete_product(int(del_id))
        st.warning(f"Product {del_id} deleted.")
        st.rerun()

with c3:
    st.markdown("**Export to CSV**")
    if st.button("📥 Export All to CSV"):
        all_products = get_all_products()
        df_export = pd.DataFrame(all_products)
        csv = df_export.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name="resale_candidates.csv",
            mime="text/csv",
        )
