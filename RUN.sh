#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/.venv"

# Create venv and install dependencies on first run
if [ ! -f "$VENV/bin/python" ]; then
    echo "Setting up virtual environment..."
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install -q -e "$SCRIPT_DIR[pretty]"
    echo "Setup complete."
fi

"$VENV/bin/python" -m hb_downloader \
  --links "$SCRIPT_DIR/links.txt" \
  --config "$SCRIPT_DIR/config.toml" \
  --output "$SCRIPT_DIR/downloads"
