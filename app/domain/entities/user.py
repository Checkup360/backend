import uuid
from dataclasses import dataclass


@dataclass
class User:
    id: uuid.UUID
    email: str
    is_superuser: bool = False
    is_active: bool = True
