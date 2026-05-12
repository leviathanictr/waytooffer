#!/usr/bin/env bash
set -euo pipefail

# Simple remote deploy script — clones (if missing) and resets to origin/deploy,
# then runs docker compose to build and start services.

DEPLOY_DIR="${1:-/root/waytooffer}"

if [ ! -d "$DEPLOY_DIR" ]; then
  git clone --branch deploy https://github.com/leviathanictr/waytooffer.git "$DEPLOY_DIR"
fi

cd "$DEPLOY_DIR"
git fetch --all
git reset --hard origin/deploy

docker compose pull || true
docker compose up -d --build --remove-orphans

echo "Deployed to $DEPLOY_DIR"
