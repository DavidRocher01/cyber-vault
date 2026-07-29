#!/usr/bin/env python3
"""Génère un backend/.env de DÉVELOPPEMENT prêt à l'emploi.

Repart de backend/.env.example, génère les secrets locaux (SECRET_KEY,
ADMIN_API_KEY) et pose des valeurs de dev sûres (Postgres local, CORS localhost,
Sentry off, phishing localhost). Les secrets de services TIERS (Stripe, Resend,
HIBP...) restent vides : ce script ne va JAMAIS chercher de vraie valeur prod
(celles-ci vivent dans AWS Secrets Manager `cybervault/prod`, jamais en dev).

Usage :
    python scripts/bootstrap_dev_env.py            # crée backend/.env s'il manque
    python scripts/bootstrap_dev_env.py --force     # écrase le .env existant
    python scripts/bootstrap_dev_env.py --print     # affiche sans écrire

Sûr par défaut : refuse d'écraser un backend/.env existant sans --force.
"""

from __future__ import annotations

import argparse
import secrets
import sys
from pathlib import Path

# Racine repo = parent de scripts/
REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = REPO_ROOT / "backend" / ".env.example"
TARGET = REPO_ROOT / "backend" / ".env"

# Clés dont la valeur est FORCÉE à un défaut de dev (l'inline comment de
# l'exemple est conservé). Les callables sont évalués à la génération.
DEV_OVERRIDES: dict[str, object] = {
    "APP_ENV": "development",
    "SECRET_KEY": lambda: secrets.token_hex(32),  # 64 hex chars
    "ADMIN_API_KEY": lambda: secrets.token_hex(32),
    "DATABASE_URL": "postgresql+asyncpg://postgres:password@localhost:5432/cybervault",
    "ALLOWED_ORIGINS": '["http://localhost:4200"]',
    "FRONTEND_URL": "http://localhost:4200",
    # Pas de Sentry en dev (le DSN vide désactive proprement l'init).
    "SENTRY_DSN": "",
    # Tracking phishing local — DOIT inclure /api/v1 (cf. commentaire .env.example).
    "PHISHING_BASE_URL": "http://localhost:8000/api/v1",
    # Redis absent en dev = fallback in-memory (comme la prod mono-instance).
    "REDIS_URL": "",
}

# Clés de services TIERS laissées telles quelles dans l'exemple : à compléter à
# la main SI tu en as besoin en dev (sinon défauts app / features désactivées).
THIRD_PARTY_TODO = [
    "STRIPE_SECRET_KEY",
    "STRIPE_PUBLISHABLE_KEY",
    "STRIPE_WEBHOOK_SECRET",
    "RESEND_API_KEY",
    "HIBP_API_KEY",
    "SMTP_USER",
    "SMTP_PASSWORD",
]


def _split_line(line: str) -> tuple[str, str, str] | None:
    """Retourne (clé, valeur, commentaire_inline) pour une ligne `KEY=...`,
    sinon None (ligne vide, commentaire, section)."""
    stripped = line.rstrip("\n")
    if not stripped or stripped.lstrip().startswith("#") or "=" not in stripped:
        return None
    key, _, rest = stripped.partition("=")
    key = key.strip()
    if not key.replace("_", "").isalnum():
        return None
    # Sépare une éventuelle valeur d'un commentaire inline « # ... ».
    value, sep, comment = rest.partition("#")
    inline = f"  #{comment}" if sep else ""
    return key, value.strip(), inline


def build_env(example_text: str) -> str:
    out_lines: list[str] = []
    for line in example_text.splitlines():
        parsed = _split_line(line)
        if parsed is None:
            out_lines.append(line)
            continue
        key, _value, inline = parsed
        if key in DEV_OVERRIDES:
            new = DEV_OVERRIDES[key]
            new_value = new() if callable(new) else new
            out_lines.append(f"{key}={new_value}{inline}")
        else:
            out_lines.append(line)
    header = (
        "# ⚠️ Fichier de DÉVELOPPEMENT généré par scripts/bootstrap_dev_env.py\n"
        "# NE JAMAIS committer (couvert par .gitignore). Secrets prod = AWS SM.\n"
        "\n"
    )
    return header + "\n".join(out_lines) + "\n"


def main() -> int:
    # Windows : la console est souvent en cp1252 et casse sur les emoji/puces.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force", action="store_true", help="écrase backend/.env existant"
    )
    parser.add_argument(
        "--print",
        dest="print_only",
        action="store_true",
        help="affiche le contenu sans écrire de fichier",
    )
    args = parser.parse_args()

    if not EXAMPLE.exists():
        print(f"[ERREUR] introuvable : {EXAMPLE}", file=sys.stderr)
        return 1

    content = build_env(EXAMPLE.read_text(encoding="utf-8"))

    if args.print_only:
        print(content)
        return 0

    if TARGET.exists() and not args.force:
        print(f"[STOP] {TARGET} existe déjà. Relance avec --force pour écraser.")
        return 1

    TARGET.write_text(content, encoding="utf-8")
    print(f"[OK] écrit : {TARGET}")
    print("  • SECRET_KEY et ADMIN_API_KEY générés aléatoirement (dev)")
    print("  • DATABASE_URL -> Postgres local :5432/cybervault")
    print("  • CORS/FRONTEND -> http://localhost:4200 ; Sentry off ; phishing local")
    print("\n  À compléter À LA MAIN seulement si tu en as besoin en dev :")
    for key in THIRD_PARTY_TODO:
        print(f"    - {key}")
    print(
        "\n  Rappel : ne JAMAIS mettre de valeur prod ici "
        "(prod = AWS Secrets Manager cybervault/prod)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
