"""Доступ к таблице валидных событий: выборка событий не позже as_of."""

from datetime import datetime
from typing import Any

import psycopg

from sla_support_tracker.schemas import EventSchema


class EventRepository:
    """Репозитрий таблицы events."""

    def __init__(self, connection: psycopg.Connection[dict[str, Any]]) -> None:
        self._connection = connection

    def get_events_up_to(self, as_of: datetime) -> list[EventSchema]:
        """События не позже as_of: по возрастанию времени, при равных моментах по event_id."""
        rows = self._connection.execute(
            """
            SELECT event_id, conversation_id, channel, chat_id, lead_id, occurred_at,
                   direction, author_id, author_type, message_type, text
            FROM events
            WHERE occurred_at <= %s
            ORDER BY occurred_at, event_id
            """,
            (as_of,),
        ).fetchall()
        return [EventSchema.model_validate(row) for row in rows]
