#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="/var/lib/recipes/stream-filter/server.pid"
if [[ -f "$PID_FILE" ]]; then
  # May be waiting on active ffmpeg children (up to a few seconds each);
  # kill-and-wait.sh handles waiting for the whole thing to actually exit.
  bash "$SCRIPT_DIR/../lib/kill-and-wait.sh" "$(cat "$PID_FILE")"
  rm -f "$PID_FILE"
fi
