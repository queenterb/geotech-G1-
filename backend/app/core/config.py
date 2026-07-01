from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./backend.db"
    REDIS_URL: str = "redis://localhost:6379"
    SECRET_KEY: str = "supersecret_local_change_me"
    SIEM_SHARED_SECRET: str = ""
    BACKEND_CORS_ORIGINS: str = "http://localhost:4173,http://localhost:8080"

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
