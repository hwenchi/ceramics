#!/bin/bash
set -euo pipefail

if ! command -v code-server >/dev/null 2>&1; then
  curl -fsSL https://code-server.dev/install.sh | sh
fi
