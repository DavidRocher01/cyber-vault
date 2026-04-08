"""add newsletter_schedule_items table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-08 18:00:00.000000

"""
from typing import Union
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None

_NOW = datetime.now(timezone.utc).isoformat()

_SEED = [
    {
        "position": 1,
        "actu_title": "Cyberhebdo : le fabricant de jouets Hasbro mis à l'arrêt par une cyberattaque",
        "actu_url": "https://www.lemagit.fr/actualites/366641123/Cyberhebdo-du-3-avril-2026",
        "actu_source": "LeMagIT",
        "reflex": "Activer un plan de réponse aux incidents",
    },
    {
        "position": 2,
        "actu_title": "Axios compromis : l'impact d'une intrusion nord-coréenne sur la chaîne logistique",
        "actu_url": "https://www.lemagit.fr/actualites/366641121/Axios-compromis-limpact-dune-intrusion-nord-coreenne-sur-la-chaine-logisitique",
        "actu_source": "LeMagIT",
        "reflex": "Auditer ses dépendances open source avant mise en prod",
    },
    {
        "position": 3,
        "actu_title": "Citrix Netscaler CVE-2026-3055 : il est à nouveau temps de patcher",
        "actu_url": "https://www.lemagit.fr/actualites/366640755/Citrix-Netscaler-il-est-a-nouveau-temps-de-patcher",
        "actu_source": "LeMagIT",
        "reflex": "Appliquer les correctifs de sécurité sans délai",
    },
    {
        "position": 4,
        "actu_title": "Ransomware : une vulnérabilité exploitée 36 jours avant d'être rendue publique",
        "actu_url": "https://www.lemagit.fr/actualites/366640450/Ransomware-36-jours-une-vulnerabilite-inedite-exploitee-36-jours-avant-detre-rendue-publique",
        "actu_source": "LeMagIT",
        "reflex": "Activer un EDR/SIEM sur vos serveurs critiques",
    },
    {
        "position": 5,
        "actu_title": "Europa.eu cyberattaquée : Bruxelles minimise l'impact et nie toute compromission",
        "actu_url": "https://www.zataz.com/cyber-actualites-zataz-de-la-semaine-du-30-mars-au-4-avril-2026/",
        "actu_source": "ZATAZ",
        "reflex": "Ne jamais ignorer une alerte de sécurité — toujours investiguer",
    },
    {
        "position": 6,
        "actu_title": "Ransomware 2025-2026 : la concentration des groupes s'accélère",
        "actu_url": "https://www.zataz.com/ransomware-2025-2026-la-concentration-saccelere/",
        "actu_source": "ZATAZ",
        "reflex": "Vérifier que sa sauvegarde est hors-ligne et testée",
    },
]


def upgrade() -> None:
    op.create_table(
        "newsletter_schedule_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("position", sa.Integer(), nullable=False, unique=True),
        sa.Column("actu_title", sa.String(300), nullable=False),
        sa.Column("actu_url", sa.String(1000), nullable=False),
        sa.Column("actu_source", sa.String(100), nullable=False),
        sa.Column("reflex", sa.String(300), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    for item in _SEED:
        op.execute(
            sa.text(
                "INSERT INTO newsletter_schedule_items "
                "(position, actu_title, actu_url, actu_source, reflex, updated_at) "
                "VALUES (:position, :actu_title, :actu_url, :actu_source, :reflex, :updated_at)"
            ).bindparams(**item, updated_at=_NOW)
        )


def downgrade() -> None:
    op.drop_table("newsletter_schedule_items")
