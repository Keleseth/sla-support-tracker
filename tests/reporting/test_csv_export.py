"""Тесты записи CSV: кодировка, разделитель, формат чисел и дат."""

import csv
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sla_support_tracker.constants import Channel, SlaStatus
from sla_support_tracker.reporting.csv_export import REPORT_COLUMNS, write_report_csv
from sla_support_tracker.schemas import ConversationEvaluationSchema

AS_OF = datetime(2026, 9, 8, 12, 0, tzinfo=UTC)


def make_result(
    status: SlaStatus, business_duration: timedelta | None, employee_name: str | None = None
) -> ConversationEvaluationSchema:
    return ConversationEvaluationSchema(
        conversation_id='case-1',
        channel=Channel.TELEGRAM,
        chat_id='chat-1',
        lead_id=None,
        first_inbound_at=datetime(2026, 9, 7, 7, 0, tzinfo=UTC),
        first_response_at=None,
        employee_id=None,
        employee_name=employee_name,
        actual_duration=business_duration,
        business_duration=business_duration,
        status=status,
        issues=[],
        as_of=AS_OF,
    )


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding='utf-8-sig', newline='') as file:
        return list(csv.DictReader(file))


def test_report_csv_has_fixed_columns_cyrillic_and_two_decimal_minutes(tmp_path: Path) -> None:
    result = make_result(SlaStatus.ANSWERED_LATE, timedelta(minutes=30, seconds=1), 'Аня')

    path = write_report_csv([result], tmp_path)

    rows = read_rows(path)
    assert list(rows[0]) == REPORT_COLUMNS
    assert rows[0]['business_minutes'] == '30.02'
    assert rows[0]['employee_name'] == 'Аня'
    assert rows[0]['first_inbound_at'] == '2026-09-07T10:00:00+03:00'


def test_report_csv_leaves_durations_empty_for_data_issue(tmp_path: Path) -> None:
    result = make_result(SlaStatus.DATA_ISSUE, None)

    rows = read_rows(write_report_csv([result], tmp_path))

    assert rows[0]['status'] == 'data_issue'
    assert rows[0]['actual_minutes'] == ''
    assert rows[0]['business_minutes'] == ''
