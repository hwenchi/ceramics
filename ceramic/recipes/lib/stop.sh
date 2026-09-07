#!/bin/bash
# stop.sh — stop whatever recipe is currently running, without starting another.
set -euo pipefail
RECIPES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CURRENT_FILE="/var/lib/recipes/current"

if [[ -f "$CURRENT_FILE" ]]; then
  prev="$(cat "$CURRENT_FILE")"
  if [[ -n "$prev" && -x "$RECIPES_DIR/$prev/stop.sh" ]]; then
    bash "$RECIPES_DIR/$prev/stop.sh"
  fi
  rm -f "$CURRENT_FILE"
fi
