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


class Incident(BaseModel):
    model_config = ConfigDict(extra="ignore", use_enum_values=True, validate_default=True)

    id: str = Field(default_factory=new_id)
    track_id: int | None = None
    camera_code: str
    detected_at: datetime
    label: DetectionLabel
    confidence: float
    plate_text: str | None = None
    bbox: list[float] = Field(default_factory=list)  # normalized [x, y, w, h]
    evidence_path: str | None = None
    video_id: str | None = None
    source: str = "detector"  # "detector" or "demo"
    review_status: ReviewStatus = ReviewStatus.PENDING
    reviewed_by: str | None = None
    reviewed_by_name: str | None = None
    reviewed_at: datetime | None = None
    review_note: str | None = None
    review_history: list[dict] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)
