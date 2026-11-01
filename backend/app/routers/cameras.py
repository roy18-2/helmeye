from fastapi import APIRouter, Depends
from ..database import db
from ..security import get_current_user

router = APIRouter(prefix="/cameras", tags=["cameras"])


@router.get("")
async def list_cameras(_: dict = Depends(get_current_user)):
    return await db.cameras.find({}, {"_id": 0}).sort("code", 1).to_list(100)
