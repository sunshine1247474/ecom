"""
Resale Scanner — Main App
=========================
Run with:  streamlit run app.py
"""

import streamlit as st

st.set_page_config(
    page_title="Resale Scanner",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Load environment variables (local .env or Codespaces Secrets) ─────────────
from dotenv import load_dotenv
load_dotenv()

# ── Sidebar navigation ────────────────────────────────────────────────────────
st.sidebar.title("🔍 Resale Scanner")
st.sidebar.markdown("---")

pages = {
    "📊 Dashboard":         "pages/1_dashboard.py",
    "🧮 Profit Calculator": "pages/2_calculator.py",
    "🔎 Product Search":    "pages/3_search.py",
    "💰 Cashback Analyzer": "pages/4_cashback.py",
    "📋 Candidates":        "pages/5_candidates.py",
    "⚙️  Settings":         "pages/6_settings.py",
}

st.sidebar.markdown("### Navigation")
for label in pages:
    st.sidebar.markdown(f"- {label}")

st.sidebar.markdown("---")
st.sidebar.caption("Keys are loaded from `.env` or Codespaces Secrets — never stored in code.")

# ── Home page ─────────────────────────────────────────────────────────────────
st.title("🔍 Resale Scanner")
st.markdown("""
Welcome to **Resale Scanner** — your independent eBay resale research system.

Use the pages in the sidebar (or the links below) to navigate:

| Page | What it does |
|:---|:---|
| 📊 **Dashboard** | Overview of all candidates, scores, and decisions |
| 🧮 **Profit Calculator** | Calculate exact eBay profit by category with real fee tables |
| 🔎 **Product Search** | Search Amazon, Walmart, Home Depot, Google Shopping in one place |
| 💰 **Cashback Analyzer** | Model realistic cashback from Rakuten, TopCashback, gift cards, credit cards |
| 📋 **Candidates** | Manage your product list — approve, test, reject |
| ⚙️ **Settings** | Verify API keys and configure defaults |
""")

st.info("👈 Use the sidebar to navigate between pages, or click a page name above.")
