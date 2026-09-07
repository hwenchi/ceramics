#!/bin/bash
set -e

dufs -A -p 8082 /workspace &
python3 /opt/console-server.py &

exec ttyd -W -p 7681 tmux new -A -s main claude
