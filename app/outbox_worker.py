
import asyncio,json
from datetime import datetime,timedelta
from sqlalchemy import select
from .db import SessionLocal
from .models import Outbox,User,Audit
from .services.notifications import send_telegram

MAX_ATTEMPTS=5
BASE_BACKOFF_SECONDS=10

def _backoff(attempts:int)->timedelta:
    # 10s, 40s, 90s, 160s, ... - exponential, not "retry every poll cycle
    # regardless of how many times it already failed".
    return timedelta(seconds=BASE_BACKOFF_SECONDS*(attempts**2))

async def process_once():
    with SessionLocal() as db:
        now=datetime.utcnow()
        jobs=db.execute(select(Outbox).where(
            Outbox.status=="PENDING",Outbox.next_attempt_at<=now
        ).order_by(Outbox.id).limit(50)).scalars().all()
        for job in jobs:
            job.attempts+=1
            u=db.get(User,job.target_user_id)
            try:
                payload=json.loads(job.payload)
                ok=await send_telegram(u.telegram_id if u else None,payload.get("text",""))
                if ok:
                    job.status="SENT";job.sent_at=datetime.utcnow()
                elif job.attempts>=MAX_ATTEMPTS:
                    job.status="FAILED"
                    db.add(Audit(actor="outbox-worker",action="notification_dead_letter",target_user_id=job.target_user_id,detail=f"attempts={job.attempts}"))
                else:
                    job.next_attempt_at=now+_backoff(job.attempts)
            except Exception as e:
                if job.attempts>=MAX_ATTEMPTS:
                    job.status="FAILED"
                    db.add(Audit(actor="outbox-worker",action="notification_dead_letter",target_user_id=job.target_user_id,detail=f"attempts={job.attempts},error={type(e).__name__}"))
                else:
                    job.next_attempt_at=now+_backoff(job.attempts)
                db.add(Audit(actor="outbox-worker",action="notification_error",target_user_id=job.target_user_id,detail=type(e).__name__))
        db.commit()
        return len(jobs)

async def main():
    while True:
        await process_once()
        await asyncio.sleep(5)
if __name__=="__main__": asyncio.run(main())
