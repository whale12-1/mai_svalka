import io
import re
import asyncio
import fitz
import pytesseract
from pdf2image import convert_from_bytes
from celery import Celery
from sqlalchemy import text, create_engine
from .config import settings
from . import storage
from .ai_service import get_embedding, extract_metadata_sync

celery_app = Celery("hub", broker=settings.redis_url, backend=settings.redis_url)

def update_status(material_id: int, status: str):
    """Вспомогательная функция для безопасного обновления статуса в БД."""
    try:
        sync_db_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
        engine = create_engine(sync_db_url)
        with engine.begin() as conn:
            conn.execute(text("UPDATE materials SET status = :status WHERE id = :id"), {"status": status, "id": material_id})
    except Exception as e:
        print(f"Не удалось обновить статус на {status}: {e}")

def clean_extracted_text(text: str) -> str:
    text = re.sub(r'([а-я])([А-Я])', r'\1 \2', text)
    text = re.sub(r' +', ' ', text)
    return text

def split_text(text: str, chunk_size: int = 600, overlap: int = 100) -> list[str]:
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
    update_status(material_id, 'processing')
    
    try:
        # 1. Скачиваем файл
        try:
            response = storage.client().get_object(settings.minio_bucket, storage_key)
            pdf_bytes = response.read()
            response.close()
            response.release_conn()
        except Exception as e:
            print(f"Ошибка скачивания: {e}")
            update_status(material_id, 'failed')
            return

        extracted_text = ""
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            for page in doc:
                extracted_text += page.get_text("text") + "\n\n"
            doc.close()
        except Exception as e:
            print(f"Ошибка парсинга PDF: {e}")
            extracted_text = ""

        # 2. OCR для сканов
        if len(extracted_text.strip()) < 100:
            print("Текстовый слой отсутствует или слишком мал. Запускаю OCR...")
            try:
                images = convert_from_bytes(pdf_bytes, dpi=200, first_page=1, last_page=5)
                ocr_text_for_meta = ""
                for img in images:
                    ocr_text_for_meta += pytesseract.image_to_string(img, lang='rus+eng') + "\n\n"
                extracted_text = ocr_text_for_meta
            except Exception as e:
                print(f"Ошибка OCR: {e}")
                update_status(material_id, 'failed')
                return
        
        extracted_text = clean_extracted_text(extracted_text)
        
        if not extracted_text.strip():
             print("Текст не извлечен вообще.")
             update_status(material_id, 'failed')
             return

        print(f"Анализ метаданных для материала {material_id}...")
        ai_meta = extract_metadata_sync(extracted_text)
        
        ai_title = ai_meta.get("title", "")
        ai_disc = ai_meta.get("discipline", "")
        ai_teacher = ai_meta.get("teacher", "")
        ai_course = ai_meta.get("course")

        # 4. Нарезаем на чанки
        raw_chunks = split_text(extracted_text)
        chunks = [c for c in raw_chunks if len(c.strip()) > 10]
        
        if not chunks:
            print("Ошибка: после нарезки не осталось валидных чанков.")
            update_status(material_id, 'failed')
            return
            
        print(f"Файл разбит на {len(chunks)} чанков.")

        # 5. Сохраняем в БД
        sync_db_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
        engine = create_engine(sync_db_url)
        
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM document_chunks WHERE material_id = :id"), {"id": material_id})
            
            conn.execute(text("""
                UPDATE materials 
                SET content_text = :extracted_text,
                    title = CASE WHEN title = '' OR title IS NULL THEN :ai_title ELSE title END,
                    discipline = CASE WHEN discipline = '' OR discipline IS NULL THEN :ai_disc ELSE discipline END,
                    teacher = CASE WHEN teacher = '' OR teacher IS NULL THEN :ai_teacher ELSE teacher END,
                    course = CASE WHEN course IS NULL THEN :ai_course ELSE course END,
                    search_tsv = to_tsvector('russian', coalesce(title,'') || ' ' || coalesce(description,'') || ' ' || coalesce(discipline,'') || ' ' || :extracted_text)
                WHERE id = :id
            """), {
                "extracted_text": extracted_text, 
                "id": material_id,
                "ai_title": ai_title,
                "ai_disc": ai_disc,
                "ai_teacher": ai_teacher,
                "ai_course": ai_course
            })

            result = conn.execute(text("SELECT title, discipline FROM materials WHERE id = :id"), {"id": material_id}).fetchone()
            final_title = result[0] if result and result[0] else "Без названия"
            final_disc = result[1] if result and result[1] else "Общее"
            
            context_header = f"Предмет: {final_disc}. Документ: {final_title}.\n\n"

            for i, chunk in enumerate(chunks):
                contextualized_chunk = context_header + chunk
                vector = get_embedding(contextualized_chunk)
                
                conn.execute(text("""
                    INSERT INTO document_chunks (material_id, content, embedding, search_tsv)
                    VALUES (:mid, :content, :vec, to_tsvector('russian', :content))
                """), {
                    "mid": material_id, 
                    "content": contextualized_chunk,
                    "vec": str(vector)
                })
        
        update_status(material_id, 'ready')
        print(f"Файл {storage_key} успешно обработан. Всего чанков: {len(chunks)}.")

    except Exception as e:
        print(f"Критическая ошибка при обработке {material_id}: {e}")
        update_status(material_id, 'failed')