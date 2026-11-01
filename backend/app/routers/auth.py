from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError

from ..database import db
from ..models import Role, User
from ..security import (
    DUMMY_HASH,
    create_access_token,
    get_current_user,
    hash_password,
    require_roles,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class LoginRequest(BaseModel):
    email: str = Field(pattern=EMAIL_PATTERN)
    password: str = Field(min_length=1, max_length=72)


class CreateUserRequest(BaseModel):
    email: str = Field(pattern=EMAIL_PATTERN)
    name: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=8, max_length=72)
    role: Role = Role.REVIEWER


@router.post("/login")
async def login(body: LoginRequest):
    email = body.email.strip().lower()
    user = await db.users.find_one({"email": email}, {"_id": 0})
    stored_hash = user["password_hash"] if user else DUMMY_HASH
    password_ok = verify_password(body.password, stored_hash)
    if not user or not password_ok or not user.get("is_active", True):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(user["id"], user["role"])
    user.pop("password_hash")
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return user


@router.get("/users")
async def list_users(_: dict = Depends(require_roles(Role.ADMIN))):
    return await db.users.find({}, {"_id": 0, "password_hash": 0}).sort("email", 1).to_list(200)


@router.post("/users", status_code=201)
async def create_user(body: CreateUserRequest, _: dict = Depends(require_roles(Role.ADMIN))):
    user = User(
        email=body.email.strip().lower(),
        name=body.name.strip(),
        role=body.role,
        password_hash=hash_password(body.password),
    )
    try:
        await db.users.insert_one(user.model_dump())
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="A user with this email already exists")
    out = user.model_dump()
    out.pop("password_hash")
    return out
