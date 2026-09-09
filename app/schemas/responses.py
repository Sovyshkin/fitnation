from typing import Literal

from pydantic import BaseModel, EmailStr

from app.schemas.events import EventType


class HealthResponse(BaseModel):
    status: Literal["healthy"]


class RootResponse(BaseModel):
    service: str
    status: Literal["ok"]
    version: str


class EventSentResponse(BaseModel):
    status: Literal["sent"]
    event: EventType
    recipient: EmailStr


class ErrorResponse(BaseModel):
    status: Literal["error"] = "error"
    code: str
    message: str

