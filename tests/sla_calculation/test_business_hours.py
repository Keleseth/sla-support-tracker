"""Тесты расчёта рабочих минут."""

from datetime import UTC, datetime, timedelta, timezone

import pytest

from sla_support_tracker.constants import BUSINESS_TIMEZONE
from sla_support_tracker.sla_calculation.business_hours import (
    business_time_elapsed_in_day,
    business_time_spent,
)


def moscow_moment(day: int, hour: int, minute: int, second: int = 0) -> datetime:
    return datetime(2026, 9, day, hour, minute, second, tzinfo=BUSINESS_TIMEZONE)


@pytest.mark.parametrize(
    ('moment', 'expected'),
    [
        (moscow_moment(7, 9, 59), timedelta(0)),
        (moscow_moment(7, 10, 0), timedelta(0)),
        (moscow_moment(7, 10, 30), timedelta(minutes=30)),
        (moscow_moment(7, 21, 59), timedelta(hours=11, minutes=59)),
        (moscow_moment(7, 22, 0), timedelta(hours=12)),
        (moscow_moment(7, 23, 30), timedelta(hours=12)),
    ],
)
def test_business_time_elapsed_in_day(moment: datetime, expected: timedelta) -> None:
    assert business_time_elapsed_in_day(moment) == expected


def test_business_time_elapsed_in_day_converts_other_timezones() -> None:
    moment_in_utc = datetime(2026, 9, 7, 7, 30, tzinfo=UTC)
    assert business_time_elapsed_in_day(moment_in_utc) == timedelta(minutes=30)


@pytest.mark.parametrize(
    ('start', 'end', 'expected'),
    [
        pytest.param(
            moscow_moment(7, 9, 40),
            moscow_moment(7, 10, 37),
            timedelta(minutes=37),
            id='scenario_1_late_answer',
        ),
        pytest.param(
            moscow_moment(7, 21, 50),
            moscow_moment(8, 10, 15),
            timedelta(minutes=25),
            id='scenario_2_overnight',
        ),
        pytest.param(
            moscow_moment(7, 10, 0),
            moscow_moment(7, 10, 30),
            timedelta(minutes=30),
            id='scenario_6_exactly_30_minutes',
        ),
        pytest.param(
            moscow_moment(7, 10, 0),
            moscow_moment(7, 10, 30, 1),
            timedelta(minutes=30, seconds=1),
            id='scenario_7_30_minutes_1_second',
        ),
        pytest.param(
            moscow_moment(7, 23, 0),
            moscow_moment(8, 9, 0),
            timedelta(0),
            id='scenario_8_night_only',
        ),
        pytest.param(
            moscow_moment(8, 11, 45),
            moscow_moment(8, 12, 0),
            timedelta(minutes=15),
            id='scenario_9_waiting_until_as_of',
        ),
        pytest.param(
            moscow_moment(8, 11, 30),
            moscow_moment(8, 12, 0),
            timedelta(minutes=30),
            id='scenario_10_waiting_30_minutes',
        ),
        pytest.param(
            moscow_moment(6, 10, 0),
            moscow_moment(6, 10, 20),
            timedelta(minutes=20),
            id='scenario_17_sunday',
        ),
        pytest.param(
            moscow_moment(7, 10, 0),
            moscow_moment(7, 10, 0),
            timedelta(0),
            id='same_moment',
        ),
        pytest.param(
            moscow_moment(7, 9, 59),
            moscow_moment(7, 10, 25),
            timedelta(minutes=25),
            id='start_before_opening',
        ),
        pytest.param(
            moscow_moment(7, 21, 59),
            moscow_moment(8, 10, 25),
            timedelta(minutes=26),
            id='one_minute_before_closing_to_next_morning',
        ),
        pytest.param(
            moscow_moment(7, 10, 0),
            moscow_moment(7, 22, 0),
            timedelta(hours=12),
            id='whole_business_day',
        ),
        pytest.param(
            moscow_moment(7, 22, 0),
            moscow_moment(8, 10, 0),
            timedelta(0),
            id='whole_night',
        ),
        pytest.param(
            moscow_moment(7, 21, 0),
            moscow_moment(9, 11, 0),
            timedelta(hours=14),
            id='several_days',
        ),
    ],
)
def test_business_time_spent(start: datetime, end: datetime, expected: timedelta) -> None:
    assert business_time_spent(start, end) == expected


def test_business_time_spent_counts_days_in_moscow() -> None:
    start = datetime(2026, 9, 7, 18, 30, tzinfo=UTC)
    end = datetime(2026, 9, 7, 21, 30, tzinfo=UTC)
    assert business_time_spent(start, end) == timedelta(minutes=30)


def test_business_time_spent_accepts_different_timezones() -> None:
    start = datetime(2026, 9, 7, 12, 30, tzinfo=timezone(timedelta(hours=5)))
    end = moscow_moment(7, 10, 50)
    assert business_time_spent(start, end) == timedelta(minutes=20)
