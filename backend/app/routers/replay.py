import mimetypes
from datetime import timedelta

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from ..config import settings
from ..database import db
from ..models import utcnow
from ..security import ALGORITHM, get_current_user
from ..services.pipeline import VIDEO_DIR

router = APIRouter(prefix="/videos", tags=["replay"])

STREAM_TTL_MINUTES = 30
BAD_TOKEN = "Invalid or expired stream token"


@router.post("/{video_id}/stream-token")
async def stream_token(video_id: str, _: dict = Depends(get_current_user)):
    if not await db.videos.find_one({"id": video_id}, {"_id": 1}):
        raise HTTPException(status_code=404, detail="Video not found")
    payload = {
        "purpose": "video-stream",
        "vid": video_id,
        "exp": utcnow() + timedelta(minutes=STREAM_TTL_MINUTES),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)
    return {"token": token, "expires_in": STREAM_TTL_MINUTES * 60}


@router.get("/{video_id}/stream")
async def stream_video(video_id: str, token: str = Query(...)):
    try:
        claims = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail=BAD_TOKEN)
    if claims.get("purpose") != "video-stream" or claims.get("vid") != video_id:
        raise HTTPException(status_code=401, detail=BAD_TOKEN)

    doc = await db.videos.find_one({"id": video_id}, {"_id": 0, "stored_name": 1})
    if not doc:
        raise HTTPException(status_code=404, detail="Video not found")
    base = VIDEO_DIR.resolve()
    path = (base / doc["stored_name"]).resolve()
    if base not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="Video file is missing")
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(path, media_type=media_type)