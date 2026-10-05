import logging

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse

from app.api.routes import admin, assessments, auth, demo, evidence, outcomes, qualifications, sync, workers
from app.core.config import get_settings
from app.core.errors import install_handlers
from app.core.ratelimit import limiter

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

DESCRIPTION = """
**RPL-Sahayak AI** — AI-Assisted Prior Learning Assessment & Assessor Support Platform (SIH26242 prototype).

AI output from this API is advisory. *AI-assisted assessment recommendation — final decision by authorised human assessor.*
Official qualification data: National Qualifications Register (DGT/NCVET). Demo worker data is synthetic.
"""


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(title=s.app_name, version="0.1.0-prototype", description=DESCRIPTION)
    app.state.limiter = limiter

    @app.exception_handler(RateLimitExceeded)
    async def _rl(_, __):
        return JSONResponse({"error": {"code": "rate_limited", "message": "Too many requests. Please wait a moment.", "details": {}}}, status_code=429)

    install_handlers(app)
    app.add_middleware(
        CORSMiddleware, allow_origins=s.cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
        expose_headers=["Content-Disposition"],  # lets the browser read report/evidence file names
    )

    api = APIRouter(prefix="/api/v1")
    api.include_router(auth.router)
    api.include_router(qualifications.router)
    api.include_router(workers.router)
    api.include_router(assessments.router)
    api.include_router(evidence.router)
    api.include_router(outcomes.router)
    api.include_router(sync.router)
    api.include_router(admin.router)
    api.include_router(demo.router)

    @api.get("/health", tags=["meta"])
    def health():
        return {"status": "ok", "ai_provider": s.ai_provider, "environment": s.environment}

    app.include_router(api)
    return app


app = create_app()
