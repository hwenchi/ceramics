#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="/var/lib/recipes/remote-desktop"
mkdir -p "$DATA_DIR"

export HOME=/root
vncserver -kill :1 >/dev/null 2>&1 || true
vncserver :1 -geometry 1280x800 -depth 24 -localhost yes -SecurityTypes None -xstartup "$DATA_DIR/xstartup"

echo $$ > "$DATA_DIR/websockify.pid"
exec websockify --web=/usr/share/novnc/ 0.0.0.0:8080 localhost:5901
