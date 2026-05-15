from httpx_oauth.clients.google import GoogleOAuth2

from app.core import settings

google_oauth_client = GoogleOAuth2(
    settings.google_client_id,
    settings.google_client_secret,
)
