#!/usr/bin/env bash
set -euo pipefail

# Usage: sudo bootstrap.sh [GIT_REPO_SSH_URL] [API_DOMAIN] [SERVICE_NAME] <ADMIN_EMAIL>
# First three parameters are optional with default values, email is required

# Default values
DEFAULT_REPO_URL="git@github.com:UMichHCI/DIY_Mod.git"
DEFAULT_API_DOMAIN="api.diy-mod.rayhan.io"
DEFAULT_SERVICE_NAME="DIY-MOD"

if [[ $# -lt 1 ]]; then
  echo "Usage: sudo $0 [GIT_REPO_SSH_URL] [API_DOMAIN] [SERVICE_NAME] <EMAIL-ID for LetsEncrypt>"
  echo "First three parameters are optional (defaults will be used), but email is required"
  exit 1
fi

# Set parameters based on argument count
if [[ $# -eq 1 ]]; then
  # Only email provided, use all defaults
  REPO_URL="$DEFAULT_REPO_URL"
  API_DOMAIN="$DEFAULT_API_DOMAIN"
  SERVICE_NAME="$DEFAULT_SERVICE_NAME"
  ADMIN_EMAIL="$1"
elif [[ $# -eq 2 ]]; then
  # Custom repo and email
  REPO_URL="$1"
  API_DOMAIN="$DEFAULT_API_DOMAIN"
  SERVICE_NAME="$DEFAULT_SERVICE_NAME"
  ADMIN_EMAIL="$2"
elif [[ $# -eq 3 ]]; then
  # Custom repo, domain and email
  REPO_URL="$1"
  API_DOMAIN="$2"
  SERVICE_NAME="$DEFAULT_SERVICE_NAME"
  ADMIN_EMAIL="$3"
else
  # All parameters provided
  REPO_URL="$1"
  API_DOMAIN="$2"
  SERVICE_NAME="$3"
  ADMIN_EMAIL="$4"
fi

# Display the configuration
echo "📋 Configuration:"
echo "  Repository URL: $REPO_URL"
echo "  API Domain: $API_DOMAIN"
echo "  Service Name: $SERVICE_NAME"
echo "  Admin Email: $ADMIN_EMAIL"
echo

APP_DIR="/opt/$SERVICE_NAME"
BACKEND_DIR="$APP_DIR/Backend"

# 1. System update & essential packages
apt update && apt upgrade -y
apt install -y build-essential curl wget git ufw fail2ban \
               software-properties-common nginx certbot python3-certbot-nginx \
               openssh-client python3-venv \
               nvidia-cuda-dev cmake python3.12-dev

# 2. NVIDIA driver ≥ 520
add-apt-repository ppa:graphics-drivers/ppa -y
apt update
apt install -y nvidia-driver-535
if ! command -v nvidia-smi &>/dev/null; then
  echo "⚠️ Nvidia driver install failed" >&2
  exit 1
fi

# 3. Swapfile (8 GiB)
SWAP_FILE="/swapfile"
if ! grep -q "$SWAP_FILE" /etc/fstab; then
  fallocate -l 8G "$SWAP_FILE" || dd if=/dev/zero of="$SWAP_FILE" bs=1M count=8192
  chmod 600 "$SWAP_FILE"
  mkswap "$SWAP_FILE"
  swapon "$SWAP_FILE"
  echo "$SWAP_FILE none swap sw 0 0" >> /etc/fstab
fi

# # 4. Firewall (UFW)
# ufw default deny incoming
# ufw default allow outgoing
ufw allow ssh
ufw allow http
ufw allow https
ufw --force enable

# 5. SSH key for GitHub (private repo access)
KEY_PATH="/root/.ssh/id_ed25519"
if [[ ! -f "$KEY_PATH" ]]; then
  echo "Generating SSH key for GitHub access..."
  ssh-keygen -t ed25519 -f "$KEY_PATH" -N "" -C "deploy@$API_DOMAIN"
  echo
  echo "🚀 Public key generated at $KEY_PATH.pub."
  echo "📋 Copy its contents into GitHub (Settings → SSH & GPG keys or your repo’s Deploy Keys)."
  echo "Then re-run this script."
  exit 0
fi

# # Test GitHub SSH auth using the generated key
# echo "🔑 Testing SSH authentication to GitHub..."
# if ! sudo ssh -i "$KEY_PATH" -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=no git@github.com &>/dev/null; then
#   echo "⚠️ SSH authentication to GitHub failed." >&2
#   echo " - Confirm the public key at $KEY_PATH.pub is added to GitHub." >&2
#   echo " - Ensure you run this script with sudo (so $KEY_PATH is used)." >&2
#   exit 1
# fi

# echo "✅ SSH authentication to GitHub succeeded."

# 6. Clone or update repo
mkdir -p "$APP_DIR"
if [[ ! -d "$APP_DIR/.git" ]]; then
  git clone "$REPO_URL" "$APP_DIR"
else
  cd "$APP_DIR" && git pull
fi

# 7. Python environment in Backend
if [[ ! -d "$BACKEND_DIR" ]]; then
  echo "❌ Backend directory not found at $BACKEND_DIR" >&2
  exit 1
fi
cd "$BACKEND_DIR"
# Ensure venv support for Python 3.12
python3 -m venv venv
. venv/bin/activate
pip install --upgrade pip
if [[ -f requirements.txt ]]; then
  pip install -r requirements.txt
fi

# Ensure logs directory exists with correct permissions
mkdir -p "$BACKEND_DIR/logs"
chmod 777 "$BACKEND_DIR/logs"
chown -R root:root "$BACKEND_DIR/logs"

mkdir -p "$BACKEND_DIR/temp"
chmod 777 "$BACKEND_DIR/temp"
chown -R root:root "$BACKEND_DIR/temp"


# Ensure root-level debug.log exists for app.py
touch "$BACKEND_DIR/debug.log"
chmod 666 "$BACKEND_DIR/debug.log"
chown root:root "$BACKEND_DIR/debug.log"



# 8. Nginx site configuration for HTTPS
echo "Writing Nginx vhost for $API_DOMAIN"
cat >/etc/nginx/sites-available/$API_DOMAIN.conf <<EOF
server {
    listen 80;
    server_name $API_DOMAIN;
    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name $API_DOMAIN;

    ssl_certificate     /etc/letsencrypt/live/$API_DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$API_DOMAIN/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    location / {
        proxy_pass         http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header   Host               \$host;
        proxy_set_header   X-Real-IP          \$remote_addr;
        proxy_set_header   X-Forwarded-For    \$proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto  \$scheme;
    }
}
EOF
ln -sf /etc/nginx/sites-available/$API_DOMAIN.conf /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

# 9. Obtain or renew Let’s Encrypt cert
systemctl stop nginx
certbot certonly --standalone -d "$API_DOMAIN" --non-interactive --agree-tos -m "$ADMIN_EMAIL"
systemctl start nginx
nginx -t && systemctl reload nginx

# 10. systemd service for your ASGI app
cat >/etc/systemd/system/$SERVICE_NAME.service <<EOF
[Unit]
Description=$SERVICE_NAME ASGI app
After=network.target

[Service]
User=root
WorkingDirectory=$BACKEND_DIR
EnvironmentFile=/home/ubuntu/.env
Environment="PATH=$BACKEND_DIR/venv/bin"
ExecStart=$BACKEND_DIR/venv/bin/hypercorn app:asgi_app --bind 127.0.0.1:5000
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now $SERVICE_NAME

echo "✅ Bootstrap complete! Your API is available at https://$API_DOMAIN/"
