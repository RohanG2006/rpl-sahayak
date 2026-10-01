import secrets

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.ai.service import ADVISORY, AIService, get_ai_service
from app.api.deps import ensure_worker_access, get_current_user
from app.core.config import get_settings
from app.core.errors import Conflict, Forbidden, NotFound
from app.core.ratelimit import limiter
from app.core.security import create_access_token, hash_password
from app.db.session import get_db
from app.models import AIObservation, User, WorkerExperience, WorkerProfile, WorkerSkill
from app.schemas.workers import ExperienceIn, ExperienceOut, SkillsConfirmIn, WorkerCreate, WorkerOut, WorkerUpdate
from app.services import audit, workflow

router = APIRouter(prefix="/workers", tags=["workers"])

PROFILE_REQUIRED = ("full_name", "age", "state", "district", "occupation", "years_experience", "education_level")


def optional_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> User | None:
    if not authorization:
        return None
    return get_current_user(authorization, db)


def load_worker(db: Session, worker_id: str, user: User) -> WorkerProfile:
    w = db.get(WorkerProfile, worker_id)
    if not w:
        raise NotFound("Worker not found.")
    ensure_worker_access(user, w)
    return w


def worker_out(w: WorkerProfile, viewer: User) -> WorkerOut:
    out = WorkerOut.model_validate(w, from_attributes=True)
    out.ncvet_stage = workflow.NCVET_STAGE.get(w.status, "")
    if w.mobile and viewer.id != w.user_id:
        out.mobile = "XXXXXX" + w.mobile[-4:]
    return out


def _maybe_profile_complete(db: Session, w: WorkerProfile, actor: User | None) -> None:
    if all(getattr(w, f) not in (None, "") for f in PROFILE_REQUIRED):
        workflow.advance_worker(db, w, "PROFILE_COMPLETE", actor)


class WorkerCreated(BaseModel):
    worker: WorkerOut
    access_token: str | None = None


@router.post("", response_model=WorkerCreated, status_code=201)
@limiter.limit("20/minute")
def create_worker(request: Request, body: WorkerCreate, db: Session = Depends(get_db), user: User | None = Depends(optional_user)):
    """Self-registration (no token: `mobile` + `pin` required) or enrolment by an assessor/admin on the worker's behalf."""
    if user and user.role_code == "worker":
        raise Conflict("You already have a worker profile.")
    if user is None and (not body.mobile or not body.pin):
        raise Forbidden("Mobile number and PIN are required to register.", code="validation_error")
    login = body.mobile or f"w-{secrets.token_hex(4)}"
    if db.scalar(select(User).where(User.login == login)):
        raise Conflict("This mobile number is already registered. Please sign in.")
    u = User(login=login, password_hash=hash_password(body.pin or secrets.token_urlsafe(16)), role_code="worker",
             full_name=body.full_name, preferred_language=body.preferred_language)
    db.add(u)
    db.flush()
    w = WorkerProfile(user_id=u.id, **body.model_dump(exclude={"pin"}))
    db.add(w)
    db.flush()
    audit.record(db, "worker.created", "worker_profile", w.id, actor=user or u,
                 summary="Candidate profile created" + (" by staff" if user else " (self-registration)"))
    _maybe_profile_complete(db, w, user or u)
    db.commit()
    token = None if user else create_access_token(u.id, "worker")[0]
    return WorkerCreated(worker=worker_out(w, user or u), access_token=token)


@router.get("/{worker_id}", response_model=WorkerOut)
def get_worker(worker_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return worker_out(load_worker(db, worker_id, user), user)


@router.put("/{worker_id}", response_model=WorkerOut)
def update_worker(worker_id: str, body: WorkerUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    w = load_worker(db, worker_id, user)
    changes = body.model_dump(exclude_unset=True)
    before = {k: getattr(w, k) for k in changes}
    for k, v in changes.items():
        setattr(w, k, v)
    audit.record(db, "worker.updated", "worker_profile", w.id, actor=user, summary="Profile updated",
                 before=before, after=changes)
    _maybe_profile_complete(db, w, user)
    db.commit()
    return worker_out(w, user)


@router.post("/{worker_id}/experience", response_model=ExperienceOut, status_code=201)
def declare_experience(worker_id: str, body: ExperienceIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Append a new declaration version. Earlier versions are never modified (spec §8)."""
    w = load_worker(db, worker_id, user)
    version = (db.scalar(select(func.max(WorkerExperience.version)).where(WorkerExperience.worker_id == w.id)) or 0) + 1
    exp = WorkerExperience(worker_id=w.id, version=version, raw_text=body.raw_text.strip(),
                           input_mode=body.input_mode, language=body.language, data_origin=w.data_origin)
    db.add(exp)
    db.flush()
    # A new declaration after skills were extracted/confirmed sends the worker back to re-confirm them.
    beyond = workflow.WORKER_STATES.index(w.status) > workflow.WORKER_STATES.index("EXPERIENCE_DECLARED")
    workflow.advance_worker(db, w, "EXPERIENCE_DECLARED", user, reset=beyond)
    audit.record(db, "experience.declared", "worker_experience", exp.id, actor=user,
                 summary=f"Experience declaration v{version} ({body.input_mode}, {body.language})")
    db.commit()
    return exp


class ExtractIn(BaseModel):
    experience_id: str | None = None


class ExtractionOut(BaseModel):
    observation_id: str
    experience_id: str
    provider: str
    model: str | None
    fallback_used: bool
    advisory: str
    applied: bool = False
    extraction: dict


@router.post("/{worker_id}/extract-skills", response_model=ExtractionOut)
@limiter.limit(get_settings().rate_limit_ai)
def extract_skills(request: Request, worker_id: str, body: ExtractIn | None = None, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user), ai: AIService = Depends(get_ai_service)):
    """Run AI extraction on a declaration. Result is a SUGGESTION stored in ai_observations; worker skills are unchanged
    until the worker confirms them via PUT /workers/{id}/skills."""
    w = load_worker(db, worker_id, user)
    workflow.require_worker_at_least(w, "EXPERIENCE_DECLARED", "extract skills")
    stmt = select(WorkerExperience).where(WorkerExperience.worker_id == w.id)
    if body and body.experience_id:
        stmt = stmt.where(WorkerExperience.id == body.experience_id)
    exp = db.scalar(stmt.order_by(WorkerExperience.version.desc()))
    if not exp:
        raise NotFound("No experience declaration found.")
    profile = {k: getattr(w, k) for k in ("occupation", "years_experience", "tools", "current_employer", "education_level")}
    res = ai.extract_worker_skills(exp.raw_text, profile)
    obs = AIObservation(worker_id=w.id, kind="skill_extraction", provider=res.provider, model=res.model,
                        prompt_file=res.prompt_file, prompt_version=res.prompt_version,
                        output=res.data.model_dump(), confidence=res.confidence, valid=res.valid,
                        fallback_used=res.fallback_used, attempts=res.attempts, error=res.error, data_origin=w.data_origin)
    db.add(obs)
    db.flush()
    workflow.advance_worker(db, w, "SKILLS_EXTRACTED", user)
    audit.record(db, "ai.skill_extraction", "ai_observation", obs.id, actor=user,
                 summary=f"AI suggestion generated ({res.provider}{', fallback' if res.fallback_used else ''}); not applied")
    db.commit()
    return ExtractionOut(observation_id=obs.id, experience_id=exp.id, provider=res.provider, model=res.model,
                         fallback_used=res.fallback_used, advisory=ADVISORY, extraction=res.data.model_dump())


@router.put("/{worker_id}/skills", response_model=WorkerOut)
def confirm_skills(worker_id: str, body: SkillsConfirmIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Worker (or assessor on their behalf) confirms the edited skill list. Edits vs the AI suggestion are audited."""
    w = load_worker(db, worker_id, user)
    workflow.require_worker_at_least(w, "EXPERIENCE_DECLARED", "confirm skills")
    before = sorted(f"{s.kind}:{s.label}" for s in w.skills)
    db.execute(delete(WorkerSkill).where(WorkerSkill.worker_id == w.id))
    latest = db.scalar(select(WorkerExperience).where(WorkerExperience.worker_id == w.id).order_by(WorkerExperience.version.desc()))
    source_default = "assessor" if user.role_code in ("assessor", "admin") else "worker"
    for s in body.skills:
        db.add(WorkerSkill(worker_id=w.id, experience_id=latest.id if latest else None, kind=s.kind, label=s.label.strip(),
                           normalized_label=s.label.strip().lower(), source=s.source if s.source == "ai" else source_default,
                           confirmed=True, confidence=s.confidence, data_origin=w.data_origin))
    if body.occupation:
        w.occupation = body.occupation
    if body.years_experience is not None:
        w.years_experience = body.years_experience
    after = sorted(f"{s.kind}:{s.label.strip()}" for s in body.skills)
    edits = {}
    if body.ai_observation_id:
        obs = db.get(AIObservation, body.ai_observation_id)
        if obs and obs.worker_id == w.id:
            kinds = {"skills": "skill", "tools": "tool", "equipment": "equipment", "safety_practices": "safety", "learning_mode": "learning_mode"}
            suggested = {f"{kind}:{i['label']}" for key, kind in kinds.items() for i in obs.output.get(key, [])}
            edits = {"removed_ai_items": sorted(suggested - set(after)), "added_by_human": sorted(set(after) - suggested)}
    db.flush()
    db.refresh(w)
    workflow.advance_worker(db, w, "SKILLS_CONFIRMED", user)
    audit.record(db, "skills.confirmed", "worker_profile", w.id, actor=user,
                 summary=f"{len(body.skills)} items confirmed by {user.role_code}", before={"items": before},
                 after={"items": after, **edits})
    db.commit()
    db.refresh(w)
    return worker_out(w, user)
