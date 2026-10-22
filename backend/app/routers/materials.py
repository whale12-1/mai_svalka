import uuid
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy import select, func, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from ..db import get_db
from ..models import Material, MaterialFile, AnonymousUser
from ..schemas import MaterialOut, MaterialFileOut, MaterialListOut
from ..auth import current_user
from .. import storage

router = APIRouter(prefix="/materials", tags=["materials"])

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
    tags: str = Form(""),  # comma-separated
    
    # ВОТ ГЛАВНОЕ ИЗМЕНЕНИЕ: Убираем list, делаем просто ОДИН файл
    file: UploadFile | None = File(None), 
    
    db: AsyncSession = Depends(get_db),
    user: AnonymousUser = Depends(current_user),
):
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    m = Material(
        title=title, description=description, discipline=discipline,
        institute=institute, course=course, semester=semester,
        teacher=teacher, type=type, tags=tag_list,
        uploader_hash=user.token_hash, status="ready",
    )
    db.add(m)
    await db.flush()

    # Обрабатываем ОДИН файл
    if file:
        data = await file.read()
        key = f"{uuid.uuid4().hex}/{file.filename}"
        storage.upload(key, data, file.content_type or "application/octet-stream")
        db.add(MaterialFile(
            material_id=m.id, filename=file.filename,
            storage_key=key, size=len(data),
            mime_type=file.content_type or "application/octet-stream",
        ))

    # обновляем tsvector для FTS
    await db.execute(text(
        "UPDATE materials SET search_tsv = to_tsvector('russian', coalesce(title,'') || ' ' || coalesce(description,'') || ' ' || coalesce(discipline,'')) WHERE id = :id"
    ), {"id": m.id})

    await db.commit()

    result = await db.execute(
        select(Material).where(Material.id == m.id).options(selectinload(Material.files))
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
    
    m.views += 1  # Чтобы возвращался актуальный счетчик
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
                mime_type=f.mime_type, url=storage.presigned_url(f.storage_key),
            ) for f in m.files
        ],
    )