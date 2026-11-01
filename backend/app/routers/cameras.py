from fastapi import APIRouter
from ..database import db

router = APIRouter(prefix="/cameras", tags=["cameras"])


@router.get("")
async def list_cameras():
    return await db.cameras.find({}, {"_id": 0}).sort("code", 1).to_list(100)
