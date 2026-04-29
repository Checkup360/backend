import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    database_url: str
    google_client_id: str
    google_client_secret: str
    auth_secret: str


def _require_env(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_dotenv()
    return Settings(
        database_url=_require_env("DATABASE_URL"),
        google_client_id=_require_env("GOOGLE_CLIENT_ID"),
        google_client_secret=_require_env("GOOGLE_CLIENT_SECRET"),
        auth_secret=_require_env("AUTH_SECRET"),
    )


settings = get_settings()
