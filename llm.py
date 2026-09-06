"""
llm.py
The one place the model client is built, and it is built on first use.

Why this exists
---------------
``content_generation_crew.py`` constructed the client at import time::

    deepseek_llm = ChatOpenAI(model="deepseek-chat", openai_api_key=api_key, ...)

With ``DEEPSEEK_API_KEY`` unset, ``api_key`` is ``None`` and the constructor
raises ``OpenAIError: Missing credentials``. ``app.py`` imported the crew at
the top of the script, so a deployment without the key did not show a login
form or an error message about the key: Streamlit rendered the import
traceback. The same line also wrote the key into ``OPENAI_API_KEY`` for the
whole process as a side effect of being imported.

``build_llm`` is called when a crew is created -- which happens when a logged-in
user clicks generate -- and raises ``LLMNotConfigured`` with an instruction the
operator can act on. Nothing is built at import.
"""

from __future__ import annotations

import os

DEFAULT_MODEL = "deepseek-chat"
DEFAULT_BASE_URL = "https://api.deepseek.com/v1"


class LLMNotConfigured(RuntimeError):
    """Raised when content generation is requested without a model key."""


def llm_configured() -> bool:
    """Whether a model key is present. Used by the preflight and the UI."""
    return bool(os.getenv("DEEPSEEK_API_KEY", "").strip())


def build_llm():
    """
    Construct the DeepSeek client through LangChain's OpenAI-compatible class.

    Imported lazily: ``langchain_openai`` pulls in the OpenAI SDK, which the
    auth module and the preflight do not need.
    """
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise LLMNotConfigured(
            "DEEPSEEK_API_KEY is not set. Content generation needs a model key; "
            "add it to .env or the environment and restart."
        )

    # CrewAI and LangChain look for OPENAI_API_KEY in places that do not take
    # the client's key as an argument. Mirror it only when nothing else set it.
    os.environ.setdefault("OPENAI_API_KEY", api_key)

    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=os.getenv("DEEPSEEK_MODEL", DEFAULT_MODEL),
        openai_api_key=api_key,
        openai_api_base=os.getenv("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL),
        temperature=0.7,
        max_tokens=4000,
    )
