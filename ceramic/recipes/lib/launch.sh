#!/bin/bash
# launch.sh <slug> — the only way recipes should be started.
# Stops whatever recipe is currently running, then starts <slug>.
set -euo pipefail
SLUG="$1"
RECIPES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CURRENT_FILE="/var/lib/recipes/current"

mkdir -p /var/lib/recipes
if [[ -f "$CURRENT_FILE" ]]; then
  prev="$(cat "$CURRENT_FILE")"
  if [[ -n "$prev" && -x "$RECIPES_DIR/$prev/stop.sh" ]]; then
    bash "$RECIPES_DIR/$prev/stop.sh"
  fi
fi

CONSOLE_LOG="/var/log/console.log"
: > "$CONSOLE_LOG"
bash "$RECIPES_DIR/$SLUG/install.sh" >>"$CONSOLE_LOG" 2>&1

echo "$SLUG" > "$CURRENT_FILE"
exec bash "$RECIPES_DIR/$SLUG/start.sh"
