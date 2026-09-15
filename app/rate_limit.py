
import time
from collections import defaultdict, deque
from fastapi import HTTPException
_hits=defaultdict(deque)
def check(key:str, limit:int=30, window:int=60):
    now=time.time(); q=_hits[key]
    while q and q[0]<now-window: q.popleft()
    if len(q)>=limit: raise HTTPException(429,"Слишком много запросов. Повторите позже.")
    q.append(now)
