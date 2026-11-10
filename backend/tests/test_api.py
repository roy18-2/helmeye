import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.config import settings
from app.security import ALGORITHM
from app.services.evidence import EVIDENCE_DIR
from app.services.pipeline import VIDEO_DIR
from tests.constants import ADMIN, INACTIVE, REVIEWER

pytestmark = pytest.mark.usefixtures("users", "clean_data")


def now():
    return datetime.now(timezone.utc)


def iso(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------- health and auth ----------


def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "db": settings.db_name}


def test_protected_route_needs_token(client):
    res = client.get("/api/cameras")
    assert res.status_code == 401


def test_garbage_token_is_rejected(client):
    res = client.get("/api/cameras", headers={"Authorization": "Bearer not-a-token"})
    assert res.status_code == 401


def test_login_success(client):
    res = client.post("/api/auth/login", json={"email": ADMIN["email"], "password": ADMIN["password"]})
    assert res.status_code == 200
    body = res.json()
    assert body["access_token"]
    assert body["user"]["role"] == "admin"
    assert "password_hash" not in body["user"]


def test_login_email_is_case_insensitive(client):
    res = client.post("/api/auth/login", json={"email": ADMIN["email"].upper(), "password": ADMIN["password"]})
    assert res.status_code == 200


def test_login_wrong_password(client):
    res = client.post("/api/auth/login", json={"email": ADMIN["email"], "password": "wrong-password"})
    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid email or password"


def test_login_unknown_email_gives_same_error(client):
    res = client.post("/api/auth/login", json={"email": "nobody@test.io", "password": "whatever123"})
    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid email or password"


def test_login_rejects_bad_email_format(client):
    res = client.post("/api/auth/login", json={"email": "not-an-email", "password": "whatever123"})
    assert res.status_code == 422


def test_inactive_user_cannot_log_in(client):
    res = client.post("/api/auth/login", json={"email": INACTIVE["email"], "password": INACTIVE["password"]})
    assert res.status_code == 401


def test_me_returns_current_user(client, admin_headers):
    res = client.get("/api/auth/me", headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["email"] == ADMIN["email"]
    assert "password_hash" not in res.json()


def test_reviewer_cannot_list_users(client, reviewer_headers):
    assert client.get("/api/auth/users", headers=reviewer_headers).status_code == 403


def test_admin_can_list_users_without_hashes(client, admin_headers):
    res = client.get("/api/auth/users", headers=admin_headers)
    assert res.status_code == 200
    assert len(res.json()) >= 3
    assert all("password_hash" not in u for u in res.json())


def test_admin_creates_user_and_duplicates_are_rejected(client, admin_headers):
    body = {"email": "new.user@test.io", "name": "New User", "password": "NewUserPass1", "role": "reviewer"}
    res = client.post("/api/auth/users", json=body, headers=admin_headers)
    assert res.status_code == 201
    assert res.json()["role"] == "reviewer"
    assert "password_hash" not in res.json()

    assert client.post("/api/auth/users", json=body, headers=admin_headers).status_code == 409

    login = client.post("/api/auth/login", json={"email": body["email"], "password": body["password"]})
    assert login.status_code == 200


def test_create_user_validation(client, admin_headers):
    base = {"email": "valid@test.io", "name": "Valid", "password": "ValidPass123", "role": "reviewer"}
    assert client.post("/api/auth/users", json={**base, "password": "short"}, headers=admin_headers).status_code == 422
    assert client.post("/api/auth/users", json={**base, "email": "nope"}, headers=admin_headers).status_code == 422
    assert client.post("/api/auth/users", json={**base, "role": "superuser"}, headers=admin_headers).status_code == 422


def test_password_over_72_bytes_is_rejected_cleanly(client, admin_headers):
    body = {"email": "bytes@test.io", "name": "Bytes", "password": "é" * 50, "role": "reviewer"}
    assert client.post("/api/auth/users", json=body, headers=admin_headers).status_code == 422


def test_reviewer_cannot_create_users(client, reviewer_headers):
    body = {"email": "x@test.io", "name": "X", "password": "ValidPass123", "role": "admin"}
    assert client.post("/api/auth/users", json=body, headers=reviewer_headers).status_code == 403


def test_cameras_list(client, admin_headers):
    res = client.get("/api/cameras", headers=admin_headers)
    assert res.status_code == 200
    assert {c["code"] for c in res.json()} >= {"CAM-01", "CAM-02"}


# ---------- incidents ----------


def test_incidents_need_auth(client):
    assert client.get("/api/incidents").status_code == 401


def test_list_hides_internal_path_and_builds_evidence_url(client, admin_headers, make_incident):
    with_image = make_incident(evidence_path="x.jpg")
    without = make_incident()
    items = {i["id"]: i for i in client.get("/api/incidents", headers=admin_headers).json()["items"]}
    assert items[with_image]["evidence_url"] == f"/api/incidents/{with_image}/evidence"
    assert "evidence_path" not in items[with_image]
    assert items[without]["evidence_url"] is None


def test_filters(client, admin_headers, make_incident):
    make_incident(camera_code="CAM-01", confidence=0.9)
    make_incident(camera_code="CAM-02", confidence=0.6)
    make_incident(camera_code="CAM-01", confidence=0.8, review_status="confirmed")

    def total(**params):
        res = client.get("/api/incidents", params=params, headers=admin_headers)
        assert res.status_code == 200
        return res.json()["total"]

    assert total() == 3
    assert total(camera_code="CAM-01") == 2
    assert total(review_status="pending") == 2
    assert total(review_status="confirmed") == 1
    assert total(min_confidence=0.85) == 1
    assert total(label="unclear_headgear") == 0


def test_invalid_filter_values_are_rejected(client, admin_headers):
    assert client.get("/api/incidents", params={"review_status": "bogus"}, headers=admin_headers).status_code == 422
    assert client.get("/api/incidents", params={"page_size": 0}, headers=admin_headers).status_code == 422
    assert client.get("/api/incidents", params={"min_confidence": 2}, headers=admin_headers).status_code == 422


def test_video_filter(client, admin_headers, make_incident):
    make_incident(video_id="video-1")
    make_incident(video_id="video-2")
    make_incident()
    res = client.get("/api/incidents", params={"video_id": "video-1"}, headers=admin_headers).json()
    assert res["total"] == 1
    assert res["items"][0]["video_id"] == "video-1"


def test_date_filters(client, admin_headers, make_incident):
    make_incident(detected_at=now() - timedelta(days=10))
    recent = make_incident(detected_at=now() - timedelta(hours=1))

    after = client.get("/api/incidents", params={"date_from": iso(now() - timedelta(days=1))}, headers=admin_headers).json()
    assert [i["id"] for i in after["items"]] == [recent]

    before = client.get("/api/incidents", params={"date_to": iso(now() - timedelta(days=5))}, headers=admin_headers).json()
    assert before["total"] == 1
    assert before["items"][0]["id"] != recent


def test_newest_first_and_paging(client, admin_headers, make_incident):
    oldest = make_incident(detected_at=now() - timedelta(hours=3))
    middle = make_incident(detected_at=now() - timedelta(hours=2))
    newest = make_incident(detected_at=now() - timedelta(hours=1))

    first = client.get("/api/incidents", params={"page": 1, "page_size": 2}, headers=admin_headers).json()
    assert first["total"] == 3
    assert [i["id"] for i in first["items"]] == [newest, middle]

    second = client.get("/api/incidents", params={"page": 2, "page_size": 2}, headers=admin_headers).json()
    assert [i["id"] for i in second["items"]] == [oldest]


def test_get_one_incident(client, admin_headers, make_incident):
    iid = make_incident()
    assert client.get(f"/api/incidents/{iid}", headers=admin_headers).json()["id"] == iid
    assert client.get("/api/incidents/does-not-exist", headers=admin_headers).status_code == 404


# ---------- review workflow ----------


def test_review_records_who_and_keeps_history(client, reviewer_headers, make_incident):
    iid = make_incident()
    url = f"/api/incidents/{iid}/review"

    first = client.patch(url, json={"status": "confirmed", "note": "clear view"}, headers=reviewer_headers)
    assert first.status_code == 200
    body = first.json()
    assert body["review_status"] == "confirmed"
    assert body["reviewed_by_name"] == REVIEWER["name"]
    assert body["review_note"] == "clear view"
    assert len(body["review_history"]) == 1

    second = client.patch(url, json={"status": "false_positive"}, headers=reviewer_headers).json()
    assert second["review_status"] == "false_positive"
    assert [h["status"] for h in second["review_history"]] == ["confirmed", "false_positive"]


def test_blank_note_is_stored_as_none(client, reviewer_headers, make_incident):
    iid = make_incident()
    res = client.patch(f"/api/incidents/{iid}/review", json={"status": "uncertain", "note": "   "}, headers=reviewer_headers)
    assert res.json()["review_note"] is None


def test_review_validation(client, reviewer_headers, make_incident):
    iid = make_incident()
    url = f"/api/incidents/{iid}/review"
    assert client.patch(url, json={"status": "pending"}, headers=reviewer_headers).status_code == 400
    assert client.patch(url, json={"status": "bogus"}, headers=reviewer_headers).status_code == 422
    assert client.patch(url, json={"status": "confirmed", "note": "x" * 501}, headers=reviewer_headers).status_code == 422
    assert client.patch("/api/incidents/nope/review", json={"status": "confirmed"}, headers=reviewer_headers).status_code == 404


def test_review_needs_auth(client, make_incident):
    iid = make_incident()
    assert client.patch(f"/api/incidents/{iid}/review", json={"status": "confirmed"}).status_code == 401


def test_summary_precision(client, admin_headers, make_incident):
    make_incident(review_status="confirmed")
    make_incident(review_status="confirmed")
    make_incident(review_status="false_positive")
    make_incident(review_status="pending")
    body = client.get("/api/incidents/summary", headers=admin_headers).json()
    assert body["total"] == 4
    assert body["by_review_status"]["confirmed"] == 2
    assert body["by_review_status"]["pending"] == 1
    assert body["reviewed_precision"] == pytest.approx(0.667, abs=0.001)


def test_summary_with_no_data(client, admin_headers):
    body = client.get("/api/incidents/summary", headers=admin_headers).json()
    assert body["total"] == 0
    assert body["reviewed_precision"] is None
    assert body["avg_confidence"] is None


# ---------- evidence images ----------


def test_evidence_needs_auth(client, make_incident):
    assert client.get(f"/api/incidents/{make_incident(evidence_path='x.jpg')}/evidence").status_code == 401


def test_evidence_missing_is_404(client, admin_headers, make_incident):
    assert client.get(f"/api/incidents/{make_incident()}/evidence", headers=admin_headers).status_code == 404


def test_evidence_is_served(client, admin_headers, make_incident):
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    name = f"test_{uuid.uuid4().hex}.jpg"
    path = EVIDENCE_DIR / name
    path.write_bytes(b"\xff\xd8\xff\xe0fake-jpeg")
    try:
        iid = make_incident(evidence_path=name)
        res = client.get(f"/api/incidents/{iid}/evidence", headers=admin_headers)
        assert res.status_code == 200
        assert res.headers["content-type"] == "image/jpeg"
        assert res.content == b"\xff\xd8\xff\xe0fake-jpeg"
    finally:
        path.unlink(missing_ok=True)


def test_evidence_path_traversal_is_blocked(client, admin_headers, make_incident):
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    secret = EVIDENCE_DIR.parent / f"secret_{uuid.uuid4().hex}.txt"
    secret.write_text("top secret")
    try:
        iid = make_incident(evidence_path=f"../{secret.name}")
        res = client.get(f"/api/incidents/{iid}/evidence", headers=admin_headers)
        assert res.status_code == 404
        assert "top secret" not in res.text
    finally:
        secret.unlink(missing_ok=True)


# ---------- analytics ----------


def test_analytics_needs_auth(client):
    assert client.get("/api/analytics").status_code == 401


def test_analytics_counts_and_source_filter(client, admin_headers, make_incident):
    make_incident(camera_code="CAM-01", source="demo")
    make_incident(camera_code="CAM-01", source="demo")
    make_incident(camera_code="CAM-02", source="mock")

    body = client.get("/api/analytics", params={"days": 1, "tz": "UTC"}, headers=admin_headers).json()
    assert body["total"] == 3
    assert len(body["by_hour"]) == 24
    assert sum(h["count"] for h in body["by_hour"]) == 3
    cameras = {c["camera_code"]: c["count"] for c in body["by_camera"]}
    assert cameras["CAM-01"] == 2 and cameras["CAM-02"] == 1

    demo = client.get("/api/analytics", params={"days": 1, "tz": "UTC", "source": "demo"}, headers=admin_headers).json()
    assert demo["total"] == 2
    mock = client.get("/api/analytics", params={"days": 1, "tz": "UTC", "source": "mock"}, headers=admin_headers).json()
    assert mock["total"] == 1


def test_analytics_period_window(client, admin_headers, make_incident):
    make_incident(detected_at=now() - timedelta(days=10))
    make_incident(detected_at=now() - timedelta(hours=1))
    week = client.get("/api/analytics", params={"days": 7, "tz": "UTC"}, headers=admin_headers).json()
    month = client.get("/api/analytics", params={"days": 30, "tz": "UTC"}, headers=admin_headers).json()
    assert week["total"] == 1
    assert month["total"] == 2
    assert len(week["daily"]) == 7
    dates = [d["date"] for d in week["daily"]]
    assert dates == sorted(dates)


def test_analytics_hour_uses_requested_timezone(client, admin_headers, make_incident):
    moment = now().replace(hour=10, minute=0, second=0, microsecond=0)
    make_incident(detected_at=moment)
    utc = client.get("/api/analytics", params={"days": 2, "tz": "UTC"}, headers=admin_headers).json()
    ist = client.get("/api/analytics", params={"days": 2, "tz": "Asia/Kolkata"}, headers=admin_headers).json()
    assert utc["total"] == 1 and ist["total"] == 1
    assert {h["hour"]: h["count"] for h in utc["by_hour"]}[10] == 1
    assert {h["hour"]: h["count"] for h in ist["by_hour"]}[15] == 1


def test_analytics_unknown_timezone_falls_back_to_utc(client, admin_headers):
    body = client.get("/api/analytics", params={"tz": "Not/AZone"}, headers=admin_headers).json()
    assert body["timezone"] == "UTC"


def test_analytics_rejects_bad_parameters(client, admin_headers):
    assert client.get("/api/analytics", params={"source": "bogus"}, headers=admin_headers).status_code == 422
    assert client.get("/api/analytics", params={"days": 0}, headers=admin_headers).status_code == 422
    assert client.get("/api/analytics", params={"days": 91}, headers=admin_headers).status_code == 422


# ---------- video upload ----------


def _upload(client, headers, filename="clip.mp4", content=b"not a video", camera="CAM-01"):
    return client.post(
        "/api/videos",
        headers=headers,
        files={"file": (filename, content, "video/mp4")},
        data={"camera_code": camera},
    )


def test_upload_needs_auth(client):
    assert _upload(client, None).status_code == 401


def test_upload_rejects_wrong_extension(client, admin_headers):
    res = _upload(client, admin_headers, filename="notes.txt")
    assert res.status_code == 400
    assert "Allowed types" in res.json()["detail"]


def test_upload_rejects_unknown_camera(client, admin_headers):
    res = _upload(client, admin_headers, camera="CAM-99")
    assert res.status_code == 400
    assert res.json()["detail"] == "Unknown camera code"


def test_upload_rejects_unreadable_video(client, admin_headers):
    res = _upload(client, admin_headers)
    assert res.status_code == 400
    assert "Could not read" in res.json()["detail"]


def test_video_list_hides_internal_fields(client, admin_headers, make_video):
    vid = make_video()
    videos = client.get("/api/videos", headers=admin_headers).json()
    match = next(v for v in videos if v["id"] == vid)
    assert "stored_name" not in match and "sha256" not in match
    assert client.get(f"/api/videos/{vid}", headers=admin_headers).status_code == 200
    assert client.get("/api/videos/does-not-exist", headers=admin_headers).status_code == 404


# ---------- replay stream tokens ----------


def _stream_token(client, headers, vid):
    res = client.post(f"/api/videos/{vid}/stream-token", headers=headers)
    assert res.status_code == 200, res.text
    return res.json()["token"]


def test_stream_token_needs_auth_and_a_real_video(client, admin_headers, make_video):
    vid = make_video()
    assert client.post(f"/api/videos/{vid}/stream-token").status_code == 401
    assert client.post("/api/videos/does-not-exist/stream-token", headers=admin_headers).status_code == 404


def test_stream_requires_a_token(client, make_video):
    vid = make_video()
    assert client.get(f"/api/videos/{vid}/stream").status_code == 422


def test_stream_serves_file_with_valid_token(client, admin_headers, make_video):
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    vid = make_video()
    path = VIDEO_DIR / f"{vid}.mp4"
    path.write_bytes(b"fake-video-bytes")
    try:
        token = _stream_token(client, admin_headers, vid)
        res = client.get(f"/api/videos/{vid}/stream", params={"token": token})
        assert res.status_code == 200
        assert res.headers["content-type"].startswith("video/mp4")
        assert res.content == b"fake-video-bytes"
    finally:
        path.unlink(missing_ok=True)


def test_stream_reports_missing_file(client, admin_headers, make_video):
    vid = make_video()
    token = _stream_token(client, admin_headers, vid)
    res = client.get(f"/api/videos/{vid}/stream", params={"token": token})
    assert res.status_code == 404


def test_stream_rejects_bad_tokens(client, admin_headers, make_video):
    vid = make_video()
    other = make_video()
    assert client.get(f"/api/videos/{vid}/stream", params={"token": "garbage"}).status_code == 401

    token_for_other = _stream_token(client, admin_headers, other)
    assert client.get(f"/api/videos/{vid}/stream", params={"token": token_for_other}).status_code == 401

    login_token = admin_headers["Authorization"].split(" ", 1)[1]
    assert client.get(f"/api/videos/{vid}/stream", params={"token": login_token}).status_code == 401

    expired = jwt.encode(
        {"purpose": "video-stream", "vid": vid, "exp": now() - timedelta(minutes=1)},
        settings.jwt_secret,
        algorithm=ALGORITHM,
    )
    assert client.get(f"/api/videos/{vid}/stream", params={"token": expired}).status_code == 401