#!/bin/bash
# setup-ec2.sh — Initialisation du serveur EC2 Ubuntu 24.04
# Exécuter en tant que ubuntu : bash setup-ec2.sh VOTRE_DOMAINE.fr
# -----------------------------------------------------------------

set -euo pipefail

DOMAIN="${1:-VOTRE_DOMAINE.fr}"
APP_DIR="/opt/cybervault"
FRONTEND_DIR="/var/www/cybervault"

echo "=== [1/7] Mise à jour du système ==="
sudo apt-get update -y && sudo apt-get upgrade -y

echo "=== [2/7] Installation des paquets ==="
sudo apt-get install -y \
    nginx \
    certbot python3-certbot-nginx \
    docker.io docker-compose-plugin \
    git curl unzip awscli \
    fail2ban ufw

echo "=== [3/7] Configuration Docker ==="
sudo systemctl enable docker
sudo usermod -aG docker ubuntu

echo "=== [4/7] Pare-feu (UFW) ==="
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP (redirect HTTPS)
sudo ufw allow 443/tcp   # HTTPS
sudo ufw --force enable

echo "=== [5/7] Fail2ban (protection SSH) ==="
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

echo "=== [6/7] Répertoires de l'app ==="
sudo mkdir -p "$APP_DIR" "$FRONTEND_DIR"
sudo chown ubuntu:ubuntu "$APP_DIR" "$FRONTEND_DIR"

echo "=== [7/7] Nginx + SSL ==="
# Copier la config Nginx
sudo cp "$(dirname "$0")/nginx.prod.conf" /etc/nginx/sites-available/cybervault
sudo sed -i "s/VOTRE_DOMAINE.fr/$DOMAIN/g" /etc/nginx/sites-available/cybervault
sudo ln -sf /etc/nginx/sites-available/cybervault /etc/nginx/sites-enabled/cybervault
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

# Certificat Let's Encrypt
sudo certbot --nginx \
    -d "$DOMAIN" \
    -d "www.$DOMAIN" \
    --non-interactive \
    --agree-tos \
    --email "admin@$DOMAIN" \
    --redirect

# Renouvellement automatique
echo "0 3 * * * root certbot renew --quiet && systemctl reload nginx" \
    | sudo tee /etc/cron.d/certbot-renew

echo ""
echo "======================================"
echo "  Serveur prêt : https://$DOMAIN"
echo "  Prochaine étape : copier .env dans $APP_DIR"
echo "======================================"
