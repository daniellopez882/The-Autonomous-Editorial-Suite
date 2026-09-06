# ADR 0001 — The login gate fails closed, and its secrets never live in the repository

**Status:** accepted · **Date:** 2026-09-06 (records the decision made in PR #1; the preflight was added in the follow-up)

## Context

`auth.py` signed the session cookie with

```python
secret_key = os.getenv("APP_SECRET_KEY", "some_random_secret_key")
```

streamlit-authenticator signs its cookie with that key, so anyone who had read
the repository could forge a valid session and skip the login form. The
default credentials were `admin` / `admin`. `ENABLE_AUTH=false` switched the
gate off with no guard. And `setup_auth()`, a second implementation reading a
`config.yaml`, called a `create_default_config()` whose body was `pass` and then
opened the file it had not written.

Streamlit has no startup hook, so even after the pull request made these
refusals, they happened at render time: a container whose process was up and
whose health check said "ok" while every page showed "Authentication is
misconfigured".

## Decision

1. **One implementation**, driven by environment variables. No credentials file
   that could be committed with a password hash in it.
2. **Production requires real secrets.** With `ENVIRONMENT=production`,
   `APP_SECRET_KEY` must be set and not the old placeholder, `APP_PASSWORD` must
   be set and not `admin` / `password` / `changeme` / empty, and `ENABLE_AUTH=false`
   is refused. Development gets a random per-process signing key — sessions do
   not survive a restart, which is the price of never shipping a known key.
3. **The refusal happens before Streamlit starts.** `auth.validate_configuration()`
   performs the same checks without rendering anything; `preflight.py` calls it
   and exits 1, and the container entrypoint runs the preflight before
   `streamlit`. The image sets `ENVIRONMENT=production`, so a container started
   without those variables exits with the reason. CI asserts that from outside.
4. `check_authentication()` keeps the render-time refusal for the case where
   the app is run directly, and the tests cover both paths and both
   streamlit-authenticator hashing APIs (the dependency range is pinned; the
   0.3 and 0.4 APIs differ).

## Consequences

- A forged cookie needs the deployment's key, not a string from GitHub.
- One user, one password. It is a single-operator tool; multi-user access would
  need a user store and is out of scope.
- Setting `ENVIRONMENT` correctly in deployment is what makes the guards bite;
  the image sets it, compose passes it through.
- Rotating `APP_SECRET_KEY` logs everyone out, which is the intended effect.
