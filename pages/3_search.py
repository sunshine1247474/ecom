"""
Product Search Page
===================
Search Amazon, Walmart, Google Shopping in one place.
For each result, show price and a quick "Add to Calculator" button.
"""

import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.sources.search import ProductSearchAggregator
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(page_title="Product Search", page_icon="🔎", layout="wide")
st.title("🔎 Product Search")
st.markdown("Search across **Amazon, Walmart, Home Depot, Target, and Google Shopping** simultaneously.")

# ── Search bar ────────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns([3, 1, 1])
with col1:
    keyword = st.text_input("Search keyword", placeholder="e.g. bamboo drawer organizer")
with col2:
    min_price = st.number_input("Min price ($)", min_value=0.0, value=0.0, step=1.0)
with col3:
    max_price = st.number_input("Max price ($)", min_value=0.0, value=50.0, step=1.0)

search_btn = st.button("🔍 Search All Sources", type="primary")

if search_btn and keyword:
    with st.spinner(f"Searching for '{keyword}' across all sources..."):
        agg = ProductSearchAggregator()
        results = agg.search(
            keyword=keyword,
            limit_per_source=12,
            min_price=min_price if min_price > 0 else None,
            max_price=max_price if max_price > 0 else None,
        )

    if not results:
        st.warning("No results found. Check your API keys in Settings or try a different keyword.")
    else:
        st.success(f"Found **{len(results)}** results across all sources.")

        # ── Source breakdown ──────────────────────────────────────────────────
        sources = {}
        for r in results:
            sources[r.source] = sources.get(r.source, 0) + 1
        cols = st.columns(len(sources))
        for i, (src, cnt) in enumerate(sorted(sources.items())):
            cols[i].metric(src.title(), f"{cnt} results")

        st.markdown("---")

        # ── Results table ─────────────────────────────────────────────────────
        rows = []
        for r in results:
            rows.append({
                "Source": r.source.title(),
                "Title": r.title[:70] + ("…" if len(r.title) > 70 else ""),
                "Price ($)": r.price,
                "Rating": r.rating or "—",
                "Reviews": r.review_count or "—",
                "Shipping": r.shipping_note or "—",
                "URL": r.url,
            })
        df = pd.DataFrame(rows)

        # Highlight cheapest per source
        st.dataframe(
            df.drop(columns=["URL"]),
            use_container_width=True,
            hide_index=True,
        )

        # ── Cheapest per source summary ───────────────────────────────────────
        st.subheader("Cheapest per Source")
        cheapest = agg.cheapest_by_source(keyword)
        c_rows = []
        for src, prod in cheapest.items():
            if prod:
                c_rows.append({
                    "Source": src.title(),
                    "Title": prod.title[:60],
                    "Price ($)": prod.price,
                    "URL": prod.url,
                })
        if c_rows:
            df_c = pd.DataFrame(c_rows)
            st.dataframe(df_c, use_container_width=True, hide_index=True)

        # ── Quick add to calculator ───────────────────────────────────────────
        st.markdown("---")
        st.subheader("Quick Add to Calculator")
        st.markdown("Select a result to pre-fill the Profit Calculator:")
        selected_idx = st.selectbox(
            "Select result",
            range(len(rows)),
            format_func=lambda i: f"[{rows[i]['Source']}] {rows[i]['Title']} — ${rows[i]['Price ($)']:.2f}",
        )
        if st.button("Open in Calculator →"):
            r = results[selected_idx]
            st.session_state["prefill_title"] = r.title
            st.session_state["prefill_source"] = r.source
            st.session_state["prefill_source_url"] = r.url
            st.session_state["prefill_source_price"] = r.price
            st.switch_page("pages/2_calculator.py")

elif search_btn and not keyword:
    st.warning("Please enter a keyword to search.")
