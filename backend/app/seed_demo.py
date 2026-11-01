import asyncio
import random
import sys
from datetime import timedelta
from pathlib import Path

from .database import client, db, ensure_indexes
from .models import DetectionLabel, Incident, ReviewStatus, utcnow
from .services.evidence import EVIDENCE_DIR, save_demo_evidence


async def reset() -> None:
    docs = await db.incidents.find({"source": "demo"}, {"_id": 0, "evidence_path": 1}).to_list(1000)
    for d in docs:
        if d.get("evidence_path"):
            (EVIDENCE_DIR / Path(d["evidence_path"]).name).unlink(missing_ok=True)
    result = await db.incidents.delete_many({"source": "demo"})
    print(f"Removed {result.deleted_count} demo incidents")


async def create() -> None:
    existing = await db.incidents.count_documents({"source": "demo"})
    if existing:
        print(f"Demo incidents already exist ({existing}). Use --reset to recreate them.")
        return

    cameras = [c["code"] async for c in db.cameras.find({}, {"_id": 0, "code": 1}).sort("code", 1)]
    if not cameras:
        print("No cameras found. Run: python -m app.seed")
        return
    admin = await db.users.find_one({"role": "admin"}, {"_id": 0, "id": 1, "name": 1})

    rng = random.Random(42)
    now = utcnow()
    statuses = (
        [ReviewStatus.PENDING] * 4
        + [ReviewStatus.CONFIRMED] * 4
        + [ReviewStatus.FALSE_POSITIVE] * 2
        + [ReviewStatus.UNCERTAIN] * 2
    )
    rng.shuffle(statuses)

    docs = []
    for i, status in enumerate(statuses):
        label = DetectionLabel.UNCLEAR_HEADGEAR if rng.random() < 0.25 else DetectionLabel.NO_HELMET
        confidence = round(rng.uniform(0.55, 0.97), 2)
        bbox = [
            round(rng.uniform(0.2, 0.55), 3),
            round(rng.uniform(0.25, 0.5), 3),
            round(rng.uniform(0.12, 0.2), 3),
            round(rng.uniform(0.2, 0.3), 3),
        ]
        detected_at = now - timedelta(minutes=rng.randint(10, 48 * 60))
        plate = None
        if rng.random() >= 0.25:
            plate = (
                f"ZZ-{rng.randint(1, 99):02d}-"
                f"{chr(rng.randint(65, 90))}{chr(rng.randint(65, 90))}-{rng.randint(1000, 9999)}"
            )

        incident = Incident(
            track_id=rng.randint(100, 999),
            camera_code=rng.choice(cameras),
            detected_at=detected_at,
            label=label,
            confidence=confidence,
            plate_text=plate,
            bbox=bbox,
            source="demo",
        )
        incident.evidence_path = save_demo_evidence(
            f"{incident.id}.jpg", bbox, label.value, confidence, seed=i
        )
        doc = incident.model_dump()

        if status != ReviewStatus.PENDING and admin:
            reviewed_at = min(now, detected_at + timedelta(minutes=rng.randint(5, 120)))
            doc["review_status"] = status.value
            doc["reviewed_by"] = admin["id"]
            doc["reviewed_by_name"] = admin["name"]
            doc["reviewed_at"] = reviewed_at
            doc["review_history"] = [
                {
                    "status": status.value,
                    "by": admin["id"],
                    "by_name": admin["name"],
                    "at": reviewed_at,
                    "note": None,
                }
            ]
        docs.append(doc)

    await db.incidents.insert_many(docs)
    print(f"Created {len(docs)} demo incidents with evidence frames in {EVIDENCE_DIR}")


async def main() -> None:
    await ensure_indexes()
    if "--reset" in sys.argv:
        await reset()
    await create()
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
