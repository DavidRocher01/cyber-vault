from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_admin
from app.models.blog_post import BlogPost
from app.schemas.blog import BlogPostDetailOut, BlogPostIn, BlogPostOut

router = APIRouter(prefix="/blog", tags=["blog"])


def _to_out(p: BlogPost) -> BlogPostOut:
    return BlogPostOut(
        id=p.id,
        slug=p.slug,
        title=p.title,
        description=p.description,
        date=p.date,
        readTime=p.read_time,
        category=p.category,
        tags=p.tags,
        isPublished=p.is_published,
    )


def _to_detail(p: BlogPost) -> BlogPostDetailOut:
    return BlogPostDetailOut(
        id=p.id,
        slug=p.slug,
        title=p.title,
        description=p.description,
        date=p.date,
        readTime=p.read_time,
        category=p.category,
        tags=p.tags,
        isPublished=p.is_published,
        htmlContent=p.html_content,
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


@router.get(
    "/admin/articles",
    response_model=list[BlogPostOut],
    dependencies=[Depends(require_admin)],
)
async def admin_list_articles(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BlogPost).order_by(BlogPost.date.desc()))
    return [_to_out(p) for p in result.scalars().all()]


@router.get(
    "/admin/articles/{slug}",
    response_model=BlogPostDetailOut,
    dependencies=[Depends(require_admin)],
)
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
    dependencies=[Depends(require_admin)],
)
async def create_article(payload: BlogPostIn, db: AsyncSession = Depends(get_db)):
    now = datetime.now(UTC)
    post = BlogPost(
        slug=payload.slug,
        title=payload.title,
        description=payload.description,
        date=payload.date,
        read_time=payload.readTime,
        category=payload.category,
        tags=payload.tags,
        html_content=payload.htmlContent,
        is_published=payload.isPublished,
        created_at=now,
        updated_at=now,
    )
    db.add(post)
    await db.commit()
    return _to_detail(post)


@router.put(
    "/admin/articles/{slug}",
    response_model=BlogPostDetailOut,
    dependencies=[Depends(require_admin)],
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
    post.updated_at = datetime.now(UTC)
    await db.commit()
    return _to_detail(post)


@router.delete(
    "/admin/articles/{slug}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
async def delete_article(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BlogPost).where(BlogPost.slug == slug))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article introuvable")
    await db.delete(post)
    await db.commit()
