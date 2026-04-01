"""
backup_db.py — Sauvegarde PostgreSQL via pg_dump (rétention 7 jours).
Usage : python scripts/backup_db.py
"""
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "cybervault")
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
PG_BIN = os.getenv("PG_BIN", r"C:\Program Files\PostgreSQL\17\bin")
BACKUP_DIR = Path(__file__).parent.parent / "backups"
RETENTION_DAYS = 7


def run_backup() -> Path:
    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = BACKUP_DIR / f"cybervault_{timestamp}.sql"

    env = os.environ.copy()
    env["PGPASSWORD"] = DB_PASSWORD

    pg_dump = Path(PG_BIN) / "pg_dump.exe" if os.name == "nt" else "pg_dump"
    subprocess.run(
        [str(pg_dump), "-h", DB_HOST, "-p", DB_PORT, "-U", DB_USER, "-F", "c", "-f", str(output_file), DB_NAME],
        env=env,
        check=True,
    )
    print(f"[OK] Backup créé : {output_file}")
    return output_file


def purge_old_backups():
    cutoff = datetime.now() - timedelta(days=RETENTION_DAYS)
    for backup in BACKUP_DIR.glob("cybervault_*.sql"):
        mtime = datetime.fromtimestamp(backup.stat().st_mtime)
        if mtime < cutoff:
            backup.unlink()
            print(f"[PURGE] Supprimé : {backup.name}")


if __name__ == "__main__":
    run_backup()
    purge_old_backups()
