#!/bin/bash
# kill-and-wait.sh <pid> — TERM a process and wait for it to actually exit
# before returning, rather than racing the next start against a process
# still mid-shutdown. Until it's truly gone it still holds its port, so a
# start right after a plain `kill` can fail with "Address already in use".
# Escalates to -9 if it hasn't exited after ~10s.
set -euo pipefail
pid="$1"

kill -TERM "$pid" 2>/dev/null || exit 0
for _ in $(seq 1 50); do
  kill -0 "$pid" 2>/dev/null || exit 0
  sleep 0.2
done
kill -9 "$pid" 2>/dev/null || true
