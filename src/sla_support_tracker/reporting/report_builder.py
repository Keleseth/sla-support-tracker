"""Сборка данных отчёта по всем обращениям."""

from collections import defaultdict
from datetime import datetime

from sla_support_tracker.schemas import ConversationEvaluationSchema, EmployeeSchema, EventSchema
from sla_support_tracker.sla_calculation.conversation_evaluation import evaluate_conversation


def generate_report_data(
    events: list[EventSchema],
    employees: list[EmployeeSchema],
    as_of: datetime,
) -> list[ConversationEvaluationSchema]:
    """
    Оценивает каждое обращение; результаты идут в порядке conversation_id.

    События раскладываются по обращениям.
    Сотрудники помещаются в словарь по author_id.
    """
    employees_by_author_id = {employee.author_id: employee for employee in employees}
    events_by_conversation: dict[str, list[EventSchema]] = defaultdict(list)
    for event in events:
        events_by_conversation[event.conversation_id].append(event)
    return [
        evaluate_conversation(
            events_by_conversation[conversation_id], employees_by_author_id, as_of
        )
        for conversation_id in sorted(events_by_conversation)
    ]
