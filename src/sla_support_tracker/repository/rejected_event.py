"""Доступ к журналу отклонённых событий: источник ошибок приёма для data_issues.csv."""

from typing import Any

import psycopg

from sla_support_tracker.schemas import RejectedEventSchema


class RejectedEventRepository:
    """Репозиторий таблицы rejected_events."""

    def __init__(self, connection: psycopg.Connection[dict[str, Any]]) -> None:
        self._connection = connection

    def get_all(self) -> list[RejectedEventSchema]:
        """Все записи журнала в порядке их появления."""
        rows = self._connection.execute(
            """
            SELECT event_id, conversation_id, issue_code, description
            FROM rejected_events
            ORDER BY id
            """
        ).fetchall()
        return [RejectedEventSchema.model_validate(row) for row in rows]
