#!/bin/bash
set -e

dufs -A -p 8082 /workspace &

exec ttyd -W -p 7681 tmux new -A -s main claude
