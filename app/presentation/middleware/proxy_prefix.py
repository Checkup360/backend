from starlette.types import ASGIApp, Receive, Scope, Send

FORWARDED_PREFIX_HEADER = b"x-forwarded-prefix"


def _read_forwarded_prefix(scope: Scope) -> str:
    for name, value in scope.get("headers", []):
        if name == FORWARDED_PREFIX_HEADER:
            prefix = value.decode("latin-1").strip().rstrip("/")
            if prefix and not prefix.startswith("/"):
                prefix = f"/{prefix}"
            return prefix
    return ""


class ProxyPrefixMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in ("http", "websocket"):
            prefix = _read_forwarded_prefix(scope)
            if prefix:
                scope["app_root_path"] = prefix
                if scope["path"].startswith(prefix):
                    scope["root_path"] = prefix
        await self.app(scope, receive, send)
