"""
LLM provider configuration.

Routes the OpenAI Agents SDK to Google Gemini via Gemini's OpenAI-compatible
endpoint, authenticated with GEMINI_API_KEY from the environment/.env.
"""

import os

from dotenv import load_dotenv
from openai import AsyncOpenAI

from agents import (
    set_default_openai_api,
    set_default_openai_client,
    set_tracing_disabled,
)

load_dotenv(override=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_BASE_URL = os.getenv(
    "GEMINI_BASE_URL",
    "https://generativelanguage.googleapis.com/v1beta/openai/",
)
# Model used by all agents. Override with the GEMINI_MODEL env var if desired.
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

_configured = False


def configure_llm() -> None:
    """Point the Agents SDK at Gemini. Idempotent; safe to call repeatedly."""
    global _configured
    if _configured:
        return
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable is not set")

    client = AsyncOpenAI(api_key=GEMINI_API_KEY, base_url=GEMINI_BASE_URL)
    # use_for_tracing=False: tracing export would need an OpenAI key, which we
    # don't use. Disable tracing entirely to avoid noisy auth errors.
    set_default_openai_client(client, use_for_tracing=False)
    set_default_openai_api("chat_completions")
    set_tracing_disabled(True)
    _configured = True
