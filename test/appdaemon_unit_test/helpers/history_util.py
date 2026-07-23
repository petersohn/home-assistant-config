from robot.libraries import DateTime
from datetime import datetime
from typing import Any


def convert_history_input(args: list[str | int]) -> list[tuple[str, int]]:
    return [
        (_convert_timestamp(args[i]), int(args[i + 1]))
        for i in range(0, len(args), 2)
    ]


def _convert_timestamp(value: str | int | datetime) -> str:
    timestamp = DateTime.convert_date(value, result_format="timestamp")
    assert isinstance(timestamp, str)
    return timestamp


def convert_history_output(
    result: list[tuple[datetime | str, float]],
) -> list[tuple[str, float]]:
    return [
        (_convert_timestamp(date), int(value))
        for date, value in result
    ]


def is_expected_history_found(
    converted_input: Any, converted_output: Any
) -> bool:
    return all(i in converted_output for i in converted_input)
