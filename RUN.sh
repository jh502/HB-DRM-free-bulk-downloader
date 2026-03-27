#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 -m hb_downloader \
  --links "$SCRIPT_DIR/links.txt" \
  --config "$SCRIPT_DIR/config.toml" \
  --output "$SCRIPT_DIR/downloads"
