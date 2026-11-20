import time

import pytest

from app.engine.executor import WorkflowExecutor
from app.engine.registry import ToolRegistry
from app.models.workflow import Workflow


def workflow(step):
    return Workflow(id="w", name="test", description="", steps=[step])


def test_retry_succeeds_after_transient_failure():
    calls = {"count": 0}
    registry = ToolRegistry()

    def flaky(**inputs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("temporary")
        return "ok"

    registry.register("mock", "flaky", flaky)
    result = WorkflowExecutor(registry).execute(workflow({"id": "s", "tool": "mock", "action": "flaky", "max_retries": 1}))
    assert result.status == "success"
    assert result.steps[0].attempts == 2


def test_retry_exhaustion_fails_and_reports_attempts():
    registry = ToolRegistry()
    registry.register("mock", "fail", lambda **inputs: (_ for _ in ()).throw(RuntimeError("boom")))
    result = WorkflowExecutor(registry).execute(workflow({"id": "s", "tool": "mock", "action": "fail", "max_retries": 2}))
    assert result.status == "failed"
    assert result.steps[0].attempts == 3
    assert result.steps[0].error == "boom"


def test_timeout_is_a_failed_step():
    registry = ToolRegistry()

    def slow(**inputs):
        time.sleep(0.05)
        return "late"

    registry.register("mock", "slow", slow)
    result = WorkflowExecutor(registry).execute(workflow({"id": "s", "tool": "mock", "action": "slow", "timeout_seconds": 0.001}))
    assert result.status == "failed"
    assert result.steps[0].attempts == 1
    assert "timed out" in (result.steps[0].error or "")


@pytest.mark.parametrize("field,value", [("max_retries", -1), ("max_retries", 6), ("timeout_seconds", 0)])
def test_invalid_execution_settings_are_rejected(field, value):
    with pytest.raises(ValueError):
        WorkflowExecutor().execute(workflow({"id": "s", "tool": "text", "action": "uppercase", "inputs": {"text": "x"}, field: value}))
