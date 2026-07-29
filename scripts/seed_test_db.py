"""
seed_test_db.py — Injecte des comptes de test dans la base de dev locale.

Idempotent et NON destructif : n'ajoute que ce qui manque, ne touche jamais au
schéma. Le schéma est la propriété exclusive d'Alembic (`alembic upgrade head`).

Historique : ce script faisait `drop_all` + `create_all`. Il détruisait donc le
schéma bâti par les migrations pour le reconstruire depuis les modèles, en
perdant au passage les données injectées par les migrations (articles de blog,
grille tarifaire). Pire, `alembic_version` n'étant pas un modèle, la table
survivait et continuait d'affirmer que la tête était appliquée : `alembic
revision --autogenerate` comparait alors les modèles à eux-mêmes et ne voyait
plus aucun écart réel. Pour repartir d'une base vierge, utiliser
`alembic downgrade base && alembic upgrade head`.

Usage : cd backend && PYTHONPATH=. python ../scripts/seed_test_db.py
"""
import asyncio
import os
import sys

# Fix pour Python 3.14 + asyncpg sur Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:password@localhost:5432/cybervault"
)

SEED_USERS = [
    ("admin@cybervault.dev", "AdminPass123!"),
    ("user@cybervault.dev", "UserPass123!"),
]

# (index utilisateur dans SEED_USERS, titre, identifiant, secret, url)
SEED_VAULT_ITEMS = [
    (0, "GitHub", "admin", "enc_github_pass", "https://github.com"),
    (0, "AWS Console", "admin@cybervault.dev", "enc_aws_pass", "https://aws.amazon.com"),
    (1, "Notion", "user", "enc_notion_pass", "https://notion.so"),
]


# Import tardif pour éviter les dépendances circulaires
async def seed():
    from app.core.security import hash_password
    from app.models.user import User
    from app.models.vault_item import VaultItem

    engine = create_async_engine(DATABASE_URL, echo=False)
    AsyncSession_ = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSession_() as session:
        users: list[User] = []
        created = 0
        for email, password in SEED_USERS:
            user = await session.scalar(select(User).where(User.email == email))
            if user is None:
                user = User(
                    email=email,
                    hashed_password=hash_password(password),
                    is_active=True,
                )
                session.add(user)
                created += 1
            users.append(user)
        await session.flush()

        added = 0
        for owner_idx, title, username, secret, url in SEED_VAULT_ITEMS:
            owner = users[owner_idx]
            exists = await session.scalar(
                select(VaultItem).where(
                    VaultItem.owner_id == owner.id, VaultItem.title == title
                )
            )
            if exists is not None:
                continue
            session.add(
                VaultItem(
                    owner_id=owner.id,
                    title=title,
                    username=username,
                    password_encrypted=secret,
                    url=url,
                )
            )
            added += 1

        await session.commit()
        print(
            f"[SEED] {created} utilisateur(s) créé(s) sur {len(SEED_USERS)}, "
            f"{added} entrée(s) vault ajoutée(s) sur {len(SEED_VAULT_ITEMS)}."
        )

    await engine.dispose()
    print("[DONE] Comptes de test prêts — schéma Alembic intact.")


if __name__ == "__main__":
    asyncio.run(seed())
