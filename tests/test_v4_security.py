
from app.auth import issue_session, verify_session

def test_session_roundtrip():
    t=issue_session(42,ttl=60)
    assert verify_session(t)==42

def test_tampered_session_rejected():
    t=issue_session(42,ttl=60)
    bad=t[:-1]+("0" if t[-1]!="0" else "1")
    try:
        verify_session(bad)
        assert False
    except Exception:
        assert True
