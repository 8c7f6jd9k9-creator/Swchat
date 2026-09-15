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

def test_admin_requires_key():
    assert client.get("/api/admin/pending").status_code==401
    assert client.get("/api/admin/pending",headers={"X-Admin-Key":"test-admin"}).status_code==200
