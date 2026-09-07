#!/bin/bash
# launch.sh <slug> — the only way recipes should be started.
# Stops whatever recipe is currently running, then starts <slug>.
set -euo pipefail
SLUG="$1"
RECIPES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CURRENT_FILE="/var/lib/recipes/current"

mkdir -p /var/lib/recipes
bash "$RECIPES_DIR/lib/stop.sh"

CONSOLE_LOG="/var/log/console.log"
: > "$CONSOLE_LOG"
bash "$RECIPES_DIR/$SLUG/install.sh" >>"$CONSOLE_LOG" 2>&1

echo "$SLUG" > "$CURRENT_FILE"
exec bash "$RECIPES_DIR/$SLUG/start.sh"
