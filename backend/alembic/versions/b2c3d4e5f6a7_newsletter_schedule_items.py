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
        "actu_title": "Ransomware sur Change Healthcare : 190 millions de dossiers médicaux volés",
        "actu_url": "https://techcrunch.com/2025/01/27/how-the-ransomware-attack-at-change-healthcare-went-down-a-timeline/",
        "actu_source": "TechCrunch",
        "reflex": "Activer la Double Authentification (MFA)",
    },
    {
        "position": 2,
        "actu_title": "Fuite chez PowerSchool : données de 60 millions d'élèves américains exposées",
        "actu_url": "https://www.bleepingcomputer.com/news/security/powerschool-data-breach-exposes-info-of-students-in-us-and-canada/",
        "actu_source": "BleepingComputer",
        "reflex": "Utiliser un gestionnaire de mots de passe",
    },
    {
        "position": 3,
        "actu_title": "Deepfake vidéo d'un CFO : Arup perd 25 millions de dollars à Hong Kong",
        "actu_url": "https://fortune.com/europe/2024/05/17/arup-deepfake-fraud-scam-victim-hong-kong-25-million-cfo/",
        "actu_source": "Fortune",
        "reflex": "Créer un mot de passe verbal pour les virements",
    },
    {
        "position": 4,
        "actu_title": "Vulnérabilités critiques dans les modems IoT industriels via SMS",
        "actu_url": "https://www.bleepingcomputer.com/news/security/widely-used-modems-in-industrial-iot-devices-open-to-sms-attack/",
        "actu_source": "BleepingComputer",
        "reflex": "Changer le mot de passe par défaut de sa box/caméra",
    },
    {
        "position": 5,
        "actu_title": "Ransomware LockBit frappe la mairie de Calvià (Majorque) — 10 M€ de rançon",
        "actu_url": "https://therecord.media/calvia-spain-ransomware-attack-10-million-euros-demand",
        "actu_source": "The Record",
        "reflex": "Vérifier que sa sauvegarde est hors-ligne",
    },
    {
        "position": 6,
        "actu_title": "Le FBI alerte sur des QR codes malveillants utilisés par le groupe Kimsuky",
        "actu_url": "https://www.bleepingcomputer.com/news/security/fbi-warns-about-kimsuky-hackers-using-qr-codes-to-phish-us-orgs/",
        "actu_source": "BleepingComputer",
        "reflex": "Ne jamais scanner un QR code public sans vérifier",
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
