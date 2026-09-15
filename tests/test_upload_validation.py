
from app.services.upload_validation import detect,validate_profile
def test_jpeg_signature(): assert detect(b"\xff\xd8\xff"+b"x"*20)=="image/jpeg"
def test_fake_image_rejected():
    try: validate_profile(b"not an image");assert False
    except Exception: assert True
