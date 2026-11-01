from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings

client = AsyncIOMotorClient(
    settings.mongo_url, serverSelectionTimeoutMS=8000, tz_aware=True
)
db = client[settings.db_name]


async def ensure_indexes() -> None:
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.cameras.create_index("code", unique=True)
    await db.videos.create_index([("created_at", -1)])
    await db.incidents.create_index("id", unique=True)
    await db.incidents.create_index([("detected_at", -1)])
    await db.incidents.create_index("camera_code")
    await db.incidents.create_index([("review_status", 1), ("detected_at", -1)])
