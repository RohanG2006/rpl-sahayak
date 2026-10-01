from collections.abc import Callable

import jwt
from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.errors import Forbidden, Unauthorized
from app.core.security import decode_token
from app.db.session import get_db
from app.models import User, WorkerProfile


def get_current_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise Unauthorized("Please sign in.")
    try:
        claims = decode_token(authorization.split(" ", 1)[1])
    except jwt.ExpiredSignatureError:
        raise Unauthorized("Your session has expired. Please sign in again.", code="session_expired")
    except jwt.PyJWTError:
        raise Unauthorized("Invalid session.")
    user = db.get(User, claims.get("sub"))
    if not user or not user.is_active:
        raise Unauthorized("Account not found or inactive.")
    return user


def require_roles(*roles: str) -> Callable[[User], User]:
    def _dep(user: User = Depends(get_current_user)) -> User:
        if user.role_code not in roles:
            raise Forbidden(f"This action requires role: {', '.join(roles)}.")
        return user

    return _dep


def ensure_worker_access(user: User, worker: WorkerProfile) -> None:
    """Workers may only touch their own profile; assessors/admins may view any."""
    if user.role_code == "worker" and worker.user_id != user.id:
        raise Forbidden("You can only access your own profile.")
