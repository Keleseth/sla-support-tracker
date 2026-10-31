"""Фикстуры интеграционных тестов: соединение с реальной базой, изменения откатываются."""

from collections.abc import Iterator
from typing import Any

import psycopg
import pytest
from pydantic import ValidationError

from sla_support_tracker.database import get_connection


@pytest.fixture
def connection() -> Iterator[psycopg.Connection[dict[str, Any]]]:
    try:
        opened_connection = get_connection()
    except (psycopg.OperationalError, ValidationError):
        pytest.skip('PostgreSQL недоступен: поднимите контейнеры и создайте файл .env')
    with opened_connection:
        yield opened_connection
        opened_connection.rollback()
