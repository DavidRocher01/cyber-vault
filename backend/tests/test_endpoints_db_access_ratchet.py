"""Garde-fou d'architecture : les endpoints ne doivent pas accéder à la DB
directement — ils délèguent aux services (règle CLAUDE.md).

On ne peut pas corriger les ~48 fichiers historiques d'un coup, alors ce test
agit en **ratchet** : la liste `_BASELINE` gèle les fichiers qui violent
encore la règle aujourd'hui. Le test échoue si :
  - un NOUVEAU fichier d'endpoint introduit un accès DB direct (dérive), OU
  - un fichier de la baseline a été nettoyé mais pas retiré de la liste
    (la baseline doit rétrécir au fil des migrations, jamais mentir).

Un accès DB direct = usage de `db.execute/add/commit/...` ou d'un `select(...)`
SQLAlchemy dans le module d'endpoint. Le simple fait de recevoir
`db: AsyncSession` et de le passer à un service n'est PAS un accès direct.
"""

import re
from pathlib import Path

_ENDPOINTS_DIR = Path(__file__).resolve().parents[1] / "app" / "api" / "v1" / "endpoints"

_DB_ACCESS = re.compile(
    r"\bdb\.(?:execute|add|commit|delete|refresh|scalar|scalars|flush|get)\b"
    r"|(?:^|\W)select\("
)

# Exceptions LÉGITIMES : ces endpoints accèdent volontairement à la DB et ne
# doivent PAS être migrés vers un service. Documenter chaque cas ici.
#   - health.py : sonde de liveness (SELECT 1 / alembic_version) — c'est le rôle
#     même de l'endpoint, aucune logique métier à déléguer.
#   - dev_testing.py : affordance E2E réservée au dev (flip d'un flag + commit),
#     jamais montée en prod.
_LEGIT_EXCEPTIONS: set[str] = {
    "health.py",
    "dev_testing.py",
}

# Fichiers qui violent ENCORE la règle (dette héritée). Cette liste ne doit que
# RÉTRÉCIR : migrer un endpoint vers un service -> le retirer d'ici.
_BASELINE: set[str] = {
    "admin_stats.py",
    "auth.py",
    "blog.py",
    "bookings.py",
    "collab.py",
    "darkweb_dossier.py",
    "newsletter.py",
    "phishing.py",
    "portal.py",
    "rssi/actions.py",
    "rssi/clients.py",
    "rssi/deliverables.py",
    "rssi/visits.py",
    "scans.py",
    "sites.py",
    "subscriptions.py",
    "users.py",
    "vault.py",
    "webhooks.py",
}


def _current_offenders() -> set[str]:
    offenders: set[str] = set()
    for path in _ENDPOINTS_DIR.rglob("*.py"):
        if path.name == "__init__.py":
            continue
        rel = path.relative_to(_ENDPOINTS_DIR).as_posix()
        if rel in _LEGIT_EXCEPTIONS:
            continue
        if _DB_ACCESS.search(path.read_text(encoding="utf-8")):
            offenders.add(rel)
    return offenders


def test_no_new_endpoint_db_access():
    offenders = _current_offenders()

    new = offenders - _BASELINE
    assert not new, (
        f"Nouveaux endpoints avec accès DB direct (déléguer aux services) : {sorted(new)}"
    )

    stale = _BASELINE - offenders
    assert not stale, (
        "Ces fichiers ne violent plus la règle : retirez-les de _BASELINE "
        f"pour garder le garde-fou honnête : {sorted(stale)}"
    )
