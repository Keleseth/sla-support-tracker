"""
Расчёт рабочих минут между двумя моментами.

Рабочее время: ежедневно с 10:00 до 22:00 по Europe/Moscow, без выходных.
Модуль содержит чистые функции, результат которых зависит только от аргументов.
"""

from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sla_support_tracker.constants import (
    BUSINESS_DAY_END,
    BUSINESS_DAY_START,
    BUSINESS_TIMEZONE,
)


def business_time_elapsed_in_day(moment: datetime) -> timedelta:
    """
    Определяет попадает ли момент времени в границы рабочих часов.
    Если вне рабочих часов, момент сдвигается к началу рабочего дня если до,
    и к концу, если после.
    """
    local_moment = moment.astimezone(BUSINESS_TIMEZONE)
    since_midnight = timedelta(
        hours=local_moment.hour,
        minutes=local_moment.minute,
        seconds=local_moment.second,
        microseconds=local_moment.microsecond,
    )
    clamped = min(max(since_midnight, BUSINESS_DAY_START), BUSINESS_DAY_END)
    return clamped - BUSINESS_DAY_START


def business_time_spent(start: datetime, end: datetime) -> timedelta:
    """
    Вычисляет секунды прошедшие между 2 временными метками start и end, учитывая границы
    рабочего дня.
    """
    days_apart = (
        end.astimezone(BUSINESS_TIMEZONE).date() - start.astimezone(BUSINESS_TIMEZONE).date()
    ).days
    business_day_length = BUSINESS_DAY_END - BUSINESS_DAY_START
    return (
        days_apart * business_day_length
        + business_time_elapsed_in_day(end)
        - business_time_elapsed_in_day(start)
    )


def duration_to_minutes(duration: timedelta) -> Decimal:
    """Длительность в минутах, округлённая до двух знаков после точки."""
    minutes = Decimal(duration // timedelta(microseconds=1)) / Decimal(60_000_000)
    return minutes.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
