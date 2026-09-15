from datetime import datetime, timedelta
from ..config import settings

def verification_expired(created_at: datetime, now: datetime | None = None) -> bool:
    now = now or datetime.utcnow()
    return created_at < now - timedelta(days=settings.verification_retention_days)

def verification_public_url(file_id: str):
    # Verification media must never be exposed as public profile media.
    return None
