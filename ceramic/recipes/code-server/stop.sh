#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="/var/lib/recipes/code-server/server.pid"
if [[ -f "$PID_FILE" ]]; then
  bash "$SCRIPT_DIR/../lib/kill-and-wait.sh" "$(cat "$PID_FILE")"
  rm -f "$PID_FILE"
fi
