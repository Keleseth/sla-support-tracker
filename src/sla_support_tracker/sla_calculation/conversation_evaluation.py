"""Оценка одного обращения: начало и первый ответ, качество данных, длительности и статус SLA."""

from collections.abc import Iterable
from datetime import datetime, timedelta
from typing import Any

from sla_support_tracker.constants import (
    SLA_THRESHOLD,
    AuthorType,
    DataIssueCode,
    Department,
    Direction,
    SlaStatus,
)
from sla_support_tracker.schemas import ConversationEvaluationSchema, EmployeeSchema, EventSchema
from sla_support_tracker.sla_calculation.business_hours import business_time_spent


def find_start(events: list[EventSchema]) -> EventSchema | None:
    """Начало обращения: самое раннее входящее событие партнёра."""
    partner_inbound = [
        event
        for event in events
        if event.direction == Direction.INBOUND and event.author_type == AuthorType.PARTNER
    ]
    return min(partner_inbound, key=lambda event: event.occurred_at, default=None)


def find_first_care_response(
    events: list[EventSchema],
    employees: dict[str, EmployeeSchema],
    start: EventSchema | None,
) -> EventSchema | None:
    """
    Поиск первого ответа сотрудника отдела care, идушщего ПОСЛЕ первого обращения
    партнера в текущем conversation.
    """
    if start is None:
        return None
    care_author_ids = {
        author_id
        for author_id, employee in employees.items()
        if employee.department == Department.CARE
    }
    return min(
        (
            event
            for event in events
            if event.direction == Direction.OUTBOUND
            and event.author_type == AuthorType.EMPLOYEE
            and event.author_id in care_author_ids
            and event.occurred_at >= start.occurred_at
        ),
        key=lambda event: (event.occurred_at, event.event_id),
        default=None,
    )


def check_lead_id(events: list[EventSchema]) -> DataIssueCode | None:
    """Проверка наличия и уникальности lead_id обращения"""
    lead_ids = {event.lead_id for event in events if event.lead_id is not None}
    if not lead_ids:
        return DataIssueCode.MISSING_LEAD_ID
    if len(lead_ids) > 1:
        return DataIssueCode.CONFLICTING_LEAD_IDS
    return None


def check_chat_consistency(events: list[EventSchema]) -> DataIssueCode | None:
    """Проверка согласованности: события одного обращения поступали из одного источника."""
    sources = {(event.channel, event.chat_id) for event in events}
    if len(sources) > 1:
        return DataIssueCode.INCONSISTENT_CONVERSATION
    return None


def check_employee_authors(
    events: list[EventSchema],
    employees: dict[str, EmployeeSchema],
    start: EventSchema | None,
    response: EventSchema | None,
) -> DataIssueCode | None:
    """
    Проверка автора: сотрудник с пустым или неизвестным author_id писал клиенту.

    Проверяются события в промежутке от начала обращения,
    до первого подтверждённого ответа - employeew/care или до as_of. Ответ от employee-sales
    не прекращает поиск неизвестного автора.
    """
    if start is None:
        return None
    in_interval = [
        event
        for event in events
        if event.occurred_at >= start.occurred_at
        and (response is None or event.occurred_at <= response.occurred_at)
    ]
    has_unresolved_author = any(
        event.direction == Direction.OUTBOUND
        and event.author_type == AuthorType.EMPLOYEE
        and event.author_id not in employees
        for event in in_interval
    )
    if has_unresolved_author:
        return DataIssueCode.UNRESOLVED_EMPLOYEE_AUTHOR
    return None


def find_data_issues(
    events: list[EventSchema],
    employees: dict[str, EmployeeSchema],
    start: EventSchema | None,
    response: EventSchema | None,
) -> list[DataIssueCode]:
    """
    Все нарушения консистетности conversation для соаставления description:
        - Наличие уникальный lead_id
        - Общение из одного источника
        - Неизвестный автор ответа

    Без нарушений - пустой список.
    """
    issues = [
        check_lead_id(events),
        DataIssueCode.MISSING_INBOUND if start is None else None,
        check_chat_consistency(events),
        check_employee_authors(events, employees, start, response),
    ]
    return [issue for issue in issues if issue is not None]


def valid_unique_value[T](values: Iterable[T]) -> T | None:
    """Общее значение, если все элементы одинаковы; None, если значений нет или их несколько."""
    unique_values = set(values)
    if len(unique_values) == 1:
        return unique_values.pop()
    return None


def find_responder(
    response: EventSchema | None,
    employees: dict[str, EmployeeSchema],
) -> EmployeeSchema | None:
    """Сотрудник из справочника, написавший ответ."""
    if response is None or response.author_id is None:
        return None
    return employees.get(response.author_id)


def calculate_status(business_duration: timedelta, answered: bool) -> SlaStatus:
    """
    Статус обращения без проблем с данными: рабочее время сравнивается с порогом SLA.
    Сравнение идёт по точному timedelta без округления.
    """
    if answered:
        within_threshold = business_duration <= SLA_THRESHOLD
        return SlaStatus.ANSWERED_IN_SLA if within_threshold else SlaStatus.ANSWERED_LATE
    within_threshold = business_duration < SLA_THRESHOLD
    return SlaStatus.WAITING if within_threshold else SlaStatus.UNANSWERED_OVERDUE


def evaluate_conversation(
    events: list[EventSchema],
    employees: dict[str, EmployeeSchema],
    as_of: datetime,
) -> ConversationEvaluationSchema:
    """
    Оценивает обращение: находит начало и ответ, проверяет данные, считает время и статус.

    events - все события обращения до as_of.
    employees - словарь всех сотрудники справочника с ключом author_id. Загружается 1 раз
    для всех проверок исключая лишние обращения к бд.
    """
    start = find_start(events)
    response = find_first_care_response(events, employees, start)
    issues = find_data_issues(events, employees, start, response)
    common_fields: dict[str, Any] = {
        'conversation_id': events[0].conversation_id,
        'channel': valid_unique_value(event.channel for event in events),
        'chat_id': valid_unique_value(event.chat_id for event in events),
        'lead_id': valid_unique_value(
            event.lead_id for event in events if event.lead_id is not None
        ),
        'first_inbound_at': start.occurred_at if start is not None else None,
        'issues': issues,
        'as_of': as_of,
    }
    if start is None or issues:
        return ConversationEvaluationSchema(
            **common_fields,
            first_response_at=None,
            employee_id=None,
            employee_name=None,
            actual_duration=None,
            business_duration=None,
            status=SlaStatus.DATA_ISSUE,
        )
    end = response.occurred_at if response is not None else as_of
    business_duration = business_time_spent(start.occurred_at, end)
    responder = find_responder(response, employees)
    return ConversationEvaluationSchema(
        **common_fields,
        first_response_at=response.occurred_at if response is not None else None,
        employee_id=responder.author_id if responder is not None else None,
        employee_name=responder.full_name if responder is not None else None,
        actual_duration=end - start.occurred_at,
        business_duration=business_duration,
        status=calculate_status(business_duration, answered=response is not None),
    )
