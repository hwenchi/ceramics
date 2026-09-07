#!/bin/bash
PID_FILE="/var/lib/recipes/live-captions/server.pid"
if [[ -f "$PID_FILE" ]]; then
  kill -TERM "$(cat "$PID_FILE")" 2>/dev/null || true
  rm -f "$PID_FILE"
fi
