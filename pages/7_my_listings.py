"""
My eBay Active Listings
========================
Scans and displays all active listings from your eBay seller account:
  - Title, Price, Watchers, Views, Time Left, Status
  - Sortable table with color-coded urgency
  - Quick stats: total listings, total watchers, avg price
  - "Ending Soon" alerts
"""

import streamlit as st
import os
import sys
import pandas as pd
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(page_title="My Listings", page_icon="🏪", layout="wide")
st.title("🏪 My eBay Active Listings")

# ── Check token ───────────────────────────────────────────────────────────────
token = os.environ.get("EBAY_USER_TOKEN", "")
if not token:
    st.error("**EBAY_USER_TOKEN not set.** Run `python get_ebay_token.py` first.")
    st.stop()

env_mode = os.environ.get("EBAY_ENVIRONMENT", "sandbox").lower()
if env_mode == "sandbox":
    st.info("🧪 Sandbox mode — showing test listings. Change `EBAY_ENVIRONMENT=production` for real data.")
else:
    st.success("✅ Production mode — showing real listings.")

# ── Controls ──────────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    enrich_views = st.checkbox(
        "Fetch view counts (slower — 1 API call per listing)",
        value=False,
        help="Fetches accurate HitCount per listing. Adds ~1s per listing."
    )
with col3:
    scan_btn = st.button("🔄 Scan Now", type="primary", use_container_width=True)

# ── Session state ─────────────────────────────────────────────────────────────
if "listings" not in st.session_state:
    st.session_state.listings = []
if "last_scan" not in st.session_state:
    st.session_state.last_scan = None

# ── Scan ──────────────────────────────────────────────────────────────────────
if scan_btn:
    with st.spinner("Scanning your eBay listings…"):
        try:
            from src.ebay.active_listings import EbayActiveListingsScanner
            scanner = EbayActiveListingsScanner()
            listings = scanner.scan(enrich_views=enrich_views)
            st.session_state.listings = listings
            st.session_state.last_scan = datetime.now()
            if listings:
                st.success(f"✅ Found **{len(listings)}** active listing(s)")
            else:
                st.warning("No active listings found.")
        except RuntimeError as e:
            st.error(f"❌ {e}")
            st.stop()
        except Exception as e:
            st.error(f"❌ Unexpected error: {e}")
            st.stop()

listings = st.session_state.listings

if st.session_state.last_scan:
    st.caption(f"Last scanned: {st.session_state.last_scan.strftime('%H:%M:%S')}")

if not listings:
    st.info("Press **Scan Now** to load your active listings.")
    st.stop()

# ── Summary metrics ───────────────────────────────────────────────────────────
total_listings  = len(listings)
total_watchers  = sum(l.watchers for l in listings)
total_views     = sum(l.views for l in listings)
avg_price       = sum(l.price for l in listings) / total_listings if listings else 0
ending_soon     = [l for l in listings if l.is_ending_soon]

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Active Listings",  total_listings)
m2.metric("Total Watchers",   total_watchers)
m3.metric("Total Views",      total_views)
m4.metric("Avg Price",        f"${avg_price:.2f}")
m5.metric("Ending < 24h",     len(ending_soon),
          delta=f"⚠️ {len(ending_soon)} urgent" if ending_soon else None,
          delta_color="inverse")

st.markdown("---")

# ── Ending soon alert ─────────────────────────────────────────────────────────
if ending_soon:
    st.warning(f"⚠️ **{len(ending_soon)} listing(s) ending within 24 hours:**")
    for l in ending_soon:
        hrs = (l.days_left or 0) * 24
        st.markdown(f"- [{l.title[:60]}]({l.listing_url}) — **{hrs:.1f}h left** — ${l.price:.2f} — {l.watchers} watchers")
    st.markdown("---")

# ── Build DataFrame ───────────────────────────────────────────────────────────
rows = []
for l in listings:
    rows.append({
        "Item ID":    l.item_id,
        "Title":      l.title,
        "Price ($)":  l.price,
        "Watchers":   l.watchers,
        "Views":      l.views,
        "Qty":        l.quantity,
        "Sold":       l.quantity_sold,
        "Time Left":  l.time_left_human,
        "Days Left":  round(l.days_left, 1) if l.days_left is not None else None,
        "Condition":  l.condition,
        "URL":        l.listing_url,
    })

df = pd.DataFrame(rows)

# ── Sort controls ─────────────────────────────────────────────────────────────
sort_col = st.selectbox(
    "Sort by",
    ["Watchers", "Views", "Price ($)", "Days Left", "Sold"],
    index=0,
)
sort_asc = st.checkbox("Ascending", value=False)
df_sorted = df.sort_values(sort_col, ascending=sort_asc).reset_index(drop=True)

# ── Display table ─────────────────────────────────────────────────────────────
st.subheader(f"All Active Listings ({total_listings})")

# Color-code Days Left
def style_days(val):
    if val is None:
        return ""
    if val < 1:
        return "background-color: #ff4b4b; color: white; font-weight: bold"
    if val < 3:
        return "background-color: #ffa500; color: white"
    return ""

display_cols = ["Title", "Price ($)", "Watchers", "Views", "Qty", "Sold", "Time Left", "Days Left", "Condition"]
styled = (
    df_sorted[display_cols]
    .style
    .applymap(style_days, subset=["Days Left"])
    .format({"Price ($)": "${:.2f}", "Days Left": lambda x: f"{x:.1f}" if x is not None else "—"})
)

st.dataframe(styled, use_container_width=True, height=500)

# ── Per-listing detail expander ───────────────────────────────────────────────
st.markdown("---")
st.subheader("Listing Details")

for l in listings:
    label = f"{'🔴' if l.is_ending_soon else '🟢'} {l.title[:70]} — ${l.price:.2f} — {l.watchers} watchers — {l.time_left_human} left"
    with st.expander(label):
        c1, c2, c3 = st.columns(3)
        c1.metric("Price",    f"${l.price:.2f}")
        c2.metric("Watchers", l.watchers)
        c3.metric("Views",    l.views)

        c4, c5, c6 = st.columns(3)
        c4.metric("Qty Available", l.quantity)
        c5.metric("Qty Sold",      l.quantity_sold)
        c6.metric("Time Left",     l.time_left_human)

        st.markdown(f"**Item ID:** `{l.item_id}`")
        st.markdown(f"**Condition:** {l.condition or 'N/A'}")
        if l.end_time:
            st.markdown(f"**Ends:** {l.end_time.strftime('%Y-%m-%d %H:%M UTC')}")
        st.markdown(f"[View on eBay ↗]({l.listing_url})")

# ── Export ────────────────────────────────────────────────────────────────────
st.markdown("---")
csv = df_sorted.to_csv(index=False)
st.download_button(
    label="⬇️ Export to CSV",
    data=csv,
    file_name=f"ebay_active_listings_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
    mime="text/csv",
)
