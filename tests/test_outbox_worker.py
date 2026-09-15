"""app/outbox_worker.py must retry with backoff (not hammer a failing
notification every 5s poll forever) and eventually dead-letter a message
that can never be delivered - both asserted against the real worker code
with only the Telegram send call replaced (no live bot token in this
sandbox), since that's the one genuinely external dependency."""
import asyncio, json
from datetime import datetime, timedelta
from sqlalchemy import select
import pytest
from app.db import SessionLocal
from app.models import Outbox, User
from app import outbox_worker


def _make_job(status="PENDING", attempts=0, next_attempt_at=None):
    with SessionLocal() as db:
        u = User(status="APPROVED")
        db.add(u); db.flush()
        job = Outbox(kind="TELEGRAM", target_user_id=u.id, payload=json.dumps({"text": "hi"}),
                     status=status, attempts=attempts, next_attempt_at=next_attempt_at or datetime.utcnow())
        db.add(job); db.commit()
        return job.id


def test_failed_send_schedules_backoff_not_immediate_retry(monkeypatch):
    async def always_fails(tid, text):
        return False
    monkeypatch.setattr(outbox_worker, "send_telegram", always_fails)

    job_id = _make_job()
    # >=1, not ==1: other tests in the suite (staff approve/ban actions)
    # can leave their own PENDING outbox rows around in the shared test DB.
    processed = asyncio.run(outbox_worker.process_once())
    assert processed >= 1
    with SessionLocal() as db:
        job = db.get(Outbox, job_id)
        assert job.status == "PENDING" and job.attempts == 1
        assert job.next_attempt_at > datetime.utcnow()  # not due again immediately

    # A poll right now must NOT pick this job up again - it isn't due yet -
    # even if unrelated rows are (that first call backs those off too).
    asyncio.run(outbox_worker.process_once())
    with SessionLocal() as db:
        assert db.get(Outbox, job_id).attempts == 1


def test_exhausted_retries_becomes_dead_letter(monkeypatch):
    async def always_fails(tid, text):
        return False
    monkeypatch.setattr(outbox_worker, "send_telegram", always_fails)

    job_id = _make_job(attempts=outbox_worker.MAX_ATTEMPTS - 1)
    asyncio.run(outbox_worker.process_once())
    with SessionLocal() as db:
        job = db.get(Outbox, job_id)
        assert job.status == "FAILED" and job.attempts == outbox_worker.MAX_ATTEMPTS


def test_exception_during_send_also_backs_off_and_dead_letters(monkeypatch):
    async def boom(tid, text):
        raise RuntimeError("telegram api down")
    monkeypatch.setattr(outbox_worker, "send_telegram", boom)

    job_id = _make_job(attempts=outbox_worker.MAX_ATTEMPTS - 1)
    asyncio.run(outbox_worker.process_once())
    with SessionLocal() as db:
        assert db.get(Outbox, job_id).status == "FAILED"


def test_successful_send_marks_sent():
    async def ok(tid, text):
        return True
    import app.outbox_worker as m
    old = m.send_telegram
    m.send_telegram = ok
    try:
        job_id = _make_job()
        asyncio.run(m.process_once())
        with SessionLocal() as db:
            job = db.get(Outbox, job_id)
            assert job.status == "SENT" and job.sent_at is not None
    finally:
        m.send_telegram = old
