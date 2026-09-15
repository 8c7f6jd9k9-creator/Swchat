
import os
os.environ["DATABASE_URL"]="sqlite:///./e2e_v7.db"
from fastapi.testclient import TestClient
from app.main import app
c=TestClient(app)
def reg(name):
    r=c.post("/api/demo/register",data={"alias":name,"age":30,"city":"Test","profile_type":"Пара","looking_for":"Пара"})
    assert r.status_code==200;return r.json()["user_id"]
def test_registration_and_approval_gate():
    uid=reg("Alpha")
    assert c.get(f"/api/users/{uid}/catalog").status_code==403
def test_underage_gate():
    r=c.post("/api/demo/register",data={"alias":"Minor","age":17,"city":"X","profile_type":"Пара","looking_for":"X"})
    assert r.status_code==403
