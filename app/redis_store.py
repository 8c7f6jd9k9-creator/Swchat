import secrets,time
from redis import Redis
from .config import settings
def r(): return Redis.from_url(settings.redis_url,decode_responses=True,socket_timeout=2)
def create_session(uid:int):
    token=secrets.token_urlsafe(32)
    c=r()
    c.setex("session:"+token,settings.session_ttl_seconds,str(uid))
    # Reverse index so all of a user's active sessions can be revoked together
    # (account deletion, ban) without needing every token they were issued.
    c.sadd(f"sessions_of:{uid}",token)
    c.expire(f"sessions_of:{uid}",settings.session_ttl_seconds)
    return token
def resolve_session(token:str):
    v=r().get("session:"+token); return int(v) if v and v.isdigit() else None
def revoke_session(token:str):
    c=r(); uid=c.get("session:"+token)
    c.delete("session:"+token)
    if uid: c.srem(f"sessions_of:{uid}",token)
def revoke_all_sessions(uid:int):
    c=r(); key=f"sessions_of:{uid}"
    tokens=c.smembers(key)
    if tokens: c.delete(*[f"session:{t}" for t in tokens])
    c.delete(key)
def limited(key:str,limit:int,window:int):
    k=f"rl:{key}:{int(time.time())//window}"; c=r(); n=c.incr(k)
    if n==1:c.expire(k,window+2)
    return n>limit
