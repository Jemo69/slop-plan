#!/bin/bash
# Start local backend for testing
set -e

cd backend

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; v = sys.version_info; print(f"{v.major}.{v.minor}")')
echo "Detected Python: $PYTHON_VERSION"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

# Install or update dependencies
.venv/bin/pip install -e .

# Ensure SQLite database directory exists
mkdir -p data

# Use local SQLite for development
DATABASE_URL="local.db" TURSO_AUTH_TOKEN="" .venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload
