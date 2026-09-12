from collections.abc import Sequence
from datetime import datetime
from dateutil import parser as date_parser
def convert_history_input(
    args: Sequence[datetime | str | int],
) -> list[tuple[str, int]]:
    result: list[tuple[str, int]] = []
    for i in range(0, len(args), 2):
        timestamp, value = args[i], args[i + 1]
        assert isinstance(value, int)
        result.append((_convert_timestamp(timestamp), value))
    return result


def _convert_timestamp(value: str | int | datetime) -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    parsed = date_parser.parse(str(value))
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def convert_history_output(
    result: list[tuple[datetime | str, float]],
) -> list[tuple[str, int]]:
    return [
        (_convert_timestamp(date), int(value))
        for date, value in result
    ]


def is_expected_history_found(
    converted_input: list[tuple[str, int]],
    converted_output: list[tuple[str, int]],
) -> bool:
    return all(i in converted_output for i in converted_input)