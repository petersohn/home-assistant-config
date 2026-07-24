from __future__ import annotations

from datetime import datetime
from unit_helpers.history_util import convert_history_input, convert_history_output


def test_convert_history_input() -> None:
    expected = [
        ("2019-01-01 00:00:00", 3),
        ("2019-02-03 01:21:04", 50),
        ("2019-01-10 12:05:00", -1),
    ]
    result = convert_history_input([
        "2019-01-01", 3,
        "20190203T012104", 50,
        "2019-01-10 12:05:00.123", -1,
    ])
    assert result == expected


def test_convert_history_output() -> None:
    expected = [
        ("2019-01-01 00:00:00", 3),
        ("2019-02-03 01:21:04", 50),
        ("2019-01-10 12:05:00", -1),
    ]
    result = convert_history_output([
        (datetime(2019, 1, 1), 3.0),
        (datetime(2019, 2, 3, 1, 21, 4), 50.01),
        (datetime(2019, 1, 10, 12, 5, 0, 123000), -1.0),
    ])
    assert result == expected