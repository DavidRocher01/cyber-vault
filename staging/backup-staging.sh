#!/usr/bin/env bash
# ============================================
# Script de sauvegarde — Staging Oracle Cloud CyberVault
# ============================================
#
# Backup quotidien PostgreSQL + config
# Sync optionnel vers stockage offsite
#
# Cron (3h du matin) :
#   0 3 * * * /home/cyberscan/cyber-vault-staging/backup-staging.sh >> /home/cyberscan/backup.log 2>&1

set -euo pipefail

STAGING_DIR="${STAGING_DIR:-/home/cyberscan/cyber-vault-staging}"
BACKUP_DIR="${BACKUP_DIR:-/home/cyberscan/backups}"
DATE=$(date +%Y-%m-%d_%H%M%S)
RETENTION_DAYS="${RETENTION_DAYS:-14}"

BACKUP_REMOTE="${BACKUP_REMOTE:-}"
BACKUP_SSH_PORT="${BACKUP_SSH_PORT:-22}"
BACKUP_SSH_KEY="${BACKUP_SSH_KEY:-$HOME/.ssh/storage_box}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
error_exit() { log "ERREUR : $*"; exit 1; }

log "▶ Démarrage du backup staging"
mkdir -p "$BACKUP_DIR"
cd "$STAGING_DIR" || error_exit "Dossier staging introuvable : $STAGING_DIR"

docker compose ps --status running | grep -q "postgres" || error_exit "Container postgres non démarré"

# ---- 1. Dump PostgreSQL ----
log "▶ Dump PostgreSQL..."
set -a; source "$STAGING_DIR/.env"; set +a

DB_BACKUP="$BACKUP_DIR/db_${DATE}.sql.gz"
docker compose exec -T postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" \
    | gzip > "$DB_BACKUP" || error_exit "Échec du dump PostgreSQL"

log "  ✓ $(basename "$DB_BACKUP") ($(du -h "$DB_BACKUP" | cut -f1))"

# ---- 2. Backup configuration ----
log "▶ Backup configuration..."
CONFIG_BACKUP="$BACKUP_DIR/config_${DATE}.tar.gz"
tar -czf "$CONFIG_BACKUP" -C "$STAGING_DIR" \
    docker-compose.yml caddy/Caddyfile 2>/dev/null || true
log "  ✓ $(basename "$CONFIG_BACKUP")"

# ---- 3. Sync offsite (CRITIQUE pour éviter suspension Oracle) ----
if [ -n "$BACKUP_REMOTE" ]; then
    log "▶ Sync vers offsite : $BACKUP_REMOTE"
    rsync -avz --delete \
        -e "ssh -p $BACKUP_SSH_PORT -i $BACKUP_SSH_KEY -o StrictHostKeyChecking=no" \
        "$BACKUP_DIR/" "$BACKUP_REMOTE/" && log "  ✓ Sync offsite OK" \
        || log "  ⚠ Échec sync offsite — backups locaux conservés"
else
    log "  ⚠ BACKUP_REMOTE non configuré — PAS DE SYNC OFFSITE"
    log "  ⚠ Oracle peut suspendre les instances sans activité — configurer un offsite !"
fi

# ---- 4. Purge ----
PURGED=$(find "$BACKUP_DIR" -name "*.gz" -mtime +"$RETENTION_DAYS" | wc -l)
find "$BACKUP_DIR" -name "*.gz" -mtime +"$RETENTION_DAYS" -delete
log "▶ $PURGED anciens backups supprimés (> $RETENTION_DAYS jours)"

log "✓ Backup terminé — Total : $(du -sh "$BACKUP_DIR" | cut -f1), $(find "$BACKUP_DIR" -name "*.gz" | wc -l) fichiers"
