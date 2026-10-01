"""Audit trail. PII fields are redacted before storage (spec §34: no sensitive data in logs)."""
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog, User

PII_KEYS = {"mobile", "password", "password_hash", "full_name", "locality", "login", "email"}


def redact(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: ("[redacted]" if k in PII_KEYS else redact(v)) for k, v in data.items()}
    if isinstance(data, list):
        return [redact(v) for v in data]
    return data


def record(
    db: Session,
    action: str,
    entity: str,
    entity_id: str | None,
    *,
    actor: User | None = None,
    summary: str | None = None,
    before: dict | None = None,
    after: dict | None = None,
    via: str = "online",
) -> AuditLog:
    log = AuditLog(
        action=action,
        entity=entity,
        entity_id=entity_id,
        actor_id=actor.id if actor else None,
        actor_role=actor.role_code if actor else "system",
        summary=summary,
        before=redact(before) if before else None,
        after=redact(after) if after else None,
        via=via,
    )
    db.add(log)
    return log
