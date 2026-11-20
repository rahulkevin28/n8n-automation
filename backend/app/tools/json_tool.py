import json
from typing import Any


def parse(value: str) -> Any:
    if not isinstance(value, str):
        raise TypeError("JSON parse input must be a string")
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError("invalid JSON") from exc


def stringify(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("value cannot be serialized as JSON") from exc


def get(value: Any, path: str) -> Any:
    if not isinstance(path, str) or not path:
        raise ValueError("JSON path is required")
    current = value
    for part in _parts(path):
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            raise KeyError(f"JSON path not found: {path}")
    return current


def set(value: Any, path: str, new_value: Any) -> Any:
    parts = _parts(path)
    if not parts:
        raise ValueError("JSON path is required")
    current = value
    for part in parts[:-1]:
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            raise KeyError(f"JSON path not found: {path}")
    last = parts[-1]
    if isinstance(current, dict):
        if last not in current:
            raise KeyError(f"JSON path not found: {path}")
        current[last] = new_value
    elif isinstance(current, list) and last.isdigit() and int(last) < len(current):
        current[int(last)] = new_value
    else:
        raise KeyError(f"JSON path not found: {path}")
    return value


def _parts(path: str) -> list[str]:
    parts = path.strip().split(".")
    if any(not part or part in {"__class__", "__dict__", "__globals__"} for part in parts):
        raise ValueError("invalid JSON path")
    return parts
