from pathlib import Path

from app.schemas.events import EventType
from app.services.delivery_store import EventDeliveryStore


def store(tmp_path: Path) -> EventDeliveryStore:
    return EventDeliveryStore(tmp_path / "deliveries.sqlite3", processing_ttl_seconds=60)


def test_sent_event_is_not_claimed_twice(tmp_path: Path) -> None:
    deliveries = store(tmp_path)

    assert deliveries.claim("1c:welcome:42", EventType.WELCOME_DAY1, "client@example.com").status == "claimed"
    deliveries.mark_sent("1c:welcome:42")

    assert deliveries.claim("1c:welcome:42", EventType.WELCOME_DAY1, "client@example.com").status == "duplicate"


def test_event_id_cannot_be_reused_for_another_recipient(tmp_path: Path) -> None:
    deliveries = store(tmp_path)

    deliveries.claim("1c:welcome:42", EventType.WELCOME_DAY1, "client@example.com")

    assert deliveries.claim("1c:welcome:42", EventType.WELCOME_DAY1, "other@example.com").status == "conflict"


def test_failed_event_can_be_claimed_again(tmp_path: Path) -> None:
    deliveries = store(tmp_path)

    deliveries.claim("1c:welcome:42", EventType.WELCOME_DAY1, "client@example.com")
    deliveries.mark_failed("1c:welcome:42")

    assert deliveries.claim("1c:welcome:42", EventType.WELCOME_DAY1, "client@example.com").status == "claimed"
