#!/bin/bash
PID_FILE="/var/lib/recipes/code-server/server.pid"
if [[ -f "$PID_FILE" ]]; then
  kill -TERM "$(cat "$PID_FILE")" 2>/dev/null || true
  rm -f "$PID_FILE"
fi
