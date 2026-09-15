from datetime import datetime,timedelta
from app.services.media import verification_expired
def test_old_verification_expires(): assert verification_expired(datetime.utcnow()-timedelta(days=30))
def test_recent_verification_does_not_expire(): assert not verification_expired(datetime.utcnow())
