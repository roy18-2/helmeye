import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Load backend/.env first so MONGO_URL is available, then force a separate test database
# and a throwaway JWT secret. The real database and secret are never used in tests.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ["DB_NAME"] = "helmeye_test"
os.environ["JWT_SECRET"] = "test-secret-not-for-production-" + "x" * 32

from fastapi.testclient import TestClient  # noqa: E402
from pymongo import MongoClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.models import Camera, Incident, User  # noqa: E402
from app.security import hash_password  # noqa: E402
from tests.constants import ADMIN, INACTIVE, REVIEWER  # noqa: E402


@pytest.fixture(scope="session")
def mongo():
    assert settings.db_name.endswith("_test"), "Refusing to run tests against a non-test database"
    client = MongoClient(settings.mongo_url, tz_aware=True, serverSelectionTimeoutMS=8000)
    try:
        client.admin.command("ping")
    except Exception as exc:
        client.close()
        pytest.fail(f"Cannot reach MongoDB ({type(exc).__name__}). Check MONGO_URL and Atlas Network Access.")
    client.drop_database(settings.db_name)
    yield client[settings.db_name]
    client.drop_database(settings.db_name)
    client.close()


@pytest.fixture(scope="session")
def client(mongo):
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def users(mongo, client):
    for spec in (ADMIN, REVIEWER, INACTIVE):
        doc = User(
            email=spec["email"],
            name=spec["name"],
            role=spec["role"],
            password_hash=hash_password(spec["password"]),
            is_active=spec is not INACTIVE,
        ).model_dump()
        mongo.users.insert_one(doc)
    for code in ("CAM-01", "CAM-02"):
        mongo.cameras.insert_one(Camera(code=code, name=f"Test {code}", location="Test").model_dump())


def _login(client, spec):
    res = client.post("/api/auth/login", json={"email": spec["email"], "password": spec["password"]})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture(scope="session")
def admin_headers(client, users):
    return _login(client, ADMIN)


@pytest.fixture(scope="session")
def reviewer_headers(client, users):
    return _login(client, REVIEWER)


@pytest.fixture
def clean_data(mongo):
    mongo.incidents.delete_many({})
    mongo.videos.delete_many({})


@pytest.fixture
def make_incident(mongo):
    def _make(**overrides):
        data = {
            "camera_code": "CAM-01",
            "detected_at": datetime.now(timezone.utc),
            "label": "no_helmet",
            "confidence": 0.9,
            "source": "demo",
        }
        data.update(overrides)
        doc = Incident(**data).model_dump()
        mongo.incidents.insert_one(doc)
        return doc["id"]

    return _make


@pytest.fixture
def make_video(mongo):
    def _make(**overrides):
        vid = overrides.pop("id", str(uuid.uuid4()))
        doc = {
            "id": vid,
            "filename": "clip.mp4",
            "stored_name": f"{vid}.mp4",
            "sha256": "abc",
            "size_bytes": 10,
            "camera_code": "CAM-01",
            "status": "completed",
            "progress": 100,
            "created_at": datetime.now(timezone.utc),
        }
        doc.update(overrides)
        mongo.videos.insert_one(doc)
        return vid

    return _make