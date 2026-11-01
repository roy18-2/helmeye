from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from pymongo import ReturnDocument

from ..database import db
from ..models import DetectionLabel, ReviewStatus, utcnow
from ..security import get_current_user
from ..services.evidence import EVIDENCE_DIR

router = APIRouter(prefix="/incidents", tags=["incidents"])


class ReviewRequest(BaseModel):
    status: ReviewStatus
    note: str | None = Field(default=None, max_length=500)


def _public(doc: dict) -> dict:
    doc = dict(doc)
    path = doc.pop("evidence_path", None)
    doc["evidence_url"] = f"/api/incidents/{doc['id']}/evidence" if path else None
    return doc


@router.get("")
async def list_incidents(
    review_status: ReviewStatus | None = None,
    camera_code: str | None = None,
    label: DetectionLabel | None = None,
    min_confidence: float = Query(0, ge=0, le=1),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _: dict = Depends(get_current_user),
):
    query: dict = {}
    if review_status:
        query["review_status"] = review_status.value
    if camera_code:
        query["camera_code"] = camera_code
    if label:
        query["label"] = label.value
    if min_confidence:
        query["confidence"] = {"$gte": min_confidence}
    if date_from or date_to:
        window: dict = {}
        if date_from:
            window["$gte"] = date_from
        if date_to:
            window["$lte"] = date_to
        query["detected_at"] = window

    total = await db.incidents.count_documents(query)
    cursor = (
        db.incidents.find(query, {"_id": 0})
        .sort("detected_at", -1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    items = [_public(d) async for d in cursor]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/summary")
async def summary(_: dict = Depends(get_current_user)):
    counts = {s.value: 0 for s in ReviewStatus}
    async for row in db.incidents.aggregate(
        [{"$group": {"_id": "$review_status", "n": {"$sum": 1}}}]
    ):
        counts[row["_id"]] = row["n"]
    avg = await db.incidents.aggregate(
        [{"$group": {"_id": None, "avg": {"$avg": "$confidence"}}}]
    ).to_list(1)
    decided = counts["confirmed"] + counts["false_positive"]
    return {
        "total": sum(counts.values()),
        "by_review_status": counts,
        "avg_confidence": round(avg[0]["avg"], 3) if avg else None,
        "reviewed_precision": round(counts["confirmed"] / decided, 3) if decided else None,
    }


@router.get("/{incident_id}")
async def get_incident(incident_id: str, _: dict = Depends(get_current_user)):
    doc = await db.incidents.find_one({"id": incident_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Incident not found")
    return _public(doc)


@router.get("/{incident_id}/evidence")
async def get_evidence(incident_id: str, _: dict = Depends(get_current_user)):
    doc = await db.incidents.find_one({"id": incident_id}, {"_id": 0, "evidence_path": 1})
    if not doc or not doc.get("evidence_path"):
        raise HTTPException(status_code=404, detail="No evidence image")
    base = EVIDENCE_DIR.resolve()
    path = (base / doc["evidence_path"]).resolve()
    if base not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="No evidence image")
    return FileResponse(path, media_type="image/jpeg")


@router.patch("/{incident_id}/review")
async def review_incident(
    incident_id: str,
    body: ReviewRequest,
    user: dict = Depends(get_current_user),
):
    if body.status == ReviewStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail="Choose confirmed, false_positive or uncertain",
        )
    now = utcnow()
    note = (body.note or "").strip() or None
    event = {
        "status": body.status.value,
        "by": user["id"],
        "by_name": user["name"],
        "at": now,
        "note": note,
    }
    doc = await db.incidents.find_one_and_update(
        {"id": incident_id},
        {
            "$set": {
                "review_status": body.status.value,
                "reviewed_by": user["id"],
                "reviewed_by_name": user["name"],
                "reviewed_at": now,
                "review_note": note,
            },
            "$push": {"review_history": event},
        },
        projection={"_id": 0},
        return_document=ReturnDocument.AFTER,
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Incident not found")
    return _public(doc)
