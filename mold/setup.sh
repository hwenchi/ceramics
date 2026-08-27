#!/bin/sh
# Usage: setup.sh user@host identity_file
set -eu

TARGET="${1:?usage: setup.sh user@host identity_file}"
IDENTITY="${2:?usage: setup.sh user@host identity_file}"
HERE="$(cd "$(dirname "$0")" && pwd)"
DEPLOY_DIR=/srv/mold/deploy
SSH_OPTS="-i $IDENTITY"

set -a
. "$HERE/.env"
set +a

mkdir -p "$HERE/site/static"
( cd "$HERE/render-kiln" && go run . -domain="$DOMAIN" -scheme="$SCHEME" -out "$HERE/site/index.html" )
cp "$HERE/../pottery/static/alpine.min.js" "$HERE/site/static/alpine.min.js"

envsubst '${DOMAIN} ${SCHEME}' \
	< "$HERE/keycloak/realm-export.json.tmpl" > "$HERE/keycloak/realm-export.json"

ssh $SSH_OPTS "$TARGET" 'bash -s' <<'REMOTE'
set -eu
if ! command -v docker >/dev/null; then
	curl -fsSL https://get.docker.com | sudo sh
fi
if ! groups "$(whoami)" | grep -q '\bdocker\b'; then
	sudo usermod -aG docker "$(whoami)"
fi
REMOTE

ssh $SSH_OPTS "$TARGET" "sudo mkdir -p '$WORKSPACE_DIR' '$DATA_DIR' '$DEPLOY_DIR' && sudo chown -R \$(id -u):\$(id -g) '$WORKSPACE_DIR' '$DATA_DIR' '$DEPLOY_DIR'"

rsync -av --delete -e "ssh $SSH_OPTS" --exclude realm-export.json.tmpl "$HERE/" "$TARGET:$DEPLOY_DIR/"

ssh $SSH_OPTS "$TARGET" "WORKSPACE_DIR='$WORKSPACE_DIR' DEPLOY_DIR='$DEPLOY_DIR' DOMAIN='$DOMAIN' bash -s" <<'REMOTE'
set -eu
cd "$WORKSPACE_DIR"
if [ -d .git ]; then
	exit 0
fi

git init
git config user.email "mold@$DOMAIN"
git config user.name "mold"
cp "$DEPLOY_DIR/workspace.gitignore" .gitignore

mkdir -p backend frontend

docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -v "$PWD/backend:/app" -w /app ghcr.io/astral-sh/uv:python3.13-bookworm-slim \
	sh -c "uv init --app --no-readme && uv add fastapi 'uvicorn[standard]'"
cp "$DEPLOY_DIR/scaffold/main.py" backend/main.py

docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -v "$PWD/frontend:/app" -w /app node:22-slim \
	npx -y @angular/cli new frontend --directory . --skip-git --defaults

git add -A
git commit -q -m "initial scaffold"
REMOTE

ssh $SSH_OPTS "$TARGET" "cd '$DEPLOY_DIR' && docker compose up -d"
