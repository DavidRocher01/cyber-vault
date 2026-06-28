"""
I3 — Test cycle migration Alembic upgrade/downgrade.
Vérifie qu'un upgrade head suivi d'un downgrade base suivi d'un re-upgrade head fonctionne sans erreur.
Ce test protège contre les migrations avec des downgrade() buggués.

Note: uses its own isolated PostgreSQL container (separate from the shared session container)
so that create_all from conftest.py doesn't interfere with Alembic DDL.
"""

import pytest
from testcontainers.postgres import PostgresContainer

from alembic import command
from alembic.config import Config


@pytest.fixture(scope="module")
def alembic_cfg():
    with PostgresContainer("postgres:16-alpine") as pg:
        url = pg.get_connection_url().replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
        cfg = Config("alembic.ini")
        cfg.set_main_option("sqlalchemy.url", url)
        yield cfg


def test_migration_upgrade_downgrade_cycle(alembic_cfg):
    """Full cycle on a clean DB: head → base → head must succeed without error."""
    command.upgrade(alembic_cfg, "head")
    command.downgrade(alembic_cfg, "base")
    command.upgrade(alembic_cfg, "head")
