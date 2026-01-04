#!/usr/bin/env bash
set -euo pipefail

# Activate local venv if present (Render creates its own environment but this helps local use)
if [ -f ".venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

# Gunicorn settings
GUNICORN_WORKERS=${GUNICORN_WORKERS:-3}
PORT=${PORT:-8000}

exec gunicorn --workers "$GUNICORN_WORKERS" --timeout 120 --bind 0.0.0.0:"$PORT" run:app
