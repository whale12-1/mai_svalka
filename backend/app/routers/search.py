import re
import json
import hashlib
import redis.asyncio as redis  # <-- ДОБАВЛЕНО ДЛЯ КЭША
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, text, func, or_, case
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import get_db
from ..schemas import SearchResponse, MaterialListOut
from ..models import Material
from ..config import settings # <-- ДЛЯ REDIS_URL
from ..ai_service import get_embedding, ask_gigachat, extract_search_keywords, reranker_model

router = APIRouter(prefix="/search", tags=["search"])

# Инициализируем клиент Redis (он будет переиспользоваться)
redis_client = redis.from_url(settings.redis_url, decode_responses=True)

@router.get("", response_model=SearchResponse)
async def search(
    q: str = Query("", description="query string"),
    discipline: str | None = None,
    type: str | None = None,
    course: int | None = None,
    institute: str | None = None,
    semester: int | None = None,
    teacher: str | None = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    # ... (код функции search остается без изменений, как в твоем файле) ...
    offset = (page - 1) * page_size
    stmt = select(Material)

    if q.strip():
        clean_q = re.sub(r'[^\w\s]', '', q, flags=re.UNICODE)
        if clean_q.strip():
            search_query = " & ".join([f"{word}:*" for word in clean_q.split()])
            stmt = stmt.where(text("search_tsv @@ to_tsquery('russian', :q)").bindparams(q=search_query))

    filter_conditions = []
    score_expr = 0

    if discipline:
        cond = Material.discipline.ilike(f"%{discipline}%")
        filter_conditions.append(cond)
        score_expr += case((cond, 1), else_=0)
    if teacher:
        cond = Material.teacher.ilike(f"%{teacher}%")
        filter_conditions.append(cond)
        score_expr += case((cond, 1), else_=0)
    if institute:
        cond = Material.institute.ilike(f"%{institute}%")
        filter_conditions.append(cond)
        score_expr += case((cond, 1), else_=0)
    if course:
        cond = Material.course == course
        filter_conditions.append(cond)
        score_expr += case((cond, 1), else_=0)
    if semester:
        cond = Material.semester == semester
        filter_conditions.append(cond)
        score_expr += case((cond, 1), else_=0)
    if type:
        cond = Material.type == type
        filter_conditions.append(cond)
        score_expr += case((cond, 1), else_=0)

    fallback_message = None

    if filter_conditions:
        stmt = stmt.where(or_(*filter_conditions))
        stmt = stmt.add_columns(score_expr.label("match_score"))
        stmt = stmt.order_by(text("match_score DESC"), Material.created_at.desc())
        fallback_message = "Показаны наиболее подходящие варианты (не по всем фильтрам есть точное совпадение)."
    else:
        if q.strip() and clean_q.strip():
            stmt = stmt.order_by(text("ts_rank(search_tsv, to_tsquery('russian', :q)) DESC").bindparams(q=search_query))
        else:
            stmt = stmt.order_by(Material.created_at.desc())

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = stmt.offset(offset).limit(page_size)
    results = (await db.execute(stmt)).all()
    
    items = []
    for row in results:
        m = row[0]
        items.append(
            MaterialListOut(
                id=m.id, title=m.title, discipline=m.discipline, type=m.type,
                tags=m.tags or [], score=m.score, created_at=m.created_at,
            )
        )
    
    return SearchResponse(
        items=items, 
        total=total, 
        page=page, 
        page_size=page_size,
        message=fallback_message if total > 0 else "Совсем ничего не найдено 😔"
    )

@router.get("/ai")
async def ai_search(
    q: str = Query(..., description="Ваш вопрос"),
    db: AsyncSession = Depends(get_db)
):
    # 0. ПРОВЕРКА КЭША REDIS
    cache_key = f"ai_answer:{hashlib.md5(q.lower().encode()).hexdigest()}"
    try:
        cached = await redis_client.get(cache_key)
        if cached:
            print(f"DEBUG: Отдаем ответ из кэша для вопроса: '{q}'")
            return json.loads(cached)
    except Exception as e:
        print(f"Ошибка Redis (чтение): {e}")

    # 1. Расширяем запрос через GigaChat
    search_keywords = await extract_search_keywords(q)
    query_vector = get_embedding(search_keywords)
    
    # 2. ЖЕСТКАЯ ОЧИСТКА ОТ СТОП-СЛОВ
    STOP_WORDS = {"что", "такое", "как", "где", "когда", "почему", "зачем", "это", "в", "на", "и", "с", "по", "для", "из", "от", "до", "не", "ни", "но", "или", "а", "же", "бы", "ли", "то", "так", "вы", "мы", "они", "она", "оно"}
    words = re.findall(r'[а-яА-ЯёЁa-zA-Z0-9]+', search_keywords.lower())
    fts_words = [w for w in words if w not in STOP_WORDS and len(w) > 2]
    if not fts_words:
        fts_words = [w for w in words if len(w) > 2]
        
    fts_query = " OR ".join(fts_words) if fts_words else "ничего"

    # 3. Ищем 20 кандидатов
    sql = text("""
        WITH vector_matches AS (
            SELECT id, ROW_NUMBER() OVER (ORDER BY embedding <=> CAST(:vec AS vector)) AS rank
            FROM document_chunks
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:vec AS vector)
            LIMIT 20
        ),
        text_matches AS (
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
        LIMIT 20
    """)
    
    rows = (await db.execute(sql, {"vec": str(query_vector), "fts_q": fts_query})).all()
    
    if not rows:
        return {"answer": "В базе нет информации по этому запросу.", "sources": []}

    # 4. МАГИЯ РЕРАНКЕРА
    pairs = [[q, r.content] for r in rows]
    rerank_scores = reranker_model.predict(pairs)
    reranked_rows = sorted(zip(rows, rerank_scores), key=lambda x: x[1], reverse=True)
    
    # Берем ТОП-3 (исправлен баг, раньше было 5)
    top_rows = [item[0] for item in reranked_rows[:3]]
    print(f"DEBUG: Реранкер отобрал 3 лучших куска из {len(rows)} кандидатов.")

    # 5. Формируем контекст и отправляем в GigaChat
    context_chunks = [
        f"Источник: {r.title}\nТекст фрагмента:\n{r.content}" 
        for r in top_rows
    ]
    
    answer = await ask_gigachat(q, context_chunks)
    sources = list({r.title for r in top_rows})
    
    result = {
        "answer": answer,
        "sources": sources,
        "debug_context": [
            {
                "rerank_score": round(float(score), 4), 
                "text": r.content[:300]
            } for r, score in reranked_rows[:3]
        ]
    }

    # 6. СОХРАНЯЕМ В КЭШ НА 24 ЧАСА (86400 секунд)
    try:
        await redis_client.set(cache_key, json.dumps(result), ex=86400)
    except Exception as e:
        print(f"Ошибка Redis (запись): {e}")

    return result