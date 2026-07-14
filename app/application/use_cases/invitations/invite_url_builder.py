from urllib.parse import quote


class InviteUrlBuilder:
    def __init__(self, public_web_origin: str):
        self.public_web_origin = public_web_origin.rstrip("/")

    def build(self, token: str) -> str:
        return f"{self.public_web_origin}/invite/{quote(token, safe='')}"
