#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="/var/lib/recipes/jupyterlab"
mkdir -p "$DATA_DIR"

echo $$ > "$DATA_DIR/server.pid"
exec "$DATA_DIR/venv/bin/jupyter" lab \
  --ip=0.0.0.0 --port=8080 --no-browser --allow-root \
  --ServerApp.token='' --ServerApp.password='' \
  --ServerApp.root_dir=/workspace
