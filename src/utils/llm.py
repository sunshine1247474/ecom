"""
Unified LLM Client
==================
Supports Groq, OpenRouter, and Google Gemini Flash.
All three expose an OpenAI-compatible API, so one client covers all.

Priority order (uses first key found in environment):
  1. Groq          — free tier, fastest inference
  2. OpenRouter    — pay-per-use, access to free models
  3. Gemini Flash  — Google free tier

Usage:
    from src.utils.llm import chat
    response = chat("Analyze this product: Bamboo Drawer Organizer...")
"""

from __future__ import annotations
import os
from typing import Optional

# ── Provider configs ──────────────────────────────────────────────────────────
PROVIDERS = {
    "groq": {
        "env_key":  "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1",
        "model_env": "GROQ_MODEL",
        "default_model": "llama-3.3-70b-versatile",
        "label": "Groq (free tier)",
    },
    "openrouter": {
        "env_key":  "OPENROUTER_API_KEY",
        "base_url": "https://openrouter.ai/api/v1",
        "model_env": "OPENROUTER_MODEL",
        "default_model": "mistralai/mistral-7b-instruct:free",
        "label": "OpenRouter",
    },
    "gemini": {
        "env_key":  "GEMINI_API_KEY",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model_env": "GEMINI_MODEL",
        "default_model": "gemini-2.0-flash",
        "label": "Google Gemini Flash (free tier)",
    },
}


def _get_active_provider() -> Optional[dict]:
    """Return the first provider that has a valid API key set."""
    # Respect explicit LLM_PROVIDER setting if present
    explicit = os.environ.get("LLM_PROVIDER", "").lower()
    if explicit and explicit in PROVIDERS:
        cfg = PROVIDERS[explicit]
        if os.environ.get(cfg["env_key"], ""):
            return {**cfg, "name": explicit}

    # Auto-detect: first key found wins
    for name, cfg in PROVIDERS.items():
        if os.environ.get(cfg["env_key"], ""):
            return {**cfg, "name": name}
    return None


def get_provider_info() -> dict:
    """Return info about the currently active LLM provider."""
    p = _get_active_provider()
    if p:
        return {
            "active": True,
            "name": p["name"],
            "label": p["label"],
            "model": os.environ.get(p["model_env"], p["default_model"]),
        }
    return {"active": False, "name": None, "label": "None — set GROQ_API_KEY or OPENROUTER_API_KEY", "model": None}


def chat(
    prompt: str,
    system: str = "You are a helpful e-commerce research assistant.",
    max_tokens: int = 512,
    temperature: float = 0.3,
) -> str:
    """
    Send a chat message to the active LLM provider.
    Returns the response text, or raises RuntimeError if no provider is configured.
    """
    provider = _get_active_provider()
    if not provider:
        raise RuntimeError(
            "No LLM provider configured. Set GROQ_API_KEY, OPENROUTER_API_KEY, "
            "or GEMINI_API_KEY in your .env or Codespaces Secrets."
        )

    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError("openai package not installed. Run: pip install openai")

    api_key = os.environ.get(provider["env_key"])
    model = os.environ.get(provider["model_env"], provider["default_model"])

    extra_headers = {}
    if provider["name"] == "openrouter":
        extra_headers = {
            "HTTP-Referer": "https://github.com/resale-scanner",
            "X-Title": "Resale Scanner",
        }

    client = OpenAI(
        api_key=api_key,
        base_url=provider["base_url"],
        default_headers=extra_headers if extra_headers else None,
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response.choices[0].message.content.strip()


def analyze_product(title: str, source_price: float, sale_price: float,
                    category: str, margin_pct: float, score: float) -> str:
    """
    Ask the LLM to give a short analysis of a product candidate.
    Returns a 2-3 sentence plain-text analysis.
    """
    prompt = f"""
Analyze this eBay resale product candidate in 2-3 sentences. Be concise and practical.

Product: {title}
Category: {category}
Source cost: ${source_price:.2f}
eBay sale price: ${sale_price:.2f}
Net margin (before cashback): {margin_pct:.1f}%
Resale score: {score:.0f}/100

Focus on: Is this a good product to resell? Any risks? Any tips to improve margin?
"""
    return chat(prompt, max_tokens=200)
