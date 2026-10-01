from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import get_settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=10)).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


def create_access_token(user_id: str, role: str) -> tuple[str, datetime]:
    s = get_settings()
    exp = datetime.now(timezone.utc) + timedelta(minutes=s.jwt_expiry_minutes)
    token = jwt.encode({"sub": user_id, "role": role, "exp": exp}, s.jwt_secret, algorithm=s.jwt_algorithm)
    return token, exp


def decode_token(token: str) -> dict:
    s = get_settings()
    return jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm])
