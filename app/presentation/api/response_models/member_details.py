from pydantic import BaseModel


class MemberDetailsCreated(BaseModel):
    ok: bool = True
