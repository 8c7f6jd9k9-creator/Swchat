
from fastapi import HTTPException
from sqlalchemy import select
from .models import User
from .security import validate_telegram_init_data
from .auth_v6 import issue,current
from .config import settings

def allowlist():
    return {int(x.strip()) for x in settings.staff_telegram_ids.split(",") if x.strip().isdigit()}

def login_staff(init_data,db):
    tg=validate_telegram_init_data(init_data); tid=int(tg["id"])
    if tid not in allowlist(): raise HTTPException(403,"Telegram account is not in staff allowlist")
    u=db.execute(select(User).where(User.telegram_id==tid)).scalar_one_or_none()
    if not u:
        u=User(telegram_id=tid,telegram_username=tg.get("username"),status="APPROVED",role="MODERATOR");db.add(u);db.commit();db.refresh(u)
    if u.role not in {"MODERATOR","ADMIN"}: raise HTTPException(403,"Staff role is not assigned")
    return {"access_token":issue(u.id),"role":u.role}

def staff_current(db,authorization):
    u=current(db,authorization)
    if u.role not in {"MODERATOR","ADMIN"}: raise HTTPException(403,"Staff access required")
    return u
