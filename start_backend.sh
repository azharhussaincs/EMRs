#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR/backend"

if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Detect if port 8000 is already in use
PORT=${PORT:-8000}
if lsof -i :8000 >/dev/null 2>&1 && [ -z "$PORT_OVERRIDE" ]; then
    echo "Notice: Port 8000 is occupied by another process. Defaulting to port 8001."
    PORT=8001
fi

export PYTHONPATH="$DIR/backend"

echo "Starting Clinical EMR FastAPI Backend on http://0.0.0.0:$PORT (Docs: http://localhost:$PORT/docs)..."
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --reload
