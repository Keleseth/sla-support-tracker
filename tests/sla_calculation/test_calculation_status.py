from datetime import timedelta

import pytest

from sla_support_tracker.constants import SlaStatus
from sla_support_tracker.sla_calculation.conversation_evaluation import (calculate_status)


@pytest.mark.parametrize(
    ('business_duration', 'answered', 'expected'),
    [
        pytest.param(
            timedelta(minutes=30), True, SlaStatus.ANSWERED_IN_SLA, id='answered_in_sla'
        ),
        pytest.param(
            timedelta(minutes=30, microseconds=1),
            True,
            SlaStatus.ANSWERED_LATE, id='answered_late'
        ),
        pytest.param(
            timedelta(minutes=29, seconds=59, microseconds=999999),
            False,
            SlaStatus.WAITING,
            id='waiting'
        ),
        pytest.param(
            timedelta(minutes=30),
            False,
            SlaStatus.UNANSWERED_OVERDUE,
            id='unanswered_overdue'

        )
    ]
)
def test_calculate_status(
    business_duration: timedelta,
    answered: bool,
    expected: SlaStatus
) -> None:
    result = calculate_status(
        business_duration=business_duration,
        answered=answered
    )
    assert result == expected