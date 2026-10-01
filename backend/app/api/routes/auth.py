from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.errors import Unauthorized
from app.core.ratelimit import limiter
from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.models import User, WorkerProfile
from app.services import audit

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    login: str = Field(min_length=3, max_length=120, examples=["raj.demo"])
    password: str = Field(min_length=4, max_length=128, examples=["demo1234"])


class UserOut(BaseModel):
    id: str
    login: str
    full_name: str
    role: str
    preferred_language: str
    assessor_code: str | None = None
    worker_id: str | None = None
    data_origin: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: str
    user: UserOut


def user_out(db: Session, u: User) -> UserOut:
    wid = db.scalar(select(WorkerProfile.id).where(WorkerProfile.user_id == u.id)) if u.role_code == "worker" else None
    return UserOut(
        id=u.id, login=u.login, full_name=u.full_name, role=u.role_code, preferred_language=u.preferred_language,
        assessor_code=u.assessor_code, worker_id=wid, data_origin=u.data_origin,
    )


@router.post("/login", response_model=TokenOut)
@limiter.limit(get_settings().rate_limit_login)
def login(request: Request, body: LoginIn, db: Session = Depends(get_db)):
    u = db.scalar(select(User).where(User.login == body.login.strip().lower()))
    if not u or not u.is_active or not verify_password(body.password, u.password_hash):
        raise Unauthorized("Incorrect login or password.")
    token, exp = create_access_token(u.id, u.role_code)
    audit.record(db, "user.login", "user", u.id, actor=u, summary="Signed in")
    db.commit()
    return TokenOut(access_token=token, expires_at=exp.isoformat(), user=user_out(db, u))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return user_out(db, user)
