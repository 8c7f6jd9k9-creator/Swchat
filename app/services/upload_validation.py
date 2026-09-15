
from fastapi import HTTPException
MAX_PROFILE=10*1024*1024
MAX_VERIFY=25*1024*1024
JPEG=b"\xff\xd8\xff"; PNG=b"\x89PNG\r\n\x1a\n"; WEBP=b"RIFF"
def detect(data:bytes)->str|None:
    if data.startswith(JPEG): return "image/jpeg"
    if data.startswith(PNG): return "image/png"
    if data.startswith(WEBP) and len(data)>12 and data[8:12]==b"WEBP": return "image/webp"
    # MP4 family: ISO BMFF 'ftyp' at offset 4.
    if len(data)>12 and data[4:8]==b"ftyp": return "video/mp4"
    return None
def validate_profile(data:bytes)->str:
    if not data or len(data)>MAX_PROFILE: raise HTTPException(413,"Недопустимый размер файла")
    mime=detect(data)
    if mime not in {"image/jpeg","image/png","image/webp"}: raise HTTPException(415,"Допустимы JPEG, PNG и WEBP")
    return mime
def validate_verification(data:bytes)->str:
    if not data or len(data)>MAX_VERIFY: raise HTTPException(413,"Недопустимый размер файла")
    mime=detect(data)
    if mime not in {"image/jpeg","image/png","image/webp","video/mp4"}: raise HTTPException(415,"Недопустимый формат верификации")
    return mime
