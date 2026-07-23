from typing import Any


def convert_history_output(result: list[tuple[Any, Any]]) -> list[Any]:
    return [i[1] for i in result]
