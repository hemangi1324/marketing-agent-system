"""
config/settings.py
All configuration lives here. OpenAI is the default.
To switch models, just change LLM_MODEL in .env
"""

import os
from dotenv import load_dotenv

load_dotenv()

LLM_PROVIDER    = os.getenv("LLM_PROVIDER", "gemini")
LLM_MODEL       = os.getenv("LLM_MODEL", "gemini-2.5-flash")
OUTPUT_DIR      = os.getenv("OUTPUT_DIR", "outputs")

os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_llm():
    if LLM_PROVIDER == "ollama":
        return f"ollama/{LLM_MODEL}"

    elif LLM_PROVIDER == "groq":
        os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY", "")
        return f"groq/{LLM_MODEL}"

    elif LLM_PROVIDER == "openai":
        os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")
        return LLM_MODEL

    elif LLM_PROVIDER == "anthropic":
        os.environ["ANTHROPIC_API_KEY"] = os.getenv("ANTHROPIC_API_KEY", "")
        return f"anthropic/{LLM_MODEL}"

    elif LLM_PROVIDER == "gemini":
        os.environ["GEMINI_API_KEY"] = os.getenv("GEMINI_API_KEY", "")
        return f"gemini/{LLM_MODEL}"

    else:
        raise ValueError(f"Unknown LLM_PROVIDER='{LLM_PROVIDER}'.")

# Shared defaults for all agents
AGENT_DEFAULTS = {
    "verbose": True,
    "allow_delegation": False,
    "max_iter": 3,
    "max_retry_limit": 2,
}
