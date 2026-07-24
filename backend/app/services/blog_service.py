"""Service d'acces aux articles de blog.

L'endpoint garde la conversion schemas HTTP <-> modele ; ce service porte
les requetes et les frontieres de transaction. Les fonctions de creation et
de mise a jour recoivent un dict de champs *modele* (snake_case), pas un
schema Pydantic.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.blog_post import BlogPost


async def list_published(db: AsyncSession) -> list[BlogPost]:
    """Articles publies, du plus recent au plus ancien."""
    result = await db.execute(
        select(BlogPost)
        .where(BlogPost.is_published == True)  # noqa: E712
        .order_by(BlogPost.date.desc())
    )
    return list(result.scalars().all())


async def get_published_by_slug(db: AsyncSession, slug: str) -> BlogPost | None:
    """Article publie par slug, sinon None."""
    result = await db.execute(
        select(BlogPost).where(BlogPost.slug == slug, BlogPost.is_published == True)  # noqa: E712
    )
    return result.scalar_one_or_none()


async def list_all(db: AsyncSession) -> list[BlogPost]:
    """Tous les articles (publies ou non), du plus recent au plus ancien."""
    result = await db.execute(select(BlogPost).order_by(BlogPost.date.desc()))
    return list(result.scalars().all())


async def get_by_slug(db: AsyncSession, slug: str) -> BlogPost | None:
    """Article par slug (sans filtre de publication), sinon None."""
    result = await db.execute(select(BlogPost).where(BlogPost.slug == slug))
    return result.scalar_one_or_none()


async def create_post(db: AsyncSession, values: dict) -> BlogPost:
    """Cree un article a partir d'un dict de champs modele."""
    now = datetime.now(UTC)
    post = BlogPost(**values, created_at=now, updated_at=now)
    db.add(post)
    await db.commit()
    return post


async def update_post(db: AsyncSession, post: BlogPost, values: dict) -> BlogPost:
    """Met a jour un article a partir d'un dict de champs modele."""
    for field, value in values.items():
        setattr(post, field, value)
    post.updated_at = datetime.now(UTC)
    await db.commit()
    return post


async def delete_post(db: AsyncSession, post: BlogPost) -> None:
    """Supprime un article."""
    await db.delete(post)
    await db.commit()
