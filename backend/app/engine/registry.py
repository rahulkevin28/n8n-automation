from collections.abc import Callable
from typing import Any
import inspect


ToolFunction = Callable[..., Any]


class ToolRegistry:
    """Maps explicitly registered tool/action names to callable functions."""

    def __init__(self) -> None:
        self._tools: dict[str, dict[str, ToolFunction]] = {}

    def register(self, tool: str, action: str, function: ToolFunction) -> None:
        if tool in self._tools and action in self._tools[tool]:
            raise ValueError(f"Tool action already registered: {tool}.{action}")
        self._tools.setdefault(tool, {})[action] = function

    def get(self, tool: str, action: str) -> ToolFunction | None:
        return self._tools.get(tool, {}).get(action)

    def available_actions(self) -> dict[str, list[str]]:
        return {tool: sorted(actions) for tool, actions in sorted(self._tools.items())}

    def input_schema(self) -> dict[str, dict[str, list[str]]]:
        return {tool: {action: list(inspect.signature(function).parameters) for action, function in actions.items()} for tool, actions in self._tools.items()}

    def validate_inputs(self, tool: str, action: str, inputs: dict[str, Any]) -> None:
        function = self.get(tool, action)
        if function is None:
            raise ValueError(f"Unknown tool action: {tool}.{action}")
        try:
            inspect.signature(function).bind(**inputs)
        except TypeError as exc:
            raise ValueError(f"Invalid inputs for {tool}.{action}: {exc}") from exc


def create_default_registry() -> ToolRegistry:
    from app.tools.calculator import add, divide, multiply, subtract
    from app.tools.condition import if_condition
    from app.tools.json_tool import get, parse, set, stringify
    from app.tools.text import lowercase, replace_text, uppercase

    registry = ToolRegistry()
    for action, function in {
        "uppercase": uppercase,
        "lowercase": lowercase,
        "replace": replace_text,
    }.items():
        registry.register("text", action, function)
    for action, function in {
        "add": add,
        "subtract": subtract,
        "multiply": multiply,
        "divide": divide,
    }.items():
        registry.register("calculator", action, function)
    for action, function in {"parse": parse, "get": get, "set": set, "stringify": stringify}.items():
        registry.register("json", action, function)
    registry.register("condition", "if", if_condition)
    return registry
