#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Updating CLI..."

if [ -d "cli/.venv" ]; then
    cli/.venv/bin/pip install -q --upgrade pip
    cli/.venv/bin/pip install -q httpx rich typer pyyaml
    echo "CLI dependencies updated!"
    cli/.venv/bin/plan --help | head -n 20
else
    echo "No venv found, running install..."
    bash cli/install.sh
fi
