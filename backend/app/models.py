import uuid
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


def new_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DetectionLabel(str, Enum):
    NO_HELMET = "no_helmet"
    UNCLEAR_HEADGEAR = "unclear_headgear"


class ReviewStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FALSE_POSITIVE = "false_positive"
    UNCERTAIN = "uncertain"


class VideoStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Camera(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=new_id)
    code: str
    name: str
    location: str


class Role(str, Enum):
    ADMIN = "admin"
    REVIEWER = "reviewer"


class User(BaseModel):
    model_config = ConfigDict(extra="ignore", use_enum_values=True)

    id: str = Field(default_factory=new_id)
    email: str
    name: str
    role: Role = Role.REVIEWER
    password_hash: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=utcnow)
