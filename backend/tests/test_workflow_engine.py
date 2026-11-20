import pytest
from pydantic import ValidationError

from app.engine.executor import WorkflowExecutor
from app.engine.registry import ToolRegistry


def workflow(steps):
    return {"id": "wf", "name": "test", "description": "test workflow", "steps": steps}


def test_executes_sequentially_and_passes_previous_output():
    result = WorkflowExecutor().execute(workflow([
        {"id": "one", "tool": "text", "action": "uppercase", "inputs": {"text": "hello"}},
        {"id": "two", "tool": "text", "action": "replace", "inputs": {
            "text": {"$ref": "one"}, "old": "L", "new": "!"
        }},
    ]))
    assert result.status == "success"
    assert [step.output for step in result.steps] == ["HELLO", "HE!!O"]


def test_unknown_tool_fails_and_later_steps_are_skipped():
    result = WorkflowExecutor().execute(workflow([
        {"id": "bad", "tool": "missing", "action": "run", "inputs": {}},
        {"id": "later", "tool": "calculator", "action": "add", "inputs": {"a": 1, "b": 2}},
    ]))
    assert result.status == "failed"
    assert result.steps[0].status == "failed"
    assert "Unknown tool action" in result.steps[0].error
    assert result.steps[1].status == "skipped"


def test_invalid_workflow_data_is_rejected_before_execution():
    with pytest.raises(ValidationError):
        WorkflowExecutor().execute({"id": "wf", "name": "test", "description": "x", "steps": [
            {"id": "bad", "tool": "calculator", "action": "add", "inputs": "not a mapping"}
        ]})


def test_invalid_tool_inputs_are_reported_and_execution_continues_as_failed():
    result = WorkflowExecutor().execute(workflow([
        {"id": "bad", "tool": "calculator", "action": "add", "inputs": {"a": "one", "b": 2}},
        {"id": "later", "tool": "text", "action": "uppercase", "inputs": {"text": "ignored"}},
    ]))
    assert result.status == "failed"
    assert result.steps[0].status == "failed"
    assert result.steps[0].error == "calculator inputs must be numbers"
    assert result.steps[1].status == "skipped"


def test_tool_failure_is_captured_and_zero_division_does_not_crash_executor():
    result = WorkflowExecutor().execute(workflow([
        {"id": "divide", "tool": "calculator", "action": "divide", "inputs": {"a": 1, "b": 0}},
    ]))
    assert result.status == "failed"
    assert result.steps[0].error == "cannot divide by zero"


def test_registry_only_runs_explicitly_registered_functions():
    registry = ToolRegistry()
    registry.register("safe", "echo", lambda value: value)
    assert WorkflowExecutor(registry).execute(workflow([
        {"id": "one", "tool": "safe", "action": "echo", "inputs": {"value": "ok"}},
    ])).steps[0].output == "ok"
    with pytest.raises(ValueError):
        registry.register("safe", "echo", lambda value: value)
