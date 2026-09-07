#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p /workspace/stream-filter
ln -sf "$SCRIPT_DIR/app.py" /workspace/stream-filter/app.py
ln -sf "$SCRIPT_DIR/preset.txt" /workspace/stream-filter/preset.txt
