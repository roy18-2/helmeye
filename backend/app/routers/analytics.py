from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query

from ..database import db
from ..models import DetectionLabel, ReviewStatus
from ..security import get_current_user

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _zone(name: str):
    try:
        return ZoneInfo(name), name
    except Exception:
        return timezone.utc, "UTC"


@router.get("")
async def analytics(
    days: int = Query(7, ge=1, le=90),
    tz: str = Query("UTC", max_length=64),
    source: str | None = Query(None, pattern="^(demo|mock|detector)$"),
    _: dict = Depends(get_current_user),
):
    zone, tz_name = _zone(tz)
    today = datetime.now(zone).date()
    first_day = today - timedelta(days=days - 1)
    start = datetime.combine(first_day, time.min, tzinfo=zone).astimezone(timezone.utc)
    end = datetime.combine(today + timedelta(days=1), time.min, tzinfo=zone).astimezone(timezone.utc)

    match: dict = {"detected_at": {"$gte": start, "$lt": end}}
    if source:
        match["source"] = source

    pipeline = [
        {"$match": match},
        {
            "$facet": {
                "by_hour": [
                    {"$group": {"_id": {"$hour": {"date": "$detected_at", "timezone": tz_name}}, "n": {"$sum": 1}}}
                ],
                "by_camera": [{"$group": {"_id": "$camera_code", "n": {"$sum": 1}}}],
                "by_status": [{"$group": {"_id": "$review_status", "n": {"$sum": 1}}}],
                "by_label": [{"$group": {"_id": "$label", "n": {"$sum": 1}}}],
                "daily": [
                    {
                        "$group": {
                            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$detected_at", "timezone": tz_name}},
                            "n": {"$sum": 1},
                        }
                    }
                ],
            }
        },
    ]
    rows = await db.incidents.aggregate(pipeline).to_list(1)
    facets = rows[0] if rows else {}

    def counts(key: str) -> dict:
        return {r["_id"]: r["n"] for r in facets.get(key, [])}

    hours, cams, statuses, labels, daily = (
        counts("by_hour"),
        counts("by_camera"),
        counts("by_status"),
        counts("by_label"),
        counts("daily"),
    )
    camera_codes = [c["code"] async for c in db.cameras.find({}, {"_id": 0, "code": 1}).sort("code", 1)]

    by_status = {s.value: statuses.get(s.value, 0) for s in ReviewStatus}
    decided = by_status["confirmed"] + by_status["false_positive"]

    return {
        "days": days,
        "timezone": tz_name,
        "source": source,
        "total": sum(by_status.values()),
        "by_hour": [{"hour": h, "count": hours.get(h, 0)} for h in range(24)],
        "by_camera": [{"camera_code": code, "count": cams.get(code, 0)} for code in camera_codes],
        "by_review_status": by_status,
        "by_label": {l.value: labels.get(l.value, 0) for l in DetectionLabel},
        "daily": [
            {
                "date": (first_day + timedelta(days=i)).isoformat(),
                "count": daily.get((first_day + timedelta(days=i)).isoformat(), 0),
            }
            for i in range(days)
        ],
        "reviewed_count": decided,
        "reviewed_precision": round(by_status["confirmed"] / decided, 3) if decided else None,
    }