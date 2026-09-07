#!/bin/bash
set -euo pipefail
DATA_DIR="/var/lib/recipes/stream-filter"
mkdir -p "$DATA_DIR"

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ffmpeg

if [[ ! -x /usr/local/bin/yt-dlp ]]; then
  curl -L -sS https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp
  chmod +x /usr/local/bin/yt-dlp
fi
