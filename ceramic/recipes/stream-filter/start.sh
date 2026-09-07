#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="/var/lib/recipes/stream-filter"
mkdir -p "$DATA_DIR"

echo $$ > "$DATA_DIR/server.pid"
exec python3 "$SCRIPT_DIR/app.py"
