#!/usr/bin/env bash
# One-shot install/upgrade for Ubuntu/Debian servers. Run from the repository root as root:
#   sudo bash deploy/install.sh
# Re-running it upgrades an existing install in place (migrations run on service start).
set -euo pipefail

PREFIX=/opt/cac
ENV_FILE=/etc/cac/cac.env

command -v python3 >/dev/null || { echo "python3 is required"; exit 1; }
command -v npm >/dev/null || { echo "Node.js 18+ (npm) is required to build the frontend"; exit 1; }

id cac >/dev/null 2>&1 || useradd --system --home "$PREFIX" --shell /usr/sbin/nologin cac
mkdir -p "$PREFIX" /etc/cac
rsync -a --delete --exclude .git --exclude node_modules --exclude .venv --exclude 'backend/data' ./ "$PREFIX/"
mkdir -p "$PREFIX/backend/data"

echo "==> Building the frontend"
(cd "$PREFIX/frontend" && npm ci --no-audit --no-fund && npm run build)

echo "==> Installing the backend"
python3 -m venv "$PREFIX/backend/.venv"
"$PREFIX/backend/.venv/bin/pip" install --quiet --upgrade pip
"$PREFIX/backend/.venv/bin/pip" install --quiet -e "$PREFIX/backend"
chown -R cac:cac "$PREFIX"

if [ ! -f "$ENV_FILE" ]; then
  cp "$PREFIX/backend/.env.example" "$ENV_FILE"
  secret=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")
  sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$secret|; s|^ENVIRONMENT=.*|ENVIRONMENT=production|" "$ENV_FILE"
  chmod 640 "$ENV_FILE" && chown root:cac "$ENV_FILE"
  echo "==> Created $ENV_FILE — set DATABASE_URL, PUBLIC_BASE_URL and SMTP_* there, then re-run this script."
  exit 0
fi

cp "$PREFIX/deploy/systemd/"*.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now cac-web cac-worker
systemctl restart cac-web cac-worker
echo "==> Running. Create the first administrator with:"
echo "    sudo -u cac bash -c 'cd $PREFIX/backend && set -a && . $ENV_FILE && .venv/bin/python -m app.cli create-admin --email you@example.edu'"
