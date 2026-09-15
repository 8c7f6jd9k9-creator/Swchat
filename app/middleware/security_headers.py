
from starlette.middleware.base import BaseHTTPMiddleware
class SecurityHeaders(BaseHTTPMiddleware):
    async def dispatch(self,request,call_next):
        r=await call_next(request)
        r.headers["X-Content-Type-Options"]="nosniff"
        r.headers["Referrer-Policy"]="no-referrer"
        r.headers["X-Frame-Options"]="SAMEORIGIN"
        r.headers["Permissions-Policy"]="camera=(self), microphone=(), geolocation=()"
        r.headers["Content-Security-Policy"]="default-src 'self'; script-src 'self' https://telegram.org 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; frame-ancestors https://web.telegram.org https://*.telegram.org"
        r.headers["Cache-Control"]="no-store"
        return r
