#!/usr/bin/env bash
# Starts the backend on a throwaway SQLite database filled with demo data, serving the built frontend.
# Used by playwright.config.ts; run `npm run build` first.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$HERE/../../backend"
PYTHON="${PYTHON:-$BACKEND/.venv/bin/python}"
[ -x "$PYTHON" ] || PYTHON=python3
DATA="$(mktemp -d)"
export DATABASE_URL="sqlite:///$DATA/e2e.db"
export FRONTEND_DIST="$HERE/../dist"
export PUBLIC_BASE_URL="http://127.0.0.1:${E2E_PORT:-8100}"
export SECRET_KEY="e2e-only-secret-key-not-for-production"
cd "$BACKEND"
"$PYTHON" -m app.cli migrate >/dev/null
"$PYTHON" -m app.cli seed-demo >/dev/null
exec "$PYTHON" -m uvicorn app.asgi:app --host 127.0.0.1 --port "${E2E_PORT:-8100}" --log-level warning
