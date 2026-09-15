"""Negative-path coverage for staff authentication and authorization.

Staff sign-in requires all three factors together: an allowlisted Telegram
id, a valid signed Telegram initData, and a correct TOTP code - each
checked against the real implementation, not a stub.
"""
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.db import SessionLocal
from app.models import User, Profile
from helpers import make_init_data, staff_totp_code

client = TestClient(app)


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_wrong_totp_rejected():
    bad = "000000" if staff_totp_code() != "000000" else "111111"
    r = client.post("/api/v8/staff/auth/telegram", data={
        "init_data": make_init_data(9001, "staff-a"), "totp_code": bad,
    })
    assert r.status_code == 401


def test_totp_is_rate_limited_against_brute_force():
    # 5 wrong attempts per 5 minutes (see app/main.py's v6_rate("staff-totp:...")).
    for _ in range(5):
        r = client.post("/api/v8/staff/auth/telegram", data={
            "init_data": make_init_data(9003, "staff-c"), "totp_code": "000001",
        })
        assert r.status_code == 401
    r = client.post("/api/v8/staff/auth/telegram", data={
        "init_data": make_init_data(9003, "staff-c"), "totp_code": staff_totp_code(),
    })
    assert r.status_code == 429


def test_non_allowlisted_telegram_id_rejected_even_with_correct_totp():
    r = client.post("/api/v8/staff/auth/telegram", data={
        "init_data": make_init_data(424242, "outsider"), "totp_code": staff_totp_code(),
    })
    assert r.status_code == 403


def test_moderator_cannot_permanently_ban():
    r = client.post("/api/v8/staff/auth/telegram", data={
        "init_data": make_init_data(9001, "mod"), "totp_code": staff_totp_code(),
    })
    assert r.status_code == 200 and r.json()["role"] == "MODERATOR"
    token = r.json()["access_token"]

    with SessionLocal() as db:
        target = User(status="ADMIN_REVIEW")
        db.add(target); db.flush()
        tid = target.id
        db.add(Profile(user_id=tid, alias="Target", age=25, city="X", profile_type="X", looking_for="X"))
        db.commit()

    r = client.post(f"/api/v7/staff/users/{tid}/ban", headers=_auth(token), data={"reason": "test"})
    assert r.status_code == 403
    # MODERATOR can still apply reversible sanctions.
    r = client.post(f"/api/v7/staff/users/{tid}/suspend", headers=_auth(token), data={"reason": "test"})
    assert r.status_code == 200


def test_admin_can_permanently_ban():
    with SessionLocal() as db:
        admin = User(telegram_id=9002, telegram_username="admin", role="ADMIN", status="APPROVED")
        db.add(admin); db.commit()

    r = client.post("/api/v8/staff/auth/telegram", data={
        "init_data": make_init_data(9002, "admin"), "totp_code": staff_totp_code(),
    })
    assert r.status_code == 200 and r.json()["role"] == "ADMIN"
    token = r.json()["access_token"]

    with SessionLocal() as db:
        target = User(status="ADMIN_REVIEW")
        db.add(target); db.flush(); tid = target.id
        db.add(Profile(user_id=tid, alias="Target2", age=25, city="X", profile_type="X", looking_for="X"))
        db.commit()

    r = client.post(f"/api/v7/staff/users/{tid}/ban", headers=_auth(token), data={"reason": "test"})
    assert r.status_code == 200 and r.json()["status"] == "BANNED"


def test_member_token_cannot_reach_staff_endpoints():
    r = client.post("/api/v6/auth/telegram", data={"init_data": make_init_data(1099, "member")})
    token = r.json()["access_token"]
    assert client.get("/api/v7/staff/pending", headers=_auth(token)).status_code == 403
    assert client.get("/api/v7/staff/dashboard", headers=_auth(token)).status_code == 403


def test_no_route_exposes_verification_media_to_members():
    # /api/v6/verification (POST) lets a member start their OWN verification
    # challenge - that's fine. What must never exist on the member surface is
    # a route that reads back verification *media*.
    paths = [r.path for r in app.routes if hasattr(r, "path")]
    member_reachable = [p for p in paths if p.startswith("/api/v6/")]
    assert not any("media" in p for p in member_reachable)
    # The only route that signs a verification-media URL is staff-only.
    media_routes = [r for r in app.routes if hasattr(r, "path") and "verification" in r.path and "media" in r.path]
    assert media_routes and all(r.path.startswith("/api/v7/staff/") for r in media_routes)
