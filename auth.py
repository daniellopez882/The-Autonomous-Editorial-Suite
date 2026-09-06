"""
auth.py
Authentication for the Streamlit app.

Four defects are fixed here.

1. **The session cookie was signed with a key committed to the repository.**

       secret_key = os.getenv("APP_SECRET_KEY", "some_random_secret_key")

   streamlit-authenticator signs the auth cookie with that key. Anyone reading
   this file could forge a valid session cookie and skip the login form
   entirely. A default is now refused in production, and a random per-process
   key is generated for local development.

2. **Default credentials were `admin` / `admin`.** With `APP_PASSWORD` unset,
   the app accepted them. Production now refuses to start without an explicit
   password.

3. **`setup_auth()` could not work.** When `config.yaml` was absent it called
   `create_default_config()`, whose entire body is `pass`, then opened the file
   it had not written -- `FileNotFoundError`. That function was dead code
   alongside `check_authentication()`, which is what the app actually calls;
   the two disagreed about where credentials come from. The file-based path is
   gone, leaving one implementation.

4. **`ENABLE_AUTH=false` disabled authentication with no guard.** It is
   intended for local development, and is now refused in production.
"""

from __future__ import annotations

import os
import secrets

import streamlit as st
import streamlit_authenticator as stauth
from dotenv import load_dotenv

from logger import log_progress

load_dotenv()

INSECURE_SECRET = "some_random_secret_key"  # noqa: S105 - the value being rejected
INSECURE_PASSWORDS = frozenset({"admin", "password", "changeme", ""})

COOKIE_NAME = "content_pipeline_auth"
COOKIE_EXPIRY_DAYS = 30


class AuthConfigurationError(RuntimeError):
    """Raised when authentication is configured in a way that is not safe to run."""


def is_production() -> bool:
    return os.getenv("ENVIRONMENT", "development").lower() == "production"


def auth_enabled() -> bool:
    """
    Whether the login gate is active.

    Disabling it is a development convenience. Doing so in production would
    publish the whole application, so it is refused there.
    """
    disabled = os.getenv("ENABLE_AUTH", "true").lower() == "false"
    if disabled and is_production():
        raise AuthConfigurationError(
            "ENABLE_AUTH=false is not permitted when ENVIRONMENT=production."
        )
    return not disabled


def _resolve_secret_key() -> str:
    """
    The cookie signing key.

    Production requires a real one. Development gets a random per-process key,
    which means sessions do not survive a restart -- an acceptable trade for
    never shipping a known signing key.
    """
    key = os.getenv("APP_SECRET_KEY", "")
    if key and key != INSECURE_SECRET:
        return key

    if is_production():
        raise AuthConfigurationError(
            "APP_SECRET_KEY is unset or still the placeholder. The auth cookie "
            "is signed with it, so a known value lets anyone forge a session. "
            'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(32))"'
        )

    log_progress(
        "APP_SECRET_KEY not set; generating a random key for this process. "
        "Sessions will not survive a restart."
    )
    return secrets.token_urlsafe(32)


def _resolve_password() -> str:
    password = os.getenv("APP_PASSWORD", "")
    if is_production() and password.lower() in INSECURE_PASSWORDS:
        raise AuthConfigurationError(
            "APP_PASSWORD is unset or a well-known value. Set a real password "
            "before running with ENVIRONMENT=production."
        )
    return password or "admin"


def _hash_password(password: str) -> str:
    """
    Hash a password with whichever streamlit-authenticator API is installed.

    The original call was ``stauth.Hasher([password]).generate()[0]``. That is
    the 0.3.x API; in 0.4.x ``Hasher.__init__`` takes no arguments and hashing
    moved to ``Hasher.hash``, so the call raises

        TypeError: Hasher.__init__() takes 1 positional argument but 2 were given

    The dependency was unpinned, so which API you got depended on when you
    installed. Both are handled, and the range is pinned.
    """
    hasher = stauth.Hasher
    if hasattr(hasher, "hash"):
        try:
            return hasher.hash(password)  # 0.4.x static form
        except TypeError:
            return hasher().hash(password)  # 0.4.x instance form
    return hasher([password]).generate()[0]  # 0.3.x


def get_auth_config_from_env() -> dict:
    """
    Build the authenticator configuration from environment variables.

    Kept out of a YAML file on purpose: a config file holding a password hash
    tends to get committed.
    """
    username = os.getenv("APP_USERNAME", "admin")
    password = _resolve_password()
    secret_key = _resolve_secret_key()

    hashed = _hash_password(password)

    return {
        "credentials": {
            "usernames": {
                username: {
                    "name": os.getenv("APP_DISPLAY_NAME", "Admin User"),
                    "password": hashed,
                    "email": os.getenv("APP_EMAIL", "admin@example.com"),
                }
            }
        },
        "cookie": {
            "name": COOKIE_NAME,
            "key": secret_key,
            "expiry_days": COOKIE_EXPIRY_DAYS,
        },
    }


def validate_configuration() -> dict:
    """
    Check the authentication configuration without rendering anything.

    ``check_authentication`` fails closed, but only when a page renders; a
    container whose process is up and whose health check says "ok" while
    every request shows a configuration error is not a healthy deployment.
    ``preflight.py`` calls this before Streamlit starts and exits non-zero on
    ``AuthConfigurationError``.
    """
    enabled = auth_enabled()
    if enabled:
        _resolve_secret_key()
        _resolve_password()
    return {
        "production": is_production(),
        "auth_enabled": enabled,
        "username": os.getenv("APP_USERNAME", "admin"),
    }


def build_authenticator(config: dict | None = None) -> stauth.Authenticate:
    """
    Construct the authenticator. Separated so it can be tested.

    The fifth positional argument (``pre_authorized``) is gone: 0.4.x raises
    ``DeprecationError`` when it is passed, and the pinned range resolves to
    0.4.x on a fresh install. Booting the container showed the login page
    replaced by that traceback -- the suite had never constructed the
    authenticator. 0.3.x treats the argument as optional, so omitting it is
    right for both.
    """
    config = config or get_auth_config_from_env()
    return stauth.Authenticate(
        config["credentials"],
        config["cookie"]["name"],
        config["cookie"]["key"],
        config["cookie"]["expiry_days"],
    )


def check_authentication() -> bool:
    """
    Gate the application.

    Usage:
        if not check_authentication():
            st.stop()
    """
    try:
        if not auth_enabled():
            log_progress("Authentication disabled (development only).")
            return True
        authenticator = build_authenticator()
    except AuthConfigurationError as exc:
        # Fail closed and loudly. Previously an unsafe configuration simply ran.
        st.error(f"Authentication is misconfigured: {exc}")
        log_progress(f"Auth configuration rejected: {exc}")
        return False

    authenticator.login("main")

    status = st.session_state.get("authentication_status")
    if status:
        authenticator.logout("Logout", "sidebar")
        return True
    if status is False:
        st.error("Username or password is incorrect")
        return False

    st.warning("Please enter your username and password")
    return False
