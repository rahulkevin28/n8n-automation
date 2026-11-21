from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any, Literal
import threading

from pydantic import ValidationError

from app.engine.registry import ToolRegistry, create_default_registry
from app.models.workflow import Workflow


@dataclass
class StepResult:
    id: str
    status: Literal["success", "failed", "skipped"]
    output: Any = None
    error: str | None = None
    attempts: int = 0


@dataclass
class WorkflowResult:
    workflow_id: str
    status: Literal["success", "failed"]
    steps: list[StepResult]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class WorkflowExecutor:
    def __init__(self, registry: ToolRegistry | None = None) -> None:
        self.registry = registry or create_default_registry()

    def execute(self, workflow: Workflow | Mapping[str, Any]) -> WorkflowResult:
        # Revalidate even existing model instances, so callers cannot bypass validation.
        validated = Workflow.model_validate(
            workflow.model_dump() if isinstance(workflow, Workflow) else workflow
        )
        _validate_workflow_structure(validated)
        results: list[StepResult] = []
        outputs: dict[str, Any] = {}
        reference_aliases: dict[str, str] = {}
        failed = False
        by_id = {step.id: step for step in validated.steps}
        branch_targets = {target for step in validated.steps if step.tool == "condition" for target in (step.true_next, step.false_next)}
        current_id = validated.steps[0].id if validated.steps else None
        visited: set[str] = set()
        branch_continuation: int | None = None

        while current_id is not None:
            if current_id in visited:
                raise ValueError("workflow contains a cycle")
            visited.add(current_id)
            step = by_id[current_id]
            function = self.registry.get(step.tool, step.action)
            if function is None:
                results.append(StepResult(
                    step.id, "failed", error=f"Unknown tool action: {step.tool}.{step.action}"
                ))
                failed = True
                break
            attempts = 0
            try:
                inputs = _resolve_references(step.inputs, outputs, reference_aliases)
                while True:
                    attempts += 1
                    try:
                        output = _call_with_timeout(function, inputs, step.timeout_seconds)
                        break
                    except Exception:
                        if attempts > step.max_retries:
                            raise
                outputs[step.id] = output
                results.append(StepResult(step.id, "success", output=output, attempts=attempts))
                if step.tool == "condition" and step.action == "if":
                    selected = step.true_next if output else step.false_next
                    unselected = step.false_next if output else step.true_next
                    if selected and unselected:
                        reference_aliases[unselected] = selected
                        branch_continuation = max(
                            next(index for index, item in enumerate(validated.steps) if item.id == selected),
                            next(index for index, item in enumerate(validated.steps) if item.id == unselected),
                        ) + 1
                    current_id = selected
                else:
                    index = validated.steps.index(step)
                    next_index = branch_continuation if step.id in branch_targets and branch_continuation is not None else index + 1
                    current_id = validated.steps[next_index].id if next_index < len(validated.steps) else None
            except Exception as exc:
                message = str(exc)
                results.append(StepResult(step.id, "failed", error=message, attempts=attempts))
                failed = True
                break
        executed = {item.id for item in results}
        for step in validated.steps:
            if step.id not in executed:
                results.append(StepResult(step.id, "skipped", error="Unselected condition branch"))
        results.sort(key=lambda item: next(index for index, step in enumerate(validated.steps) if step.id == item.id))
        return WorkflowResult(validated.id, "failed" if failed else "success", results)


def _validate_workflow_structure(workflow: Workflow) -> None:
    by_id = {step.id: step for step in workflow.steps}
    if len(by_id) != len(workflow.steps):
        raise ValueError("workflow contains duplicate step IDs")
    for step in workflow.steps:
        if step.true_next and step.true_next not in by_id or step.false_next and step.false_next not in by_id:
            raise ValueError(f"condition branch references an unknown step from {step.id}")
        if step.tool == "condition":
            if step.action != "if" or not step.true_next or not step.false_next:
                raise ValueError(f"condition step {step.id} requires true_next and false_next")
            if "value" not in step.inputs:
                raise ValueError(f"condition step {step.id} requires a value")
            if "operator" not in step.inputs:
                raise ValueError(f"condition step {step.id} requires an operator")
            operators = {"equals", "not_equals", "greater_than", "less_than", "contains", "is_empty"}
            if step.inputs["operator"] not in operators:
                raise ValueError(f"condition step {step.id} has invalid operator: {step.inputs['operator']!r}")
            if step.inputs["operator"] != "is_empty" and "target" not in step.inputs:
                raise ValueError(f"condition step {step.id} requires a comparison target")
        elif step.true_next or step.false_next:
            raise ValueError(f"only condition steps may define branches: {step.id}")
    adjacency: dict[str, list[str]] = {}
    for index, step in enumerate(workflow.steps):
        if step.tool == "condition":
            adjacency[step.id] = [step.true_next, step.false_next]  # type: ignore[list-item]
        elif index + 1 < len(workflow.steps):
            adjacency[step.id] = [workflow.steps[index + 1].id]
        else:
            adjacency[step.id] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(step_id: str) -> None:
        if step_id in visiting:
            raise ValueError("workflow contains a cycle")
        if step_id in visited:
            return
        visiting.add(step_id)
        for next_id in adjacency[step_id]:
            visit(next_id)
        visiting.remove(step_id)
        visited.add(step_id)

    for step_id in adjacency:
        visit(step_id)


def _resolve_references(value: Any, outputs: dict[str, Any], aliases: dict[str, str] | None = None) -> Any:
    aliases = aliases or {}
    if isinstance(value, dict):
        if set(value) == {"$ref"}:
            step_id = value["$ref"]
            step_id = aliases.get(step_id, step_id)
            if not isinstance(step_id, str) or step_id not in outputs:
                raise ValueError(f"Unknown or unavailable step output reference: {step_id!r}")
            return outputs[step_id]
        return {key: _resolve_references(item, outputs, aliases) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve_references(item, outputs, aliases) for item in value]
    return value


def _call_with_timeout(function: Any, inputs: dict[str, Any], timeout_seconds: float | None) -> Any:
    if timeout_seconds is None:
        return function(**inputs)
    result: list[Any] = []
    error: list[BaseException] = []

    def run() -> None:
        try:
            result.append(function(**inputs))
        except BaseException as exc:
            error.append(exc)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    thread.join(timeout_seconds)
    if thread.is_alive():
        raise TimeoutError(f"step execution timed out after {timeout_seconds:g} seconds; background work may still be running")
    if error:
        raise error[0]
    return result[0] if result else None
