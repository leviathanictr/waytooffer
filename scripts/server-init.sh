#!/usr/bin/env bash
# =============================================================================
# WayToOffer — First-time server initialization
# Run as root on the VPS:
#   bash /root/waytooffer/scripts/server-init.sh your@email.com
# =============================================================================
set -euo pipefail

EMAIL="${1:?Usage: bash scripts/server-init.sh your@email.com}"
DOMAIN="waytooffer.ru"
REPO="https://github.com/leviathanictr/waytooffer.git"
DEPLOY_DIR="/root/waytooffer"

# ── 1. Docker ─────────────────────────────────────────────────────────────────
echo ""
echo ">>> [1/6] Installing Docker..."
if ! command -v docker &>/dev/null; then
  apt-get update -y
  apt-get install -y ca-certificates curl gnupg lsb-release
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin git
  systemctl enable --now docker
  echo "Docker installed."
else
  echo "Docker already installed: $(docker --version)"
fi

# ── 2. SSH key for GitHub Actions ─────────────────────────────────────────────
echo ""
echo ">>> [2/6] Generating SSH key for GitHub Actions..."
mkdir -p /root/.ssh && chmod 700 /root/.ssh
if [ ! -f /root/.ssh/github_actions ]; then
  ssh-keygen -t ed25519 -f /root/.ssh/github_actions -N "" -C "github-actions-waytooffer"
  cat /root/.ssh/github_actions.pub >> /root/.ssh/authorized_keys
  chmod 600 /root/.ssh/authorized_keys
  echo "SSH key generated."
else
  echo "SSH key already exists, skipping."
fi

echo ""
echo "================================================================="
echo "  Copy this PRIVATE KEY to GitHub Secret SSH_PRIVATE_KEY:"
echo "  (Settings → Secrets and variables → Actions → New secret)"
echo "================================================================="
cat /root/.ssh/github_actions
echo "================================================================="
echo ""
read -r -p "Press Enter once you've saved the key to GitHub Secrets..."

# ── 3. Clone repo ─────────────────────────────────────────────────────────────
echo ""
echo ">>> [3/6] Cloning / updating repo..."
if [ ! -d "$DEPLOY_DIR/.git" ]; then
  git clone --branch deploy "$REPO" "$DEPLOY_DIR"
else
  echo "Repo already exists, pulling latest deploy branch..."
  cd "$DEPLOY_DIR"
  git fetch --all
  git reset --hard origin/deploy
fi
cd "$DEPLOY_DIR"

# ── 4. backend/.env ───────────────────────────────────────────────────────────
echo ""
echo ">>> [4/6] Setting up backend/.env..."
if [ ! -f backend/.env ]; then
  cp backend/.env.example backend/.env
  # Switch to Postgres
  sed -i 's|^DATABASE_URL=.*|DATABASE_URL=postgresql+psycopg://resume:resume_pass@postgres:5432/resume_db|' backend/.env
  # Set production CORS
  sed -i 's|^CORS_ORIGINS=.*|CORS_ORIGINS=https://waytooffer.ru|' backend/.env
fi

echo ""
echo "================================================================="
echo "  Fill in the required values in backend/.env:"
echo "    OPENAI_API_KEY   — your OpenAI key"
echo "    JWT_SECRET       — any long random string (min 32 chars)"
echo "    SMTP_PASSWORD    — Yandex app password for waytooffer@yandex.ru"
echo "    SMSC_LOGIN / SMSC_PASSWORD — smsc.ru credentials (optional)"
echo "================================================================="
nano "$DEPLOY_DIR/backend/.env"

# ── 5. SSL certificates ───────────────────────────────────────────────────────
echo ""
echo ">>> [5/6] Obtaining SSL certificates..."
echo "  Starting nginx in HTTP-only mode for certbot challenge..."

# Swap to bootstrap config (no SSL references)
cp nginx/nginx.conf nginx/nginx.conf.ssl_backup
cp nginx/nginx.bootstrap.conf nginx/nginx.conf

docker compose up -d nginx certbot
sleep 6

echo "  Running certbot..."
docker compose run --rm certbot certonly \
  --webroot --webroot-path=/var/www/certbot \
  --email "$EMAIL" --agree-tos --no-eff-email \
  -d "$DOMAIN" -d "api.$DOMAIN"

# Restore full SSL config
cp nginx/nginx.conf.ssl_backup nginx/nginx.conf
rm  nginx/nginx.conf.ssl_backup

echo "  Restarting nginx with HTTPS config..."
docker compose restart nginx

# ── 6. Start full stack ───────────────────────────────────────────────────────
echo ""
echo ">>> [6/6] Starting full stack..."
docker compose up -d --build --remove-orphans

echo ""
echo "================================================================="
echo "  Setup complete!"
echo "  Site: https://$DOMAIN"
echo "  API:  https://api.$DOMAIN/docs"
echo ""
echo "  Check logs: docker compose -f $DEPLOY_DIR/docker-compose.yml logs -f"
echo "================================================================="
