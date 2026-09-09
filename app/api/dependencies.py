from functools import lru_cache

from app.config import BASE_DIR, get_settings
from app.services.email_service import EmailService
from app.services.event_service import EventService
from app.services.template_service import TemplateService


@lru_cache
def get_event_service() -> EventService:
    settings = get_settings()
    return EventService(
        settings=settings,
        template_service=TemplateService(BASE_DIR / "app" / "templates" / "emails"),
        email_service=EmailService(settings),
    )

