"""
Командная строка: формирование отчётов на момент as_of.

Запуск из корня репозитория:
    python -m sla_support_tracker.cli --as-of 2026-09-08T12:00:00+03:00

Аргумент --as-of обязателен и должен содержать часовой пояс.
"""

import argparse
import io
import sys
from datetime import datetime
from pathlib import Path

from sla_support_tracker.database import get_connection
from sla_support_tracker.reporting.csv_export import (
    write_data_issues_csv,
    write_report_csv,
    write_summary_json,
)
from sla_support_tracker.reporting.report_builder import generate_report_data
from sla_support_tracker.reporting.summary import build_summary
from sla_support_tracker.repository.employee import EmployeeRepository
from sla_support_tracker.repository.event import EventRepository
from sla_support_tracker.repository.rejected_event import RejectedEventRepository


def parse_as_of(value: str) -> datetime:
    """
    Разбирает строку ISO 8601 в момент времени с часовым поясом.

    Аргумент --as-of ожидается только с часовым поясом. Невалидная строка будет отклоняться.
    """
    try:
        moment = datetime.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f'не дата ISO 8601: {value!r}') from error
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise argparse.ArgumentTypeError(f'нужен часовой пояс, например +03:00 или Z: {value!r}')
    return moment


def build_parser() -> argparse.ArgumentParser:
    """Собирает разбор аргументов командной строки."""
    parser = argparse.ArgumentParser(
        prog='python -m sla_support_tracker.cli',
        description='Формирует report.csv, data_issues.csv и summary.json на момент as_of.',
    )
    parser.add_argument(
        '--as-of',
        dest='as_of',
        required=True,
        type=parse_as_of,
        help='момент отчёта в ISO 8601 с часовым поясом, например 2026-09-08T12:00:00+03:00',
    )
    parser.add_argument(
        '--output-dir',
        dest='output_dir',
        type=Path,
        default=Path('output'),
        help='каталог для результатов (по умолчанию output)',
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Оценивает обращения на момент as_of, записывает отчёты; возвращает код завершения."""
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding='utf-8')
    arguments = build_parser().parse_args(argv)
    with get_connection() as connection:
        events = EventRepository(connection).get_events_up_to(arguments.as_of)
        employees = EmployeeRepository(connection).get_all()
        rejected_events = RejectedEventRepository(connection).get_all()
    results = generate_report_data(events, employees, arguments.as_of)
    paths = [
        write_report_csv(results, arguments.output_dir),
        write_data_issues_csv(results, rejected_events, arguments.output_dir),
        write_summary_json(build_summary(results, arguments.as_of), arguments.output_dir),
    ]
    print(f'Обращений: {len(results)}. Файлы: {", ".join(str(path) for path in paths)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
