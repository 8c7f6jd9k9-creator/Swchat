
from datetime import timedelta
import io, secrets
import urllib3
from minio import Minio
from ..config import settings

# Small, fixed retry/timeout budget: the default urllib3 policy retries
# repeatedly with backoff, which turned a single unreachable-MinIO call into
# a 10+ second stall on a request thread (e.g. account deletion). Callers
# that need "delete this object" to be reliable over time already retry at
# a higher level (the retention worker), so a fast failure here is correct.
_http_client = urllib3.PoolManager(
    timeout=urllib3.Timeout(connect=2, read=5),
    retries=urllib3.Retry(total=1, backoff_factor=0.2),
)

def _client():
    return Minio(settings.s3_endpoint,
                 access_key=settings.s3_access_key,
                 secret_key=settings.s3_secret_key,
                 secure=settings.s3_secure,
                 http_client=_http_client)

def ensure_bucket():
    c=_client()
    if not c.bucket_exists(settings.s3_bucket):
        c.make_bucket(settings.s3_bucket)

def put_profile_photo(data:bytes,content_type:str)->str:
    ensure_bucket()
    ext={"image/jpeg":".jpg","image/png":".png","image/webp":".webp"}.get(content_type,"")
    key=f"profile/{secrets.token_urlsafe(24)}{ext}"
    _client().put_object(settings.s3_bucket,key,io.BytesIO(data),len(data),content_type=content_type)
    return key

def put_verification(data:bytes,content_type:str)->str:
    ensure_bucket()
    key=f"verification/{secrets.token_urlsafe(24)}"
    _client().put_object(settings.s3_bucket,key,io.BytesIO(data),len(data),content_type=content_type)
    return key

def signed_profile_url(key:str,minutes:int=10)->str:
    if not key.startswith("profile/"): raise ValueError("Only profile media can be signed for member delivery")
    return _client().presigned_get_object(settings.s3_bucket,key,expires=timedelta(minutes=minutes))

def delete_object(key:str):
    _client().remove_object(settings.s3_bucket,key)

def signed_verification_url(*args,**kwargs):
    raise PermissionError("Verification media is staff-only and is never issued through member media API")

def staff_signed_verification_url(key:str,minutes:int=5)->str:
    """Short-lived signed URL for staff review only. Callers must have already
    authenticated the caller as MODERATOR/ADMIN before invoking this."""
    if not key.startswith("verification/"): raise ValueError("Not a verification media key")
    return _client().presigned_get_object(settings.s3_bucket,key,expires=timedelta(minutes=minutes))
