"""
LLM Provider Module
====================
Centralised interface for calling LLMs.  Supports **Gemini** and **Groq**.

Provider is selected by the ``provider`` argument or auto-detected from
environment variables (``GEMINI_API_KEY`` → Gemini, ``GROQ_API_KEY`` → Groq).
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Supported providers & models
# ---------------------------------------------------------------------------

_GEMINI_MODEL = "gemini-2.0-flash"
_GROQ_MODEL = "llama-3.3-70b-versatile"

# ---------------------------------------------------------------------------
# Lazy singletons (configured once on first use)
# ---------------------------------------------------------------------------

_gemini_configured = False
_groq_client = None


def _init_gemini() -> None:
    global _gemini_configured
    if _gemini_configured:
        return
    import google.generativeai as genai

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY is not set. "
            "Add it to your .env file or use --llm groq instead."
        )
    genai.configure(api_key=api_key)
    _gemini_configured = True


def _init_groq():
    global _groq_client
    if _groq_client is not None:
        return _groq_client
    from groq import Groq

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY is not set. "
            "Get a free key at https://console.groq.com and add it to .env."
        )
    _groq_client = Groq(api_key=api_key)
    return _groq_client


# ---------------------------------------------------------------------------
# Auto-detect provider
# ---------------------------------------------------------------------------


def detect_provider() -> str:
    """Return 'gemini' or 'groq' based on which API key is available."""
    if os.getenv("GEMINI_API_KEY"):
        return "gemini"
    if os.getenv("GROQ_API_KEY"):
        return "groq"
    raise EnvironmentError(
        "No LLM API key found. Set GEMINI_API_KEY or GROQ_API_KEY in .env."
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def call_llm(
    system_prompt: str,
    user_prompt: str,
    provider: str = "gemini",
) -> str:
    """
    Send a system + user prompt to the selected LLM and return the raw text.

    Parameters
    ----------
    system_prompt : str
        System / instruction prompt.
    user_prompt : str
        User message content.
    provider : str
        ``"gemini"`` or ``"groq"``.

    Returns
    -------
    str
        The model's response text.
    """
    provider = provider.lower()

    if provider == "gemini":
        return _call_gemini(system_prompt, user_prompt)
    elif provider == "groq":
        return _call_groq(system_prompt, user_prompt)
    else:
        raise ValueError(f"Unknown LLM provider '{provider}'. Use 'gemini' or 'groq'.")


# ---------------------------------------------------------------------------
# Provider implementations
# ---------------------------------------------------------------------------


def _call_gemini(system_prompt: str, user_prompt: str) -> str:
    import google.generativeai as genai

    _init_gemini()

    model = genai.GenerativeModel(
        model_name=_GEMINI_MODEL,
        system_instruction=system_prompt,
    )
    try:
        response = model.generate_content(user_prompt)
    except Exception as exc:
        raise RuntimeError(f"Gemini API call failed: {exc}") from exc

    return response.text.strip()


def _call_groq(system_prompt: str, user_prompt: str) -> str:
    client = _init_groq()

    try:
        response = client.chat.completions.create(
            model=_GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=4096,
        )
    except Exception as exc:
        raise RuntimeError(f"Groq API call failed: {exc}") from exc

    return response.choices[0].message.content.strip()
