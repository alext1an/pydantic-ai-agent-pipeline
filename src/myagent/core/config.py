# src/pydantic_ai_agent_pipeline/core/config.py
from functools import lru_cache

import myagent.core.telemetry
        
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings for the Pydantic AI Agent Pipeline."""

    DEFAULT_LLM_MODEL: str = "deepseek/deepseek-v4-flash-0731"
    API_KEY: SecretStr
    BASE_URL: str
    PHOENIX_COLLECTOR_ENDPOINT: str = ""

    # Pydantic Settings
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings() # type: ignore

settings = get_settings()
myagent.core.telemetry.init_telemetry(endpoint=settings.PHOENIX_COLLECTOR_ENDPOINT)
