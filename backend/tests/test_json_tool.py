import pytest

from app.engine.executor import WorkflowExecutor
from app.tools.json_tool import get, parse, set, stringify


def test_json_actions():
    assert parse('{"name":"Ada","items":[1,2]}')["name"] == "Ada"
    assert get({"user": {"name": "Ada"}}, "user.name") == "Ada"
    value = {"user": {"name": "Ada"}}
    assert set(value, "user.name", "Grace") == {"user": {"name": "Grace"}}
    assert stringify({"ok": True, "n": 2}) == '{"ok":true,"n":2}'


@pytest.mark.parametrize("function,args", [
    (parse, ("not json",)),
    (get, ({"a": 1}, "missing.key")),
    (set, ({"a": 1}, "missing.key", 2)),
    (stringify, ({"value": float("nan")},)),
])
def test_json_actions_reject_invalid_inputs(function, args):
    with pytest.raises((ValueError, KeyError, TypeError)):
        function(*args)


def test_json_tool_is_registered_and_supports_references():
    result = WorkflowExecutor().execute({"id": "json-wf", "name": "json", "description": "json", "steps": [
        {"id": "parsed", "tool": "json", "action": "parse", "inputs": {"value": "{\"name\":\"Ada\"}"}},
        {"id": "name", "tool": "json", "action": "get", "inputs": {"value": {"$ref": "parsed"}, "path": "name"}},
    ]})
    assert result.status == "success"
    assert result.steps[-1].output == "Ada"
