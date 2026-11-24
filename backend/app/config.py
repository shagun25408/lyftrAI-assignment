from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=Path(__file__).resolve().parents[2] / ".env", extra="ignore")
    llm_api_keys: str = ""
    llm_model: str = "gpt-4o-mini"
    database_url: str = "sqlite:///./app.db"
    allowed_origins: str = "http://localhost:3000"
    enable_failure_simulation: bool = False
    cache_enabled: bool = True

    @property
    def api_keys(self) -> list[str]:
        return [key.strip() for key in self.llm_api_keys.split(",") if key.strip()]

@lru_cache
def get_settings() -> Settings:
    return Settings()
