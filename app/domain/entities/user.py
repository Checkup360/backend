import uuid

from pydantic import BaseModel


class User(BaseModel):
    id: uuid.UUID
    email: str
    is_superuser: bool = False
    is_active: bool = True
