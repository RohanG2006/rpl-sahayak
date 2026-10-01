"""Base seed: roles + demo accounts. All demo accounts are SYNTHETIC (data_origin='synthetic').
Demo password for every seeded account: DEMO_PASSWORD below (prototype only; documented in README)."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import Role, User

DEMO_PASSWORD = "demo1234"

ROLES = [("worker", "Worker / Candidate"), ("assessor", "Assessor"), ("admin", "Administrator")]

# Synthetic assessor personas A01–A05 (names invented)
ASSESSORS = [
    ("A01", "assessor1@demo.rpl", "Meera Iyer (A01)"),
    ("A02", "assessor2@demo.rpl", "Harpreet Gill (A02)"),
    ("A03", "assessor3@demo.rpl", "Suresh Nair (A03)"),
    ("A04", "assessor4@demo.rpl", "Farah Siddiqui (A04)"),
    ("A05", "assessor5@demo.rpl", "Anil Deshmukh (A05)"),
]


def seed_roles_and_staff(db: Session) -> dict[str, User]:
    for code, label in ROLES:
        if not db.get(Role, code):
            db.add(Role(code=code, label=label))
    db.flush()
    pw = hash_password(DEMO_PASSWORD)
    out: dict[str, User] = {}

    def upsert(login: str, role: str, name: str, assessor_code: str | None = None) -> User:
        u = db.scalar(select(User).where(User.login == login))
        if not u:
            u = User(login=login, password_hash=pw, role_code=role, full_name=name,
                     assessor_code=assessor_code, data_origin="synthetic")
            db.add(u)
        return u

    out["admin"] = upsert("admin@demo.rpl", "admin", "Demo Administrator")
    for code, login, name in ASSESSORS:
        out[code] = upsert(login, "assessor", name, code)
    db.flush()
    return out
