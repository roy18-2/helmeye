import asyncio
from .database import client, db, ensure_indexes
from .models import Camera

CAMERAS = [
    ("CAM-01", "Junction 4 - MG Road North", "MG Road, Bengaluru"),
    ("CAM-02", "Flyover Toll Plaza", "Silk Board Jct"),
    ("CAM-03", "Ring Road East Bypass", "Hebbal Flyover"),
    ("CAM-04", "Market Signal Lane 2", "KR Market"),
    ("CAM-05", "Airport Expressway Km 14", "Devanahalli"),
]


async def main() -> None:
    await ensure_indexes()
    for code, name, location in CAMERAS:
        doc = Camera(code=code, name=name, location=location).model_dump()
        doc.pop("code")
        await db.cameras.update_one({"code": code}, {"$setOnInsert": doc}, upsert=True)
    total = await db.cameras.count_documents({})
    print(f"Seed complete. Cameras in database: {total}")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
