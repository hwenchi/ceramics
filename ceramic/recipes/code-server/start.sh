#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="/var/lib/recipes/code-server"
mkdir -p "$DATA_DIR"

echo $$ > "$DATA_DIR/server.pid"
exec code-server --bind-addr 0.0.0.0:8080 --auth none --user-data-dir "$DATA_DIR/user-data" /workspace
