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
        "actu_title": "L'IA accélère les cyberattaques : une faille exploitée en seulement 72 minutes",
        "actu_url": "https://www.lemondeinformatique.fr/actualites/lire-l-ia-accelere-la-vitesse-des-cyberattaques-99405.html",
        "actu_source": "Le Monde Informatique",
        "reflex": "Réduire le délai de détection grâce à un EDR/SIEM",
    },
    {
        "position": 2,
        "actu_title": "Piratage du fichier SIA : 41 000 détenteurs d'armes exposés en France",
        "actu_url": "https://korben.info/fuite-sia-armes-ministere-interieur.html",
        "actu_source": "Korben",
        "reflex": "Activer la double authentification sur tous vos comptes",
    },
    {
        "position": 3,
        "actu_title": "Axios compromis : l'impact d'une intrusion nord-coréenne sur la chaîne logistique",
        "actu_url": "https://www.lemagit.fr/actualites/366641121/Axios-compromis-limpact-dune-intrusion-nord-coreenne-sur-la-chaine-logisitique",
        "actu_source": "LeMagIT",
        "reflex": "Auditer ses dépendances open source avant mise en prod",
    },
    {
        "position": 4,
        "actu_title": "Europa.eu cyberattaquée par ShinyHunters : Bruxelles minimise l'impact",
        "actu_url": "https://www.zataz.com/cyber-actualites-zataz-de-la-semaine-du-30-mars-au-4-avril-2026/",
        "actu_source": "ZATAZ",
        "reflex": "Ne jamais minimiser une alerte de sécurité — toujours investiguer",
    },
    {
        "position": 5,
        "actu_title": "Exposition de 16 milliards d'identifiants et mots de passe : que faire ?",
        "actu_url": "https://www.cnil.fr/fr/exposition-de-16-milliards-didentifiants-et-des-mots-de-passe-que-faire",
        "actu_source": "CNIL",
        "reflex": "Vérifier ses comptes sur haveibeenpwned.com et changer ses mots de passe",
    },
    {
        "position": 6,
        "actu_title": "17Cyber : le nouveau réflexe officiel pour signaler une cyberattaque en France",
        "actu_url": "https://www.gendarmerie.interieur.gouv.fr/gendinfo/actualites/2026/17cyber-le-reflexe-cyber-pour-tous",
        "actu_source": "Gendarmerie nationale",
        "reflex": "Signaler toute cyberattaque sur 17cyber.gouv.fr",
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
