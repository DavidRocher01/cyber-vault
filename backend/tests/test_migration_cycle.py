"""
I3 — Test cycle migration Alembic upgrade/downgrade.
Vérifie qu'un upgrade head suivi d'un downgrade base suivi d'un re-upgrade head fonctionne sans erreur.
Ce test protège contre les migrations avec des downgrade() buggués.
"""

import pytest

from alembic import command
from alembic.config import Config


@pytest.fixture(scope="module")
def alembic_cfg(pg_url):
    cfg = Config("alembic.ini")
    cfg.set_main_option(
        "sqlalchemy.url", pg_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    )
    return cfg


@pytest.mark.asyncio
async def test_migration_upgrade_downgrade_cycle(alembic_cfg):
    """Full cycle: head → base → head must succeed without error."""
    command.upgrade(alembic_cfg, "head")
    command.downgrade(alembic_cfg, "base")
    command.upgrade(alembic_cfg, "head")
