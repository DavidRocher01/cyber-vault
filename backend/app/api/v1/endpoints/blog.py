from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_admin
from app.core.http_cache import cache_public
from app.models.blog_post import BlogPost
from app.schemas.blog import BlogPostDetailOut, BlogPostIn, BlogPostOut
from app.services import blog_service


def _post_values(payload: BlogPostIn) -> dict:
    """Mappe le schema HTTP (camelCase) vers les champs modele (snake_case)."""
    return {
        "slug": payload.slug,
        "title": payload.title,
        "description": payload.description,
        "date": payload.date,
        "read_time": payload.readTime,
        "category": payload.category,
        "tags": payload.tags,
        "html_content": payload.htmlContent,
        "is_published": payload.isPublished,
    }


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


@router.get(
    "/articles",
    response_model=list[BlogPostOut],
    summary="Lister les articles de blog publiés",
    dependencies=[Depends(cache_public(300))],
)
async def list_articles(db: AsyncSession = Depends(get_db)):
    return [_to_out(p) for p in await blog_service.list_published(db)]


@router.get(
    "/articles/{slug}",
    response_model=BlogPostDetailOut,
    summary="Détail d'un article publié (par slug)",
    responses={404: {"description": "Article introuvable ou non publié"}},
    dependencies=[Depends(cache_public(300))],
)
async def get_article(slug: str, db: AsyncSession = Depends(get_db)):
    post = await blog_service.get_published_by_slug(db, slug)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article introuvable")
    return _to_detail(post)


@router.get(
    "/admin/articles",
    response_model=list[BlogPostOut],
    dependencies=[Depends(require_admin)],
    summary="[Admin] Lister tous les articles (publiés ou non)",
)
async def admin_list_articles(db: AsyncSession = Depends(get_db)):
    return [_to_out(p) for p in await blog_service.list_all(db)]


@router.get(
    "/admin/articles/{slug}",
    response_model=BlogPostDetailOut,
    dependencies=[Depends(require_admin)],
    summary="[Admin] Détail d'un article (par slug)",
    responses={404: {"description": "Article introuvable"}},
)
async def admin_get_article(slug: str, db: AsyncSession = Depends(get_db)):
    post = await blog_service.get_by_slug(db, slug)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article introuvable")
    return _to_detail(post)


@router.post(
    "/admin/articles",
    response_model=BlogPostDetailOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
    summary="[Admin] Créer un article",
)
async def create_article(payload: BlogPostIn, db: AsyncSession = Depends(get_db)):
    post = await blog_service.create_post(db, _post_values(payload))
    return _to_detail(post)


@router.put(
    "/admin/articles/{slug}",
    response_model=BlogPostDetailOut,
    dependencies=[Depends(require_admin)],
    summary="[Admin] Mettre à jour un article",
    responses={404: {"description": "Article introuvable"}},
)
async def update_article(slug: str, payload: BlogPostIn, db: AsyncSession = Depends(get_db)):
    post = await blog_service.get_by_slug(db, slug)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article introuvable")
    post = await blog_service.update_post(db, post, _post_values(payload))
    return _to_detail(post)


@router.delete(
    "/admin/articles/{slug}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
    summary="[Admin] Supprimer un article",
    responses={404: {"description": "Article introuvable"}},
)
async def delete_article(slug: str, db: AsyncSession = Depends(get_db)):
    post = await blog_service.get_by_slug(db, slug)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article introuvable")
    await blog_service.delete_post(db, post)
