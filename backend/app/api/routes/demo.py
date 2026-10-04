"""DEMO MODE (spec §46). Enabled only when DEMO_MODE_ENABLED=true — disable in any real deployment.

Every endpoint here touches only SYNTHETIC records: the Raj Kumar persona and the synthetic demo staff accounts,
whose credentials are public in the README anyway.
"""
from typing import Literal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.routes.auth import user_out
from app.core.config import get_settings
from app.core.errors import NotFound
from app.core.ratelimit import limiter
from app.core.security import create_access_token
from app.db.session import get_db
from app.models import AssessmentPlan, User, WorkerProfile
from app.seed import demo

router = APIRouter(prefix="/demo", tags=["demo"])


def require_demo():
    if not get_settings().demo_mode_enabled:
        raise NotFound("Demo mode is disabled.")


class RajIn(BaseModel):
    checkpoint: Literal["fresh", "practical", "evidence_ready", "awaiting_decision"]


def _session(db: Session, user_id: str) -> dict:
    u = db.get(User, user_id)
    token, exp = create_access_token(u.id, u.role_code)
    return {"access_token": token, "expires_at": exp.isoformat(), "user": user_out(db, u).model_dump()}


@router.post("/raj", dependencies=[Depends(require_demo)])
@limiter.limit("10/minute")
def reset_raj(request: Request, body: RajIn, db: Session = Depends(get_db)):
    """Rebuild the synthetic Raj Kumar at a checkpoint and return ready sessions for him and his assessor (A01)."""
    r = demo.reset_raj(body.checkpoint)
    db.expire_all()
    return {**r, "label": "SYNTHETIC / DEMONSTRATION DATA — NOT REAL WORKER DATA",
            "worker_session": _session(db, r["worker_user_id"]), "assessor_session": _session(db, r["assessor_user_id"])}


@router.get("/status", dependencies=[Depends(require_demo)])
def status(db: Session = Depends(get_db)):
    synthetic = db.scalar(select(func.count()).select_from(WorkerProfile).where(WorkerProfile.data_origin == "synthetic")) or 0
    plans = db.scalar(select(func.count()).select_from(AssessmentPlan).where(AssessmentPlan.data_origin == "synthetic")) or 0
    raj = db.scalar(select(WorkerProfile).where(WorkerProfile.archetype.is_not(None), WorkerProfile.full_name == "Raj Kumar", WorkerProfile.data_origin == "synthetic"))
    rp = db.scalar(select(AssessmentPlan).where(AssessmentPlan.worker_id == raj.id)) if raj else None
    return {"enabled": True, "synthetic_workers": synthetic, "synthetic_assessments": plans,
            "raj": None if not raj else {"worker_status": raj.status, "plan_status": rp.status if rp else None},
            "evidence_pack": [{"upload_name": e["upload_name"], "criterion_code": e["criterion_code"], "caption": e["caption"],
                               "url": f"/demo/evidence/{e['upload_name']}"} for e in demo.demo_evidence_pack()],
            "checkpoints": list(demo.CHECKPOINTS)}


@router.get("/evidence/{upload_name}", dependencies=[Depends(require_demo)])
def evidence_file(upload_name: str):
    """Raj's placeholder image, served under the file name that has a prepared observation."""
    item = next((e for e in demo.demo_evidence_pack() if e["upload_name"] == upload_name), None)
    if not item:
        raise NotFound("Not part of the demo evidence pack.")
    return FileResponse(demo.evidence_path(item["base_image"]), media_type="image/png", filename=upload_name)
