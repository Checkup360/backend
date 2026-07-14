import asyncio
from urllib.parse import urlencode

from app.application.interfaces import EmailSender


class RequestPasswordReset:
    def __init__(self, email_sender: EmailSender, public_web_origin: str):
        self.email_sender = email_sender
        self.public_web_origin = public_web_origin.rstrip("/")

    async def execute(self, email: str, token: str) -> None:
        query = urlencode({"token": token})
        reset_url = f"{self.public_web_origin}/reset-password?{query}"
        await asyncio.to_thread(
            self.email_sender.send_password_reset_email,
            email,
            reset_url,
        )
