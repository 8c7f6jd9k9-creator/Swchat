
import asyncio,json
from datetime import datetime
from sqlalchemy import select
from .db import SessionLocal
from .models import Outbox,User,Audit
from .services.notifications import send_telegram

async def process_once():
    with SessionLocal() as db:
        jobs=db.execute(select(Outbox).where(Outbox.status=="PENDING").order_by(Outbox.id).limit(50)).scalars().all()
        for job in jobs:
            job.attempts+=1
            u=db.get(User,job.target_user_id)
            try:
                payload=json.loads(job.payload)
                ok=await send_telegram(u.telegram_id if u else None,payload.get("text",""))
                if ok:
                    job.status="SENT";job.sent_at=datetime.utcnow()
                elif job.attempts>=5: job.status="FAILED"
            except Exception as e:
                if job.attempts>=5: job.status="FAILED"
                db.add(Audit(actor="outbox-worker",action="notification_error",target_user_id=job.target_user_id,detail=type(e).__name__))
        db.commit()
        return len(jobs)

async def main():
    while True:
        await process_once()
        await asyncio.sleep(5)
if __name__=="__main__": asyncio.run(main())
