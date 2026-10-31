"""Подключение к PostgreSQL через psycopg."""

from typing import Any

import psycopg
from psycopg.rows import dict_row

from sla_support_tracker.config import get_settings


def get_connection() -> psycopg.Connection[dict[str, Any]]:
    """Открывает соединение; строки результатов приходят словарями с именами колонок."""
    settings = get_settings()
    return psycopg.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        user=settings.postgres_user,
        password=settings.postgres_password,
        dbname=settings.postgres_db,
        connect_timeout=2,
        row_factory=dict_row,
    )
