#!/bin/sh
# Refuse an unsafe configuration before Streamlit binds a port, then hand the
# process over to streamlit so it is PID 1 and receives SIGTERM directly.
set -e

python preflight.py

exec streamlit run app.py \
    --server.port="${STREAMLIT_SERVER_PORT:-8501}" \
    --server.address="${STREAMLIT_SERVER_ADDRESS:-0.0.0.0}" \
    --server.headless=true
