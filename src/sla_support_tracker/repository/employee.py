"""Доступ к таблице справочника сотрудников."""

from typing import Any

import psycopg

from sla_support_tracker.schemas import EmployeeSchema


class EmployeeRepository:
    """Репозиторий таблицы employees."""

    def __init__(self, connection: psycopg.Connection[dict[str, Any]]) -> None:
        self._connection = connection

    def get_all(self) -> list[EmployeeSchema]:
        """Все сотрудники справочника."""
        rows = self._connection.execute(
            'SELECT author_id, full_name, department FROM employees'
        ).fetchall()
        return [EmployeeSchema.model_validate(row) for row in rows]
