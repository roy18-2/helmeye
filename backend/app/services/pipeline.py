import asyncio
import logging
from datetime import timedelta

import cv2

from ..config import settings
from ..database import db
from ..detectors.mock import MockDetector
from ..models import Incident, VideoStatus, utcnow
from .evidence import save_frame_evidence

logger = logging.getLogger("helmeye.pipeline")

VIDEO_DIR = settings.upload_dir / "videos"
SAMPLE_EVERY_S = 1.0
MAX_SAMPLED_FRAMES = 1800
MAX_INCIDENTS_PER_VIDEO = 25

_slot = asyncio.Semaphore(1)  # process one video at a time


def probe_video(path) -> dict | None:
    cap = cv2.VideoCapture(str(path))
    try:
        if not cap.isOpened():
            return None
        ok, _ = cap.read()
        if not ok:
            return None
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0)
        frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        return {
            "fps": round(fps, 2) if fps > 0 else None,
            "frame_count": frames if frames > 0 else None,
            "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0) or None,
            "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0) or None,
            "duration_s": round(frames / fps, 1) if fps > 0 and frames > 0 else None,
        }
    finally:
        cap.release()


def iter_frames(path, every_s: float):
    cap = cv2.VideoCapture(str(path))
    try:
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0) or 30.0
        step = max(1, round(fps * every_s))
        idx = 0
        while cap.grab():
            if idx % step == 0:
                ok, frame = cap.retrieve()
                if ok:
                    yield idx, idx / fps, frame
            idx += 1
    finally:
        cap.release()


async def process_video(video_id: str) -> None:
    async with _slot:
        video = await db.videos.find_one({"id": video_id}, {"_id": 0})
        if not video:
            return
        await db.videos.update_one(
            {"id": video_id},
            {"$set": {"status": VideoStatus.PROCESSING.value, "started_at": utcnow(), "progress": 0}},
        )

        path = VIDEO_DIR / video["stored_name"]
        detector = MockDetector(seed=video["sha256"])
        duration = video.get("duration_s")
        expected = max(1, int(duration / SAMPLE_EVERY_S) + 1) if duration else None
        frames = iter_frames(path, SAMPLE_EVERY_S)
        sampled = 0
        found = 0

        try:
            while True:
                item = await asyncio.to_thread(next, frames, None)
                if item is None:
                    break
                frame_idx, t, frame = item
                sampled += 1
                if sampled > MAX_SAMPLED_FRAMES:
                    break

                for det in detector.detect(frame, frame_idx, t):
                    if found >= MAX_INCIDENTS_PER_VIDEO:
                        break
                    incident = Incident(
                        track_id=det.track_id,
                        camera_code=video["camera_code"],
                        detected_at=video["recorded_at"] + timedelta(seconds=t),
                        label=det.label,
                        confidence=det.confidence,
                        bbox=det.bbox,
                        video_id=video_id,
                        source="mock",
                    )
                    name = f"{incident.id}.jpg"
                    await asyncio.to_thread(
                        save_frame_evidence, name, frame, det.bbox, incident.label, det.confidence
                    )
                    incident.evidence_path = name
                    await db.incidents.insert_one(incident.model_dump())
                    found += 1

                if sampled % 5 == 0:
                    progress = min(99, int(sampled / expected * 100)) if expected else 0
                    await db.videos.update_one(
                        {"id": video_id},
                        {"$set": {"progress": progress, "sampled_frames": sampled, "incidents_count": found}},
                    )

            await db.videos.update_one(
                {"id": video_id},
                {"$set": {
                    "status": VideoStatus.COMPLETED.value,
                    "progress": 100,
                    "sampled_frames": sampled,
                    "incidents_count": found,
                    "completed_at": utcnow(),
                }},
            )
        except Exception as exc:
            logger.exception("Video processing failed for %s", video_id)
            await db.videos.update_one(
                {"id": video_id},
                {"$set": {
                    "status": VideoStatus.FAILED.value,
                    "error": str(exc)[:300],
                    "sampled_frames": sampled,
                    "incidents_count": found,
                    "completed_at": utcnow(),
                }},
            )
        finally:
            frames.close()
