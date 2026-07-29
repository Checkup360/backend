import pytest

from app.infrastructure.config.settings import (
    _default_cors_origins_csv,
    _normalize_origin,
    _parse_csv_env,
    _require_env,
)


def test_require_env_success(monkeypatch):
    monkeypatch.setenv("TEST_KEY", "test_val")
    assert _require_env("TEST_KEY") == "test_val"


def test_require_env_missing_raises_runtime_error(monkeypatch):
    monkeypatch.delenv("NON_EXISTENT_KEY", raising=False)
    with pytest.raises(
        RuntimeError, match="Missing required environment variable: NON_EXISTENT_KEY"
    ):
        _require_env("NON_EXISTENT_KEY")


def test_parse_csv_env_custom_and_default(monkeypatch):
    monkeypatch.setenv("CSV_KEY", "  a.com , b.com , c.com  ")
    assert _parse_csv_env("CSV_KEY", "default.com") == ["a.com", "b.com", "c.com"]

    monkeypatch.delenv("CSV_KEY", raising=False)
    assert _parse_csv_env("CSV_KEY", "default1.com, default2.com") == [
        "default1.com",
        "default2.com",
    ]


def test_normalize_origin():
    assert _normalize_origin("https://app.example.com/") == "https://app.example.com"
    assert _normalize_origin("https://app.example.com") == "https://app.example.com"


def test_default_cors_origins_csv():
    assert (
        _default_cors_origins_csv("http://localhost:5173")
        == "http://localhost:5173,http://localhost:5174,http://localhost:5175"
    )
    assert (
        _default_cors_origins_csv("http://127.0.0.1:3000")
        == "http://localhost:5173,http://localhost:5174,http://localhost:5175"
    )
    assert (
        _default_cors_origins_csv("https://app.checkup360.com")
        == "https://app.checkup360.com"
    )
