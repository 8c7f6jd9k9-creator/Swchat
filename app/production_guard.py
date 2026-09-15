
from .config import settings
def validate_production():
    if settings.environment!="production": return
    bad=[]
    if len(settings.secret_key)<32 or settings.secret_key.lower() in {"change-me","secret","dev"}: bad.append("SECRET_KEY")
    if not settings.redis_url: bad.append("REDIS_URL")
    if not settings.staff_telegram_ids: bad.append("STAFF_TELEGRAM_IDS")
    if len(settings.staff_totp_secret)<16: bad.append("STAFF_TOTP_SECRET")
    if settings.s3_secret_key in {"change-me","replace-with-strong-secret"} or len(settings.s3_secret_key)<16: bad.append("S3_SECRET_KEY")
    if not settings.clamav_host: bad.append("CLAMAV_HOST")
    if not settings.telegram_bot_token: bad.append("TELEGRAM_BOT_TOKEN")
    if not settings.public_base_url.startswith("https://"): bad.append("PUBLIC_BASE_URL (must be https://)")
    if bad: raise RuntimeError("Production configuration rejected: "+", ".join(bad))
