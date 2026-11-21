import pytest

from app.engine.executor import WorkflowExecutor


@pytest.mark.parametrize("action,inputs,expected", [
    ("add", {"a": 2, "b": 3}, 5),
    ("subtract", {"a": 7, "b": 2}, 5),
    ("multiply", {"a": 4, "b": 3}, 12),
    ("divide", {"a": 8, "b": 2}, 4),
])
def test_calculator_operations_use_registered_argument_names(action, inputs, expected):
    result = WorkflowExecutor().execute({"id": action, "name": action, "description": "", "steps": [{"id": "calc", "tool": "calculator", "action": action, "inputs": inputs}]})
    assert result.status == "success"
    assert result.steps[0].output == expected


def test_invalid_calculator_argument_names_fail_before_tool_execution():
    result = WorkflowExecutor().execute({"id": "bad", "name": "bad", "description": "", "steps": [{"id": "calc", "tool": "calculator", "action": "add", "inputs": {"value1": 2, "value2": 3}}]})
    assert result.status == "failed"
    assert "Invalid inputs for calculator.add" in (result.steps[0].error or "")
