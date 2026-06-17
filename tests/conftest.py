import pytest
import os


@pytest.fixture(scope="session", autouse=True)
def clean_db():
    """Remove the database file before test session starts so each session is fresh."""
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data.db")
    for _ in range(3):
        try:
            if os.path.exists(db_path):
                os.remove(db_path)
            break
        except PermissionError:
            import time
            time.sleep(1)
    yield
