import uuid
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy import select, func, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import hashlib
from pydantic import BaseModel # <-- ДОБАВЛЕНО
from ..db import get_db
from ..models import Material, MaterialFile, AnonymousUser
from ..schemas import MaterialOut, MaterialFileOut, MaterialListOut
from ..auth import current_user
from .. import storage
from fastapi.responses import StreamingResponse
from urllib.parse import quote
from ..config import settings

router = APIRouter(prefix="/materials", tags=["materials"])

# Схема для PATCH-запроса
class MaterialUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    discipline: str | None = None
    institute: str | None = None
    course: int | None = None
    semester: int | None = None
    teacher: str | None = None
    type: str | None = None

@router.post("", response_model=MaterialOut, status_code=201)
async def create_material(
    title: str = Form(...),
    description: str = Form(""),
    discipline: str = Form(""),
    institute: str = Form(""),
    course: int | None = Form(None),
    semester: int | None = Form(None),
    teacher: str = Form(""),
    type: str = Form("other"),
    tags: str = Form(""), 
    files: list[UploadFile] = File(default=[]), 
    db: AsyncSession = Depends(get_db),
    user: AnonymousUser = Depends(current_user),
):
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    m = Material(
        title=title, description=description, discipline=discipline,
        institute=institute, course=course, semester=semester,
        teacher=teacher, type=type, tags=tag_list,
        uploader_hash=user.token_hash, status="processing", # <-- СРАЗУ СТАВИМ PROCESSING
    )
    db.add(m)
    await db.flush()

    if files:
        for f in files:
            data = await f.read()
            file_hash = hashlib.md5(data).hexdigest()
            
            existing_file = (await db.execute(
                select(MaterialFile).where(MaterialFile.file_hash == file_hash)
            )).scalar_one_or_none()
            
            if existing_file:
                print(f"Файл {f.filename} уже есть в базе (дубликат)")
                continue 
                
            key = f"{uuid.uuid4().hex}/{f.filename}"
            storage.upload(key, data, f.content_type or "application/octet-stream")
            db.add(MaterialFile(
                material_id=m.id, filename=f.filename,
                storage_key=key, size=len(data),
                file_hash=file_hash,
                mime_type=f.content_type or "application/octet-stream",
            ))
            
            if f.content_type == "application/pdf" or f.filename.endswith(".pdf"):
                from ..worker import process_pdf_file
                process_pdf_file.delay(m.id, key)
            
    # Исправляем simple на russian
    await db.execute(text(
        "UPDATE materials SET search_tsv = to_tsvector('russian', coalesce(title,'') || ' ' || coalesce(description,'') || ' ' || coalesce(discipline,'')) WHERE id = :id"
    ), {"id": m.id})

    await db.commit()

    result = await db.execute(
        select(Material).where(Material.id == m.id).options(selectinload(Material.files))
    )
    m = result.scalar_one()
    return _to_out(m)

# --- НОВЫЙ ЭНДПОИНТ ДЛЯ РЕДАКТИРОВАНИЯ ---
@router.patch("/{mid}", response_model=MaterialOut)
async def update_material(
    mid: int, 
    data: MaterialUpdate, 
    db: AsyncSession = Depends(get_db)
):
    m = await db.get(Material, mid)
    if not m:
        raise HTTPException(404, "Material not found")
        
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(m, key, value)
        
    # Обновляем FTS-индекс после изменения
    await db.execute(text("""
        UPDATE materials 
        SET search_tsv = to_tsvector('russian', coalesce(title,'') || ' ' || coalesce(description,'') || ' ' || coalesce(discipline,'')) 
        WHERE id = :id
    """), {"id": mid})

    await db.commit()
    
    # Возвращаем обновленный материал
    result = await db.execute(
        select(Material).where(Material.id == mid).options(selectinload(Material.files))
    )
    m = result.scalar_one()
    return _to_out(m)

@router.get("/{mid}", response_model=MaterialOut)
async def get_material(mid: int, db: AsyncSession = Depends(get_db)):
    m = (await db.execute(
        select(Material).where(Material.id == mid).options(selectinload(Material.files))
    )).scalar_one_or_none()
    if not m:
        raise HTTPException(404)
    
    await db.execute(update(Material).where(Material.id == mid).values(views=Material.views + 1))
    await db.commit()
    
    m.views += 1
    return _to_out(m)

def _to_out(m: Material) -> MaterialOut:
    return MaterialOut(
        id=m.id, title=m.title, description=m.description,
        discipline=m.discipline, institute=m.institute,
        course=m.course, semester=m.semester, teacher=m.teacher,
        type=m.type, tags=m.tags, score=m.score, views=m.views,
        downloads=m.downloads, created_at=m.created_at,
        files=[
            MaterialFileOut(
                id=f.id, filename=f.filename, size=f.size,
                mime_type=f.mime_type, url=f"/api/materials/download/{f.storage_key}",
            ) for f in m.files
        ],
    )

@router.get("/download/{key:path}")
async def download_file(key: str, db: AsyncSession = Depends(get_db)):
    file_record = (await db.execute(
        select(MaterialFile).where(MaterialFile.storage_key == key)
    )).scalar_one_or_none()
    
    if not file_record:
        raise HTTPException(404, "File not found")
    
    try:
        response = storage.client().get_object(settings.minio_bucket, key)
    except Exception:
        raise HTTPException(404, "File not found in storage")
        
    def iter_file():
        try:
            for chunk in response.stream(64 * 1024):
                yield chunk
        finally:
            response.close()
            response.release_conn()

    filename_encoded = quote(file_record.filename)
    
    return StreamingResponse(
        iter_file(), 
        media_type=file_record.mime_type,
        headers={"Content-Disposition": f"inline; filename*=UTF-8''{filename_encoded}"}
    )

@router.post("/{mid}/reprocess")
async def reprocess_material(mid: int, db: AsyncSession = Depends(get_db)):
    m = await db.get(Material, mid)
    if not m:
        raise HTTPException(404, "Material not found")
        
    files = (await db.execute(select(MaterialFile).where(MaterialFile.material_id == mid))).scalars().all()
    
    if not files:
        raise HTTPException(400, "No files found for this material")

    m.status = "processing"
    await db.commit()

    for f in files:
        if f.mime_type == "application/pdf" or f.filename.endswith(".pdf"):
            from ..worker import process_pdf_file
            process_pdf_file.delay(m.id, f.storage_key)

    return {"status": "ok", "message": f"Reprocessing started for {len(files)} files"}