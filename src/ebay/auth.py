"""
eBay OAuth Token Manager
=========================
Handles automatic token refresh so you never have to run get_ebay_token.py again
after the initial setup.

The Access Token expires every 2 hours.
The Refresh Token lasts ~18 months.

Usage (automatic — called by other modules):
    from src.ebay.auth import get_valid_token
    token = get_valid_token()
"""

from __future__ import annotations
import os
import base64
import time
from pathlib import Path

try:
    import requests
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

try:
    from dotenv import load_dotenv, set_key
    load_dotenv(Path(__file__).parent.parent.parent / ".env")
except ImportError:
    pass


# In-memory token cache (avoids hitting the API on every call)
_token_cache: dict = {"token": None, "expires_at": 0}


def _get_env(key: str) -> str:
    return os.environ.get(key, "").strip()


def _token_url() -> str:
    env = _get_env("EBAY_ENVIRONMENT").lower()
    if env == "production":
        return "https://api.ebay.com/identity/v1/oauth2/token"
    return "https://api.sandbox.ebay.com/identity/v1/oauth2/token"


def refresh_access_token() -> str:
    """
    Use the Refresh Token to get a new Access Token.
    Saves the new Access Token to .env automatically.
    Returns the new Access Token string.
    """
    app_id      = _get_env("EBAY_APP_ID")
    cert_id     = _get_env("EBAY_CERT_ID")
    refresh_tok = _get_env("EBAY_REFRESH_TOKEN")

    if not all([app_id, cert_id, refresh_tok]):
        raise RuntimeError(
            "Missing eBay credentials. Run: python get_ebay_token.py\n"
            "Required: EBAY_APP_ID, EBAY_CERT_ID, EBAY_REFRESH_TOKEN"
        )

    credentials = base64.b64encode(f"{app_id}:{cert_id}".encode()).decode()
    headers = {
        "Content-Type":  "application/x-www-form-urlencoded",
        "Authorization": f"Basic {credentials}",
    }
    data = {
        "grant_type":    "refresh_token",
        "refresh_token": refresh_tok,
        "scope": (
            "https://api.ebay.com/oauth/api_scope "
            "https://api.ebay.com/oauth/api_scope/sell.inventory "
            "https://api.ebay.com/oauth/api_scope/sell.fulfillment "
            "https://api.ebay.com/oauth/api_scope/sell.account "
            "https://api.ebay.com/oauth/api_scope/commerce.catalog.readonly"
        ),
    }

    resp = requests.post(_token_url(), headers=headers, data=data, timeout=30)
    resp.raise_for_status()
    token_data = resp.json()

    new_token  = token_data["access_token"]
    expires_in = token_data.get("expires_in", 7200)

    # Save to .env
    env_file = Path(__file__).parent.parent.parent / ".env"
    if env_file.exists():
        set_key(str(env_file), "EBAY_USER_TOKEN", new_token)

    # Update in-memory cache
    _token_cache["token"]      = new_token
    _token_cache["expires_at"] = time.time() + expires_in - 60  # 1-min buffer

    return new_token


def get_valid_token() -> str:
    """
    Return a valid eBay Access Token.
    Automatically refreshes if expired or about to expire.
    Falls back to the stored EBAY_USER_TOKEN if no refresh token is available.
    """
    now = time.time()

    # Return cached token if still valid
    if _token_cache["token"] and now < _token_cache["expires_at"]:
        return _token_cache["token"]

    # Try to refresh using the Refresh Token
    refresh_tok = _get_env("EBAY_REFRESH_TOKEN")
    if refresh_tok:
        try:
            return refresh_access_token()
        except Exception:
            pass  # Fall through to stored token

    # Fall back to stored Access Token (may be expired — user needs to re-run get_ebay_token.py)
    stored = _get_env("EBAY_USER_TOKEN")
    if stored:
        _token_cache["token"]      = stored
        _token_cache["expires_at"] = now + 7200  # Assume 2h from now
        return stored

    raise RuntimeError(
        "No valid eBay token found.\n"
        "Run: python get_ebay_token.py\n"
        "to get your initial token."
    )


def get_app_token() -> str:
    """
    Get an Application Token (no user login required).
    Used for public API calls like Browse API.
    """
    app_id  = _get_env("EBAY_APP_ID")
    cert_id = _get_env("EBAY_CERT_ID")

    if not app_id or not cert_id:
        raise RuntimeError("EBAY_APP_ID and EBAY_CERT_ID must be set.")

    credentials = base64.b64encode(f"{app_id}:{cert_id}".encode()).decode()
    headers = {
        "Content-Type":  "application/x-www-form-urlencoded",
        "Authorization": f"Basic {credentials}",
    }
    data = {
        "grant_type": "client_credentials",
        "scope":      "https://api.ebay.com/oauth/api_scope",
    }

    resp = requests.post(_token_url(), headers=headers, data=data, timeout=30)
    resp.raise_for_status()
    return resp.json()["access_token"]
