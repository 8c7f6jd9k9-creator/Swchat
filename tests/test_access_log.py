"""Structured access logging must never leak secrets/PII: request bodies
and query strings can carry Telegram initData, session bearer tokens, or
TOTP codes (see CLAUDE.md's "never log" list). Verifies both that logging
actually happens (not just configured and silent) and that it stays to
method/path/status/duration - nothing from the request body/headers/query.
"""
import logging
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_access_log_records_request_metadata_only(caplog):
    with caplog.at_level(logging.INFO, logger="privateclub.access"):
        r = client.post("/api/v6/auth/telegram", data={"init_data": "auth_date=1&user=%7B%22id%22%3A1%7D&hash=deadbeefsecrettoken"})
    assert "X-Request-Id" in r.headers
    log_text = "\n".join(rec.message for rec in caplog.records)
    assert "/api/v6/auth/telegram" in log_text
    assert str(r.status_code) in log_text
    assert "deadbeefsecrettoken" not in log_text
    assert "init_data" not in log_text


def test_access_log_records_error_responses_too(caplog):
    with caplog.at_level(logging.INFO, logger="privateclub.access"):
        r = client.get("/api/v6/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401
    assert "X-Request-Id" in r.headers
    log_text = "\n".join(rec.message for rec in caplog.records)
    assert "401" in log_text and "/api/v6/me" in log_text
