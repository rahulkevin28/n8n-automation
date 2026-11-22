import json

import pytest

from app.engine.registry import create_default_registry
from app.services.workflow_planner import (
    InvalidPlannerResponse,
    InvalidToolSelection,
    WorkflowPlanner,
    WorkflowPlanningError,
)


VALID_WORKFLOW = {
    "id": "wf_1",
    "name": "Normalize text",
    "description": "Convert text to uppercase",
    "steps": [{"id": "step_1", "tool": "text", "action": "uppercase", "inputs": {"text": "hello"}}],
}


def test_planner_validates_gemini_workflow_json():
    prompts = []
    planner = WorkflowPlanner(response_generator=lambda prompt: prompts.append(prompt) or json.dumps(VALID_WORKFLOW))
    result = planner.plan("Make hello uppercase")
    assert result.id == VALID_WORKFLOW["id"]
    assert result.steps[0].inputs == VALID_WORKFLOW["steps"][0]["inputs"]
    assert '"calculator"' in prompts[0]
    assert "Never include code" in prompts[0]


def test_planner_accepts_json_markdown_fence():
    planner = WorkflowPlanner(response_generator=lambda _: f"```json\n{json.dumps(VALID_WORKFLOW)}\n```")
    assert planner.plan("uppercase hello").name == "Normalize text"


def test_planner_rejects_alias_response_when_tool_and_action_are_missing():
    malformed = {"workflow_id": "wf_legacy", "name": "Legacy", "description": "", "steps": [{"step_id": "s1", "inputs": {"text": "hello"}}]}
    with pytest.raises(InvalidPlannerResponse, match="tool"):
        WorkflowPlanner(response_generator=lambda _: json.dumps(malformed)).plan("uppercase hello")


def test_planner_normalizes_unambiguous_id_aliases_only():
    aliased = {"workflow_id": "wf_legacy", "name": "Legacy", "description": "", "steps": [{"step_id": "s1", "tool": "text", "action": "uppercase", "inputs": {"text": "hello"}}]}
    result = WorkflowPlanner(response_generator=lambda _: json.dumps(aliased)).plan("uppercase hello")
    assert result.id == "wf_legacy"
    assert result.steps[0].id == "s1"


@pytest.mark.parametrize("response", ["not json", "{}", json.dumps({**VALID_WORKFLOW, "steps": "invalid"})])
def test_planner_rejects_invalid_json_or_schema(response):
    with pytest.raises(InvalidPlannerResponse):
        WorkflowPlanner(response_generator=lambda _: response).plan("do something")


def test_planner_rejects_unregistered_tool_action():
    invalid = {**VALID_WORKFLOW, "steps": [{"id": "step", "tool": "os", "action": "system", "inputs": {}}]}
    with pytest.raises(InvalidToolSelection):
        WorkflowPlanner(response_generator=lambda _: json.dumps(invalid)).plan("run a command")


def test_gemini_failure_is_wrapped_without_leaking_details():
    def fail(_):
        raise RuntimeError("private provider detail")

    with pytest.raises(WorkflowPlanningError, match="generation failed") as error:
        WorkflowPlanner(response_generator=fail).plan("make a workflow")
    assert "private provider detail" not in str(error.value)


def test_empty_gemini_response_is_wrapped():
    with pytest.raises(WorkflowPlanningError, match="generation failed"):
        WorkflowPlanner(response_generator=lambda _: (_ for _ in ()).throw(RuntimeError("empty response"))).plan("make a workflow")


def test_registry_action_list_is_the_registered_tool_surface():
    assert create_default_registry().available_actions() == {
        "calculator": ["add", "divide", "multiply", "subtract"],
        "condition": ["if"],
        "json": ["get", "parse", "set", "stringify"],
        "text": ["lowercase", "replace", "uppercase"],
    }


def test_planner_accepts_refs_branches_and_execution_settings():
    workflow = {"id": "wf", "name": "branch", "description": "", "steps": [
        {"id": "text", "tool": "text", "action": "uppercase", "inputs": {"text": "x"}, "max_retries": 1, "timeout_seconds": 2},
        {"id": "check", "tool": "condition", "action": "if", "inputs": {"value": {"$ref": "text"}, "operator": "equals", "target": "X"}, "true_next": "yes", "false_next": "no"},
        {"id": "yes", "tool": "text", "action": "lowercase", "inputs": {"text": {"$ref": "text"}}},
        {"id": "no", "tool": "text", "action": "replace", "inputs": {"text": "x", "old": "x", "new": "y"}},
    ]}
    result = WorkflowPlanner(response_generator=lambda _: json.dumps(workflow)).plan("branch")
    assert result.steps[1].true_next == "yes"
    assert result.steps[0].max_retries == 1


def test_planner_condition_requires_value_and_operator():
    base = {"id": "wf", "name": "branch", "description": "", "steps": [{"id": "check", "tool": "condition", "action": "if", "inputs": {"operator": "equals", "target": "yes"}, "true_next": "yes", "false_next": "no"}, {"id": "yes", "tool": "text", "action": "uppercase", "inputs": {"text": "y"}}, {"id": "no", "tool": "text", "action": "uppercase", "inputs": {"text": "n"}}]}
    with pytest.raises(InvalidPlannerResponse, match="requires a value"):
        WorkflowPlanner(response_generator=lambda _: json.dumps(base)).plan("check")
    base["steps"][0]["inputs"] = {"value": "yes", "target": "yes"}
    with pytest.raises(InvalidPlannerResponse, match="requires an operator"):
        WorkflowPlanner(response_generator=lambda _: json.dumps(base)).plan("check")


def test_planner_corrects_invalid_condition_on_regeneration():
    invalid = {"id": "wf", "name": "branch", "description": "", "steps": [{"id": "s5_check_sales_performance", "tool": "condition", "action": "if", "inputs": {"value": {"$ref": "sales_step"}}, "true_next": "yes", "false_next": "no"}, {"id": "yes", "tool": "text", "action": "uppercase", "inputs": {"text": "y"}}, {"id": "no", "tool": "text", "action": "uppercase", "inputs": {"text": "n"}}]}
    valid = {**invalid, "steps": [{**invalid["steps"][0], "inputs": {"value": "sales", "operator": "equals", "target": "good"}}, *invalid["steps"][1:]]}
    prompts = []
    result = WorkflowPlanner(response_generator=lambda prompt: prompts.append(prompt) or json.dumps(invalid if len(prompts) == 1 else valid)).plan("check sales performance")
    assert result.steps[0].inputs["operator"] == "equals"
    assert "requires an operator" in prompts[1]
    assert "check sales performance" in prompts[1]


def test_planner_regenerates_once_after_invalid_response():
    responses = iter(["not json", json.dumps(VALID_WORKFLOW)])
    result = WorkflowPlanner(response_generator=lambda _: next(responses)).plan("uppercase")
    assert result.id == "wf_1"


def test_planner_rejects_future_reference_after_single_recovery_attempt():
    invalid = {**VALID_WORKFLOW, "steps": [{"id": "one", "tool": "text", "action": "uppercase", "inputs": {"text": {"$ref": "two"}}}, {"id": "two", "tool": "text", "action": "uppercase", "inputs": {"text": "x"}}]}
    with pytest.raises(InvalidPlannerResponse, match="future step"):
        WorkflowPlanner(response_generator=lambda _: json.dumps(invalid)).plan("bad ref")
