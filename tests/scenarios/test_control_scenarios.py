"""Прогон контрольных сценариев по файлам из каталога fixtures."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from sla_support_tracker.constants import Department
from sla_support_tracker.reporting.csv_export import build_report_row
from sla_support_tracker.reporting.report_builder import generate_report_data
from sla_support_tracker.schemas import EmployeeSchema, EventSchema

FIXTURES_DIR = Path(__file__).resolve().parents[2] / 'fixtures'
SCENARIOS_DIR = FIXTURES_DIR / 'scenarios'
EXPECTED_RESULTS = json.loads((FIXTURES_DIR / 'expected_results.json').read_text(encoding='utf-8'))
AS_OF = datetime.fromisoformat(EXPECTED_RESULTS['as_of'])

EMPLOYEES = [
    EmployeeSchema(author_id='care-001', full_name='Анна Тестовая', department=Department.CARE),
    EmployeeSchema(author_id='care-002', full_name='Борис Тестовый', department=Department.CARE),
    EmployeeSchema(author_id='sales-001', full_name='Виктор Тестовый', department=Department.SALES),
]


def read_raw_events(scenario: dict[str, Any]) -> list[dict[str, Any]]:
    """События из всех файлов сценария в том виде, как они лежат в запросах."""
    raw_events: list[dict[str, Any]] = []
    for file_name in scenario['files']:
        request_body = json.loads((SCENARIOS_DIR / file_name).read_text(encoding='utf-8'))
        raw_events.extend(request_body['events'])
    return raw_events


def load_events(scenario: dict[str, Any]) -> list[EventSchema]:
    """События сценария; те, что не проходят проверку схемы, отбрасываются, как при приёме."""
    events = []
    for raw_event in read_raw_events(scenario):
        try:
            events.append(EventSchema.model_validate(raw_event))
        except ValidationError:
            continue
    return events


CASES = [
    pytest.param(scenario, expected_row, id=f'{scenario["number"]:02d}_{scenario["name"]}')
    for scenario in EXPECTED_RESULTS['scenarios']
    for expected_row in scenario['expected_rows']
]


@pytest.mark.parametrize(('scenario', 'expected_row'), CASES)
def test_scenario_matches_expected_row(
    scenario: dict[str, Any], expected_row: dict[str, str]
) -> None:
    """
    Строка отчёта по событиям сценария совпадает с ожидаемой строкой.

    Сравниваются только колонки, заданные в expected_results.json. Тест запускается
    отдельно для каждой каждого сценария.

    results и rows содержат данные только одного конкретного обращения по его conversation_id.
    """
    results = generate_report_data(load_events(scenario), EMPLOYEES, AS_OF)
    rows = {result.conversation_id: build_report_row(result) for result in results}

    actual_row = rows[expected_row['conversation_id']]

    assert {column: actual_row[column] for column in expected_row} == expected_row
