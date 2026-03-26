"""
config/settings.py
-----------------
LLM configuration and shared agent defaults for the Marketing AI Crew.
Supports Gemini (default) via LLM_PROVIDER=gemini in .env.

LLM_PROVIDER options:
  gemini  — Google Gemini via GEMINI_API_KEY
  openai  — OpenAI via OPENAI_API_KEY

Caches the LLM instance as a module-level singleton to avoid repeated
construction (performance optimization — reduces LLM init overhead).
"""

import os
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv(override=True)

# ── Read provider from .env ───────────────────────────────────────────────────
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()
LLM_MODEL    = os.getenv("LLM_MODEL", "gemini-2.5-flash")

# ── Shared agent defaults (applied to every Agent()) ─────────────────────────
AGENT_DEFAULTS = {
    "verbose":          True,
    "allow_delegation": False,
    "max_iter":         8,       # prevent runaway reasoning loops
    "max_retry_limit":  2,
}


@lru_cache(maxsize=1)
def get_llm():
    """
    Returns a cached LLM instance.
    Called exactly once per process — subsequent calls return the cached object.
    """
    from crewai import LLM

    if LLM_PROVIDER == "gemini":
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            raise EnvironmentError(
                "GEMINI_API_KEY is not set. Add it to marketing_ai_crew/.env"
            )
        return LLM(
            model=f"gemini/{LLM_MODEL}",
            api_key=api_key,
        )

    elif LLM_PROVIDER == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            raise EnvironmentError(
                "OPENAI_API_KEY is not set. Add it to marketing_ai_crew/.env"
            )
        return LLM(
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            api_key=api_key,
        )

    elif LLM_PROVIDER == "groq":
        api_key = os.getenv("GROQ_API_KEY", "")
        if not api_key:
            raise EnvironmentError("GROQ_API_KEY is not set.")
        return LLM(
            model=f"groq/{os.getenv('LLM_MODEL', 'llama3-8b-8192')}",
            api_key=api_key,
        )

    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER='{LLM_PROVIDER}'. "
            "Supported: gemini | openai | groq"
        )
