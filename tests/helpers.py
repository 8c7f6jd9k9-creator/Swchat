"""Shared helpers for exercising the real Telegram/staff auth flows in tests.

Telegram Mini App initData is a signed query string (WebAppData HMAC-SHA256
over the bot token, per Telegram's documented algorithm). We don't have a
real Telegram client in CI, but the algorithm is public and deterministic,
so tests sign fixtures exactly the way a real Mini App client would and the
server-side validator in app.security exercises the genuine code path -
this is not a mock of validate_telegram_init_data, it is real input to it.
"""
import hashlib, hmac, json, time
from urllib.parse import urlencode
import pyotp
from app.config import settings


def make_init_data(user_id: int, username: str = "tester", auth_date: int | None = None) -> str:
    auth_date = auth_date or int(time.time())
    user = json.dumps({"id": user_id, "username": username}, separators=(",", ":"))
    data = {"auth_date": str(auth_date), "user": user}
    check = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret = hmac.new(b"WebAppData", settings.telegram_bot_token.encode(), hashlib.sha256).digest()
    data["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(data)


def staff_totp_code() -> str:
    return pyotp.TOTP(settings.staff_totp_secret).now()
