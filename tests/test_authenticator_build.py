"""
The authenticator can be constructed with the installed streamlit-authenticator.

Reproduced defect: ``build_authenticator`` passed a fifth positional argument,
``pre_authorized``. streamlit-authenticator 0.4.x raises ``DeprecationError``
for it, and the pinned range resolves to 0.4.x on a fresh install, so the
container served a traceback where the login form should have been. The suite
tested the key and password rules but never constructed the authenticator.
"""

from __future__ import annotations

import importlib

import pytest

import auth as auth_module


@pytest.fixture
def auth(monkeypatch):
    for var in ("ENVIRONMENT", "APP_SECRET_KEY", "APP_PASSWORD", "ENABLE_AUTH"):
        monkeypatch.delenv(var, raising=False)
    return importlib.reload(auth_module)


class TestConstruction:
    def test_the_authenticator_constructs_in_development(self, auth):
        authenticator = auth.build_authenticator()
        assert authenticator is not None

    def test_the_authenticator_constructs_in_production_with_real_values(self, auth, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("APP_SECRET_KEY", "a-genuinely-random-value")
        monkeypatch.setenv("APP_PASSWORD", "a-real-password")
        assert auth.build_authenticator() is not None

    def test_the_config_carries_no_removed_field(self, auth):
        config = auth.get_auth_config_from_env()
        assert set(config) == {"credentials", "cookie"}
        assert set(config["cookie"]) == {"name", "key", "expiry_days"}

    def test_the_password_is_stored_hashed(self, auth, monkeypatch):
        monkeypatch.setenv("APP_PASSWORD", "plain-text-password")
        config = auth.get_auth_config_from_env()
        stored = config["credentials"]["usernames"]["admin"]["password"]
        assert stored != "plain-text-password"
        assert stored.startswith("$2")  # bcrypt
