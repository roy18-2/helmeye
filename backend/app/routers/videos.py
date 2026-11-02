import asyncio
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile

from ..database import db
from ..models import Video, new_id, utcnow
from ..security import get_current_user
from ..services.pipeline import VIDEO_DIR, probe_video, process_video

router = APIRouter(prefix="/videos", tags=["videos"])

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
MAX_BYTES = 500 * 1024 * 1024
CHUNK = 1024 * 1024
HIDDEN = {"_id": 0, "stored_name": 0, "sha256": 0}


@router.post("", status_code=202)
async def upload_video(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    camera_code: str = Form(...),
    recorded_at: datetime | None = Form(None),
    user: dict = Depends(get_current_user),
):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}")
    if not await db.cameras.find_one({"code": camera_code}, {"_id": 1}):
        raise HTTPException(status_code=400, detail="Unknown camera code")

    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    video_id = new_id()
    stored_name = f"{video_id}{ext}"
    path = VIDEO_DIR / stored_name
    digest = hashlib.sha256()
    size = 0
    try:
        with open(path, "wb") as out:
            while chunk := await file.read(CHUNK):
                size += len(chunk)
                if size > MAX_BYTES:
                    raise HTTPException(status_code=413, detail="File is larger than 500 MB")
                digest.update(chunk)
                out.write(chunk)
    except BaseException:
        path.unlink(missing_ok=True)
        raise

    info = await asyncio.to_thread(probe_video, path)
    if info is None:
        path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Could not read this file as a video")

    if recorded_at is None:
        recorded_at = utcnow()
    elif recorded_at.tzinfo is None:
        recorded_at = recorded_at.replace(tzinfo=timezone.utc)

    video = Video(
        id=video_id,
        filename=Path(file.filename or stored_name).name,
        stored_name=stored_name,
        sha256=digest.hexdigest(),
        size_bytes=size,
        camera_code=camera_code,
        recorded_at=recorded_at,
        uploaded_by=user["id"],
        uploaded_by_name=user["name"],
        **info,
    )
    await db.videos.insert_one(video.model_dump())
    background.add_task(process_video, video_id)

    doc = video.model_dump()
    doc.pop("stored_name")
    doc.pop("sha256")
    return doc


@router.get("")
async def list_videos(_: dict = Depends(get_current_user)):
    return await db.videos.find({}, HIDDEN).sort("created_at", -1).to_list(50)


@router.get("/{video_id}")
async def get_video(video_id: str, _: dict = Depends(get_current_user)):
    doc = await db.videos.find_one({"id": video_id}, HIDDEN)
    if not doc:
        raise HTTPException(status_code=404, detail="Video not found")
    return doc
