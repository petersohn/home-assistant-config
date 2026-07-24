from typing import Any


def extract_from_dictionary(dictionary: dict[Any, Any], key: Any) -> Any:
    result = None
    if key in dictionary:
        result = dictionary[key]
        del dictionary[key]
    return result


def _try_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def values_equal(a: Any, b: Any) -> bool:
    """Compare two values with numeric coercion.

    Mimics Robot Framework's ``Should Be Equal`` semantics: if both values
    can be converted to floats, compare them numerically so that a state
    string like ``"0"`` equals the expected float ``0.0``. Otherwise fall
    back to a direct equality check.
    """
    fa, fb = _try_float(a), _try_float(b)
    if fa is not None and fb is not None:
        return fa == fb
    return a == b
