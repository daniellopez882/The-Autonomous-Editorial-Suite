"""
The preflight refuses an unsafe production configuration before Streamlit starts.

Streamlit has no startup hook, so ``auth.check_authentication`` could only fail
closed at render time -- the process was up, the health check said "ok", and
every page said "Authentication is misconfigured". The container entrypoint
runs ``preflight.py`` first; CI asserts the exit codes from outside.
"""

from __future__ import annotations

import importlib

import pytest

import auth as auth_module
import preflight as preflight_module


@pytest.fixture
def modules(monkeypatch):
    """Fresh copies of auth and preflight after the environment is arranged."""
    for var in ("ENVIRONMENT", "APP_SECRET_KEY", "APP_PASSWORD", "ENABLE_AUTH", "DEEPSEEK_API_KEY"):
        monkeypatch.delenv(var, raising=False)

    def load():
        auth = importlib.reload(auth_module)
        pre = importlib.reload(preflight_module)
        return auth, pre

    return load


class TestValidateConfiguration:
    def test_development_passes_with_nothing_set(self, modules):
        auth, _ = modules()
        summary = auth.validate_configuration()
        assert summary["auth_enabled"] is True
        assert summary["username"] == "admin"
        assert summary["production"] is False

    def test_production_refuses_a_missing_secret(self, modules, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("APP_PASSWORD", "a-real-password")
        auth, _ = modules()
        with pytest.raises(auth.AuthConfigurationError, match="APP_SECRET_KEY"):
            auth.validate_configuration()

    def test_production_refuses_a_well_known_password(self, modules, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("APP_SECRET_KEY", "a-genuinely-random-value")
        monkeypatch.setenv("APP_PASSWORD", "admin")
        auth, _ = modules()
        with pytest.raises(auth.AuthConfigurationError, match="APP_PASSWORD"):
            auth.validate_configuration()

    def test_production_refuses_a_disabled_gate(self, modules, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("ENABLE_AUTH", "false")
        auth, _ = modules()
        with pytest.raises(auth.AuthConfigurationError, match="ENABLE_AUTH"):
            auth.validate_configuration()

    def test_production_passes_with_a_real_configuration(self, modules, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("APP_SECRET_KEY", "a-genuinely-random-value")
        monkeypatch.setenv("APP_PASSWORD", "a-real-password")
        auth, _ = modules()
        summary = auth.validate_configuration()
        assert summary["production"] is True
        assert summary["auth_enabled"] is True

    def test_validation_renders_nothing(self, modules, monkeypatch):
        """It must be callable outside a Streamlit run: the entrypoint calls it."""
        auth, _ = modules()
        monkeypatch.setattr(auth.st, "error", lambda *a, **k: pytest.fail("rendered a widget"))
        auth.validate_configuration()


class TestPreflightExitCodes:
    def test_refusal_is_exit_1_with_the_reason_on_stderr(self, modules, monkeypatch, capsys):
        monkeypatch.setenv("ENVIRONMENT", "production")
        _, pre = modules()
        assert pre.main([]) == 1
        assert "APP_SECRET_KEY" in capsys.readouterr().err

    def test_a_safe_start_is_exit_0(self, modules, monkeypatch, capsys):
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("APP_SECRET_KEY", "a-genuinely-random-value")
        monkeypatch.setenv("APP_PASSWORD", "a-real-password")
        _, pre = modules()
        assert pre.main([]) == 0
        out = capsys.readouterr()
        assert "production" in out.out
        assert "DEEPSEEK_API_KEY not set" in out.err

    def test_a_present_model_key_is_reported(self, modules, monkeypatch, capsys):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-looks-real")
        _, pre = modules()
        assert pre.main([]) == 0
        assert "generation is available" in capsys.readouterr().out
