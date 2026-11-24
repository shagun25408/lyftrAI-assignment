import os
import pytest
os.environ.setdefault("LLM_API_KEYS", "test-key-one,test-key-two")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test-app.db")
os.environ.setdefault("ENABLE_FAILURE_SIMULATION", "true")

@pytest.fixture(autouse=True)
def reset_database():
    from app.database import Base, engine
    from app import models  # noqa: F401
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
