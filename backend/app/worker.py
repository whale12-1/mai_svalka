import io
import asyncio
import pdfplumber
from celery import Celery
from sqlalchemy import text, create_engine
from .config import settings
from . import storage
from .ai_service import get_embedding # <-- Импортируем функцию эмбеддинга

celery_app = Celery("hub", broker=settings.redis_url, backend=settings.redis_url)

@celery_app.task
def process_pdf_file(material_id: int, storage_key: str):
    # 1. Скачиваем файл из MinIO
    try:
        response = storage.client().get_object(settings.minio_bucket, storage_key)
        pdf_bytes = response.read()
        response.close()
        response.release_conn()
    except Exception as e:
        print(f"Ошибка скачивания файла из MinIO: {e}")
        return

    # 2. Вытаскиваем текст
    extracted_text = ""
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                text_content = page.extract_text()
                if text_content:
                    extracted_text += text_content + "\n"
    except Exception as e:
        print(f"Ошибка парсинга PDF: {e}")
        return

    # 3. Создаем эмбеддинг (вектор) для текста
    print(f"Создание эмбеддинга для материала {material_id}...")
    # Для длинных текстов можно разбивать на чанки, но для примера берем первые 8000 символов
    vector = get_embedding(extracted_text[:8000])

    # 4. Сохраняем текст и вектор в БД
    sync_db_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    engine = create_engine(sync_db_url) 

    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE materials 
            SET content_text = :extracted_text,
                content_vector = :vector,
                search_tsv = to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(description,'') || ' ' || coalesce(discipline,'') || ' ' || :extracted_text)
            WHERE id = :id
        """), {
            "extracted_text": extracted_text, 
            "vector": str(vector), 
            "id": material_id
        })
        
    print(f"Файл {storage_key} успешно обработан. Длина текста: {len(extracted_text)} символов.")