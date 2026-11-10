from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app import config, security
from app.config import settings


def test_password_hash_roundtrip():
    hashed = security.hash_password("CorrectHorse1")
    assert hashed != "CorrectHorse1"
    assert security.verify_password("CorrectHorse1", hashed)
    assert not security.verify_password("wrong-password", hashed)


def test_hashes_use_different_salts():
    assert security.hash_password("SamePassword1") != security.hash_password("SamePassword1")


def test_verify_rejects_garbage_hash():
    assert not security.verify_password("anything", "not-a-real-hash")


def test_token_contains_user_and_role():
    token = security.create_access_token("user-1", "admin")
    claims = jwt.decode(token, settings.jwt_secret, algorithms=[security.ALGORITHM])
    assert claims["sub"] == "user-1"
    assert claims["role"] == "admin"
    assert "exp" in claims


def test_token_signed_with_other_secret_is_rejected():
    forged = jwt.encode({"sub": "user-1", "role": "admin"}, "a-different-secret-" + "y" * 32, algorithm="HS256")
    with pytest.raises(jwt.PyJWTError):
        jwt.decode(forged, settings.jwt_secret, algorithms=[security.ALGORITHM])


def test_expired_token_is_rejected():
    expired = jwt.encode(
        {"sub": "user-1", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        settings.jwt_secret,
        algorithm=security.ALGORITHM,
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        jwt.decode(expired, settings.jwt_secret, algorithms=[security.ALGORITHM])


def test_placeholder_jwt_secret_is_rejected(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "change-me-to-a-long-random-string")
    with pytest.raises(RuntimeError):
        config._secret()


def test_short_jwt_secret_is_rejected(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "too-short")
    with pytest.raises(RuntimeError):
        config._secret()


def test_strong_jwt_secret_is_accepted(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "a" * 48)
    assert config._secret() == "a" * 48


def test_missing_setting_has_clear_error(monkeypatch):
    monkeypatch.delenv("SOME_MISSING_SETTING", raising=False)
    with pytest.raises(RuntimeError, match="SOME_MISSING_SETTING"):
        config._require("SOME_MISSING_SETTING")