from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.presentation.middleware.proxy_prefix import ProxyPrefixMiddleware

CALLBACK_NAME = "oauth:google.jwt.callback"


def build_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(ProxyPrefixMiddleware)

    @app.get("/auth/google/authorize")
    async def authorize(request: Request):
        return {"redirect_uri": str(request.url_for(CALLBACK_NAME))}

    @app.get("/auth/google/callback", name=CALLBACK_NAME)
    async def callback():
        return {"ok": True}

    return app


class TestProxyPrefixMiddleware:
    def test_url_for_includes_forwarded_prefix(self):
        client = TestClient(build_app())

        response = client.get(
            "/auth/google/authorize",
            headers={
                "host": "checkup360.duckdns.org",
                "x-forwarded-prefix": "/api",
            },
        )

        assert (
            response.json()["redirect_uri"]
            == "http://checkup360.duckdns.org/api/auth/google/callback"
        )

    def test_url_for_without_prefix_is_unchanged(self):
        client = TestClient(build_app())

        response = client.get(
            "/auth/google/authorize",
            headers={"host": "api.checkup360.duckdns.org"},
        )

        assert (
            response.json()["redirect_uri"]
            == "http://api.checkup360.duckdns.org/auth/google/callback"
        )

    def test_prefix_is_normalized(self):
        client = TestClient(build_app())

        response = client.get(
            "/auth/google/authorize",
            headers={
                "host": "checkup360.duckdns.org",
                "x-forwarded-prefix": "/api/",
            },
        )

        assert (
            response.json()["redirect_uri"]
            == "http://checkup360.duckdns.org/api/auth/google/callback"
        )

    def test_routing_is_not_affected_by_prefix(self):
        client = TestClient(build_app())

        response = client.get(
            "/auth/google/callback",
            headers={"x-forwarded-prefix": "/api"},
        )

        assert response.status_code == 200
        assert response.json() == {"ok": True}
