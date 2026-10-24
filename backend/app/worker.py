import io
import re  # <-- ВАЖНО: добавлен импорт для очистки текста
import fitz 
from celery import Celery
from sqlalchemy import text, create_engine
from .config import settings
from . import storage
from .ai_service import get_embedding

celery_app = Celery("hub", broker=settings.redis_url, backend=settings.redis_url)

def clean_extracted_text(text: str) -> str:
    """Добавляет пробелы между слипшимися словами."""
    text = re.sub(r'([а-я])([А-Я])', r'\1 \2', text)
    text = re.sub(r' +', ' ', text)
    return text

def split_text(text: str, chunk_size: int = 600, overlap: int = 100) -> list[str]:
    """Режет по абзацам, собирая их в куски по ~600 символов."""
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""
    
    for p in paragraphs:
        if len(p) > chunk_size:
            if current_chunk:
                chunks.append(current_chunk.strip())
            for i in range(0, len(p), chunk_size - overlap):
                chunks.append(p[i:i+chunk_size].strip())
            current_chunk = ""
        elif len(current_chunk) + len(p) < chunk_size:
            current_chunk += p + "\n\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = p + "\n\n"
            
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks

@celery_app.task
def process_pdf_file(material_id: int, storage_key: str):
    # 1. Скачиваем файл
    try:
        response = storage.client().get_object(settings.minio_bucket, storage_key)
        pdf_bytes = response.read()
        response.close()
        response.release_conn()
    except Exception as e:
        print(f"Ошибка скачивания: {e}")
        return

    # 2. Извлекаем текст (ВОТ ЗДЕСЬ БЫЛА ОШИБКА)
    extracted_text = ""  # <--- Эту строчку нельзя удалять!
    try:
        # Открываем PDF из байтов через PyMuPDF
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page in doc:
            extracted_text += page.get_text("text") + "\n\n"
        doc.close()
    except Exception as e:
        print(f"Ошибка парсинга PDF: {e}")
        return
    # 3. Нарезаем на чанки
    chunks = split_text(extracted_text)
    print(f"Файл разбит на {len(chunks)} чанков.")

    # 4. Сохраняем в БД
    sync_db_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    engine = create_engine(sync_db_url)
    
    with engine.begin() as conn:
        # Очищаем старые чанки для этого файла (если делаем переобработку)
        conn.execute(text("DELETE FROM document_chunks WHERE material_id = :id"), {"id": material_id})
        
        # Обновляем общий текст в материале
        conn.execute(text("""
            UPDATE materials 
            SET content_text = :extracted_text,
                search_tsv = to_tsvector('russian', coalesce(title,'') || ' ' || coalesce(description,'') || ' ' || coalesce(discipline,'') || ' ' || :extracted_text)
            WHERE id = :id
        """), {"extracted_text": extracted_text, "id": material_id})

        # Генерируем векторы для каждого чанка и сохраняем
        for i, chunk in enumerate(chunks):
            vector = get_embedding(chunk)
            conn.execute(text("""
                INSERT INTO document_chunks (material_id, content, embedding, search_tsv)
                VALUES (
                    :mid, 
                    :content, 
                    :vec, 
                    to_tsvector('russian', :content)
                )
            """), {
                "mid": material_id, 
                "content": chunk, 
                "vec": str(vector)
            })
                
    print(f"Файл {storage_key} успешно обработан. Всего чанков: {len(chunks)}.")