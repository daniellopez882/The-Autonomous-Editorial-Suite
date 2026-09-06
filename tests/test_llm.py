"""
The model client is built on first use, not at import.

Reproduced defect: ``content_generation_crew.py`` ran
``ChatOpenAI(model="deepseek-chat", openai_api_key=None, ...)`` at import time
when ``DEEPSEEK_API_KEY`` was unset, which raises
``OpenAIError: Missing credentials``. ``app.py`` imported the crew at the top
of the script, so a deployment without the key rendered the import traceback
instead of a login form.
"""

from __future__ import annotations

import pytest

import llm


@pytest.fixture
def no_keys(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


class TestWithoutAKey:
    def test_importing_the_module_needs_nothing(self, no_keys):
        assert llm.llm_configured() is False

    def test_building_the_client_is_a_clear_error(self, no_keys):
        with pytest.raises(llm.LLMNotConfigured, match="DEEPSEEK_API_KEY"):
            llm.build_llm()

    def test_a_blank_key_counts_as_unset(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "   ")
        assert llm.llm_configured() is False
        with pytest.raises(llm.LLMNotConfigured):
            llm.build_llm()


class TestWithAKey:
    def test_the_client_targets_deepseek(self, monkeypatch, no_keys):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-looks-real")
        client = llm.build_llm()
        assert client.model_name == llm.DEFAULT_MODEL
        assert client.openai_api_base == llm.DEFAULT_BASE_URL

    def test_model_and_base_url_are_overridable(self, monkeypatch, no_keys):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-looks-real")
        monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-reasoner")
        monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://example.test/v1")
        client = llm.build_llm()
        assert client.model_name == "deepseek-reasoner"
        assert client.openai_api_base == "https://example.test/v1"

    def test_an_existing_openai_key_is_not_overwritten(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-deepseek")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-someone-elses")
        llm.build_llm()
        import os

        assert os.environ["OPENAI_API_KEY"] == "sk-someone-elses"
