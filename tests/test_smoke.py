from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)

def test_health():
    r=client.get("/health")
    assert r.status_code==200 and r.json()["status"]=="ok"

def test_underage_rejected():
    r=client.post("/api/demo/register",data={"alias":"x","age":17,"city":"x","profile_type":"Пара","looking_for":"x"})
    assert r.status_code==403

def test_gate_before_approval():
    r=client.post("/api/demo/register",data={"alias":"adult","age":30,"city":"x","profile_type":"Пара","looking_for":"x"})
    uid=r.json()["user_id"]
    assert client.get(f"/api/users/{uid}/catalog").status_code==403

def test_legacy_admin_key_route_removed():
    # The ADMIN_API_KEY-in-the-browser admin surface has been removed entirely
    # (staff auth is Telegram allowlist + TOTP only, see tests/test_staff_security.py).
    assert client.get("/api/admin/pending").status_code==404
    assert client.get("/api/admin/pending",headers={"X-Admin-Key":"anything"}).status_code==404

def test_legacy_v4_and_v1_routes_removed():
    assert client.post("/api/auth/telegram",data={"init_data":"x"}).status_code==404
    assert client.post("/api/v4/auth/telegram",data={"init_data":"x"}).status_code==404

def test_demo_and_uid_path_routes_disabled_in_production():
    # app.config.settings/app.db.engine are process-wide singletons (see
    # conftest.py), so this is checked in a clean subprocess rather than by
    # mutating os.environ and re-importing app.main in this test process,
    # which would leave other tests running against half-swapped modules.
    import os, subprocess, sys, textwrap
    env = dict(os.environ, ENVIRONMENT="production", DATABASE_URL="sqlite:///./_prod_route_check.db",
               SECRET_KEY="x"*32, STAFF_TELEGRAM_IDS="9001", STAFF_TOTP_SECRET="y"*16,
               S3_SECRET_KEY="z"*16, CLAMAV_HOST="localhost",
               TELEGRAM_BOT_TOKEN="prod-check-token", PUBLIC_BASE_URL="https://club.example.com",
               REDIS_URL=os.environ.get("REDIS_URL","redis://localhost:6379/0"))
    code = textwrap.dedent("""
        from app.main import app
        paths=[r.path for r in app.routes if hasattr(r,'path')]
        assert not any('demo' in p or p.startswith('/api/users/') for p in paths), paths
        print("OK")
    """)
    result = subprocess.run([sys.executable,"-c",code], cwd=os.path.dirname(os.path.dirname(__file__)),
                             env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode==0 and "OK" in result.stdout, result.stdout+result.stderr


def test_production_rejects_incomplete_config():
    import os, subprocess, sys, textwrap
    # Missing TELEGRAM_BOT_TOKEN and an http:// PUBLIC_BASE_URL should both
    # be rejected at startup rather than silently degrading in production.
    env = dict(os.environ, ENVIRONMENT="production", DATABASE_URL="sqlite:///./_prod_guard_check.db",
               SECRET_KEY="x"*32, STAFF_TELEGRAM_IDS="9001", STAFF_TOTP_SECRET="y"*16,
               S3_SECRET_KEY="z"*16, CLAMAV_HOST="localhost", PUBLIC_BASE_URL="http://club.example.com",
               REDIS_URL=os.environ.get("REDIS_URL","redis://localhost:6379/0"))
    env.pop("TELEGRAM_BOT_TOKEN", None)
    result = subprocess.run([sys.executable,"-c","from app.main import app"],
                             cwd=os.path.dirname(os.path.dirname(__file__)), env=env,
                             capture_output=True, text=True, timeout=30)
    assert result.returncode != 0
    assert "TELEGRAM_BOT_TOKEN" in result.stderr and "PUBLIC_BASE_URL" in result.stderr


def test_trusted_host_middleware_rejects_forged_host_in_production():
    import os, subprocess, sys, textwrap
    env = dict(os.environ, ENVIRONMENT="production", DATABASE_URL="sqlite:///./_prod_host_check.db",
               SECRET_KEY="x"*32, STAFF_TELEGRAM_IDS="9001", STAFF_TOTP_SECRET="y"*16,
               S3_SECRET_KEY="z"*16, CLAMAV_HOST="localhost", TELEGRAM_BOT_TOKEN="tok",
               PUBLIC_BASE_URL="https://club.example.com",
               REDIS_URL=os.environ.get("REDIS_URL","redis://localhost:6379/0"))
    code = textwrap.dedent("""
        from fastapi.testclient import TestClient
        from app.main import app
        c = TestClient(app, base_url="http://club.example.com")
        assert c.get("/health").status_code == 200
        c2 = TestClient(app, base_url="http://evil.example.com")
        assert c2.get("/health").status_code == 400
        print("OK")
    """)
    result = subprocess.run([sys.executable,"-c",code], cwd=os.path.dirname(os.path.dirname(__file__)),
                             env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode==0 and "OK" in result.stdout, result.stdout+result.stderr
