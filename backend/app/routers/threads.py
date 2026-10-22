from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime
from ..db import get_db
from ..models import Thread, Post, AnonymousUser
from ..schemas import ThreadCreate, ThreadOut, PostCreate, PostOut
from ..auth import current_user

router = APIRouter(prefix="/threads", tags=["threads"])

@router.get("", response_model=list[ThreadOut])
async def list_threads(category: str | None = None, db: AsyncSession = Depends(get_db)):
    stmt = select(Thread).order_by(Thread.updated_at.desc())
    if category:
        stmt = stmt.where(Thread.category == category)
    
    threads = (await db.execute(stmt)).scalars().all()
    return [
        ThreadOut(
            id=t.id, title=t.title, category=t.category, 
            created_at=t.created_at, updated_at=t.updated_at,
            posts=[] # В списке веток посты не грузим для оптимизации
        ) for t in threads
    ]

@router.get("/{thread_id}", response_model=ThreadOut)
async def get_thread(thread_id: int, db: AsyncSession = Depends(get_db)):
    # selectinload нужен, чтобы одним запросом подтянуть все посты этой ветки
    stmt = select(Thread).where(Thread.id == thread_id).options(selectinload(Thread.posts))
    thread = (await db.execute(stmt)).scalar_one_or_none()
    
    if not thread:
        raise HTTPException(404, "Thread not found")
        
    return ThreadOut(
        id=thread.id, title=thread.title, category=thread.category,
        created_at=thread.created_at, updated_at=thread.updated_at,
        posts=[
            PostOut(id=p.id, content=p.content, created_at=p.created_at) 
            for p in thread.posts
        ]
    )

@router.post("", response_model=ThreadOut, status_code=201)
async def create_thread(
    data: ThreadCreate, 
    db: AsyncSession = Depends(get_db),
    user: AnonymousUser = Depends(current_user)
):
    t = Thread(title=data.title, category=data.category, author_hash=user.token_hash)
    db.add(t)
    await db.flush()

    if data.first_post:
        db.add(Post(thread_id=t.id, content=data.first_post, author_hash=user.token_hash))

    await db.commit()
    await db.refresh(t)
    return ThreadOut(
        id=t.id, title=t.title, category=t.category, 
        created_at=t.created_at, updated_at=t.updated_at, posts=[]
    )

@router.post("/{thread_id}/posts", response_model=PostOut, status_code=201)
async def create_post(
    thread_id: int, 
    data: PostCreate,
    db: AsyncSession = Depends(get_db),
    user: AnonymousUser = Depends(current_user)
):
    t = await db.get(Thread, thread_id)
    if not t:
        raise HTTPException(404, "Thread not found")

    p = Post(thread_id=thread_id, content=data.content, author_hash=user.token_hash)
    db.add(p)
    
    # Обновляем дату у ветки, чтобы она всплывала вверх при новом сообщении
    await db.execute(update(Thread).where(Thread.id == thread_id).values(updated_at=datetime.now()))
    
    await db.commit()
    await db.refresh(p)
    return PostOut(id=p.id, content=p.content, created_at=p.created_at)