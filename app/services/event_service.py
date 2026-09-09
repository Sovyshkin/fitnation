import logging
from dataclasses import dataclass
from time import perf_counter

from app.config import Settings
from app.schemas.events import EventRequest, EventType
from app.services.email_service import EmailService
from app.services.template_service import TemplateService
from app.utils.logger import mask_email


logger = logging.getLogger(__name__)


class EventDataError(ValueError):
    pass


@dataclass(frozen=True)
class EventDefinition:
    subject: str
    template_name: str
    required_fields: tuple[str, ...] = ()


EVENT_DEFINITIONS: dict[EventType, EventDefinition] = {
    EventType.WELCOME_DAY1: EventDefinition("Добро пожаловать в FITNATION!", "welcome_day1.html"),
    EventType.BONUS_DAY15: EventDefinition("Ваш бонус от FITNATION", "bonus_day15.html"),
    EventType.SUBSCRIPTION_4DAYS_BEFORE: EventDefinition("До следующего платежа осталось 4 дня", "subscription_4days_before.html", ("next_payment_date",)),
    EventType.MEMBERSHIP_4DAYS_BEFORE: EventDefinition("Абонемент закончится через 4 дня", "membership_4days_before.html", ("membership_end_date",)),
    EventType.SUBSCRIPTION_1DAY_BEFORE: EventDefinition("Следующий платеж уже завтра", "subscription_1day_before.html", ("next_payment_date",)),
    EventType.SUBSCRIPTION_OVERDUE_DAY1: EventDefinition("Не удалось провести платеж", "subscription_overdue_day1.html"),
    EventType.MEMBERSHIP_EXPIRED_DAY1: EventDefinition("Срок абонемента завершился", "membership_expired_day1.html", ("membership_end_date",)),
    EventType.SUBSCRIPTION_OVERDUE_NEXT_DAY: EventDefinition("Напоминание о платеже", "subscription_overdue_next_day.html"),
    EventType.SUBSCRIPTION_OVERDUE_DAY5: EventDefinition("Платеж ожидает уже 5 дней", "subscription_overdue_day5.html"),
    EventType.MEMBERSHIP_EXPIRED_DAY5: EventDefinition("Вернитесь в FITNATION", "membership_expired_day5.html"),
    EventType.SUBSCRIPTION_OVERDUE_DAY10: EventDefinition("Важно: платеж просрочен", "subscription_overdue_day10.html"),
    EventType.MEMBERSHIP_EXPIRED_DAY10: EventDefinition("Мы скучаем по вам", "membership_expired_day10.html"),
}


class EventService:
    def __init__(self, settings: Settings, template_service: TemplateService, email_service: EmailService) -> None:
        self._settings = settings
        self._templates = template_service
        self._email = email_service

    def process(self, request: EventRequest) -> None:
        started_at = perf_counter()
        recipient = str(request.recipient.email)
        masked_recipient = mask_email(recipient)
        logger.info("event_received event=%s recipient=%s", request.event.value, masked_recipient)

        definition = EVENT_DEFINITIONS[request.event]
        supplied_data = request.data.model_dump(exclude_none=True, mode="json")
        missing = [field for field in definition.required_fields if not supplied_data.get(field)]
        if missing:
            logger.warning(
                "event_rejected event=%s recipient=%s missing_fields=%s duration_ms=%.1f",
                request.event.value,
                masked_recipient,
                ",".join(missing),
                (perf_counter() - started_at) * 1000,
            )
            raise EventDataError(f"Missing required data fields: {', '.join(missing)}")

        context = {
            "recipient_name": request.recipient.name,
            "club_name": supplied_data.get("club_name", "FITNATION"),
            "support_url": supplied_data.get("support_url", str(self._settings.support_url)),
            "tariff_name": supplied_data.get("tariff_name", ""),
            "payment_amount": supplied_data.get("payment_amount", ""),
            "next_payment_date": supplied_data.get("next_payment_date", ""),
            "membership_end_date": supplied_data.get("membership_end_date", ""),
        }
        try:
            html_body = self._templates.render(definition.template_name, context)
            text_body = self._plain_text(request.event, context)
            self._email.send(
                recipient=recipient,
                subject=definition.subject,
                html_body=html_body,
                text_body=text_body,
            )
        except Exception:
            logger.exception(
                "event_failed event=%s recipient=%s duration_ms=%.1f",
                request.event.value,
                masked_recipient,
                (perf_counter() - started_at) * 1000,
            )
            raise
        logger.info(
            "event_sent event=%s recipient=%s duration_ms=%.1f",
            request.event.value,
            masked_recipient,
            (perf_counter() - started_at) * 1000,
        )

    @staticmethod
    def _plain_text(event: EventType, context: dict[str, str]) -> str:
        if event is EventType.WELCOME_DAY1:
            return (
                f"{context['recipient_name']}, отлично, что Вы с нами! Теперь Вы стали частью FITNATION.\n\n"
                "Ваш Welcome Pack: 500 баллов, 1 вводная персональная тренировка, "
                "замок для шкафчика и 1 напиток на выбор.\n\n"
                f"Поддержка: {context['support_url']}"
            )
        return (
            f"{context['recipient_name']}, для Вас новое уведомление от {context['club_name']}.\n\n"
            f"Поддержка: {context['support_url']}"
        )
