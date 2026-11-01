import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing setting {name}. Add it to backend/.env")
    return value


def _secret() -> str:
    value = _require("JWT_SECRET")
    if value.startswith("change-me") or len(value) < 32:
        raise RuntimeError("JWT_SECRET is still a placeholder or too short. Generate a real one.")
    return value


class Settings:
    mongo_url = _require("MONGO_URL")
    db_name = _require("DB_NAME")
    jwt_secret = _secret()
    jwt_expire_minutes = int(os.environ.get("JWT_EXPIRE_MINUTES", "480"))
    cors_origins = [
        o.strip()
        for o in os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")
        if o.strip()
    ]
    upload_dir = BASE_DIR / "uploads"
    seed_admin_email = os.environ.get("SEED_ADMIN_EMAIL", "").strip().lower()
    seed_admin_name = os.environ.get("SEED_ADMIN_NAME", "Admin").strip() or "Admin"
    seed_admin_password = os.environ.get("SEED_ADMIN_PASSWORD", "")


settings = Settings()
