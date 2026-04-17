from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


async def paginate(
    db: AsyncSession,
    base_query,
    count_query,
    page: int,
    per_page: int,
) -> dict:
    """Run a count + paged SELECT and return a standard pagination dict.

    base_query  — the SELECT statement to paginate (no offset/limit applied yet)
    count_query — a SELECT(func.count()) statement for the same filter
    """
    total_result = await db.execute(count_query)
    total: int = total_result.scalar_one()

    items_result = await db.execute(
        base_query.offset((page - 1) * per_page).limit(per_page)
    )
    items = items_result.scalars().all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": max(1, -(-total // per_page)),
    }
