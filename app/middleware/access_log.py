import json, logging, time, uuid
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("privateclub.access")

# Query strings and request bodies can carry initData, session bearer
# tokens, or TOTP codes (see CLAUDE.md's "never log" list) - this logs only
# method/path/status/duration/request-id, deliberately never headers,
# query strings, or bodies.
class AccessLog(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = uuid.uuid4().hex[:16]
        start = time.monotonic()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.monotonic()-start)*1000, 1)
            logger.exception(json.dumps({"request_id": request_id, "method": request.method,
                                          "path": request.url.path, "status": 500, "duration_ms": duration_ms}))
            raise
        duration_ms = round((time.monotonic()-start)*1000, 1)
        response.headers["X-Request-Id"] = request_id
        logger.info(json.dumps({"request_id": request_id, "method": request.method,
                                 "path": request.url.path, "status": response.status_code, "duration_ms": duration_ms}))
        return response
