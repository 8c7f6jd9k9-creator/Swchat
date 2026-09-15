import hashlib, hmac, json, time
from urllib.parse import parse_qsl
from fastapi import HTTPException
from .config import settings

def validate_telegram_init_data(init_data: str, max_age: int = 3600) -> dict:
    if not settings.telegram_bot_token:
        raise HTTPException(503, "Telegram integration is not configured")
    data = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = data.pop("hash", None)
    if not received_hash:
        raise HTTPException(401, "Missing Telegram signature")
    auth_date = int(data.get("auth_date", "0") or 0)
    if not auth_date or abs(int(time.time()) - auth_date) > max_age:
        raise HTTPException(401, "Telegram authorization expired")
    check = "\n".join(f"{k}={v}" for k,v in sorted(data.items()))
    secret = hmac.new(b"WebAppData", settings.telegram_bot_token.encode(), hashlib.sha256).digest()
    calculated = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calculated, received_hash):
        raise HTTPException(401, "Invalid Telegram signature")
    try:
        return json.loads(data["user"])
    except Exception:
        raise HTTPException(401, "Invalid Telegram user payload")

def require_admin_key(value: str|None):
    if not settings.admin_api_key or not value or not hmac.compare_digest(value, settings.admin_api_key):
        raise HTTPException(401, "Administrator authorization required")
