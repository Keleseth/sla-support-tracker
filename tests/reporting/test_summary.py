"""Тесты сводных показателей, включая null при нулевом знаменателе."""

from datetime import UTC, datetime, timedelta

from sla_support_tracker.constants import SlaStatus
from sla_support_tracker.reporting.summary import build_summary
from sla_support_tracker.schemas import ConversationEvaluationSchema

AS_OF = datetime(2026, 9, 8, 12, 0, tzinfo=UTC)


def make_result(
    status: SlaStatus, business_minutes: int | None = None
) -> ConversationEvaluationSchema:
    business_duration = None if business_minutes is None else timedelta(minutes=business_minutes)
    return ConversationEvaluationSchema(
        conversation_id='case',
        channel=None,
        chat_id=None,
        lead_id=None,
        first_inbound_at=None,
        first_response_at=None,
        employee_id=None,
        employee_name=None,
        actual_duration=None,
        business_duration=business_duration,
        status=status,
        issues=[],
        as_of=AS_OF,
    )


def test_summary_counts_compliance_and_average() -> None:
    results = [
        make_result(SlaStatus.ANSWERED_IN_SLA, 10),
        make_result(SlaStatus.ANSWERED_IN_SLA, 20),
        make_result(SlaStatus.ANSWERED_LATE, 40),
        make_result(SlaStatus.UNANSWERED_OVERDUE, 90),
        make_result(SlaStatus.WAITING, 5),
        make_result(SlaStatus.DATA_ISSUE),
    ]

    summary = build_summary(results, AS_OF)

    assert summary.conversations_without_data_issue == 5
    assert (summary.answered_in_sla, summary.answered_late) == (2, 1)
    assert (summary.unanswered_overdue, summary.waiting, summary.data_issue) == (1, 1, 1)
    assert summary.sla_compliance_percent == 50.0
    assert summary.average_response_business_minutes == 23.33


def test_summary_gives_null_instead_of_zero_when_nothing_to_judge() -> None:
    results = [make_result(SlaStatus.WAITING, 5), make_result(SlaStatus.DATA_ISSUE)]

    summary = build_summary(results, AS_OF)

    assert summary.sla_compliance_percent is None
    assert summary.average_response_business_minutes is None
