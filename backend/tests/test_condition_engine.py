import pytest

from app.engine.executor import WorkflowExecutor
from app.tools.condition import if_condition


def wf(steps):
    return {"id": "conditional", "name": "conditional", "description": "test", "steps": steps}


def test_true_branch_runs_and_false_branch_is_skipped():
    result = WorkflowExecutor().execute(wf([
        {"id": "check", "tool": "condition", "action": "if", "inputs": {"value": 5, "operator": "greater_than", "target": 2}, "true_next": "yes", "false_next": "no"},
        {"id": "yes", "tool": "text", "action": "uppercase", "inputs": {"text": "true"}},
        {"id": "no", "tool": "text", "action": "uppercase", "inputs": {"text": "false"}},
    ]))
    assert result.status == "success"
    assert [(s.id, s.status) for s in result.steps] == [("check", "success"), ("yes", "success"), ("no", "skipped")]
    assert result.steps[0].output is True


def test_false_branch_runs_and_true_branch_is_skipped():
    result = WorkflowExecutor().execute(wf([
        {"id": "check", "tool": "condition", "action": "if", "inputs": {"value": "cat", "operator": "contains", "target": "z"}, "true_next": "yes", "false_next": "no"},
        {"id": "yes", "tool": "text", "action": "uppercase", "inputs": {"text": "yes"}},
        {"id": "no", "tool": "text", "action": "uppercase", "inputs": {"text": "no"}},
    ]))
    assert result.steps[0].output is False
    assert result.steps[1].status == "skipped"
    assert result.steps[2].status == "success"


def test_condition_can_use_ref_value():
    result = WorkflowExecutor().execute(wf([
        {"id": "value", "tool": "calculator", "action": "add", "inputs": {"a": 2, "b": 3}},
        {"id": "check", "tool": "condition", "action": "if", "inputs": {"value": {"$ref": "value"}, "operator": "equals", "target": 5}, "true_next": "yes", "false_next": "no"},
        {"id": "yes", "tool": "text", "action": "uppercase", "inputs": {"text": "ok"}},
        {"id": "no", "tool": "text", "action": "uppercase", "inputs": {"text": "bad"}},
    ]))
    assert result.status == "success"
    assert result.steps[1].output is True
    assert result.steps[2].status == "success"


@pytest.mark.parametrize("operator", ["bad", "greater_than"])
def test_invalid_condition_is_rejected(operator):
    with pytest.raises((ValueError, TypeError)):
        if_condition("x", operator)


def test_malformed_branch_is_rejected():
    with pytest.raises(ValueError, match="requires true_next"):
        WorkflowExecutor().execute(wf([{"id": "check", "tool": "condition", "action": "if", "inputs": {"value": 1, "operator": "equals", "target": 1}}]))


@pytest.mark.parametrize("value,expected", [("excellent", "EXCELLENT"), ("needs", "needs improvement")])
def test_condition_branch_merge_uses_executed_output(value, expected):
    result = WorkflowExecutor().execute(wf([
        {"id": "check", "tool": "condition", "action": "if", "inputs": {"value": value, "operator": "equals", "target": "excellent"}, "true_next": "classify_excellent", "false_next": "classify_needs_improvement"},
        {"id": "classify_excellent", "tool": "text", "action": "uppercase", "inputs": {"text": "excellent"}},
        {"id": "classify_needs_improvement", "tool": "text", "action": "lowercase", "inputs": {"text": "NEEDS IMPROVEMENT"}},
        {"id": "combine_results", "tool": "text", "action": "replace", "inputs": {"text": {"$ref": "classify_excellent"}, "old": " ", "new": " "}},
    ]))
    outputs = {step.id: step for step in result.steps}
    assert result.status == "success"
    assert outputs["combine_results"].output == expected
