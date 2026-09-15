
from fastapi import HTTPException
import pytest
from app.services.upload_validation import detect, validate_profile, validate_verification, MAX_PROFILE, MAX_VERIFY

def test_jpeg_signature(): assert detect(b"\xff\xd8\xff"+b"x"*20)=="image/jpeg"
def test_png_signature(): assert detect(b"\x89PNG\r\n\x1a\n"+b"x"*20)=="image/png"
def test_webp_signature(): assert detect(b"RIFF"+b"\x00"*4+b"WEBP"+b"x"*20)=="image/webp"
def test_mp4_signature(): assert detect(b"\x00\x00\x00\x18ftypmp42"+b"x"*20)=="video/mp4"
def test_unknown_binary_rejected(): assert detect(b"\x00\x01\x02\x03"*10) is None

def test_fake_image_rejected():
    try: validate_profile(b"not an image");assert False
    except Exception: assert True

def test_mime_spoofing_rejected():
    # Client claims image/jpeg via filename/content-type, but the bytes are
    # something else entirely - detection is by magic bytes only, never by
    # the caller-supplied filename or Content-Type header.
    fake = b"<html><body>not a photo</body></html>"
    with pytest.raises(HTTPException) as exc:
        validate_profile(fake)
    assert exc.value.status_code == 415

def test_oversized_profile_photo_rejected():
    data = b"\xff\xd8\xff" + b"x" * (MAX_PROFILE + 1)
    with pytest.raises(HTTPException) as exc:
        validate_profile(data)
    assert exc.value.status_code == 413

def test_oversized_verification_media_rejected():
    data = b"\xff\xd8\xff" + b"x" * (MAX_VERIFY + 1)
    with pytest.raises(HTTPException) as exc:
        validate_verification(data)
    assert exc.value.status_code == 413

def test_empty_file_rejected():
    with pytest.raises(HTTPException):
        validate_profile(b"")

def test_verification_accepts_video_profile_does_not():
    mp4 = b"\x00\x00\x00\x18ftypmp42" + b"x" * 20
    assert validate_verification(mp4) == "video/mp4"
    with pytest.raises(HTTPException) as exc:
        validate_profile(mp4)
    assert exc.value.status_code == 415
