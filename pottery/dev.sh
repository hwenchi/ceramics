#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
pkill -f "b001/exe/pottery" 2>/dev/null || true
sleep 1
KUBECONFIG="${KUBECONFIG:-$HOME/.kube/software-dev}" go run .
