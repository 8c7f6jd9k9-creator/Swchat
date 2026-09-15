from fastapi import HTTPException
from .models import User
from .redis_store import create_session,resolve_session,revoke_session,limited
def issue(uid): return create_session(uid)
def current(db,authorization):
    if not authorization or not authorization.startswith("Bearer "): raise HTTPException(401,"Требуется авторизация")
    uid=resolve_session(authorization[7:])
    if not uid: raise HTTPException(401,"Сессия истекла или отозвана")
    u=db.get(User,uid)
    if not u or u.status=="DELETED": raise HTTPException(401,"Пользователь недоступен")
    return u
def rate(key,limit,window):
    if limited(key,limit,window): raise HTTPException(429,"Слишком много запросов")
