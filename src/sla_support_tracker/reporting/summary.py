"""Сводные показатели: количества по статусам, соблюдение SLA, среднее время ответа."""

from collections import Counter
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sla_support_tracker.constants import SlaStatus
from sla_support_tracker.schemas import ConversationEvaluationSchema, SummarySchema
from sla_support_tracker.sla_calculation.business_hours import duration_to_minutes


def calculate_compliance_percent(in_sla: int, judged: int) -> float | None:
    """Доля обращений в SLA среди оценённых, в процентах; None, если оценённых нет."""
    if judged == 0:
        return None
    percent = Decimal(in_sla) * 100 / Decimal(judged)
    return float(percent.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def calculate_average_response_minutes(durations: list[timedelta]) -> float | None:
    """Среднее время ответа в рабочих минутах; None, если ответов нет."""
    if not durations:
        return None
    average = sum(durations, timedelta()) / len(durations)
    return float(duration_to_minutes(average))


def build_summary(results: list[ConversationEvaluationSchema], as_of: datetime) -> SummarySchema:
    """Считает сводные показатели по результатам оценки всех обращений."""
    counts = Counter(result.status for result in results)
    in_sla = counts[SlaStatus.ANSWERED_IN_SLA]
    late = counts[SlaStatus.ANSWERED_LATE]
    overdue = counts[SlaStatus.UNANSWERED_OVERDUE]
    answered_durations = [
        result.business_duration
        for result in results
        if result.status in (SlaStatus.ANSWERED_IN_SLA, SlaStatus.ANSWERED_LATE)
        and result.business_duration is not None
    ]
    return SummarySchema(
        as_of=as_of,
        conversations_without_data_issue=len(results) - counts[SlaStatus.DATA_ISSUE],
        answered_in_sla=in_sla,
        answered_late=late,
        unanswered_overdue=overdue,
        waiting=counts[SlaStatus.WAITING],
        data_issue=counts[SlaStatus.DATA_ISSUE],
        sla_compliance_percent=calculate_compliance_percent(in_sla, in_sla + late + overdue),
        average_response_business_minutes=calculate_average_response_minutes(answered_durations),
    )
