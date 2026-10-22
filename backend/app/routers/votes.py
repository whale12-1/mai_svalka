from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import get_db
from ..models import Vote, Material, AnonymousUser
from ..schemas import VoteIn
from ..auth import current_user

router = APIRouter(prefix="/materials", tags=["votes"])

@router.post("/{mid}/vote")
async def vote(mid: int, body: VoteIn, db: AsyncSession = Depends(get_db), user: AnonymousUser = Depends(current_user)):
    mat = await db.get(Material, mid)
    if not mat:
        raise HTTPException(404)
    if body.value not in (-1, 0, 1):
        raise HTTPException(400)

    existing = await db.get(Vote, (user.token_hash, mid))
    delta = 0
    if body.value == 0:
        if existing:
            delta = -existing.value
            await db.delete(existing)
    elif existing:
        delta = body.value - existing.value
        existing.value = body.value
    else:
        db.add(Vote(token_hash=user.token_hash, material_id=mid, value=body.value))
        delta = body.value

    await db.execute(update(Material).where(Material.id == mid).values(score=Material.score + delta))
    await db.commit()
    return {"score": mat.score + delta}