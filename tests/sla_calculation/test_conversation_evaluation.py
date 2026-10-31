"""Тесты оценки обращения: поиск начала и ответа, качество данных, статусы SLA."""

from datetime import UTC, datetime
from typing import Any

import pytest

from sla_support_tracker.constants import (
    AuthorType,
    Channel,
    DataIssueCode,
    Department,
    Direction,
    MessageType,
)
from sla_support_tracker.schemas import EmployeeSchema, EventSchema
from sla_support_tracker.sla_calculation.conversation_evaluation import (
    check_chat_consistency,
    check_employee_authors,
    check_lead_id,
    find_data_issues,
    find_first_care_response,
    find_start,
)

EMPLOYEES = {
    'care-001': EmployeeSchema(
        author_id='care-001', full_name='Анна Тестовая', department=Department.CARE
    ),
    'sales-001': EmployeeSchema(
        author_id='sales-001', full_name='Виктор Тестовый', department=Department.SALES
    ),
}


def moment(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 9, 7, hour, minute, tzinfo=UTC)


def make_event(**overrides: Any) -> EventSchema:
    fields: dict[str, Any] = {
        'event_id': 'evt-1',
        'conversation_id': 'case-1',
        'channel': Channel.TELEGRAM,
        'chat_id': 'chat-1',
        'lead_id': '10001',
        'occurred_at': moment(10),
        'direction': Direction.INBOUND,
        'author_id': 'partner-1',
        'author_type': AuthorType.PARTNER,
        'message_type': MessageType.TEXT,
        'text': None,
    }
    return EventSchema(**{**fields, **overrides})


def make_employee_reply(author_id: str | None, occurred_at: datetime, event_id: str) -> EventSchema:
    return make_event(
        event_id=event_id,
        occurred_at=occurred_at,
        direction=Direction.OUTBOUND,
        author_id=author_id,
        author_type=AuthorType.EMPLOYEE,
    )


@pytest.mark.parametrize(
    ('lead_ids', 'expected'),
    [
        pytest.param([None, None], DataIssueCode.MISSING_LEAD_ID, id='all_null'),
        pytest.param([], DataIssueCode.MISSING_LEAD_ID, id='no_events'),
        pytest.param(['10001', '10001'], None, id='same_lead_everywhere'),
        pytest.param([None, '10001', None], None, id='one_lead_and_nulls'),
        pytest.param(['10001', '10002'], DataIssueCode.CONFLICTING_LEAD_IDS, id='two_leads'),
        pytest.param(
            [None, '10001', '10002'], DataIssueCode.CONFLICTING_LEAD_IDS, id='two_leads_and_null'
        ),
    ],
)
def test_check_lead_id(lead_ids: list[str | None], expected: DataIssueCode | None) -> None:
    events = [
        make_event(event_id=f'evt-{number}', lead_id=lead_id)
        for number, lead_id in enumerate(lead_ids)
    ]
    assert check_lead_id(events) == expected


def test_check_chat_consistency_accepts_single_chat() -> None:
    events = [make_event(event_id='evt-1'), make_event(event_id='evt-2')]
    assert check_chat_consistency(events) is None


@pytest.mark.parametrize(
    'other_fields',
    [{'chat_id': 'chat-2'}, {'channel': Channel.MAX}],
    ids=['different_chat', 'different_channel'],
)
def test_check_chat_consistency_detects_difference(other_fields: dict[str, Any]) -> None:
    events = [make_event(event_id='evt-1'), make_event(event_id='evt-2', **other_fields)]
    assert check_chat_consistency(events) == DataIssueCode.INCONSISTENT_CONVERSATION


def test_check_employee_authors_detects_unknown_author_before_response() -> None:
    start = make_event(event_id='start', occurred_at=moment(10))
    unknown = make_employee_reply('ghost-1', moment(10, 10), 'unknown')
    response = make_employee_reply('care-001', moment(10, 20), 'response')
    events = [start, unknown, response]

    result = check_employee_authors(events, EMPLOYEES, start, response)

    assert result == DataIssueCode.UNRESOLVED_EMPLOYEE_AUTHOR


def test_check_employee_authors_detects_null_author_before_response() -> None:
    start = make_event(event_id='start', occurred_at=moment(10))
    without_author = make_employee_reply(None, moment(10, 10), 'no-author')
    response = make_employee_reply('care-001', moment(10, 20), 'response')
    events = [start, without_author, response]

    result = check_employee_authors(events, EMPLOYEES, start, response)

    assert result == DataIssueCode.UNRESOLVED_EMPLOYEE_AUTHOR


def test_check_employee_authors_ignores_unknown_author_after_response() -> None:
    start = make_event(event_id='start', occurred_at=moment(10))
    response = make_employee_reply('care-001', moment(10, 20), 'response')
    unknown_later = make_employee_reply('ghost-1', moment(10, 40), 'unknown')
    events = [start, response, unknown_later]

    assert check_employee_authors(events, EMPLOYEES, start, response) is None


def test_check_employee_authors_includes_event_at_response_moment() -> None:
    start = make_event(event_id='start', occurred_at=moment(10))
    unknown = make_employee_reply('ghost-1', moment(10, 20), 'unknown')
    response = make_employee_reply('care-001', moment(10, 20), 'response')
    events = [start, unknown, response]

    result = check_employee_authors(events, EMPLOYEES, start, response)

    assert result == DataIssueCode.UNRESOLVED_EMPLOYEE_AUTHOR


def test_check_employee_authors_without_response_checks_until_the_end() -> None:
    start = make_event(event_id='start', occurred_at=moment(10))
    unknown = make_employee_reply('ghost-1', moment(11), 'unknown')
    events = [start, unknown]

    result = check_employee_authors(events, EMPLOYEES, start, None)

    assert result == DataIssueCode.UNRESOLVED_EMPLOYEE_AUTHOR


def test_check_employee_authors_accepts_known_sales_author() -> None:
    start = make_event(event_id='start', occurred_at=moment(10))
    sales = make_employee_reply('sales-001', moment(10, 5), 'sales')
    response = make_employee_reply('care-001', moment(10, 25), 'response')
    events = [start, sales, response]

    assert check_employee_authors(events, EMPLOYEES, start, response) is None


def test_check_employee_authors_ignores_bot_and_partner_without_known_author() -> None:
    start = make_event(event_id='start', occurred_at=moment(10))
    bot = make_event(
        event_id='bot',
        occurred_at=moment(10, 1),
        direction=Direction.OUTBOUND,
        author_id=None,
        author_type=AuthorType.BOT,
    )
    partner = make_event(event_id='partner', occurred_at=moment(10, 2), author_id='someone')
    response = make_employee_reply('care-001', moment(10, 20), 'response')
    events = [start, bot, partner, response]

    assert check_employee_authors(events, EMPLOYEES, start, response) is None


def test_check_employee_authors_without_start_has_nothing_to_check() -> None:
    unknown = make_employee_reply('ghost-1', moment(11), 'unknown')

    assert check_employee_authors([unknown], EMPLOYEES, None, None) is None


def test_find_start_takes_earliest_partner_inbound() -> None:
    later = make_event(event_id='later', occurred_at=moment(10, 10))
    earlier = make_event(event_id='earlier', occurred_at=moment(10))

    assert find_start([later, earlier]) == earlier


def test_find_start_ignores_everything_except_partner_inbound() -> None:
    bot_inbound = make_event(event_id='bot', occurred_at=moment(9), author_type=AuthorType.BOT)
    employee_reply = make_employee_reply('care-001', moment(9, 30), 'reply')
    partner_outbound = make_event(
        event_id='outbound', occurred_at=moment(9, 40), direction=Direction.OUTBOUND
    )
    partner_inbound = make_event(event_id='partner', occurred_at=moment(10))

    result = find_start([bot_inbound, employee_reply, partner_outbound, partner_inbound])

    assert result == partner_inbound


def test_find_start_returns_none_without_partner_inbound() -> None:
    bot = make_event(event_id='bot', author_type=AuthorType.BOT)

    assert find_start([bot]) is None
    assert find_start([]) is None


def test_find_first_care_response_takes_earliest_care_reply() -> None:
    start = make_event(event_id='start', occurred_at=moment(10))
    later = make_employee_reply('care-001', moment(10, 30), 'later')
    earlier = make_employee_reply('care-001', moment(10, 20), 'earlier')

    assert find_first_care_response([start, later, earlier], EMPLOYEES, start) == earlier


def test_find_first_care_response_skips_sales_bot_and_unknown_employee() -> None:
    start = make_event(event_id='start', occurred_at=moment(10))
    sales = make_employee_reply('sales-001', moment(10, 5), 'sales')
    bot = make_event(
        event_id='bot',
        occurred_at=moment(10, 1),
        direction=Direction.OUTBOUND,
        author_id=None,
        author_type=AuthorType.BOT,
    )
    unknown = make_employee_reply('ghost-1', moment(10, 10), 'unknown')
    care = make_employee_reply('care-001', moment(10, 25), 'care')

    result = find_first_care_response([start, sales, bot, unknown, care], EMPLOYEES, start)

    assert result == care


def test_find_first_care_response_ignores_reply_before_start() -> None:
    start = make_event(event_id='start', occurred_at=moment(10))
    too_early = make_employee_reply('care-001', moment(9, 50), 'early')

    assert find_first_care_response([too_early, start], EMPLOYEES, start) is None


def test_find_first_care_response_accepts_reply_at_start_moment() -> None:
    start = make_event(event_id='start', occurred_at=moment(10))
    same_moment = make_employee_reply('care-001', moment(10), 'same-moment')

    assert find_first_care_response([start, same_moment], EMPLOYEES, start) == same_moment


def test_find_first_care_response_accepts_any_message_type() -> None:
    start = make_event(event_id='start', occurred_at=moment(10))
    file_reply = make_event(
        event_id='file',
        occurred_at=moment(10, 12),
        direction=Direction.OUTBOUND,
        author_id='care-001',
        author_type=AuthorType.EMPLOYEE,
        message_type=MessageType.FILE,
    )

    assert find_first_care_response([start, file_reply], EMPLOYEES, start) == file_reply


def test_find_first_care_response_breaks_ties_by_event_id() -> None:
    start = make_event(event_id='start', occurred_at=moment(10))
    second = make_employee_reply('care-001', moment(10, 20), 'reply-b')
    first = make_employee_reply('care-001', moment(10, 20), 'reply-a')

    assert find_first_care_response([start, second, first], EMPLOYEES, start) == first


def test_find_first_care_response_ignores_inbound_events_of_care() -> None:
    start = make_event(event_id='start', occurred_at=moment(10))
    inbound_by_care = make_event(
        event_id='inbound',
        occurred_at=moment(10, 5),
        author_id='care-001',
        author_type=AuthorType.EMPLOYEE,
    )

    assert find_first_care_response([start, inbound_by_care], EMPLOYEES, start) is None


def test_find_first_care_response_without_start_is_none() -> None:
    care = make_employee_reply('care-001', moment(10, 20), 'care')

    assert find_first_care_response([care], EMPLOYEES, None) is None


def test_find_data_issues_returns_empty_list_for_clean_conversation() -> None:
    start = make_event(event_id='start', occurred_at=moment(10))
    care = make_employee_reply('care-001', moment(10, 20), 'care')

    assert find_data_issues([start, care], EMPLOYEES, start, care) == []


def test_find_data_issues_reports_missing_inbound() -> None:
    care = make_employee_reply('care-001', moment(10, 20), 'care')

    assert find_data_issues([care], EMPLOYEES, None, None) == [DataIssueCode.MISSING_INBOUND]


def test_find_data_issues_lists_all_problems_in_fixed_order() -> None:
    start = make_event(event_id='start', occurred_at=moment(10), lead_id='10001')
    ghost = make_event(
        event_id='ghost',
        occurred_at=moment(10, 10),
        direction=Direction.OUTBOUND,
        author_id='ghost-1',
        author_type=AuthorType.EMPLOYEE,
        lead_id='10002',
        chat_id='chat-2',
    )
    care = make_employee_reply('care-001', moment(10, 20), 'care')

    result = find_data_issues([start, ghost, care], EMPLOYEES, start, care)

    assert result == [
        DataIssueCode.CONFLICTING_LEAD_IDS,
        DataIssueCode.INCONSISTENT_CONVERSATION,
        DataIssueCode.UNRESOLVED_EMPLOYEE_AUTHOR,
    ]
