from typing import Any


OPERATORS = {"equals", "not_equals", "greater_than", "less_than", "contains", "is_empty"}


def if_condition(value: Any, operator: str, target: Any = None) -> bool:
    if operator not in OPERATORS:
        raise ValueError(f"unsupported condition operator: {operator}")
    if operator == "is_empty":
        return value is None or value == "" or value == [] or value == {}
    if operator == "equals": return value == target
    if operator == "not_equals": return value != target
    if operator == "greater_than":
        try: return value > target
        except TypeError as exc: raise TypeError("greater_than requires comparable values") from exc
    if operator == "less_than":
        try: return value < target
        except TypeError as exc: raise TypeError("less_than requires comparable values") from exc
    if operator == "contains":
        try: return target in value
        except TypeError as exc: raise TypeError("contains requires a collection or string") from exc
    raise ValueError(f"unsupported condition operator: {operator}")
