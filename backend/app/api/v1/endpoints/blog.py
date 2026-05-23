import json
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.blog_post import BlogPost
from app.schemas.blog import BlogPostDetailOut, BlogPostIn, BlogPostOut

router = APIRouter(prefix="/blog", tags=["blog"])


def _require_admin(x_admin_key: str = Header(default="")) -> None:
    if not settings.ADMIN_API_KEY or not secrets.compare_digest(x_admin_key, settings.ADMIN_API_KEY):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé")


def _to_out(p: BlogPost) -> BlogPostOut:
    try:
        tags = json.loads(p.tags)
    except Exception:
        tags = []
    return BlogPostOut(
        id=p.id, slug=p.slug, title=p.title, description=p.description,
        date=p.date, readTime=p.read_time, category=p.category,
        tags=tags, isPublished=p.is_published,
    )


def _to_detail(p: BlogPost) -> BlogPostDetailOut:
    try:
        tags = json.loads(p.tags)
    except Exception:
        tags = []
    return BlogPostDetailOut(
        id=p.id, slug=p.slug, title=p.title, description=p.description,
        date=p.date, readTime=p.read_time, category=p.category,
        tags=tags, isPublished=p.is_published, htmlContent=p.html_content,
    )


@router.get("/articles", response_model=list[BlogPostOut])
async def list_articles(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(BlogPost)
        .where(BlogPost.is_published == True)  # noqa: E712
        .order_by(BlogPost.date.desc())
    )
    return [_to_out(p) for p in result.scalars().all()]


@router.get("/articles/{slug}", response_model=BlogPostDetailOut)
async def get_article(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(BlogPost).where(BlogPost.slug == slug, BlogPost.is_published == True)  # noqa: E712
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article introuvable")
    return _to_detail(post)


@router.get("/admin/articles", response_model=list[BlogPostOut], dependencies=[Depends(_require_admin)])
async def admin_list_articles(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BlogPost).order_by(BlogPost.date.desc()))
    return [_to_out(p) for p in result.scalars().all()]


@router.get("/admin/articles/{slug}", response_model=BlogPostDetailOut, dependencies=[Depends(_require_admin)])
async def admin_get_article(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BlogPost).where(BlogPost.slug == slug))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article introuvable")
    return _to_detail(post)


@router.post(
    "/admin/articles",
    response_model=BlogPostDetailOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_require_admin)],
)
async def create_article(payload: BlogPostIn, db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    post = BlogPost(
        slug=payload.slug,
        title=payload.title,
        description=payload.description,
        date=payload.date,
        read_time=payload.readTime,
        category=payload.category,
        tags=json.dumps(payload.tags),
        html_content=payload.htmlContent,
        is_published=payload.isPublished,
        created_at=now,
        updated_at=now,
    )
    db.add(post)
    await db.flush()
    return _to_detail(post)


@router.put(
    "/admin/articles/{slug}",
    response_model=BlogPostDetailOut,
    dependencies=[Depends(_require_admin)],
)
async def update_article(slug: str, payload: BlogPostIn, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BlogPost).where(BlogPost.slug == slug))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article introuvable")
    post.slug = payload.slug
    post.title = payload.title
    post.description = payload.description
    post.date = payload.date
    post.read_time = payload.readTime
    post.category = payload.category
    post.tags = json.dumps(payload.tags)
    post.html_content = payload.htmlContent
    post.is_published = payload.isPublished
    post.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return _to_detail(post)


@router.delete(
    "/admin/articles/{slug}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(_require_admin)],
)
async def delete_article(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BlogPost).where(BlogPost.slug == slug))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article introuvable")
    await db.delete(post)
