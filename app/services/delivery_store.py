import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.schemas.events import EventType


@dataclass(frozen=True)
class DeliveryClaim:
    status: str


class EventDeliveryStore:
    """Durable idempotency ledger for events received from 1C."""

    def __init__(self, path: Path, processing_ttl_seconds: int) -> None:
        self._path = path
        self._processing_ttl_seconds = processing_ttl_seconds
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS event_deliveries (
                    event_id TEXT PRIMARY KEY,
                    event TEXT NOT NULL,
                    recipient TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status IN ('processing', 'sent', 'failed')),
                    updated_at TEXT NOT NULL
                )
                """
            )

    def claim(self, event_id: str, event: EventType, recipient: str) -> DeliveryClaim:
        now = datetime.now(UTC)
        stale_before = (now - timedelta(seconds=self._processing_ttl_seconds)).isoformat()
        now_value = now.isoformat()

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT event, recipient, status, updated_at FROM event_deliveries WHERE event_id = ?",
                (event_id,),
            ).fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO event_deliveries (event_id, event, recipient, status, updated_at) VALUES (?, ?, ?, 'processing', ?)",
                    (event_id, event.value, recipient, now_value),
                )
                return DeliveryClaim("claimed")

            stored_event, stored_recipient, state, updated_at = row
            if stored_event != event.value or stored_recipient != recipient:
                return DeliveryClaim("conflict")
            if state == "sent":
                return DeliveryClaim("duplicate")
            if state == "processing" and updated_at >= stale_before:
                return DeliveryClaim("in_progress")

            connection.execute(
                "UPDATE event_deliveries SET status = 'processing', updated_at = ? WHERE event_id = ?",
                (now_value, event_id),
            )
            return DeliveryClaim("claimed")

    def mark_sent(self, event_id: str) -> None:
        self._set_status(event_id, "sent")

    def mark_failed(self, event_id: str) -> None:
        self._set_status(event_id, "failed")

    def _set_status(self, event_id: str, state: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE event_deliveries SET status = ?, updated_at = ? WHERE event_id = ?",
                (state, datetime.now(UTC).isoformat(), event_id),
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path, timeout=10, isolation_level=None)
