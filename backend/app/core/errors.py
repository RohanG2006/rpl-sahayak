"""Typed application errors -> safe JSON. Never return stack traces to clients."""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("rpl")


class AppError(Exception):
    status = 400
    code = "bad_request"

    def __init__(self, message: str, *, code: str | None = None, status: int | None = None, details: dict | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        if status:
            self.status = status
        self.details = details or {}


class NotFound(AppError):
    status, code = 404, "not_found"


class Forbidden(AppError):
    status, code = 403, "forbidden"


class Unauthorized(AppError):
    status, code = 401, "unauthorized"


class Conflict(AppError):
    status, code = 409, "conflict"


class InvalidState(AppError):
    status, code = 409, "invalid_workflow_state"


class AIUnavailable(AppError):
    status, code = 503, "ai_unavailable"


def _body(code: str, message: str, details: dict | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or {}}}


def install_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        return JSONResponse(_body(exc.code, exc.message, exc.details), status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        fields = [{"loc": [str(p) for p in e["loc"]], "msg": e["msg"]} for e in exc.errors()]
        return JSONResponse(_body("validation_error", "Some fields are invalid.", {"fields": fields}), status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        code = {401: "unauthorized", 403: "forbidden", 404: "not_found", 413: "payload_too_large", 429: "rate_limited"}.get(
            exc.status_code, "http_error"
        )
        return JSONResponse(_body(code, str(exc.detail)), status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        log.exception("Unhandled error: %s", type(exc).__name__)
        return JSONResponse(_body("internal_error", "Something went wrong. Please try again."), status_code=500)
