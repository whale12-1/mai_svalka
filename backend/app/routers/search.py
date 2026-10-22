import re
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, text, func
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

    # 1. Базовый запрос (SELECT * FROM materials)
    stmt = select(Material)

    # 2. Добавляем полнотекстовый поиск, если есть запрос
    if q.strip():
        clean_q = re.sub(r'[^\w\s]', '', q, flags=re.UNICODE)
        
        if clean_q.strip():
            search_query = " & ".join([f"{word}:*" for word in clean_q.split()])
            
            # Используем text() только для FTS-условия, привязывая параметр :q
            stmt = stmt.where(text("search_tsv @@ to_tsquery('simple', :q)").bindparams(q=search_query))
            # Сортируем по релевантности (рангу)
            stmt = stmt.order_by(text("ts_rank(search_tsv, to_tsquery('simple', :q)) DESC").bindparams(q=search_query))
        else:
            # Если ввели только спецсимволы, возвращаем пустоту
            return SearchResponse(items=[], total=0, page=page, page_size=page_size)
    else:
        # Если поиска нет, сортируем по дате добавления
        stmt = stmt.order_by(Material.created_at.desc())

    # 3. Динамически добавляем фильтры (если они не None)
    if discipline:
        stmt = stmt.where(Material.discipline == discipline)
    if type:
        stmt = stmt.where(Material.type == type)
    if course:
        stmt = stmt.where(Material.course == course)

    # 4. Считаем общее количество строк (для пагинации)
    # Оборачиваем наш запрос в подзапрос и считаем
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    # 5. Применяем лимит и смещение, выполняем запрос
    stmt = stmt.offset(offset).limit(page_size)
    materials = (await db.execute(stmt)).scalars().all()

    # 6. Формируем ответ
    items = [
        MaterialListOut(
            id=m.id, title=m.title, discipline=m.discipline, type=m.type,
            tags=m.tags or [], score=m.score, created_at=m.created_at,
        ) for m in materials
    ]
    
    return SearchResponse(items=items, total=total, page=page, page_size=page_size)