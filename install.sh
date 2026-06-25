#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/Skribb11es/homepage-nvidia-widget"
INSTALL_DIR="/opt/nvidia-status-server"
ENV_FILE="/etc/nvidia-status-server.env"
SERVICE_FILE_SRC="nvidia-status-server.service"
SERVICE_FILE_DST="/etc/systemd/system/nvidia-status-server.service"

echo "== NVIDIA Status Homepage Widget Installer =="

if [[ "$EUID" -ne 0 ]]; then
  echo "ERROR: Please run as root (sudo ./install.sh)"
  exit 1
fi

echo "[1/6] installing python..."
apt update && apt upgrade -y
apt install -y git python3
apt install -y python3-flask
apt install -y python3-gunicorn

TMP_DIR="$(mktemp -d)"
echo "[2/6] cloning into $TMP_DIR ..."
git clone "$REPO_URL" "$TMP_DIR"

if [[ ! -f "$TMP_DIR/server.py" ]]; then
  echo "ERROR: server.py not found in repo root!"
  exit 1
fi

if [[ ! -f "$TMP_DIR/$SERVICE_FILE_SRC" ]]; then
  echo "ERROR: $SERVICE_FILE_SRC not found in repo root!"
  exit 1
fi

echo "[3/6] moving server.py into $INSTALL_DIR ..."
mkdir -p "$INSTALL_DIR"
cp -f "$TMP_DIR/server.py" "$INSTALL_DIR/server.py"
chmod +x "$INSTALL_DIR/server.py"

echo "[4/6] creating env file in $ENV_FILE ..."
if [[ ! -f "$ENV_FILE" ]]; then
  cat > "$ENV_FILE" <<EOF
EOF
  chmod 600 "$ENV_FILE"
  echo "Created $ENV_FILE"
else
  echo "$ENV_FILE already exists."
fi

echo "[5/6] setting up systemd service..."
cp -f "$TMP_DIR/$SERVICE_FILE_SRC" "$SERVICE_FILE_DST"

systemctl daemon-reload
systemctl enable nvidia-status-server.service
systemctl start nvidia-status-server.service

rm -rf "$TMP_DIR"

echo "[6/6] finished!"
echo
echo "Service status:"
systemctl status nvidia-status-server.service --no-pager || true