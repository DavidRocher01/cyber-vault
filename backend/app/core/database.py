from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import AsyncAdaptedQueuePool

from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    poolclass=AsyncAdaptedQueuePool,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
    # Fixe la timezone de session à UTC sur CHAQUE connexion, indépendamment du
    # défaut du serveur. RDS est en UTC, mais un Postgres local (ex. Windows) est
    # souvent en Europe/Paris -> tout `now()`/`CURRENT_DATE` côté base divergerait.
    # On rend le comportement déterministe partout et on blinde la prod contre une
    # dérive du paramètre RDS. Les colonnes timestamptz sont déjà en UTC ; ceci
    # couvre les timestamp naïfs et les fonctions temporelles côté serveur.
    connect_args={"server_settings": {"timezone": "UTC"}},
)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
