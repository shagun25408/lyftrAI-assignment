import os
os.environ.setdefault("LLM_API_KEYS", "test-key-one,test-key-two")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test-app.db")
os.environ.setdefault("ENABLE_FAILURE_SIMULATION", "true")
