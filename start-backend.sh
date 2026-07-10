#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/backend"

PYTHON_VERSION=$(python3 -c 'import sys; v = sys.version_info; print(f"{v.major}.{v.minor}")')
echo "Detected Python: $PYTHON_VERSION"

if [ ! -d ".venv" ]; then
    echo "Creating venv..."
    python3 -m venv .venv
fi

if ! .venv/bin/python -c "import fastapi" 2>/dev/null; then
    echo "Installing dependencies..."
    .venv/bin/pip install -q --upgrade pip
    .venv/bin/pip install -q fastapi "uvicorn[standard]" tortoise-orm aiosqlite httpx "pydantic[email]" python-dotenv pyyaml rich
fi

mkdir -p data

echo "Starting backend on http://0.0.0.0:8000..."
echo "Docs: http://localhost:8000/docs"
echo "Health: http://localhost:8000/health"

DATABASE_URL="local.db" TURSO_AUTH_TOKEN="" .venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
