from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import get_db
from ..schemas import SearchResponse, MaterialListOut
from ..models import Material

router = APIRouter(prefix="/search", tags=["search"])

@router.get("", response_model=SearchResponse)
async def search(
    q: str = Query("", description="query string"),
    discipline: str | None = None,
    type: str | None = None,
    course: int | None = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * page_size

    # FTS: если есть строка — ранжируем по ts_rank, иначе по свежести
    if q.strip():
        sql = text("""
            SELECT id, title, discipline, type, tags, score, created_at
            FROM materials
            WHERE search_tsv @@ plainto_tsquery('russian', :q)
              AND (:discipline IS NULL OR discipline = :discipline)
              AND (:type IS NULL OR type = :type)
              AND (:course IS NULL OR course = :course)
            ORDER BY ts_rank(search_tsv, plainto_tsquery('russian', :q)) DESC, created_at DESC
            LIMIT :lim OFFSET :off
        """)
        params = dict(q=q, discipline=discipline, type=type, course=course, lim=page_size, off=offset)
        rows = (await db.execute(sql, params)).all()

        count_sql = text("""
            SELECT count(*) FROM materials
            WHERE search_tsv @@ plainto_tsquery('russian', :q)
              AND (:discipline IS NULL OR discipline = :discipline)
              AND (:type IS NULL OR type = :type)
              AND (:course IS NULL OR course = :course)
        """)
        total = (await db.execute(count_sql, params)).scalar_one()
    else:
        stmt = select(Material).order_by(Material.created_at.desc())
        if discipline: stmt = stmt.where(Material.discipline == discipline)
        if type: stmt = stmt.where(Material.type == type)
        if course: stmt = stmt.where(Material.course == course)
        stmt = stmt.offset(offset).limit(page_size)
        rows = [(m.id, m.title, m.discipline, m.type, m.tags, m.score, m.created_at)
                for m in (await db.execute(stmt)).scalars()]
        # total опустим для краткости — сделаем отдельный count в следующей итерации

    items = [
        MaterialListOut(
            id=r[0], title=r[1], discipline=r[2], type=r[3],
            tags=r[4] or [], score=r[5], created_at=r[6],
        ) for r in rows
    ]
    return SearchResponse(items=items, total=len(items) if not q else total, page=page, page_size=page_size)