"""Session-wide test configuration.

app.config.settings and app.db.engine are process-wide singletons built from
os.environ at first import. Individual test modules used to set
os.environ["DATABASE_URL"] right before importing app.main, but whichever
test module pytest imports first "wins" for the whole process — later
per-file assignments are silently ignored. That made the suite order
dependent. Setting the required env vars here, in conftest.py, guarantees
they exist before any test module can trigger the first import of
app.config.
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_club.db")
os.environ.setdefault("SECRET_KEY", "unit-test-secret-not-for-production")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-bot-token-0000000000")
os.environ.setdefault("STAFF_TELEGRAM_IDS", "9001,9002,9003,9004")
os.environ.setdefault("STAFF_TOTP_SECRET", "JBSWY3DPEHPK3PXPJBSWY3DP")
# Sessions/rate limiting are genuinely Redis-backed (no in-memory fallback -
# see app/redis_store.py), so the suite needs a real Redis to run against.
# DB index 1 (not the default 0 staging/dev normally use) keeps test runs
# from ever touching a real environment's session/rate-limit state.
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")

_db_path = os.path.join(os.path.dirname(__file__), "..", "test_club.db")
if os.path.exists(_db_path):
    # Start every test session from a clean sqlite file: tests key data on
    # fixed telegram_ids, and a leftover DB from a previous run would make
    # them read as already-registered/already-approved instead of fresh.
    os.remove(_db_path)

try:
    # Rate-limit counters (e.g. staff TOTP brute-force protection) live in
    # Redis across process runs; flush the dedicated test DB so one run's
    # attempts don't trip another run's rate-limit assertions.
    import redis as _redis_mod
    _redis_mod.Redis.from_url(os.environ["REDIS_URL"], socket_timeout=2).flushdb()
except Exception:
    pass
