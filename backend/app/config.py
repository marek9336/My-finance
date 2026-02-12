import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    storage_backend: str = os.getenv("STORAGE_BACKEND", "memory").strip().lower()
    database_url: str = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/my_finance")
    default_user_id: str = os.getenv("APP_DEFAULT_USER_ID", "00000000-0000-0000-0000-000000000001")


settings = Settings()
