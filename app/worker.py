import asyncio
from sqlalchemy import select
from .db import SessionLocal
from .models import Verification, Audit
from .services.media import verification_expired

def cleanup_verification_media() -> int:
    with SessionLocal() as db:
        rows = db.execute(select(Verification).where(Verification.media_file_id.is_not(None))).scalars().all()
        cleared = 0
        for v in rows:
            if verification_expired(v.created_at):
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
