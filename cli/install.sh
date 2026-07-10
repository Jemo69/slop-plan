#!/bin/bash
set -e

REPO="Jemo69/html-planner-server"
INSTALL_DIR="$HOME/.plan-cli"
BIN_DIR="$HOME/.local/bin"

echo "Installing Plan CLI..."

mkdir -p "$INSTALL_DIR" "$BIN_DIR"

if [ -d "$INSTALL_DIR/repo" ]; then
    cd "$INSTALL_DIR/repo"
    git pull || true
else
    git clone "https://github.com/$REPO.git" "$INSTALL_DIR/repo" 2>/dev/null || {
        echo "Cloning failed, trying local copy..."
        mkdir -p "$INSTALL_DIR/repo"
        cp -r "$(dirname "$0")/.." "$INSTALL_DIR/repo/" 2>/dev/null || true
    }
    cd "$INSTALL_DIR/repo" 2>/dev/null || true
fi

if [ -d "cli" ]; then
    cd cli
else
    cd "$INSTALL_DIR/repo/cli" 2>/dev/null || cd "$(dirname "$0")"
fi

echo "Setting up venv..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q httpx rich typer pyyaml

# Create wrapper bin
cat > .venv/bin/plan << 'WRAP'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Find project root (cli folder)
CLI_DIR="$(dirname "$SCRIPT_DIR")"
# If installed via repo, CLI_DIR is cli
# Run with PYTHONPATH
PYTHONPATH="$CLI_DIR" exec "$SCRIPT_DIR/python" -m plan_cli.main "$@"
WRAP
chmod +x .venv/bin/plan

ln -sf "$(pwd)/.venv/bin/plan" "$BIN_DIR/plan"
echo "Installed to $BIN_DIR/plan"

if ! echo "$PATH" | grep -q "$BIN_DIR"; then
    echo "Add to PATH: export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

echo "Done! Run 'plan --help' to get started."
