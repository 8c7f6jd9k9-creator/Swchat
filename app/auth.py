
import hashlib, hmac, secrets, time
from fastapi import Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import User
from .config import settings

# Stateless signed bearer token for MVP. Production can replace with Redis-backed sessions.
def issue_session(user_id:int, ttl:int=86400)->str:
    exp=int(time.time())+ttl
    nonce=secrets.token_hex(8)
    payload=f"{user_id}.{exp}.{nonce}"
    sig=hmac.new(settings.secret_key.encode(),payload.encode(),hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"

def verify_session(token:str)->int:
    try:
        uid,exp,nonce,sig=token.split(".",3)
        payload=f"{uid}.{exp}.{nonce}"
        calc=hmac.new(settings.secret_key.encode(),payload.encode(),hashlib.sha256).hexdigest()
        if not hmac.compare_digest(calc,sig) or int(exp)<int(time.time()):
            raise ValueError
        return int(uid)
    except Exception:
        raise HTTPException(401,"Недействительная или истекшая сессия")

def current_user(db:Session, authorization:str|None):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401,"Требуется авторизация")
    uid=verify_session(authorization[7:])
    u=db.get(User,uid)
    if not u or u.status=="DELETED": raise HTTPException(401,"Пользователь недоступен")
    return u

def require_staff(db:Session, authorization:str|None, roles={"MODERATOR","ADMIN"}):
    u=current_user(db,authorization)
    if u.role not in roles: raise HTTPException(403,"Недостаточно прав")
    return u
