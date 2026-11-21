import pytest

from app.engine.executor import WorkflowExecutor
from app.tools.json_tool import get, parse, set, stringify


def test_json_actions():
    assert parse('{"name":"Ada","items":[1,2]}')["name"] == "Ada"
    assert get({"user": {"name": "Ada"}}, "user.name") == "Ada"
    assert get({"base_salary": 2000}, "$.base_salary") == 2000
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


def test_sales_commission_data_flow_uses_parsed_object_and_json_paths():
    result = WorkflowExecutor().execute({"id": "sales", "name": "Sales commission", "description": "", "steps": [
        {"id": "parse_initial_data", "tool": "json", "action": "parse", "inputs": {"value": '{"base_salary":2000,"total_sales":12000}'}},
        {"id": "get_base_salary", "tool": "json", "action": "get", "inputs": {"value": {"$ref": "parse_initial_data"}, "path": "$.base_salary"}},
        {"id": "get_total_sales", "tool": "json", "action": "get", "inputs": {"value": {"$ref": "parse_initial_data"}, "path": "$.total_sales"}},
        {"id": "commission", "tool": "calculator", "action": "multiply", "inputs": {"a": {"$ref": "get_total_sales"}, "b": 0.1}},
        {"id": "earnings", "tool": "calculator", "action": "add", "inputs": {"a": {"$ref": "get_base_salary"}, "b": {"$ref": "commission"}}},
    ]})
    assert result.status == "success"
    assert result.steps[-1].output == 3200


@pytest.mark.parametrize("path", ["base_salary", "$.base_salary", "total_sales", "$.total_sales"])
def test_set_paths_work_on_the_exact_parsed_sales_object(path):
    result = WorkflowExecutor().execute({"id": "set-sales", "name": "set", "description": "", "steps": [
        {"id": "parse_initial_data", "tool": "json", "action": "parse", "inputs": {"value": '{"base_salary":2000,"total_sales":12000}'}},
        {"id": "set_value", "tool": "json", "action": "set", "inputs": {"value": {"$ref": "parse_initial_data"}, "path": path, "new_value": 999}},
    ]})
    assert result.status == "success"
    assert result.steps[-1].output[path.removeprefix("$.")] == 999


@pytest.mark.parametrize("path", ["base_salary", "$.base_salary"])
def test_set_can_initialize_missing_final_key(path):
    assert set({}, path, 2000) == {"base_salary": 2000}


def test_sales_output_initialization_preserves_sequentially_added_fields():
    result = WorkflowExecutor().execute({"id": "sales-output", "name": "Sales output", "description": "", "steps": [
        {"id": "init_output_excellent", "tool": "json", "action": "set", "inputs": {"value": {}, "path": "base_salary", "new_value": 2000}},
        {"id": "add_commission", "tool": "json", "action": "set", "inputs": {"value": {"$ref": "init_output_excellent"}, "path": "commission", "new_value": 1200}},
        {"id": "add_total", "tool": "json", "action": "set", "inputs": {"value": {"$ref": "add_commission"}, "path": "total_earnings", "new_value": 3200}},
    ]})
    assert result.status == "success"
    assert result.steps[-1].output == {"base_salary": 2000, "commission": 1200, "total_earnings": 3200}
