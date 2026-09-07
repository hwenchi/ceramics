#!/bin/bash
# launch.sh <slug> — the only way recipes should be started.
# Stops whatever recipe is currently running, then starts <slug>.
#
# Run this in the foreground, not backgrounded - it blocks only through
# install (so the caller's exit status/timing reflects whether install
# actually succeeded), then starts the recipe in the background itself
# and returns. Don't wrap it in your own nohup/& - the recipe keeps
# running after this script exits either way.
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
nohup bash "$RECIPES_DIR/$SLUG/start.sh" >>"$CONSOLE_LOG" 2>&1 &
disown
