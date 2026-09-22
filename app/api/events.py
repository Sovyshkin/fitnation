from fastapi import APIRouter, Depends, HTTPException, status
from starlette.concurrency import run_in_threadpool

from app.api.dependencies import get_event_delivery_store, get_event_service
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
    if request.event_id is not None:
        delivery_store = get_event_delivery_store()
        claim = await run_in_threadpool(
            delivery_store.claim, request.event_id, request.event, str(request.recipient.email)
        )
        if claim.status == "duplicate":
            return EventSentResponse(status="duplicate", event=request.event, recipient=request.recipient.email)
        if claim.status == "conflict":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="event_id belongs to another event")
        if claim.status == "in_progress":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="event is already processing")
        try:
            await run_in_threadpool(service.process, request)
        except Exception:
            await run_in_threadpool(delivery_store.mark_failed, request.event_id)
            raise
        await run_in_threadpool(delivery_store.mark_sent, request.event_id)
    else:
        await run_in_threadpool(service.process, request)
    return EventSentResponse(status="sent", event=request.event, recipient=request.recipient.email)
