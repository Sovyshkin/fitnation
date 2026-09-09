#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="/opt/fitnation"
SERVICE_NAME="fitnation.service"
HEALTH_URL="http://127.0.0.1:8000/health"

cd "$APP_DIR"
if ! git diff --quiet || ! git diff --cached --quiet; then
  printf 'Deployment aborted: tracked files contain local changes.\n' >&2
  exit 1
fi
git pull --ff-only
"$APP_DIR/venv/bin/python" -m pip install --disable-pip-version-check -r requirements.txt
sudo systemctl restart "$SERVICE_NAME"
sudo systemctl --no-pager --full status "$SERVICE_NAME"
curl --fail --silent --show-error --retry 10 --retry-delay 2 --retry-connrefused --max-time 5 "$HEALTH_URL"
printf '\nDeployment completed successfully.\n'
