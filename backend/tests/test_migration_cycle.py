"""
I3 — Tests Alembic : cycle upgrade/downgrade ET conformite migrations <-> modeles.

Note: uses its own isolated PostgreSQL container (separate from the shared session container)
so that create_all from conftest.py doesn't interfere with Alembic DDL.
"""

import asyncio

import pytest
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer

import app.models  # noqa: F401 — enregistre tous les modeles dans Base.metadata
from alembic import command
from app.core.database import Base


@pytest.fixture(scope="module")
def alembic_env():
    """Conteneur PostgreSQL dedie + config Alembic pointant dessus.

    postgres:17 = meme version majeure que la PROD (RDS 17), comme le conteneur
    de conftest.py. Tester les migrations sur 16 alors qu'elles s'appliquent sur
    17 en prod laisserait passer exactement le genre d'ecart qu'on cherche ici.
    """
    with PostgresContainer("postgres:17-alpine") as pg:
        async_url = pg.get_connection_url().replace(
            "postgresql+psycopg2://", "postgresql+asyncpg://", 1
        )
        cfg = Config("alembic.ini")
        cfg.set_main_option("sqlalchemy.url", async_url)
        yield cfg, async_url


@pytest.fixture(scope="module")
def alembic_cfg(alembic_env):
    return alembic_env[0]


def test_migration_upgrade_downgrade_cycle(alembic_cfg):
    """Full cycle on a clean DB: head → base → head must succeed without error."""
    command.upgrade(alembic_cfg, "head")
    command.downgrade(alembic_cfg, "base")
    command.upgrade(alembic_cfg, "head")


# ── Conformite migrations <-> modeles ─────────────────────────────────────────


# Differences tolerees, avec la raison. Toute autre divergence fait echouer le
# test : c'est le but. Format : (type_de_diff, nom_table, nom_colonne_ou_None).
_DIVERGENCES_ACCEPTEES: set[tuple[str, str, str | None]] = set()


def _aplatir(diffs) -> list[tuple]:
    """compare_metadata groupe les modifications d'une meme colonne dans une
    sous-liste (['modify_type', ...], ['modify_nullable', ...]). On aplatit pour
    traiter chaque divergence individuellement."""
    plat: list[tuple] = []
    for d in diffs:
        if isinstance(d, list):
            plat.extend(d)
        else:
            plat.append(d)
    return plat


def _resume_diff(diff: tuple) -> tuple[str, str, str | None]:
    """Normalise un element de compare_metadata en (type, table, colonne)."""
    # Les diffs de colonne sont des tuples plats : ('add_column', schema, table, col)
    # ou ('modify_type', schema, table, colname, opts, old, new).
    kind = diff[0]
    if kind in {"add_table", "remove_table"}:
        return (kind, diff[1].name, None)
    if kind in {"add_column", "remove_column"}:
        return (kind, diff[2], diff[3].name)
    if kind in {"add_index", "remove_index", "add_constraint", "remove_constraint"}:
        obj = diff[1]
        return (kind, getattr(obj.table, "name", "?"), getattr(obj, "name", None))
    if kind.startswith("modify_"):
        return (kind, diff[2], diff[3])
    return (kind, str(diff[1:2]), None)


def _diff_schema(sync_conn) -> list:
    """Compare le schema connecte aux modeles. Execute via run_sync : Alembic
    n'a pas d'API d'autogenerate asynchrone."""
    ctx = MigrationContext.configure(sync_conn, opts={"compare_type": True})
    return compare_metadata(ctx, Base.metadata)


@pytest.mark.asyncio
async def test_migrations_match_models(alembic_env):
    """Le schema produit par les migrations doit correspondre aux modeles.

    Garde-fou du bug de prod du 2026-07-29 : ``Notification.created_at`` etait
    declare sans ``timezone=True``, la colonne prod etait donc en TIMESTAMP
    WITHOUT TIME ZONE et asyncpg rejetait chaque insert. Invisible en test car
    la suite construit son schema avec ``Base.metadata.create_all`` (conftest.py)
    et n'execute JAMAIS les migrations : les deux sources de verite pouvaient
    diverger sans que rien ne le signale.

    Ici on part d'une base vierge, on applique ``alembic upgrade head``, puis on
    compare le schema reel aux modeles avec ``compare_type=True`` (indispensable :
    sans lui, un changement de type comme timestamp -> timestamptz passe inapercu).
    """
    cfg, async_url = alembic_env
    # env.py fait asyncio.run() : impossible depuis une boucle deja active, on
    # passe donc l'upgrade dans un thread sans boucle.
    await asyncio.to_thread(command.upgrade, cfg, "head")

    engine = create_async_engine(async_url)
    try:
        async with engine.connect() as conn:
            diffs = await conn.run_sync(_diff_schema)
    finally:
        await engine.dispose()

    inattendus = [d for d in _aplatir(diffs) if _resume_diff(d) not in _DIVERGENCES_ACCEPTEES]

    assert not inattendus, (
        "Le schema issu des migrations diverge des modeles SQLAlchemy.\n"
        "Chaque ligne est une correction manquante : soit le modele, soit une\n"
        "nouvelle migration.\n\n" + "\n".join(f"  - {_resume_diff(d)}  |  {d}" for d in inattendus)
    )
