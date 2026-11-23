import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.workflows import WorkflowPlanRequest
from app.core.rate_limit import InMemoryRateLimiter


def test_rate_limiter_rejects_after_limit_with_retry_after():
    limiter = InMemoryRateLimiter()
    limiter.check("test", "client", limit=1)
    with pytest.raises(HTTPException) as error:
        limiter.check("test", "client", limit=1)
    assert error.value.status_code == 429
    assert error.value.headers["Retry-After"]


def test_rate_limiter_scopes_clients_independently():
    limiter = InMemoryRateLimiter()
    limiter.check("test", "one", limit=1)
    limiter.check("test", "two", limit=1)


def test_planning_task_has_a_reasonable_size_limit():
    with pytest.raises(ValidationError):
        WorkflowPlanRequest(task_description="x" * 4001)
