#!/usr/bin/env bash
# ============================================
# Script de setup initial — Oracle Cloud staging CyberVault
# ============================================
#
# À exécuter UNE FOIS sur une instance Ubuntu fraîchement créée
# (Ampere A1, ARM64, Ubuntu 22.04+)
#
# Usage :
#   ssh ubuntu@<IP_ORACLE>
#   curl -fsSL https://raw.githubusercontent.com/DavidRocher01/cyber-vault/develop/staging/setup-oracle.sh -o setup.sh
#   chmod +x setup.sh && ./setup.sh

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[$(date '+%H:%M:%S')] $*${NC}"; }
warn() { echo -e "${YELLOW}[$(date '+%H:%M:%S')] ⚠ $*${NC}"; }
error(){ echo -e "${RED}[$(date '+%H:%M:%S')] ✗ $*${NC}" >&2; exit 1; }

[ "$EUID" -eq 0 ] && error "Ne pas exécuter en root — lancer en tant qu'utilisateur 'ubuntu'."
command -v sudo &>/dev/null || error "sudo non disponible."

log "▶ Setup Oracle Cloud staging CyberVault"
log "▶ Architecture : $(uname -m)"
log "▶ Distribution : $(lsb_release -d | cut -f2)"

# ---- 1. Mise à jour système ----
log "▶ Mise à jour du système..."
sudo apt update
sudo DEBIAN_FRONTEND=noninteractive apt upgrade -y

# ---- 2. Outils ----
log "▶ Installation des outils..."
sudo DEBIAN_FRONTEND=noninteractive apt install -y \
    curl git htop fail2ban unattended-upgrades \
    ufw netfilter-persistent iptables-persistent \
    jq ncdu rsync

# ---- 3. iptables (Oracle bloque les ports 80/443 par défaut) ----
log "▶ Configuration iptables..."
sudo iptables -C INPUT -p tcp --dport 80 -j ACCEPT 2>/dev/null || \
    sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -C INPUT -p tcp --dport 443 -j ACCEPT 2>/dev/null || \
    sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save

# ---- 4. ufw ----
log "▶ Configuration ufw..."
sudo ufw --force default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp  comment 'SSH'
sudo ufw allow 80/tcp  comment 'HTTP'
sudo ufw allow 443/tcp comment 'HTTPS'
sudo ufw --force enable

# ---- 5. SSH hardening ----
log "▶ Hardening SSH..."
sudo tee /etc/ssh/sshd_config.d/99-hardening.conf > /dev/null <<'EOF'
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 2
X11Forwarding no
AllowAgentForwarding no
AllowTcpForwarding no
PermitEmptyPasswords no
EOF
sudo systemctl restart sshd

# ---- 6. fail2ban ----
log "▶ Configuration fail2ban..."
sudo tee /etc/fail2ban/jail.local > /dev/null <<'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = 22
filter = sshd
logpath = /var/log/auth.log
EOF
sudo systemctl enable --now fail2ban && sudo systemctl restart fail2ban

# ---- 7. Mises à jour automatiques ----
log "▶ Mises à jour automatiques de sécurité..."
sudo tee /etc/apt/apt.conf.d/20auto-upgrades > /dev/null <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
EOF

# ---- 8. Docker ----
log "▶ Installation de Docker..."
if ! command -v docker &>/dev/null; then
    curl -fsSL https://get.docker.com | sudo sh
else
    log "  ✓ Docker déjà présent : $(docker --version)"
fi

sudo tee /etc/docker/daemon.json > /dev/null <<'EOF'
{
  "log-driver": "json-file",
  "log-opts": { "max-size": "10m", "max-file": "3" },
  "live-restore": true
}
EOF
sudo systemctl restart docker && sudo systemctl enable docker

# ---- 9. Utilisateur dédié 'cyberscan' ----
log "▶ Création de l'utilisateur cyberscan..."
if ! id -u cyberscan &>/dev/null; then
    sudo adduser --disabled-password --gecos "" cyberscan
    sudo usermod -aG sudo,docker cyberscan
    sudo mkdir -p /home/cyberscan/.ssh
    sudo cp /home/ubuntu/.ssh/authorized_keys /home/cyberscan/.ssh/
    sudo chown -R cyberscan:cyberscan /home/cyberscan/.ssh
    sudo chmod 700 /home/cyberscan/.ssh && sudo chmod 600 /home/cyberscan/.ssh/authorized_keys
    echo "cyberscan ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/cyberscan
    sudo chmod 440 /etc/sudoers.d/cyberscan
fi

# ---- 10. Résumé ----
echo ""
echo "=============================================="
echo "  ✓ Setup terminé !"
echo "=============================================="
echo "  Architecture : $(uname -m)"
echo "  Docker       : $(docker --version)"
echo ""
echo "  Prochaines étapes :"
echo "  1. Se reconnecter en cyberscan :"
echo "       ssh -i ~/.ssh/oracle_staging cyberscan@$(hostname -I | awk '{print $1}')"
echo ""
echo "  2. Cloner le repo et configurer le staging :"
echo "       git clone https://github.com/DavidRocher01/cyber-vault.git"
echo "       cd cyber-vault/staging"
echo "       cp .env.example .env && chmod 600 .env"
echo "       # Éditer .env et caddy/Caddyfile"
echo "       docker compose pull && docker compose up -d"
echo ""
warn "DNS requis : staging.cyberscanapp.com + api-staging.cyberscanapp.com → $(hostname -I | awk '{print $1}')"
warn "Désactiver le login ubuntu après validation : sudo passwd -l ubuntu"
