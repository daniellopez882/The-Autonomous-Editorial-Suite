# syntax=docker/dockerfile:1
#
# Fixes over the previous image:
#   * ran as root; now uid 10001
#   * single stage with build-essential in the runtime layer; two stages now
#   * curl installed for the HEALTHCHECK; the probe is Python
#   * no .dockerignore, so COPY . . took .git, virtualenvs and any .env
#   * nothing checked the configuration before Streamlit started: with the
#     login gate misconfigured the process was "healthy" while every page said
#     "Authentication is misconfigured"; and without DEEPSEEK_API_KEY the old
#     app died importing the crew. The entrypoint runs preflight.py first and
#     the image defaults to ENVIRONMENT=production, which refuses a missing
#     APP_SECRET_KEY or a well-known APP_PASSWORD.

FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    ENVIRONMENT=production \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_PORT=8501

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --create-home app

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY --chown=app:app . .

# Generated articles and the version database are written here; mount a volume.
RUN mkdir -p /app/generated_content && chown -R app:app /app/generated_content
VOLUME ["/app/generated_content"]

USER app

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=4).status == 200 else 1)"]

ENTRYPOINT ["./docker-entrypoint.sh"]
