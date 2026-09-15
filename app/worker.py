import asyncio
from sqlalchemy import select, or_
from .db import SessionLocal
from .models import Verification, Audit
from .services.media import verification_expired
from .services.object_storage import delete_object

def cleanup_verification_media() -> int:
    with SessionLocal() as db:
        rows = db.execute(select(Verification).where(
            or_(Verification.media_file_id.is_not(None), Verification.storage_key.is_not(None))
        )).scalars().all()
        cleared = 0
        for v in rows:
            if verification_expired(v.created_at):
                if v.storage_key:
                    try:
                        delete_object(v.storage_key)
                    except Exception:
                        # Object store unreachable: keep the reference so the next run retries
                        # the actual delete instead of only forgetting the DB pointer.
                        continue
                v.storage_key = None
                v.media_file_id = None
                cleared += 1
        if cleared:
            db.add(Audit(actor="worker", action="verification_retention_cleanup", detail=f"cleared={cleared}"))
        db.commit()
        return cleared

async def main():
    while True:
        cleanup_verification_media()
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
