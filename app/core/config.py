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
    cookie_secure: bool
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str


def _require_env(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return value


def _parse_csv_env(key: str, default: str) -> list[str]:
    raw_value = os.getenv(key, default)
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def _normalize_origin(url: str) -> str:
    return url.rstrip("/")


def _default_cors_origins_csv(web_origin: str) -> str:
    if web_origin.startswith("http://localhost:") or web_origin.startswith(
        "http://127.0.0.1:"
    ):
        return "http://localhost:5173,http://localhost:5174,http://localhost:5175"
    return web_origin


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_dotenv()
    web_origin = _normalize_origin(
        os.getenv("PUBLIC_WEB_ORIGIN")
        or os.getenv("FRONTEND_URL")
        or "http://localhost:5173"
    )
    cors_allowed_origins = _parse_csv_env(
        "CORS_ALLOWED_ORIGINS",
        _default_cors_origins_csv(web_origin),
    )

    return Settings(
        database_url=_require_env("DATABASE_URL"),
        google_client_id=_require_env("GOOGLE_CLIENT_ID"),
        google_client_secret=_require_env("GOOGLE_CLIENT_SECRET"),
        auth_secret=_require_env("AUTH_SECRET"),
        cors_allowed_origins=cors_allowed_origins,
        frontend_post_login_url=f"{web_origin}/login/complete",
        frontend_url=web_origin,
        cookie_secure=os.getenv("AUTH_COOKIE_SECURE", "false").lower()
        in (
            "1",
            "true",
            "yes",
        ),
        smtp_host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
        smtp_port=int(os.getenv("SMTP_PORT", "587")),
        smtp_user=os.getenv("SMTP_USER", ""),
        smtp_password=os.getenv("SMTP_PASSWORD", ""),
    )


settings = get_settings()
