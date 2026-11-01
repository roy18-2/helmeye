import asyncio
from .config import settings
from .database import client, db, ensure_indexes
from .models import Camera, Role, User
from .security import hash_password

CAMERAS = [
    ("CAM-01", "Junction 4 - MG Road North", "MG Road, Bengaluru"),
    ("CAM-02", "Flyover Toll Plaza", "Silk Board Jct"),
    ("CAM-03", "Ring Road East Bypass", "Hebbal Flyover"),
    ("CAM-04", "Market Signal Lane 2", "KR Market"),
    ("CAM-05", "Airport Expressway Km 14", "Devanahalli"),
]


async def seed_cameras() -> None:
    for code, name, location in CAMERAS:
        doc = Camera(code=code, name=name, location=location).model_dump()
        doc.pop("code")
        await db.cameras.update_one({"code": code}, {"$setOnInsert": doc}, upsert=True)
    total = await db.cameras.count_documents({})
    print(f"Cameras in database: {total}")


async def seed_admin() -> None:
    email = settings.seed_admin_email
    password = settings.seed_admin_password
    if not email or not password:
        print("Admin not created: set SEED_ADMIN_EMAIL and SEED_ADMIN_PASSWORD in .env")
        return
    if not 8 <= len(password) <= 72:
        print("Admin not created: SEED_ADMIN_PASSWORD must be 8 to 72 characters")
        return
    user = User(
        email=email,
        name=settings.seed_admin_name,
        role=Role.ADMIN,
        password_hash=hash_password(password),
    )
    doc = user.model_dump()
    doc.pop("email")
    result = await db.users.update_one({"email": email}, {"$setOnInsert": doc}, upsert=True)
    if result.upserted_id is not None:
        print(f"Admin user created: {email}")
    else:
        print(f"Admin user already exists: {email} (password left unchanged)")


async def main() -> None:
    await ensure_indexes()
    await seed_cameras()
    await seed_admin()
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
