"""
seed_test_db.py — Nettoie et injecte des données de test (Clean Slate).
Usage : python scripts/seed_test_db.py
"""
import asyncio
import os
import sys

# Fix pour Python 3.14 + asyncpg sur Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:password@localhost:5432/cybervault"
)

# Import tardif pour éviter les dépendances circulaires
async def seed():
    from app.core.database import Base
    from app.core.security import hash_password
    from app.models.user import User  # noqa: F401

    engine = create_async_engine(DATABASE_URL, echo=True)
    AsyncSession_ = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        print("[CLEAN] Suppression des tables existantes...")
        await conn.run_sync(Base.metadata.drop_all)
        print("[CREATE] Recréation des tables...")
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession_() as session:
        from app.models.vault_item import VaultItem  # noqa: F401
        users = [
            User(email="admin@cybervault.dev", hashed_password=hash_password("AdminPass123!"), is_active=True),
            User(email="user@cybervault.dev", hashed_password=hash_password("UserPass123!"), is_active=True),
        ]
        session.add_all(users)
        await session.flush()

        vault_items = [
            VaultItem(owner_id=users[0].id, title="GitHub", username="admin", password_encrypted="enc_github_pass", url="https://github.com"),
            VaultItem(owner_id=users[0].id, title="AWS Console", username="admin@cybervault.dev", password_encrypted="enc_aws_pass", url="https://aws.amazon.com"),
            VaultItem(owner_id=users[1].id, title="Notion", username="user", password_encrypted="enc_notion_pass", url="https://notion.so"),
        ]
        session.add_all(vault_items)
        await session.commit()
        print(f"[SEED] {len(users)} utilisateurs + {len(vault_items)} entrées vault injectés.")

    await engine.dispose()
    print("[DONE] Base de test prête.")


if __name__ == "__main__":
    asyncio.run(seed())
