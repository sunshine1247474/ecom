"""
eBay OAuth User Token Fetcher — FIXED
======================================
The key insight: eBay does NOT accept localhost as a redirect_uri.
Instead, the redirect_uri MUST be your RuName (exactly as registered
in the Developer Portal under "User Tokens").

Flow:
  1. Build the eBay authorization URL using your RuName as redirect_uri
  2. You open the URL in your browser and log in to eBay
  3. eBay redirects to its own "success" page — you copy the "code" from the URL
  4. Paste the code here — the script exchanges it for tokens
  5. Tokens are saved to your .env automatically

Usage:
  python get_ebay_token.py

Requirements (already in requirements.txt):
  pip install requests python-dotenv
"""

import os
import sys
import base64
import urllib.parse
from pathlib import Path

try:
    import requests
except ImportError:
    os.system(f"{sys.executable} -m pip install requests")
    import requests

try:
    from dotenv import load_dotenv, set_key
except ImportError:
    os.system(f"{sys.executable} -m pip install python-dotenv")
    from dotenv import load_dotenv, set_key

# ─────────────────────────────────────────────────────────────────────────────
# Load .env
# ─────────────────────────────────────────────────────────────────────────────
ENV_FILE = Path(__file__).parent / ".env"
if not ENV_FILE.exists():
    example = Path(__file__).parent / ".env.example"
    if example.exists():
        import shutil
        shutil.copy(example, ENV_FILE)

load_dotenv(ENV_FILE, override=True)

# ─────────────────────────────────────────────────────────────────────────────
# Read credentials from environment
# ─────────────────────────────────────────────────────────────────────────────
APP_ID   = os.environ.get("EBAY_APP_ID", "").strip()
CERT_ID  = os.environ.get("EBAY_CERT_ID", "").strip()
RUNAME   = os.environ.get("EBAY_RUNAME", "").strip()
ENV_MODE = os.environ.get("EBAY_ENVIRONMENT", "sandbox").strip().lower()

# eBay endpoints
if ENV_MODE == "production":
    AUTH_URL  = "https://auth.ebay.com/oauth2/authorize"
    TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
    print("⚠️   PRODUCTION mode — this will use your real eBay account")
else:
    AUTH_URL  = "https://auth.sandbox.ebay.com/oauth2/authorize"
    TOKEN_URL = "https://api.sandbox.ebay.com/identity/v1/oauth2/token"
    print("🧪   SANDBOX mode")

# Scopes — space-separated, using the correct eBay scope format
SCOPES = " ".join([
    "https://api.ebay.com/oauth/api_scope",
    "https://api.ebay.com/oauth/api_scope/sell.inventory",
    "https://api.ebay.com/oauth/api_scope/sell.inventory.readonly",
    "https://api.ebay.com/oauth/api_scope/sell.fulfillment",
    "https://api.ebay.com/oauth/api_scope/sell.fulfillment.readonly",
    "https://api.ebay.com/oauth/api_scope/sell.account",
    "https://api.ebay.com/oauth/api_scope/sell.account.readonly",
    "https://api.ebay.com/oauth/api_scope/commerce.catalog.readonly",
])

# ─────────────────────────────────────────────────────────────────────────────
# Validate
# ─────────────────────────────────────────────────────────────────────────────
def validate():
    errors = []
    if not APP_ID:
        errors.append("EBAY_APP_ID")
    if not CERT_ID:
        errors.append("EBAY_CERT_ID")
    if not RUNAME:
        errors.append("EBAY_RUNAME")

    if errors:
        print("\n❌  Missing values in your .env file:")
        for e in errors:
            print(f"    {e}=<your value>")
        print("\n📋  Where to find them:")
        print("    → https://developer.ebay.com/my/keys")
        print("    → EBAY_RUNAME: click 'User Tokens' → copy the RuName value")
        print(f"\n    Your .env file is at: {ENV_FILE}")
        print("\n💡  Example .env:")
        print("    EBAY_APP_ID=ItayShkl-OrderTra-SBX-fb02c4443-a6d10e91")
        print("    EBAY_CERT_ID=SBX-b02c4443xxxx-xxxx-xxxx-xxxxxxxxxxxx")
        print("    EBAY_RUNAME=Itay_Shklyar-ItayShkl-OrderT-ftibn")
        print("    EBAY_ENVIRONMENT=sandbox")
        sys.exit(1)

    print(f"\n✅  App ID:  {APP_ID}")
    print(f"✅  Cert ID: {CERT_ID[:8]}…")
    print(f"✅  RuName:  {RUNAME}")

# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — Build and print the authorization URL
# ─────────────────────────────────────────────────────────────────────────────
def build_auth_url() -> str:
    params = {
        "client_id":     APP_ID,
        "redirect_uri":  RUNAME,          # ← Must be the RuName, NOT localhost
        "response_type": "code",
        "scope":         SCOPES,
        "prompt":        "login",
    }
    return AUTH_URL + "?" + urllib.parse.urlencode(params)

# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — Exchange auth code for tokens
# ─────────────────────────────────────────────────────────────────────────────
def exchange_code(code: str) -> dict:
    credentials = base64.b64encode(f"{APP_ID}:{CERT_ID}".encode()).decode()
    headers = {
        "Content-Type":  "application/x-www-form-urlencoded",
        "Authorization": f"Basic {credentials}",
    }
    data = {
        "grant_type":   "authorization_code",
        "code":         code.strip(),
        "redirect_uri": RUNAME,           # ← Must match exactly
    }
    resp = requests.post(TOKEN_URL, headers=headers, data=data, timeout=30)

    if resp.status_code != 200:
        print(f"\n❌  Token exchange failed (HTTP {resp.status_code})")
        print(f"    Response: {resp.text}")
        print("\n💡  Common causes:")
        print("    1. The code expires after 5 minutes — try again quickly")
        print("    2. EBAY_RUNAME must match EXACTLY what's in the Developer Portal")
        print("    3. EBAY_APP_ID and EBAY_CERT_ID must be from the SAME keyset")
        sys.exit(1)

    return resp.json()

# ─────────────────────────────────────────────────────────────────────────────
# Step 3 — Save tokens to .env
# ─────────────────────────────────────────────────────────────────────────────
def save_tokens(token_data: dict):
    access_token  = token_data.get("access_token", "")
    refresh_token = token_data.get("refresh_token", "")
    expires_in    = token_data.get("expires_in", 7200)

    if not ENV_FILE.exists():
        ENV_FILE.touch()

    set_key(str(ENV_FILE), "EBAY_USER_TOKEN", access_token)
    if refresh_token:
        set_key(str(ENV_FILE), "EBAY_REFRESH_TOKEN", refresh_token)

    print(f"\n✅  Access Token saved  (expires in {expires_in // 60} minutes)")
    if refresh_token:
        print(f"✅  Refresh Token saved (valid for ~18 months — auto-refresh enabled)")
    print(f"\n📄  Saved to: {ENV_FILE}")
    print("\n🎉  Done! You can now run:")
    print("    streamlit run app.py")

    print("\n" + "─" * 60)
    print("EBAY_USER_TOKEN (first 50 chars):")
    print("  " + access_token[:50] + "…")
    if refresh_token:
        print("EBAY_REFRESH_TOKEN (first 50 chars):")
        print("  " + refresh_token[:50] + "…")
    print("─" * 60)

# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
def main():
    print("\n" + "═" * 60)
    print("  eBay OAuth Token Fetcher")
    print("═" * 60)

    validate()

    auth_url = build_auth_url()

    print("\n" + "─" * 60)
    print("STEP 1 — Open this URL in your browser:")
    print("─" * 60)
    print(f"\n{auth_url}\n")
    print("─" * 60)

    if ENV_MODE == "sandbox":
        print("\n⚠️   SANDBOX: You need a TEST USER to log in.")
        print("    Create one at: https://developer.ebay.com/my/test_users")
        print("    (Use the test user credentials — NOT your real eBay login)")
    else:
        print("\n    Log in with your real eBay account.")

    print("\nAfter logging in, eBay will redirect you to a page that says")
    print("'You have successfully granted access' or shows a URL like:")
    print("  https://signin.ebay.com/...?code=v%5E1.1%23i%5E1%23...")
    print("\nCopy the FULL 'code' value from that URL (everything after 'code=')")
    print("It starts with: v%5E1.1 or similar\n")

    code = input("STEP 2 — Paste the authorization code here: ").strip()

    # Handle URL-encoded code (user might paste the full URL)
    if "code=" in code:
        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(code).query)
        code = parsed.get("code", [code])[0]

    # URL-decode if needed
    code = urllib.parse.unquote(code)

    if not code:
        print("❌  No code provided. Exiting.")
        sys.exit(1)

    print(f"\n🔄  Exchanging code for tokens…")
    token_data = exchange_code(code)
    save_tokens(token_data)


if __name__ == "__main__":
    main()
