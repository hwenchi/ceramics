#!/bin/bash
PID_FILE="/var/lib/recipes/gutenberg-search/server.pid"
if [[ -f "$PID_FILE" ]]; then
  kill -9 "$(cat "$PID_FILE")" 2>/dev/null || true
  rm -f "$PID_FILE"
fi
