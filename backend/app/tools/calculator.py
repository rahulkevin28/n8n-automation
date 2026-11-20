import math
from typing import Any


def _number(value: Any) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("calculator inputs must be numbers")
    if not math.isfinite(value):
        raise ValueError("calculator inputs must be finite")
    return value


def add(a: int | float, b: int | float) -> int | float:
    return _number(a) + _number(b)


def subtract(a: int | float, b: int | float) -> int | float:
    return _number(a) - _number(b)


def multiply(a: int | float, b: int | float) -> int | float:
    return _number(a) * _number(b)


def divide(a: int | float, b: int | float) -> float:
    divisor = _number(b)
    if divisor == 0:
        raise ZeroDivisionError("cannot divide by zero")
    return _number(a) / divisor
