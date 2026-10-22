from fastapi import APIRouter, Depends
from ..auth import current_user
from ..models import AnonymousUser

router = APIRouter(prefix="/me", tags=["auth"])

@router.get("")
async def me(user: AnonymousUser = Depends(current_user)):
    return {"reputation": user.reputation}