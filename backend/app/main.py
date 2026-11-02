import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .database import client, db, ensure_indexes
from .routers import auth, cameras, incidents, videos

logger = logging.getLogger("helmeye")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await ensure_indexes()
        await db.videos.update_many(
            {"status": {"$in": ["queued", "processing"]}},
            {"$set": {"status": "failed", "error": "Server restarted before processing finished"}},
        )
    except Exception as exc:
        logger.warning("Startup tasks failed: %s", exc)
    yield
    client.close()


app = FastAPI(title="HelmEye API", lifespan=lifespan)
api = APIRouter(prefix="/api")


@api.get("/health")
async def health():
    await client.admin.command("ping")
    return {"status": "ok", "db": settings.db_name}


api.include_router(auth.router)
api.include_router(cameras.router)
api.include_router(incidents.router)
api.include_router(videos.router)
app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
