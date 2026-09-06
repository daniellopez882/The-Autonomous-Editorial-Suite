"""
Tests for auth.

The defect that matters most: the session cookie was signed with a key
committed to the repository.

    secret_key = os.getenv("APP_SECRET_KEY", "some_random_secret_key")

streamlit-authenticator signs the auth cookie with that value, so anyone who
read this file could forge a valid session and skip the login form. Default
credentials were ``admin`` / ``admin`` alongside it, and ``ENABLE_AUTH=false``
turned the gate off entirely with no guard on where it was used.

``setup_auth()`` was separately unusable: with no ``config.yaml`` it called
``create_default_config()``, whose whole body is ``pass``, then opened the file
it had not written.
"""

from __future__ import annotations

import importlib

import pytest

streamlit = pytest.importorskip(
    "streamlit", reason="streamlit is a runtime dependency; installed in CI"
)
pytest.importorskip("streamlit_authenticator")

import auth as auth_module  # noqa: E402


@pytest.fixture
def auth(monkeypatch):
    """A freshly imported auth module with a clean environment."""
    for key in (
        "ENVIRONMENT",
        "ENABLE_AUTH",
        "APP_SECRET_KEY",
        "APP_PASSWORD",
        "APP_USERNAME",
    ):
        monkeypatch.delenv(key, raising=False)
    return importlib.reload(auth_module)


class TestSecretKey:
    def test_the_committed_placeholder_is_never_returned(self, auth):
        """The exact value that was signing production cookies."""
        assert auth._resolve_secret_key() != auth.INSECURE_SECRET

    def test_development_gets_a_random_key_each_time(self, auth):
        assert auth._resolve_secret_key() != auth._resolve_secret_key()

    def test_development_keys_are_long_enough_to_be_useless_to_guess(self, auth):
        assert len(auth._resolve_secret_key()) >= 32

    def test_production_refuses_an_unset_key(self, auth, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        with pytest.raises(auth.AuthConfigurationError, match="APP_SECRET_KEY"):
            auth._resolve_secret_key()

    def test_production_refuses_the_placeholder_explicitly_set(self, auth, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("APP_SECRET_KEY", auth.INSECURE_SECRET)
        with pytest.raises(auth.AuthConfigurationError):
            auth._resolve_secret_key()

    def test_production_accepts_a_real_key(self, auth, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("APP_SECRET_KEY", "a-genuinely-random-value-here")
        assert auth._resolve_secret_key() == "a-genuinely-random-value-here"


class TestPassword:
    @pytest.mark.parametrize("value", ["admin", "password", "changeme", ""])
    def test_production_refuses_well_known_passwords(self, auth, monkeypatch, value):
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("APP_PASSWORD", value)
        with pytest.raises(auth.AuthConfigurationError, match="APP_PASSWORD"):
            auth._resolve_password()

    def test_production_refuses_an_unset_password(self, auth, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        with pytest.raises(auth.AuthConfigurationError):
            auth._resolve_password()

    def test_development_tolerates_the_default(self, auth):
        assert auth._resolve_password() == "admin"

    def test_production_accepts_a_real_password(self, auth, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("APP_PASSWORD", "a-real-password")
        assert auth._resolve_password() == "a-real-password"


class TestAuthToggle:
    def test_enabled_by_default(self, auth):
        assert auth.auth_enabled() is True

    def test_can_be_disabled_in_development(self, auth, monkeypatch):
        monkeypatch.setenv("ENABLE_AUTH", "false")
        assert auth.auth_enabled() is False

    def test_cannot_be_disabled_in_production(self, auth, monkeypatch):
        """Turning the gate off in production publishes the whole app."""
        monkeypatch.setenv("ENABLE_AUTH", "false")
        monkeypatch.setenv("ENVIRONMENT", "production")
        with pytest.raises(auth.AuthConfigurationError, match="ENABLE_AUTH"):
            auth.auth_enabled()


class TestConfigShape:
    def test_password_is_stored_hashed(self, auth, monkeypatch):
        monkeypatch.setenv("APP_PASSWORD", "hunter2")
        config = auth.get_auth_config_from_env()
        stored = config["credentials"]["usernames"]["admin"]["password"]
        assert stored != "hunter2"
        assert len(stored) > 20

    def test_username_is_configurable(self, auth, monkeypatch):
        monkeypatch.setenv("APP_USERNAME", "editor")
        assert "editor" in auth.get_auth_config_from_env()["credentials"]["usernames"]

    def test_config_carries_every_key_the_authenticator_needs(self, auth):
        config = auth.get_auth_config_from_env()
        assert set(config) == {"credentials", "cookie"}
        assert set(config["cookie"]) == {"name", "key", "expiry_days"}


class TestDeadCodeIsGone:
    def test_the_broken_file_based_path_was_removed(self, auth):
        """
        setup_auth() called create_default_config(), whose body is `pass`, then
        opened the file it had not written -- FileNotFoundError every time.
        """
        assert not hasattr(auth, "create_default_config")
        assert not hasattr(auth, "setup_auth")

    def test_one_entry_point_remains(self, auth):
        assert callable(auth.check_authentication)
