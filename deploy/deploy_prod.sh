#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   sudo bash deploy/deploy_prod.sh /opt/table
# Then edit /etc/table-signup.env and restart service.

APP_DIR="${1:-/opt/table}"

if [[ $EUID -ne 0 ]]; then
  echo "Please run as root: sudo bash deploy/deploy_prod.sh ${APP_DIR}" >&2
  exit 1
fi

apt-get update
apt-get install -y python3 python3-venv python3-pip nginx redis-server

mkdir -p "${APP_DIR}"
rsync -av --delete --exclude '.git' --exclude '.venv' /workspaces/table/ "${APP_DIR}/"

python3 -m venv "${APP_DIR}/.venv"
"${APP_DIR}/.venv/bin/pip" install --upgrade pip
"${APP_DIR}/.venv/bin/pip" install -r "${APP_DIR}/requirements.txt"

cp -f "${APP_DIR}/deploy/env/table-signup.env.example" /etc/table-signup.env
cp -f "${APP_DIR}/deploy/systemd/table-signup.service" /etc/systemd/system/table-signup.service
cp -f "${APP_DIR}/deploy/nginx/table-signup.conf" /etc/nginx/sites-available/table-signup.conf
ln -sf /etc/nginx/sites-available/table-signup.conf /etc/nginx/sites-enabled/table-signup.conf
rm -f /etc/nginx/sites-enabled/default

systemctl daemon-reload
systemctl enable redis-server
systemctl start redis-server
systemctl enable table-signup
systemctl restart table-signup
nginx -t
systemctl reload nginx

echo
echo "Deployment files installed. Next step:"
echo "1) edit /etc/table-signup.env and set your real SEATABLE_API_TOKEN"
echo "2) systemctl restart table-signup"
echo "3) systemctl status table-signup --no-pager"
