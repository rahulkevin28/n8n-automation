import json
import logging
import re
from collections.abc import Callable
from typing import Any

from pydantic import ValidationError

from app.engine.registry import ToolRegistry, create_default_registry
from app.engine.executor import _validate_workflow_structure
from app.models.workflow import Workflow
from app.services.gemini_service import generate_response

logger = logging.getLogger(__name__)


class WorkflowPlanningError(Exception):
    """Base error for turning a task description into a workflow."""


class InvalidPlannerResponse(WorkflowPlanningError):
    pass


class InvalidToolSelection(WorkflowPlanningError):
    pass


class WorkflowPlanner:
    def __init__(
        self,
        registry: ToolRegistry | None = None,
        response_generator: Callable[[str], str] | None = None,
    ) -> None:
        self.registry = registry or create_default_registry()
        self.response_generator = response_generator or generate_response

    def plan(self, task_description: str) -> Workflow:
        actions = self.registry.available_actions()
        prompt = (
            "Create the simplest workflow that completes the user's task. Return only one JSON object "
            "matching the Workflow schema: id, name, description, steps. Each step has id, tool, action, "
            "inputs and may have max_retries (0-5), timeout_seconds (>0), true_next and false_next. "
            f"The only allowed tool actions are {json.dumps(actions)}. "
            "Use sequential steps and $ref objects such as {\"$ref\":\"step_id\"} when a step needs "
            "a previous output. Every condition.if step MUST have inputs.value and inputs.operator. "
            "operator MUST be exactly one of equals, not_equals, greater_than, less_than, contains, is_empty. "
            "For every operator except is_empty, inputs.target is also required. A valid condition example is "
            "{\"id\":\"check_sales_performance\",\"tool\":\"condition\",\"action\":\"if\","
            "\"inputs\":{\"value\":{\"$ref\":\"sales_step\"},\"operator\":\"greater_than\",\"target\":100},"
            "\"true_next\":\"high_sales\",\"false_next\":\"low_sales\"}. "
            "Condition values must be a literal or a valid reference to a previous step output; never omit them. "
            "Never invent tools/actions, include executable code (Never include code), generate Python, execute code, or omit a branch. Avoid unnecessary nodes. "
            f"Task: {task_description}"
        )
        last_error: WorkflowPlanningError | None = None
        current_prompt = prompt
        for attempt in range(2):
            try:
                raw = self.response_generator(current_prompt)
            except Exception as exc:
                logger.exception("Workflow planner response generation failed")
                raise WorkflowPlanningError("Workflow generation failed") from exc
            try:
                data: Any = json.loads(_strip_json_fence(raw))
                workflow = Workflow.model_validate(data)
                for step in workflow.steps:
                    if self.registry.get(step.tool, step.action) is None:
                        raise InvalidToolSelection(f"Workflow selected an unavailable tool action: {step.tool}.{step.action}")
                _validate_workflow_structure(workflow)
                _validate_references(workflow)
                return workflow
            except InvalidToolSelection:
                raise
            except (json.JSONDecodeError, TypeError, ValidationError, ValueError) as exc:
                last_error = InvalidPlannerResponse(f"Gemini returned invalid workflow: {exc}")
                if attempt == 0:
                    current_prompt = (
                        f"The workflow JSON for this task was rejected: {task_description}\n"
                        f"Exact validation error: {exc}\n"
                        "Return a complete corrected Workflow JSON object, not a patch. For every condition.if step, "
                        "include inputs.value, inputs.operator from [equals, not_equals, greater_than, less_than, contains, is_empty], "
                        "and inputs.target unless operator is is_empty. Preserve valid step IDs, references, and true_next/false_next."
                    )
                    continue
        raise last_error or InvalidPlannerResponse("Gemini returned invalid workflow")


def _strip_json_fence(response: str) -> str:
    match = re.fullmatch(r"\s*```(?:json)?\s*(.*?)\s*```\s*", response, re.DOTALL | re.IGNORECASE)
    return match.group(1) if match else response


def _validate_references(workflow: Workflow) -> None:
    known = {step.id for step in workflow.steps}
    for index, step in enumerate(workflow.steps):
        prior = {item.id for item in workflow.steps[:index]}

        def visit(value: Any) -> None:
            if isinstance(value, dict):
                if set(value) == {"$ref"}:
                    ref = value["$ref"]
                    if not isinstance(ref, str) or ref not in known or ref not in prior:
                        raise ValueError(f"step {step.id} references an unknown or future step: {ref!r}")
                else:
                    for item in value.values(): visit(item)
            elif isinstance(value, list):
                for item in value: visit(item)

        visit(step.inputs)
