"""Интеграционные проверки чтения событий из реальной базы."""

from datetime import UTC, datetime
from typing import Any

import psycopg

from sla_support_tracker.repository.event import EventRepository
from sla_support_tracker.schemas import EventSchema


def insert_event(
    connection: psycopg.Connection[dict[str, Any]],
    event_id: str,
    conversation_id: str,
    occurred_at: datetime,
) -> None:
    connection.execute(
        """
        INSERT INTO events (event_id, conversation_id, channel, chat_id, lead_id, occurred_at,
                            direction, author_id, author_type, message_type, text)
        VALUES (%s, %s, 'telegram', 'chat-test', NULL, %s, 'inbound', NULL, 'partner', 'text', NULL)
        """,
        (event_id, conversation_id, occurred_at),
    )


def moment(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 9, 7, hour, minute, tzinfo=UTC)


def event_ids_of(events: list[EventSchema], conversation_id: str) -> list[str]:
    return [event.event_id for event in events if event.conversation_id == conversation_id]


def test_returns_events_sorted_by_time(connection: psycopg.Connection[dict[str, Any]]) -> None:
    insert_event(connection, 'repo-a-2', 'repo-test-a', moment(11))
    insert_event(connection, 'repo-a-1', 'repo-test-a', moment(10))

    result = EventRepository(connection).get_events_up_to(moment(23))

    assert event_ids_of(result, 'repo-test-a') == ['repo-a-1', 'repo-a-2']


def test_breaks_ties_by_event_id(connection: psycopg.Connection[dict[str, Any]]) -> None:
    insert_event(connection, 'repo-b-2', 'repo-test-b', moment(10))
    insert_event(connection, 'repo-b-1', 'repo-test-b', moment(10))

    result = EventRepository(connection).get_events_up_to(moment(23))

    assert event_ids_of(result, 'repo-test-b') == ['repo-b-1', 'repo-b-2']


def test_ignores_events_after_as_of(connection: psycopg.Connection[dict[str, Any]]) -> None:
    insert_event(connection, 'repo-c-1', 'repo-test-c', moment(10))
    insert_event(connection, 'repo-c-2', 'repo-test-c', moment(11))

    result = EventRepository(connection).get_events_up_to(moment(10, 30))

    assert event_ids_of(result, 'repo-test-c') == ['repo-c-1']


def test_includes_event_exactly_at_as_of(connection: psycopg.Connection[dict[str, Any]]) -> None:
    insert_event(connection, 'repo-d-1', 'repo-test-d', moment(10))

    result = EventRepository(connection).get_events_up_to(moment(10))

    assert event_ids_of(result, 'repo-test-d') == ['repo-d-1']


def test_conversation_without_events_before_as_of_is_absent(
    connection: psycopg.Connection[dict[str, Any]],
) -> None:
    insert_event(connection, 'repo-e-1', 'repo-test-e', moment(12))

    result = EventRepository(connection).get_events_up_to(moment(10))

    assert event_ids_of(result, 'repo-test-e') == []
