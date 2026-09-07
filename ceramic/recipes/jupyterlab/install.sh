#!/bin/bash
set -euo pipefail
DATA_DIR="/var/lib/recipes/jupyterlab"
VENV="$DATA_DIR/venv"
mkdir -p "$DATA_DIR"

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y python3-venv

if [[ ! -x "$VENV/bin/jupyter" ]]; then
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install --quiet --upgrade pip
  "$VENV/bin/pip" install --quiet jupyterlab
fi
