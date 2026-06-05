#!/usr/bin/env python3
"""
Vérifie la santé du DAG Alembic avant commit :
  - Une seule tête
  - Pas de révisions dupliquées
  - Pas de migrations fantômes (upgrade=pass AND downgrade=pass)

Usage :
  cd backend && python ../scripts/check_migrations.py
"""

import re
import sys
from pathlib import Path


def main() -> int:
    versions_dir = Path(__file__).parent.parent / "backend" / "alembic" / "versions"
    if not versions_dir.exists():
        print("ERROR: backend/alembic/versions/ introuvable")
        return 1

    files = list(versions_dir.glob("*.py"))
    errors: list[str] = []

    revision_ids: dict[str, list[str]] = {}  # id → [fichiers]
    phantoms: list[str] = []

    for f in files:
        content = f.read_text(encoding="utf-8")

        # Extraire revision ID
        m = re.search(r'^revision:\s*str\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
        if not m:
            continue
        rev_id = m.group(1)
        revision_ids.setdefault(rev_id, []).append(f.name)

        # Détecter migration fantôme (upgrade=pass ET downgrade=pass)
        # Exclure les migrations merge (branch_labels ou plusieurs down_revision)
        is_merge = bool(re.search(r'branch_labels.*merge|down_revision.*\(', content))
        has_real_upgrade = bool(re.search(r'def upgrade.*?(?:op\.|alembic\.)', content, re.DOTALL))
        has_real_downgrade = bool(re.search(r'def downgrade.*?(?:op\.|alembic\.)', content, re.DOTALL))
        if not is_merge and not has_real_upgrade and not has_real_downgrade:
            phantoms.append(f.name)

    # Vérifier doublons
    for rev_id, fnames in revision_ids.items():
        if len(fnames) > 1:
            errors.append(f"ID dupliqué '{rev_id}' dans : {', '.join(fnames)}")

    # Rapporter fantômes
    for fname in phantoms:
        errors.append(f"Migration fantôme (upgrade+downgrade vides) : {fname}")

    # Vérifier nombre de têtes via alembic
    try:
        import subprocess
        result = subprocess.run(
            ["python", "-m", "alembic", "heads"],
            cwd=Path(__file__).parent.parent / "backend",
            capture_output=True, text=True
        )
        heads = [l for l in result.stdout.splitlines() if l.strip() and not l.startswith("INFO")]
        if len(heads) > 1:
            errors.append(f"Plusieurs têtes Alembic détectées ({len(heads)}) — merger avant de continuer")
        elif len(heads) == 1:
            print(f"OK - tete unique : {heads[0].strip()}")
    except Exception as e:
        print(f"WARN — impossible de vérifier les têtes : {e}")

    if errors:
        print("\nERROR - Problemes detectes :")
        for err in errors:
            print(f"  FAIL {err}")
        print()
        return 1

    print(f"OK - {len(files)} migrations, pas de doublons, pas de fantomes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
