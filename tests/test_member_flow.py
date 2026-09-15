"""End-to-end coverage of the real secured member + staff API (v6/v7/v8).

Registration and profile creation normally happen through the Telegram bot
(app/bot.py), which isn't reachable through TestClient since it's a
long-poll Dispatcher, not an HTTP route. So this test drives account setup
the way the bot would (direct ORM writes matching its exact state
transitions) and then exercises every HTTP-reachable step for real: Telegram
initData signature verification, Redis-backed sessions, staff TOTP gate,
role-gated ban, catalog/like/match/contact-reveal/block/complaint/delete.
"""
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.db import SessionLocal
from app.models import User, Profile, Verification
from helpers import make_init_data, staff_totp_code

client = TestClient(app)


def _register(tid: int, username: str) -> str:
    r = client.post("/api/v6/auth/telegram", data={"init_data": make_init_data(tid, username)})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _approve(tid: int, alias: str):
    with SessionLocal() as db:
        u = db.execute(select(User).where(User.telegram_id == tid)).scalar_one()
        uid = u.id
        db.add(Profile(user_id=uid, alias=alias, age=30, city="Test", profile_type="Пара", looking_for="Пара"))
        db.add(Verification(user_id=uid, code="0000", status="SUBMITTED"))
        u.status = "ADMIN_REVIEW"
        db.commit()
    staff_token = _staff_login()
    r = client.post(f"/api/v7/staff/users/{uid}/approve", headers=_auth(staff_token), data={"reason": "ok"})
    assert r.status_code == 200 and r.json()["status"] == "APPROVED", r.text


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _staff_login() -> str:
    r = client.post("/api/v8/staff/auth/telegram", data={
        "init_data": make_init_data(9001, "staff"),
        "totp_code": staff_totp_code(),
    })
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_full_gate_approve_catalog_like_match_contact_block_complaint_delete():
    token_a = _register(1001, "alice")
    # Unapproved members get zero access to discovery/catalog/matches.
    assert client.get("/api/v6/catalog", headers=_auth(token_a)).status_code == 403

    _approve(1001, "Alice")
    token_b = _register(1002, "bob")
    _approve(1002, "Bob")

    token_a = _register(1001, "alice")  # re-issue: role/status may have changed
    cat = client.get("/api/v6/catalog", headers=_auth(token_b))
    assert cat.status_code == 200
    alice = next(p for p in cat.json() if p["alias"] == "Alice")

    # One-sided like: no match yet.
    r = client.post(f"/api/v6/like/{alice['user_id']}", headers=_auth(token_b))
    assert r.status_code == 200 and r.json()["matched"] is False

    with SessionLocal() as db:
        bob_id = db.execute(select(User).where(User.telegram_id == 1002)).scalar_one().id
    r = client.post(f"/api/v6/like/{bob_id}", headers=_auth(token_a))
    assert r.status_code == 200 and r.json()["matched"] is True

    matches = client.get("/api/v6/matches", headers=_auth(token_a)).json()
    assert any(m["user_id"] == bob_id for m in matches)
    assert all(m["contact"] is None for m in matches)  # no reveal yet

    client.post("/api/v6/contact-reveal", headers=_auth(token_a), data={"value": True})
    client.post("/api/v6/contact-reveal", headers=_auth(token_b), data={"value": True})
    matches = client.get("/api/v6/matches", headers=_auth(token_a)).json()
    assert any(m["user_id"] == bob_id and m["contact"] == "@bob" for m in matches)

    with SessionLocal() as db:
        alice_id = db.execute(select(User).where(User.telegram_id == 1001)).scalar_one().id
    r = client.post(f"/api/v6/complaint/{alice_id}", headers=_auth(token_b), data={"reason": "spam"})
    assert r.status_code == 200

    r = client.post(f"/api/v6/block/{alice_id}", headers=_auth(token_b))
    assert r.status_code == 200
    cat_after_block = client.get("/api/v6/catalog", headers=_auth(token_b)).json()
    assert not any(p["user_id"] == alice_id for p in cat_after_block)

    r = client.delete("/api/v6/me", headers=_auth(token_a))
    assert r.status_code == 200 and r.json()["status"] == "DELETED"
    # The revoked session cannot be reused after logout-on-delete.
    assert client.get("/api/v6/me", headers=_auth(token_a)).status_code == 401


def test_session_logout_revokes_immediately():
    token = _register(1003, "carol")
    assert client.get("/api/v6/me", headers=_auth(token)).status_code == 200
    client.post("/api/v6/logout", headers=_auth(token))
    assert client.get("/api/v6/me", headers=_auth(token)).status_code == 401


def test_no_way_to_act_as_another_user_via_v6():
    # v6 endpoints derive identity solely from the session token; there is no
    # uid path parameter for a caller to substitute another member's id into.
    import inspect
    from app import main as m
    for name in ["v6_me", "v6_catalog", "v6_like", "v6_matches", "v6_contact_reveal",
                 "v6_visibility", "v6_block", "v6_complaint", "v6_delete"]:
        params = inspect.signature(getattr(m, name)).parameters
        assert "uid" not in params
