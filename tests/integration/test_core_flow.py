
import os,pytest
pytestmark=pytest.mark.skipif(os.getenv("RUN_INTEGRATION")!="1",reason="requires staging services")
def test_staging_marker():
    # Real Telegram initData is intentionally not forged in tests.
    # This suite is activated in a controlled staging environment with test fixtures.
    assert os.getenv("DATABASE_URL")
    assert os.getenv("REDIS_URL")
