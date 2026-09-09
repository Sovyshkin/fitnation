from fastapi import APIRouter, Depends, HTTPException
from starlette.concurrency import run_in_threadpool

from app.api.dependencies import get_event_service
from app.config import Settings, get_settings
from app.schemas.events import EventData, EventRequest, EventType, Recipient, TestEmailRequest
from app.schemas.responses import EventSentResponse
from app.services.event_service import EventService
from app.utils.security import verify_api_key


router = APIRouter(prefix="/api/v1", tags=["development"])


@router.post("/test-email", response_model=EventSentResponse, dependencies=[Depends(verify_api_key)])
async def send_test_email(
    request: TestEmailRequest,
    settings: Settings = Depends(get_settings),
    service: EventService = Depends(get_event_service),
) -> EventSentResponse:
    if settings.app_env != "development":
        raise HTTPException(status_code=404, detail="Not found")
    event = EventRequest(
        event=EventType.WELCOME_DAY1,
        recipient=Recipient(email=request.to, name="Друг"),
        data=EventData(),
    )
    await run_in_threadpool(service.process, event)
    return EventSentResponse(status="sent", event=event.event, recipient=event.recipient.email)

