"""
Общий словарь проекта: перечисления и параметры правил SLA.

Границы рабочего дня заданы как время, прошедшее с полуночи по часовому поясу BUSINESS_TIMEZONE.

Значения перечислений используются в трёх местах: в проверке событий в n8n, в ограничениях
CHECK таблиц и в расчёте на Python. При переименовании значения правятся все три.
"""

from datetime import timedelta
from enum import StrEnum
from zoneinfo import ZoneInfo

BUSINESS_TIMEZONE = ZoneInfo('Europe/Moscow')
BUSINESS_DAY_START = timedelta(hours=10)
BUSINESS_DAY_END = timedelta(hours=22)
SLA_THRESHOLD = timedelta(minutes=30)


class Channel(StrEnum):
    """Канал, в котором идёт обращение."""

    TELEGRAM = 'telegram'
    MAX = 'max'


class Direction(StrEnum):
    """Направление сообщения: от партнёра к нам или от нас партнёру."""

    INBOUND = 'inbound'
    OUTBOUND = 'outbound'


class AuthorType(StrEnum):
    """Кто автор события."""

    PARTNER = 'partner'
    EMPLOYEE = 'employee'
    BOT = 'bot'
    SYSTEM = 'system'


class MessageType(StrEnum):
    """Тип сообщения; для расчёта SLA все типы ответа равнозначны."""

    TEXT = 'text'
    FILE = 'file'
    IMAGE = 'image'
    VOICE = 'voice'
    TEMPLATE = 'template'


class Department(StrEnum):
    """Отдел сотрудника из справочника."""

    CARE = 'care'
    SALES = 'sales'


class SlaStatus(StrEnum):
    """Итоговый статус обращения в report.csv."""

    ANSWERED_IN_SLA = 'answered_in_sla'
    ANSWERED_LATE = 'answered_late'
    WAITING = 'waiting'
    UNANSWERED_OVERDUE = 'unanswered_overdue'
    DATA_ISSUE = 'data_issue'


class DataIssueCode(StrEnum):
    """Коды проблем качества данных обращения."""

    MISSING_LEAD_ID = 'missing_lead_id'
    CONFLICTING_LEAD_IDS = 'conflicting_lead_ids'
    MISSING_INBOUND = 'missing_inbound'
    INCONSISTENT_CONVERSATION = 'inconsistent_conversation'
    UNRESOLVED_EMPLOYEE_AUTHOR = 'unresolved_employee_author'


DATA_ISSUE_DESCRIPTIONS = {
    DataIssueCode.MISSING_LEAD_ID: 'Ни у одного события обращения не указан lead_id',
    DataIssueCode.CONFLICTING_LEAD_IDS: 'У событий обращения указаны разные lead_id',
    DataIssueCode.MISSING_INBOUND: 'В обращении нет входящего события партнёра',
    DataIssueCode.INCONSISTENT_CONVERSATION: (
        'События обращения относятся к разным каналам или чатам'
    ),
    DataIssueCode.UNRESOLVED_EMPLOYEE_AUTHOR: (
        'До первого ответа care есть исходящее сообщение сотрудника '
        'с пустым или неизвестным author_id'
    ),
}
