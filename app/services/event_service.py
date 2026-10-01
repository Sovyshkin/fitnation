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
    EventType.SUBSCRIPTION_4DAYS_BEFORE: EventDefinition("Автоматическое списание через 3 дня", "subscription_4days_before.html", ("next_payment_date",)),
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
        name = context["recipient_name"]
        support = f"ссылка на ТГ сервис: {context['support_url']}"
        messages = {
            EventType.WELCOME_DAY1: (
                f"{name}, отлично, что Вы с нами! Теперь Вы стали частью Fitnation.\n\n"
                "Воспользуйтесь Welcome Pack (приветственный пакет):\n"
                "• 500 баллов, которые Вы можете потратить в нашем Магазине (в мобильном приложении)\n"
                "• 1 вводная персональная тренировка (запись через администратора). Вводная персональная тренировка - это возможность познакомиться с оборудованием, техникой выполнения упражнений и чувствовать себя более уверенно в тренажерном зале!\n"
                "• Замок для шкафчика\n"
                "• 1 напиток на выбор (обратитесь к администратору)\n\n"
                "По любым вопросам обращайтесь в данный чат поддержки. С удовольствием поможем!\n"
                + support
            ),
            EventType.BONUS_DAY15: (
                f"{name}, добрый день! Это FITNATION!\n\n"
                "Надеемся, что Вы уже освоились в клубе и вовсю тренируетесь на пути к своей цели!\n\n"
                "А мы, для поддержания Вас, дарим дополнительно 200 баллов в мобильном приложении, которые можно потратить в разделе Магазин. Покажите данное сообщение администратору для начисления бонуса 🎁"
            ),
            EventType.SUBSCRIPTION_4DAYS_BEFORE: (
                f"{name}, добрый день! Это FITNATION!\n\n"
                "Напоминаем Вам, что по вашему контракту формата подписки, через 3 дня, произойдет автоматическое списание для продления посещений клуба.\n\n"
                f"Рады, что остаетесь с нами!\nЕсли возникнут вопросы, напишите нам {support}"
            ),
            EventType.MEMBERSHIP_4DAYS_BEFORE: (
                f"{name}, добрый день! Это FITNATION!\n\n"
                "Напоминаем Вам, что ваш абонемент подходит к завершению. Будем рады предложить новый абонемент или переход на тариф подписки. Уточните, какой вариант рассматриваете?\n\n"
                f"Рады, что остаетесь с нами!\nЕсли возникнут вопросы, напишите нам {support}"
            ),
            EventType.SUBSCRIPTION_1DAY_BEFORE: (
                f"{name}, добрый день! Это FITNATION!\n\n"
                "Напоминаем Вам, что завтра по вашему контракту формата подписки, произойдет автоматическое списание для продления посещений клуба."
            ),
            EventType.SUBSCRIPTION_OVERDUE_DAY1: (
                f"{name}, добрый день! Это FITNATION!\n\n"
                f"Заметили, что по Вашему контракту не прошла оплата. Если вам необходима помощь, напишите нам {support}"
            ),
            EventType.MEMBERSHIP_EXPIRED_DAY1: (
                f"{name}, добрый день! Это FITNATION!\n\n"
                f"Заметили, что Ваш абонемент закончился, готовы предложить лучшие условия, чтобы продолжить тренировки. Если вам необходима помощь, напишите нам {support}"
            ),
            EventType.SUBSCRIPTION_OVERDUE_NEXT_DAY: (
                f"{name}, добрый день! Это FITNATION!\n\n"
                f"Не получилось до Вас дозвониться, доступ в клуб ограничен. Если вам необходима помощь, напишите нам {support}"
            ),
            EventType.SUBSCRIPTION_OVERDUE_DAY5: (
                f"{name}, добрый день!\n\n"
                "Хотим подчеркнуть, что расторгнув контракт, Вы можете потерять свой выгодный тариф, а так же при оформлении нового абонемента потребуется повторно оплачивать вступительный взнос. "
                f"Оставайтесь с нами, для решения любых вопросов напишите нам {support}"
            ),
            EventType.MEMBERSHIP_EXPIRED_DAY5: (
                f"{name}, добрый день! Это FITNATION!\n\n"
                "Не удалось до Вас дозвониться. Срок действия Вашего абонемента подошел к концу и доступ в клуб органичен. Продолжайте тренировки на выгодных услових. "
                f"Подбробности у администратора, напишите нам {support}"
            ),
            EventType.SUBSCRIPTION_OVERDUE_DAY10: (
                f"{name}, добрый день! Это FITNATION!\n\n"
                "Вновь не дозвонились Вам. Еще есть возможность продлить Ваш контракт, оплатите сейчас, чтобы не переплачивать в будущем. "
                f"Обратитесь к администратору или напиши нам {support}"
            ),
            EventType.MEMBERSHIP_EXPIRED_DAY10: (
                f"{name}, добрый день!\n\n"
                "Ваш абонемент закончился, но у нас всегда есть \"второй шанс\". Выбирайте FITNATION - это больше, чем просто тренировки! "
                f"Напишите нам {support}"
            ),
        }
        return messages[event]
