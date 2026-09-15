
import pyotp
from fastapi import HTTPException
from .config import settings
def verify(code:str):
    if not settings.staff_totp_secret: raise HTTPException(503,"Staff 2FA is not configured")
    if not pyotp.TOTP(settings.staff_totp_secret).verify(code,valid_window=1):
        raise HTTPException(401,"Неверный код второго фактора")
    return True
