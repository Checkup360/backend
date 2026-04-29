from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from jwt import InvalidTokenError
from jwt import decode as jwt_decode

from app.core import settings
from app.routers import auth, organizations

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(organizations.router)
app.include_router(auth.router)

# TODO: Esto no debería estar aca
@app.middleware("http")
async def redirect_oauth_callback_204(request, call_next):
    response = await call_next(request)
    is_oauth_callback = request.url.path.startswith("/auth/") and request.url.path.endswith(
        "/callback"
    )
    if not is_oauth_callback or response.status_code != 204:
        return response

    redirect_url = settings.frontend_post_login_url
    state = request.query_params.get("state")
    if state:
        try:
            payload = jwt_decode(
                state,
                settings.auth_secret,
                algorithms=["HS256"],
                audience="fastapi-users:oauth-state",
            )
            maybe_redirect = payload.get("redirect_url")
            if isinstance(maybe_redirect, str) and maybe_redirect.strip():
                redirect_url = maybe_redirect.strip()
        except InvalidTokenError:
            pass

    response.status_code = 303
    response.headers["location"] = redirect_url
    return response


@app.get("/")
def root():
    return {"ok": True}

