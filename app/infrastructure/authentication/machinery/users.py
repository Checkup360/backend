import uuid

from fastapi_users import FastAPIUsers

from app.infrastructure.authentication.machinery.backend import auth_backend
from app.infrastructure.authentication.manager import get_user_manager
from app.infrastructure.persistence.models import User

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

current_active_user = fastapi_users.current_user(active=True)
