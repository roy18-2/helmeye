import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv(Path(__file__).parent.parent / ".env")

client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="HelmEye API")
api = APIRouter(prefix="/api")


@api.get("/health")
async def health():
    await client.admin.command("ping")
    return {"status": "ok", "db": os.environ["DB_NAME"]}


app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown():
    client.close()
