"""Pydantic-схемы данных проекта: события, справочник сотрудников и результат оценки обращения."""

from datetime import timedelta

from pydantic import AwareDatetime, BaseModel, ConfigDict

from sla_support_tracker.constants import (
    AuthorType,
    Channel,
    DataIssueCode,
    Department,
    Direction,
    MessageType,
    SlaStatus,
)


class EventSchema(BaseModel):
    """
    Событие обращения из таблицы events.

    Поле occurred_at всегда содержит часовой пояс.
    """

    model_config = ConfigDict(frozen=True)

    event_id: str
    conversation_id: str
    channel: Channel
    chat_id: str
    lead_id: str | None
    occurred_at: AwareDatetime
    direction: Direction
    author_id: str | None
    author_type: AuthorType
    message_type: MessageType
    text: str | None


class EmployeeSchema(BaseModel):
    """Строка справочника сотрудников."""

    model_config = ConfigDict(frozen=True)

    author_id: str
    full_name: str
    department: Department


class ConversationEvaluationSchema(BaseModel):
    """
    Результат оценки одного обращения: данные строки отчёта и найденные проблемы.

    Для статуса data_issue длительности и сведения об ответе не заполняются.
    """

    model_config = ConfigDict(frozen=True)

    conversation_id: str
    channel: Channel | None
    chat_id: str | None
    lead_id: str | None
    first_inbound_at: AwareDatetime | None
    first_response_at: AwareDatetime | None
    employee_id: str | None
    employee_name: str | None
    actual_duration: timedelta | None
    business_duration: timedelta | None
    status: SlaStatus
    issues: list[DataIssueCode]
    as_of: AwareDatetime


class RejectedEventSchema(BaseModel):
    """Запись журнала отклонённых событий: причина, по которой событие не попало в events."""

    model_config = ConfigDict(frozen=True)

    event_id: str | None
    conversation_id: str | None
    issue_code: str
    description: str


class SummarySchema(BaseModel):
    """Сводные показатели отчёта на момент as_of."""

    model_config = ConfigDict(frozen=True)

    as_of: AwareDatetime
    conversations_without_data_issue: int
    answered_in_sla: int
    answered_late: int
    unanswered_overdue: int
    waiting: int
    data_issue: int
    sla_compliance_percent: float | None
    average_response_business_minutes: float | None
