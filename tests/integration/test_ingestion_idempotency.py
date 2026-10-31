"""Интеграционные проверки приёма событий на реальной бд: повторная доставка не создаёт строк."""

from typing import Any

import psycopg
from psycopg.types.json import Jsonb

CONVERSATION_ID = 'idempotency-test'


def make_event(item_index: int, event_id: str, text: str) -> dict[str, Any]:
    return {
        'item_index': item_index,
        'event_id': event_id,
        'conversation_id': CONVERSATION_ID,
        'channel': 'telegram',
        'chat_id': 'chat-idempotency',
        'lead_id': None,
        'occurred_at': '2026-09-07T10:00:00+03:00',
        'direction': 'inbound',
        'author_id': 'partner-idempotency',
        'author_type': 'partner',
        'message_type': 'text',
        'text': text,
    }


def insert_events(
    connection: psycopg.Connection[dict[str, Any]], events: list[dict[str, Any]]
) -> dict[str, Any]:
    row = connection.execute(
        'SELECT insert_events(%s, %s) AS result', (Jsonb(events), Jsonb([]))
    ).fetchone()
    assert row is not None
    result: dict[str, Any] = row['result']
    return result


def count_events(connection: psycopg.Connection[dict[str, Any]]) -> int:
    row = connection.execute(
        'SELECT count(*) AS total FROM events WHERE conversation_id = %s', (CONVERSATION_ID,)
    ).fetchone()
    assert row is not None
    return int(row['total'])


def test_repeated_package_creates_no_new_rows(
    connection: psycopg.Connection[dict[str, Any]],
) -> None:
    package = [make_event(0, 'idem-1', 'Первое'), make_event(1, 'idem-2', 'Второе')]

    first = insert_events(connection, package)
    second = insert_events(connection, package)

    assert (first['inserted'], first['duplicates']) == (2, 0)
    assert (second['inserted'], second['duplicates']) == (0, 2)
    assert count_events(connection) == 2


def test_same_event_id_with_other_data_keeps_the_first_version(
    connection: psycopg.Connection[dict[str, Any]],
) -> None:
    """Событие с тем же event_id, но другими данными отклоняется, первая версия не меняется."""
    insert_events(connection, [make_event(0, 'idem-3', 'Первая версия')])

    result = insert_events(connection, [make_event(0, 'idem-3', 'Вторая версия')])

    stored = connection.execute("SELECT text FROM events WHERE event_id = 'idem-3'").fetchone()
    assert result['inserted'] == 0
    assert [error['issue_code'] for error in result['errors']] == ['event_id_conflict']
    assert stored is not None
    assert stored['text'] == 'Первая версия'
