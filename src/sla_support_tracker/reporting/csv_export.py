"""Запись report.csv, data_issues.csv и summary.json."""

import csv
import json
from collections.abc import Iterable
from datetime import datetime, timedelta
from pathlib import Path

from sla_support_tracker.constants import BUSINESS_TIMEZONE, DATA_ISSUE_DESCRIPTIONS
from sla_support_tracker.schemas import (
    ConversationEvaluationSchema,
    RejectedEventSchema,
    SummarySchema,
)
from sla_support_tracker.sla_calculation.business_hours import duration_to_minutes

REPORT_COLUMNS = [
    'conversation_id',
    'channel',
    'chat_id',
    'lead_id',
    'first_inbound_at',
    'first_response_at',
    'employee_id',
    'employee_name',
    'actual_minutes',
    'business_minutes',
    'status',
    'issue_reason',
    'as_of',
]

DATA_ISSUES_COLUMNS = ['event_id', 'conversation_id', 'issue_code', 'description']


def format_minutes(duration: timedelta | None) -> str:
    """Минуты с двумя знаками после точки; пустая строка, если длительности нет."""
    if duration is None:
        return ''
    return str(duration_to_minutes(duration))


def format_moment(moment: datetime | None) -> str:
    """Момент в ISO 8601 по московскому времени; пустая строка, если момента нет."""
    if moment is None:
        return ''
    return moment.astimezone(BUSINESS_TIMEZONE).isoformat()


def build_report_row(result: ConversationEvaluationSchema) -> dict[str, str]:
    """Строка report.csv: все значения текстом, неизвестные значения пустые."""
    return {
        'conversation_id': result.conversation_id,
        'channel': result.channel.value if result.channel is not None else '',
        'chat_id': result.chat_id or '',
        'lead_id': result.lead_id or '',
        'first_inbound_at': format_moment(result.first_inbound_at),
        'first_response_at': format_moment(result.first_response_at),
        'employee_id': result.employee_id or '',
        'employee_name': result.employee_name or '',
        'actual_minutes': format_minutes(result.actual_duration),
        'business_minutes': format_minutes(result.business_duration),
        'status': result.status.value,
        'issue_reason': '; '.join(issue.value for issue in result.issues),
        'as_of': result.as_of.isoformat(),
    }


def build_data_issue_rows(
    results: list[ConversationEvaluationSchema],
    rejected_events: list[RejectedEventSchema],
) -> list[dict[str, str]]:
    """Строки data_issues.csv: сначала ошибки приёма из журнала, затем проблемы обращений."""
    rows = [
        {
            'event_id': rejected.event_id or '',
            'conversation_id': rejected.conversation_id or '',
            'issue_code': rejected.issue_code,
            'description': rejected.description,
        }
        for rejected in rejected_events
    ]
    rows.extend(
        {
            'event_id': '',
            'conversation_id': result.conversation_id,
            'issue_code': issue.value,
            'description': DATA_ISSUE_DESCRIPTIONS[issue],
        }
        for result in results
        for issue in result.issues
    )
    return rows


def write_csv(path: Path, columns: list[str], rows: Iterable[dict[str, str]]) -> None:
    """Пишет CSV в UTF-8 с BOM: шапка из columns, затем строки."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8-sig', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def write_report_csv(results: list[ConversationEvaluationSchema], output_dir: Path) -> Path:
    """Записывает report.csv: одна строка на обращение."""
    path = output_dir / 'report.csv'
    write_csv(path, REPORT_COLUMNS, (build_report_row(result) for result in results))
    return path


def write_data_issues_csv(
    results: list[ConversationEvaluationSchema],
    rejected_events: list[RejectedEventSchema],
    output_dir: Path,
) -> Path:
    """Записывает data_issues.csv: ошибки приёма и проблемы качества обращений."""
    path = output_dir / 'data_issues.csv'
    write_csv(path, DATA_ISSUES_COLUMNS, build_data_issue_rows(results, rejected_events))
    return path


def write_summary_json(summary: SummarySchema, output_dir: Path) -> Path:
    """Записывает summary.json в UTF-8; недостающие показатели записываются как null."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / 'summary.json'
    text = json.dumps(summary.model_dump(mode='json'), ensure_ascii=False, indent=2)
    path.write_text(text + '\n', encoding='utf-8')
    return path
