from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.events import router as events_router
from app.api.health import router as health_router
from app.api.test_email import router as test_email_router
from app.config import get_settings
from app.schemas.responses import RootResponse
from app.services.email_service import EmailDeliveryError
from app.services.event_service import EventDataError
from app.services.template_service import TemplateServiceError
from app.utils.logger import configure_logging


settings = get_settings()
configure_logging(settings.log_level)

development = settings.app_env == "development"
app = FastAPI(
    title="FITNATION Notification Service",
    version="1.0.0",
    docs_url="/docs" if development else None,
    redoc_url="/redoc" if development else None,
    openapi_url="/openapi.json" if development else None,
)
app.include_router(health_router)
app.include_router(events_router)
app.include_router(test_email_router)


@app.get("/", response_model=RootResponse)
async def root() -> RootResponse:
    return RootResponse(service="FITNATION Notification Service", status="ok", version="1.0.0")


@app.exception_handler(EmailDeliveryError)
async def email_error_handler(_request: Request, exc: EmailDeliveryError) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content={"status": "error", "code": exc.code, "message": "Email delivery failed"},
    )


@app.exception_handler(EventDataError)
async def event_data_error_handler(_request: Request, exc: EventDataError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"status": "error", "code": "invalid_event_data", "message": str(exc)},
    )


@app.exception_handler(TemplateServiceError)
async def template_error_handler(_request: Request, _exc: TemplateServiceError) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"status": "error", "code": "template_error", "message": "Email template is unavailable"},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    unknown_event = any(
        error.get("loc", ())[-2:] == ("body", "event") and error.get("type") == "enum"
        for error in errors
    )
    if unknown_event:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "code": "unknown_event", "message": "Unknown event type"},
        )
    safe_errors = [
        {"loc": list(error.get("loc", ())), "msg": error["msg"], "type": error["type"]}
        for error in errors
    ]
    return JSONResponse(status_code=422, content={"detail": safe_errors})


@app.exception_handler(HTTPException)
async def http_error_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    content = exc.detail if isinstance(exc.detail, dict) else {"detail": exc.detail}
    return JSONResponse(status_code=exc.status_code, content=content, headers=exc.headers)
