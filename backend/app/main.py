import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .database import client, ensure_indexes
from .routers import auth, cameras

logger = logging.getLogger("helmeye")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await ensure_indexes()
    except Exception as exc:
        logger.warning("Could not create indexes at startup: %s", exc)
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
app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
