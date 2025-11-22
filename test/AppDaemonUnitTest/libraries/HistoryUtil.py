from robot.libraries import DateTime
from datetime import datetime
from typing import Any


def convert_history_input(args: list[str | int]) -> list[tuple[str, int]]:
    return [
        (DateTime.convert_date(args[i], result_format="timestamp"), args[i + 1])
        for i in range(0, len(args), 2)
    ]


def convert_history_output(
    result: list[tuple[datetime | str, float]],
) -> list[tuple[str, float]]:
    return [
        (DateTime.convert_date(date, result_format="timestamp"), int(value))
        for date, value in result
    ]


def is_expected_history_found(converted_input: Any, converted_output: Any):
    return all(i in converted_output for i in converted_input)
