"""
preflight.py
Refuse to start on an unsafe configuration; say what is missing otherwise.

Streamlit has no startup hook. ``auth.check_authentication`` fails closed when
the page renders, but a container whose process is up and whose health check
answers "ok" while every request shows "Authentication is misconfigured" is not
a healthy deployment. The container entrypoint runs this before ``streamlit``,
so a production start without ``APP_SECRET_KEY`` or with a well-known
``APP_PASSWORD`` exits with the reason instead.

Exit codes: 0 safe to start, 1 refused.
"""

from __future__ import annotations

import sys

from auth import AuthConfigurationError, is_production, validate_configuration
from llm import llm_configured


def main(argv: list[str] | None = None) -> int:
    del argv  # no options yet
    try:
        summary = validate_configuration()
    except AuthConfigurationError as exc:
        print(f"preflight: refusing to start: {exc}", file=sys.stderr)
        return 1

    mode = "production" if is_production() else "development"
    gate = "enabled" if summary["auth_enabled"] else "DISABLED (development only)"
    print(f"preflight: {mode}; authentication {gate}; user {summary['username']!r}")

    if llm_configured():
        print("preflight: DEEPSEEK_API_KEY present; generation is available")
    else:
        # Not fatal: the app serves its login page and reports the missing key
        # when generation is attempted. It is still worth saying out loud.
        print(
            "preflight: DEEPSEEK_API_KEY not set; the app will start but every "
            "generation attempt will be refused until it is",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
