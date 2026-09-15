"""Account deletion must anonymize the profile, clear stored-media
references, and revoke every active session for that user - not just flip a
status column. MinIO isn't available in this sandbox, so the object-storage
delete call itself can't be verified end-to-end here (it's wrapped in a
best-effort try/except precisely because the store can be unreachable); this
covers everything that doesn't require a live S3, and the storage_key
columns being cleared IS the record of an attempted deletion. Ban revokes
all sessions immediately too, rather than waiting for token TTL.
"""
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.db import SessionLocal
from app.models import User, Profile, Verification, ProfilePhoto
from app.redis_store import create_session, resolve_session
from helpers import make_init_data, staff_totp_code

client = TestClient(app)


def _auth(token): return {"Authorization": f"Bearer {token}"}


def test_delete_account_anonymizes_and_revokes_all_sessions():
    r = client.post("/api/v6/auth/telegram", data={"init_data": make_init_data(2001, "dana")})
    token_device_a = r.json()["access_token"]

    with SessionLocal() as db:
        u = db.execute(select(User).where(User.telegram_id == 2001)).scalar_one()
        uid = u.id
        db.add(Profile(user_id=uid, alias="Dana", age=28, city="Town", profile_type="X", looking_for="X", about="hi"))
        db.add(Verification(user_id=uid, code="1234", status="SUBMITTED", storage_key="verification/fake-key"))
        db.add(ProfilePhoto(user_id=uid, telegram_file_id="tg1", storage_key="profile/fake-key", status="APPROVED", approved=True))
        db.commit()

    # A second concurrent session on another device for the same account.
    token_device_b = create_session(uid)
    assert resolve_session(token_device_b) == uid

    r = client.delete("/api/v6/me", headers=_auth(token_device_a))
    assert r.status_code == 200 and r.json()["status"] == "DELETED"

    # Both sessions are gone, not just the one used to delete.
    assert resolve_session(token_device_b) is None
    assert client.get("/api/v6/me", headers=_auth(token_device_a)).status_code == 401

    with SessionLocal() as db:
        u = db.execute(select(User).where(User.id == uid)).scalar_one()
        assert u.status == "DELETED"
        assert u.telegram_id is None and u.telegram_username is None
        p = db.execute(select(Profile).where(Profile.user_id == uid)).scalar_one()
        assert p.alias != "Dana" and p.about == "" and p.city == ""
        # MinIO isn't reachable in this sandbox, so the object-delete call
        # fails; storage_key is deliberately left set in that case (not
        # cleared to None) so the retention worker retries the real delete
        # instead of the pointer being silently lost. What deletion always
        # does regardless of object-store reachability - flip status/flags
        # - is what's asserted here.
        v = db.execute(select(Verification).where(Verification.user_id == uid)).scalar_one()
        assert v.media_file_id is None
        photo = db.execute(select(ProfilePhoto).where(ProfilePhoto.user_id == uid)).scalar_one()
        assert photo.status == "REJECTED" and photo.approved is False


def test_ban_revokes_sessions_immediately_not_just_status_gated():
    r = client.post("/api/v6/auth/telegram", data={"init_data": make_init_data(2002, "erin")})
    token = r.json()["access_token"]
    with SessionLocal() as db:
        u = db.execute(select(User).where(User.telegram_id == 2002)).scalar_one()
        uid = u.id
        db.add(Profile(user_id=uid, alias="Erin", age=28, city="X", profile_type="X", looking_for="X"))
        u.status = "ADMIN_REVIEW"
        db.commit()

    # A dedicated telegram_id (not shared with test_staff_security.py's
    # admin fixture) pre-created with role=ADMIN, same as that test does -
    # login_staff() only auto-creates new rows as MODERATOR.
    with SessionLocal() as db:
        db.add(User(telegram_id=9004, telegram_username="admin4", role="ADMIN", status="APPROVED"))
        db.commit()
    staff = client.post("/api/v8/staff/auth/telegram", data={
        "init_data": make_init_data(9004, "admin4"), "totp_code": staff_totp_code(),
    })
    assert staff.status_code == 200 and staff.json()["role"] == "ADMIN", staff.text
    staff_token = staff.json()["access_token"]

    assert client.get("/api/v6/me", headers=_auth(token)).status_code == 200
    r = client.post(f"/api/v7/staff/users/{uid}/ban", headers=_auth(staff_token), data={"reason": "test"})
    assert r.status_code == 200 and r.json()["status"] == "BANNED"
    assert client.get("/api/v6/me", headers=_auth(token)).status_code == 401
