import asyncio
from sqlalchemy import select, or_
from .db import SessionLocal
from .models import Verification, Audit, ProfilePhoto, User
from .services.media import verification_expired
from .services.object_storage import delete_object

def cleanup_deleted_account_photos() -> int:
    """Retry deleting profile-photo objects for DELETED accounts.

    delete_account() attempts this inline, but leaves storage_key set when
    the object store was unreachable at the time so it isn't lost - this is
    the retry that eventually finishes the job instead of the DB pointer
    quietly going stale.
    """
    with SessionLocal() as db:
        rows = db.execute(
            select(ProfilePhoto).join(User, User.id == ProfilePhoto.user_id)
            .where(User.status == "DELETED", ProfilePhoto.storage_key.is_not(None))
        ).scalars().all()
        cleared = 0
        for p in rows:
            try:
                delete_object(p.storage_key)
            except Exception:
                continue
            p.storage_key = None
            cleared += 1
        if cleared:
            db.add(Audit(actor="worker", action="deleted_account_photo_cleanup", detail=f"cleared={cleared}"))
        db.commit()
        return cleared

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
        cleanup_deleted_account_photos()
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
