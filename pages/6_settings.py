"""
Settings Page
=============
Verify API keys and configure system defaults.
Keys are NEVER stored in code — they come from .env or Codespaces Secrets.
"""

import streamlit as st
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(page_title="Settings", page_icon="⚙️", layout="wide")
st.title("⚙️ Settings")

st.markdown("""
API keys are loaded from:
1. **GitHub Codespaces Secrets** (recommended) — set under `Settings > Codespaces > Secrets`
2. **`.env` file** in the project root (for local development only — never commit this file)

Keys are **never** stored in code or the database.
""")

# ── API Key Status ────────────────────────────────────────────────────────────
st.subheader("API Key Status")

st.markdown("#### Traject Data — Retailer APIs (trajectdata.com)")
st.caption("Each API covers one retailer. You only need the ones you plan to source from.")

traject_keys = {
    "RAINFOREST_API_KEY": ("Rainforest API",  "Amazon",     "https://www.rainforestapi.com/"),
    "BLUECART_API_KEY":   ("BlueCart API",    "Walmart",    "https://app.bluecartapi.com/"),
    "REDCIRCLE_API_KEY":  ("Red Circle API",  "Target",     "https://app.redcircleapi.com/"),
    "BIGBOX_API_KEY":     ("BigBox API",      "Home Depot", "https://docs.trajectdata.com/bigboxapi"),
    "BACKYARD_API_KEY":   ("Backyard API",    "Lowe's",     "https://app.backyardapi.com/"),
    "COUNTDOWN_API_KEY":  ("Countdown API",   "eBay",       "https://docs.trajectdata.com/countdownapi"),
}

import pandas as pd

def key_row(env_var, label, retailer, url):
    val = os.environ.get(env_var, "")
    if val:
        masked = val[:4] + "•" * max(0, len(val) - 8) + val[-4:] if len(val) > 8 else "•" * len(val)
        status = "✅ Set"
    else:
        masked = "—"
        status = "❌ Missing"
    return {"API": label, "Retailer": retailer, "Env Variable": env_var,
            "Status": status, "Value (masked)": masked, "Sign Up": url}

traject_rows = [key_row(k, v[0], v[1], v[2]) for k, v in traject_keys.items()]
df_t = pd.DataFrame(traject_rows)
st.dataframe(df_t.drop(columns=["Sign Up"]), use_container_width=True, hide_index=True)

st.markdown("**Sign-up links:**")
for _, (label, retailer, url) in traject_keys.items():
    st.markdown(f"- **{label}** ({retailer}): [{url}]({url})")

st.markdown("---")
st.markdown("#### Google Shopping APIs (use ONE)")
st.caption("SerpWow is preferred. Scale SERP and Value SERP are automatic fallbacks.")

google_keys = {
    "SERPWOW_API_KEY":   ("SerpWow",    "Primary",   "https://serpwow.com/"),
    "SCALESERP_API_KEY": ("Scale SERP", "Fallback 1","https://scaleserp.com/"),
    "VALUESERP_API_KEY": ("Value SERP", "Fallback 2","https://valueserp.com/"),
}
google_rows = [key_row(k, v[0], v[1], v[2]) for k, v in google_keys.items()]
df_g = pd.DataFrame(google_rows)
st.dataframe(df_g.drop(columns=["Sign Up"]), use_container_width=True, hide_index=True)

st.markdown("---")
st.markdown("#### eBay Developer Keys")
ebay_keys = {
    "EBAY_APP_ID":     ("eBay App ID",    "eBay", "https://developer.ebay.com/"),
    "EBAY_CERT_ID":    ("eBay Cert ID",   "eBay", "https://developer.ebay.com/"),
    "EBAY_USER_TOKEN": ("eBay User Token","eBay", "https://developer.ebay.com/"),
    "OPENAI_API_KEY":  ("OpenAI API Key", "OpenAI","https://platform.openai.com/api-keys"),
}
ebay_rows = [key_row(k, v[0], v[1], v[2]) for k, v in ebay_keys.items()]
df_e = pd.DataFrame(ebay_rows)
st.dataframe(df_e.drop(columns=["Sign Up"]), use_container_width=True, hide_index=True)

# ── eBay environment ──────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("eBay Environment")
ebay_env = os.environ.get("EBAY_ENVIRONMENT", "sandbox")
if ebay_env == "production":
    st.warning("⚠️ **PRODUCTION** mode — eBay API calls are LIVE.")
else:
    st.info("🧪 **SANDBOX** mode — eBay API calls are for testing only.")

# ── Active sources summary ────────────────────────────────────────────────────
st.markdown("---")
st.subheader("Active Search Sources")
from src.sources.search import ProductSearchAggregator
agg = ProductSearchAggregator()
active = agg.active_sources
if active:
    st.success(f"**{len(active)} sources active:** {', '.join(s.title() for s in active)}")
else:
    st.error("No search sources active. Add at least one Traject Data API key.")

# ── Connection tests ──────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("Connection Tests")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("Test Walmart (BlueCart)"):
        from src.sources.search import WalmartBlueCartSource
        results = WalmartBlueCartSource().search("drawer organizer", limit=2)
        if results:
            st.success(f"✅ Walmart OK — {results[0].title[:40]}… ${results[0].price}")
        else:
            st.error("❌ No results (check BLUECART_API_KEY)")

    if st.button("Test Target (Red Circle)"):
        from src.sources.search import TargetRedCircleSource
        results = TargetRedCircleSource().search("drawer organizer", limit=2)
        if results:
            st.success(f"✅ Target OK — {results[0].title[:40]}… ${results[0].price}")
        else:
            st.error("❌ No results (check REDCIRCLE_API_KEY)")

with col2:
    if st.button("Test Home Depot (BigBox)"):
        from src.sources.search import HomeDepotBigBoxSource
        results = HomeDepotBigBoxSource().search("storage bin", limit=2)
        if results:
            st.success(f"✅ Home Depot OK — {results[0].title[:40]}… ${results[0].price}")
        else:
            st.error("❌ No results (check BIGBOX_API_KEY)")

    if st.button("Test Lowe's (Backyard)"):
        from src.sources.search import LowesBackyardSource
        results = LowesBackyardSource().search("storage bin", limit=2)
        if results:
            st.success(f"✅ Lowe's OK — {results[0].title[:40]}… ${results[0].price}")
        else:
            st.error("❌ No results (check BACKYARD_API_KEY)")

with col3:
    if st.button("Test eBay Sold Prices (Countdown)"):
        from src.sources.search import EbayCountdownSource
        avg = EbayCountdownSource().avg_sold_price("drawer organizer", limit=10)
        if avg:
            st.success(f"✅ eBay Countdown OK — avg sold price: ${avg:.2f}")
        else:
            st.error("❌ No results (check COUNTDOWN_API_KEY)")

    if st.button("Test Amazon (Rainforest)"):
        from src.sources.search import AmazonRainforestSource
        results = AmazonRainforestSource().search("drawer organizer", limit=2)
        if results:
            st.success(f"✅ Amazon OK — {results[0].title[:40]}… ${results[0].price}")
        else:
            st.error("❌ No results (check RAINFOREST_API_KEY)")

if st.button("Test Cashback Engine"):
    from src.cashback.engine import calculate_cashback
    r = calculate_cashback(20.0, "walmart", "home_organization")
    st.success(f"✅ Cashback engine OK — combined expected: ${r.combined_expected_savings:.2f}")

# ── LLM Provider ──────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("AI / LLM Provider (optional)")
st.caption("Used for product analysis. Free options available — no OpenAI required.")

from src.utils.llm import get_provider_info
info = get_provider_info()
if info["active"]:
    st.success(f"✅ Active: **{info['label']}** — model: `{info['model']}`")
else:
    st.warning("No LLM provider configured. Set one of: `GROQ_API_KEY`, `OPENROUTER_API_KEY`, or `GEMINI_API_KEY`")

st.markdown("""
| Provider | Cost | Free Tier | Sign Up |
|:---|:---|:---|:---|
| **Groq** | Free (rate-limited) | ✅ Yes | [console.groq.com](https://console.groq.com/keys) |
| **OpenRouter** | ~$0.0001/1K tokens | ✅ Free models available | [openrouter.ai](https://openrouter.ai/keys) |
| **Gemini Flash** | Free (generous limits) | ✅ Yes | [aistudio.google.com](https://aistudio.google.com/app/apikey) |
""")

if st.button("Test LLM"):
    from src.utils.llm import chat
    try:
        resp = chat("Say 'LLM OK' and nothing else.")
        st.success(f"✅ LLM OK — response: {resp[:80]}")
    except Exception as e:
        st.error(f"❌ LLM failed: {e}")
