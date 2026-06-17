#!/bin/bash
set -e

REPO="Jemo69/html-planner-server"
INSTALL_DIR="$HOME/.plan-cli"
BIN_DIR="$HOME/.local/bin"

echo "Installing Plan CLI..."

# Create dirs
mkdir -p "$INSTALL_DIR" "$BIN_DIR"

# Clone or update
if [ -d "$INSTALL_DIR/repo" ]; then
    cd "$INSTALL_DIR/repo"
    git pull
else
    git clone "https://github.com/$REPO.git" "$INSTALL_DIR/repo"
    cd "$INSTALL_DIR/repo"
fi

# Setup venv and install
cd cli
python3 -m venv .venv
.venv/bin/pip install -e .

# Symlink
ln -sf "$INSTALL_DIR/repo/cli/.venv/bin/plan" "$BIN_DIR/plan"

# Add to PATH if needed
if ! echo "$PATH" | grep -q "$BIN_DIR"; then
    echo "export PATH=\"\$HOME/.local/bin:\$PATH\"" >> ~/.bashrc
    echo "Run: export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

echo "Done! Run 'plan --help' to get started."
