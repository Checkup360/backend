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
    cors_allowed_origins: list[str]
    frontend_post_login_url: str
    frontend_url: str


def _require_env(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return value


def _parse_csv_env(key: str, default: str) -> list[str]:
    raw_value = os.getenv(key, default)
    return [item.strip() for item in raw_value.split(",") if item.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_dotenv()
    return Settings(
        database_url=_require_env("DATABASE_URL"),
        google_client_id=_require_env("GOOGLE_CLIENT_ID"),
        google_client_secret=_require_env("GOOGLE_CLIENT_SECRET"),
        auth_secret=_require_env("AUTH_SECRET"),
        cors_allowed_origins=_parse_csv_env(
            "CORS_ALLOWED_ORIGINS",
            "http://localhost:5173,http://localhost:5174,http://localhost:5175",
        ),
        frontend_post_login_url=os.getenv(
            "FRONTEND_POST_LOGIN_URL", "http://localhost:5173/login/complete"
        ),
        frontend_url=os.getenv("FRONTEND_URL", "http://localhost:5173"),
    )


settings = get_settings()
