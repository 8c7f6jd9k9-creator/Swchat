from app.services.storage import safe_path
def test_traversal_rejected():
    try: safe_path("../../etc/passwd"); assert False
    except ValueError: assert True
