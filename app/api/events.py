from fastapi import APIRouter, Depends
from starlette.concurrency import run_in_threadpool

from app.api.dependencies import get_event_service
from app.schemas.events import EventRequest
from app.schemas.responses import EventSentResponse
from app.services.event_service import EventService
from app.utils.security import verify_api_key


router = APIRouter(prefix="/api/v1", tags=["events"])


@router.post("/events", response_model=EventSentResponse, dependencies=[Depends(verify_api_key)])
async def receive_event(
    request: EventRequest,
    service: EventService = Depends(get_event_service),
) -> EventSentResponse:
    await run_in_threadpool(service.process, request)
    return EventSentResponse(status="sent", event=request.event, recipient=request.recipient.email)

