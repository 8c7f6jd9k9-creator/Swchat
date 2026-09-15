
import os
os.environ["DATABASE_URL"]="sqlite:///./headers.db"
from fastapi.testclient import TestClient
from app.main import app
def test_headers():
    r=TestClient(app).get("/health")
    assert r.headers["x-content-type-options"]=="nosniff"
    assert "content-security-policy" in r.headers
