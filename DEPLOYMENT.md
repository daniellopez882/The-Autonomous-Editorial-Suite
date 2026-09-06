# Deployment

The previous version of this file was upstream's guide
([`Ismail-2001/Content-Generation-Pipeline-Agent`](https://github.com/Ismail-2001/Content-Generation-Pipeline-Agent))
for Streamlit Community Cloud, Heroku-style hosts and a root container. This
is what this repository's image needs.

## What the service needs

| | Required | Why |
|---|---|---|
| `APP_SECRET_KEY` | yes, in production | Signs the session cookie; the preflight refuses a missing or placeholder value |
| `APP_PASSWORD` | yes, in production | `admin`, `password`, `changeme` and empty are refused |
| `DEEPSEEK_API_KEY` | to generate | The app starts without it and refuses each generation with a sentence naming the variable |
| `APP_USERNAME` | no | Defaults to `admin` |

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"   # a signing key
```

## Container

```bash
docker build -t editorial-suite .
docker run -d -p 8501:8501 \
  -e APP_SECRET_KEY=... -e APP_PASSWORD=... -e DEEPSEEK_API_KEY=... \
  -v "$PWD/generated_content:/app/generated_content" \
  editorial-suite
curl -s localhost:8501/_stcore/health     # ok
```

The image runs as uid 10001 with `ENVIRONMENT=production`. Its entrypoint runs
`preflight.py` first: a start without the two secrets exits with the reason and
Streamlit never binds the port. `/_stcore/health` is Streamlit's own liveness
endpoint and is what the image's `HEALTHCHECK` probes.

Or with compose, which marks the two secrets required:

```bash
APP_SECRET_KEY=... APP_PASSWORD=... DEEPSEEK_API_KEY=... docker compose up --build
```

## Without a container

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env
.venv/bin/python preflight.py      # says what is missing
.venv/bin/streamlit run app.py
```

Set `ENVIRONMENT=production` anywhere reachable from the internet; the
refusals above apply only then. Behind a reverse proxy, terminate TLS there and
enable Streamlit's `--server.enableXsrfProtection` (the default).

## Before exposing it

- One user, one password. Put the app behind your own SSO or VPN if more than
  one person needs it.
- Each generation is several model calls billed to `DEEPSEEK_API_KEY`; there is
  no quota.
- Read [docs/threat-model.md](docs/threat-model.md) for what remains open.
