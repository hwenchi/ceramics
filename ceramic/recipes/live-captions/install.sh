#!/bin/bash
set -euo pipefail
DATA_DIR="/var/lib/recipes/live-captions"
mkdir -p "$DATA_DIR"

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y build-essential cmake git ffmpeg

WHISPER_DIR="$DATA_DIR/whisper.cpp"
if [[ ! -x "$WHISPER_DIR/build/bin/whisper-cli" ]]; then
  rm -rf "$WHISPER_DIR"
  git clone --depth 1 https://github.com/ggml-org/whisper.cpp.git "$WHISPER_DIR"
  cmake -B "$WHISPER_DIR/build" -S "$WHISPER_DIR"
  cmake --build "$WHISPER_DIR/build" -j "$(nproc)" --config Release
fi

MODEL="$WHISPER_DIR/models/ggml-tiny.en-q5_1.bin"
if [[ ! -s "$MODEL" ]]; then
  (cd "$WHISPER_DIR" && bash ./models/download-ggml-model.sh tiny.en-q5_1)
fi

if [[ ! -x /usr/local/bin/yt-dlp ]]; then
  curl -L -sS https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp
  chmod +x /usr/local/bin/yt-dlp
fi
