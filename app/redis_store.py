import secrets,time
from redis import Redis
from .config import settings
def r(): return Redis.from_url(settings.redis_url,decode_responses=True,socket_timeout=2)
def create_session(uid:int):
    token=secrets.token_urlsafe(32); r().setex("session:"+token,settings.session_ttl_seconds,str(uid)); return token
def resolve_session(token:str):
    v=r().get("session:"+token); return int(v) if v and v.isdigit() else None
def revoke_session(token:str): r().delete("session:"+token)
def limited(key:str,limit:int,window:int):
    k=f"rl:{key}:{int(time.time())//window}"; c=r(); n=c.incr(k)
    if n==1:c.expire(k,window+2)
    return n>limit
