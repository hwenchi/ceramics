#!/bin/bash
DATA_DIR="/var/lib/recipes/remote-desktop"
export HOME=/root
vncserver -kill :1 2>/dev/null || true
if [[ -f "$DATA_DIR/websockify.pid" ]]; then
  kill -9 "$(cat "$DATA_DIR/websockify.pid")" 2>/dev/null || true
  rm -f "$DATA_DIR/websockify.pid"
fi
