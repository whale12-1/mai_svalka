import hashlib, secrets
from fastapi import Request, Response, HTTPException, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .db import get_db
from .models import AnonymousUser
from .config import settings

COOKIE = "anon_token"

def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

async def get_or_issue_user(request: Request, response: Response, db: AsyncSession) -> AnonymousUser:
    raw = request.cookies.get(COOKIE)
    if not raw:
        raw = secrets.token_urlsafe(32)
        response.set_cookie(
            COOKIE, raw,
            httponly=True, samesite="lax",
            secure=settings.cookie_secure, max_age=60*60*24*365,
        )
    h = _hash(raw)
    user = await db.get(AnonymousUser, h)
    if not user:
        user = AnonymousUser(token_hash=h)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    if user.is_banned:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "banned")
    return user

async def current_user(request: Request, response: Response, db: AsyncSession = Depends(get_db)) -> AnonymousUser:
    return await get_or_issue_user(request, response, db)