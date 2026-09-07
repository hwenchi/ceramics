#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="/var/lib/recipes/remote-desktop"
export HOME=/root
vncserver -kill :1 2>/dev/null || true
if [[ -f "$DATA_DIR/websockify.pid" ]]; then
  bash "$SCRIPT_DIR/../lib/kill-and-wait.sh" "$(cat "$DATA_DIR/websockify.pid")"
  rm -f "$DATA_DIR/websockify.pid"
fi
