#!/usr/bin/env bash
# Start OxFood: API on :8000, web app on :5173. Ctrl+C stops both.
set -e
cd "$(dirname "$0")"
ROOT=$PWD

# --- backend ---
if [ ! -d backend/.venv ]; then
  echo "Setting up Python env…"
  if command -v uv >/dev/null; then uv venv --python 3.14 backend/.venv -q && uv pip install -q -p backend/.venv -r backend/requirements.txt
  else python3 -m venv backend/.venv && backend/.venv/bin/pip install -q -r backend/requirements.txt; fi
fi
[ "$1" = "--reset" ] && rm -f backend/oxfood.db && echo "Database reset."

# --- frontend (Node is kept inside frontend/.node if not installed system-wide) ---
if ! command -v node >/dev/null; then
  if [ ! -x frontend/.node/bin/node ]; then
    echo "Installing Node locally into frontend/.node…"
    uvx nodeenv --node=22.12.0 --prebuilt frontend/.node >/dev/null
  fi
  export PATH="$ROOT/frontend/.node/bin:$PATH"
fi
[ -d frontend/node_modules ] || (cd frontend && npm install --no-fund --no-audit)

(cd backend && exec .venv/bin/uvicorn app.main:app --port 8000 --reload) &
API=$!
trap 'kill $API 2>/dev/null' EXIT INT TERM
cd frontend && npx vite --port 5173 --strictPort &
WEB=$!
trap 'kill $API $WEB 2>/dev/null' EXIT INT TERM
sleep 2
cat <<MSG

  🌱 OxFood is running
     Manager dashboard  http://localhost:5173/
     Kitchen tablet     http://localhost:5173/tablet
     Smart bin          http://localhost:5173/bin
     Student phone      http://localhost:5173/student
     API docs           http://localhost:8000/docs

MSG
wait
