import re
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import get_db
from ..schemas import SearchResponse, MaterialListOut
from ..models import Material
from ..ai_service import get_embedding, ask_gigachat, extract_search_keywords


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
            stmt = stmt.where(text("search_tsv @@ to_tsquery('russian', :q)").bindparams(q=search_query))
            # Сортируем по релевантности (рангу)
            stmt = stmt.order_by(text("ts_rank(search_tsv, to_tsquery('russian', :q)) DESC").bindparams(q=search_query))
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

@router.get("/ai")
async def ai_search(
    q: str = Query(..., description="Ваш вопрос"),
    db: AsyncSession = Depends(get_db)
):
    # 1. Расширяем запрос через GigaChat (или берем оригинал)
    search_keywords = await extract_search_keywords(q)
    
    # 2. Векторный поиск
    query_vector = get_embedding(search_keywords)
    
    # 3. ЖЕСТКАЯ ОЧИСТКА ОТ СТОП-СЛОВ (возвращаем то, что случайно удалили)
    STOP_WORDS = {"что", "такое", "как", "где", "когда", "почему", "зачем", "это", "в", "на", "и", "с", "по", "для", "из", "от", "до", "не", "ни", "но", "или", "а", "же", "бы", "ли", "то", "так", "вы", "мы", "они", "она", "оно"}
    words = re.findall(r'[а-яА-ЯёЁa-zA-Z0-9]+', search_keywords.lower())
    
    # Оставляем только слова длиннее 2 символов, которых нет в стоп-листе
    fts_words = [w for w in words if w not in STOP_WORDS and len(w) > 2]
    
    # Если вдруг все слова оказались стоп-словами, берем просто длинные
    if not fts_words:
        fts_words = [w for w in words if len(w) > 2]
        
    # Склеиваем через OR (ИЛИ), чтобы найти хотя бы одно совпадение
    fts_query = " OR ".join(fts_words) if fts_words else "ничего"
    print(f"DEBUG FTS QUERY: '{fts_query}'")

    sql = text("""
        WITH vector_matches AS (
            SELECT id, ROW_NUMBER() OVER (ORDER BY embedding <=> CAST(:vec AS vector)) AS rank
            FROM document_chunks
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:vec AS vector)
            LIMIT 20
        ),
        text_matches AS (
            -- websearch_to_tsquery отлично понимает слово OR
            SELECT id, ROW_NUMBER() OVER (ORDER BY ts_rank(search_tsv, websearch_to_tsquery('russian', :fts_q)) DESC) AS rank
            FROM document_chunks
            WHERE search_tsv @@ websearch_to_tsquery('russian', :fts_q)
            LIMIT 20
        )
        SELECT m.title, c.content, 
               (COALESCE(1.0 / (60 + v.rank), 0.0) + COALESCE(1.0 / (60 + t.rank), 0.0)) AS score
        FROM document_chunks c
        JOIN materials m ON m.id = c.material_id
        LEFT JOIN vector_matches v ON v.id = c.id
        LEFT JOIN text_matches t ON t.id = c.id
        WHERE v.id IS NOT NULL OR t.id IS NOT NULL
        ORDER BY score DESC
        LIMIT 5
    """)
    
    rows = (await db.execute(sql, {"vec": str(query_vector), "fts_q": fts_query})).all()
    
    if not rows:
        return {"answer": "В базе нет информации по этому запросу.", "sources": []}

    context_chunks = [
        f"Источник: {r.title}\nТекст фрагмента:\n{r.content}" 
        for r in rows
    ]
    
    answer = await ask_gigachat(q, context_chunks)
    sources = list({r.title for r in rows})
    
    return {
        "answer": answer,
        "sources": sources,
        "debug_context": [
            {
                "score": round(r.score, 4), 
                "text": r.content[:300]
            } for r in rows
        ]
    }