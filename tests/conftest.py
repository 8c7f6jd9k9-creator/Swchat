"""Session-wide test configuration.

app.config.settings and app.db.engine are process-wide singletons built from
os.environ at first import. Individual test modules used to set
os.environ["DATABASE_URL"]/["ADMIN_API_KEY"] right before importing app.main,
but whichever test module pytest imports first "wins" for the whole process —
later per-file assignments are silently ignored. That made the suite order
dependent (e.g. test_smoke.py's admin-key check failed only because some
other module happened to import app.main first without ADMIN_API_KEY set).
Setting the required env vars here, in conftest.py, guarantees they exist
before any test module can trigger the first import of app.config.
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_club.db")
os.environ.setdefault("ADMIN_API_KEY", "test-admin")
os.environ.setdefault("SECRET_KEY", "unit-test-secret-not-for-production")
os.environ.setdefault("ENVIRONMENT", "development")
