import asyncio
from sqlalchemy import text
from app.db import SessionLocal

async def test():
    # Запрос, который в psql вернул 111 строк
    q_fts = 'функция:* | эйлера:*'
    
    async with SessionLocal() as db:
        sql = text("""
            SELECT id, left(content, 50) as text_preview
            FROM document_chunks
            WHERE search_tsv @@ to_tsquery('russian', :fts_q)
            LIMIT 5
        """)
        
        print(f"--- ТЕСТ FTS ---")
        print(f"Запрос: {q_fts}")
        
        try:
            res = await db.execute(sql, {'fts_q': q_fts})
            rows = res.all()
            print(f"Найдено строк: {len(rows)}")
            for r in rows:
                print(f"ID: {r[0]} | Текст: {r[1]}")
        except Exception as e:
            print(f"ОШИБКА SQL: {e}")

if __name__ == "__main__":
    asyncio.run(test())