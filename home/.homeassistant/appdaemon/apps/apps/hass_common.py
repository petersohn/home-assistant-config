from __future__ import annotations

from typing import TypeAlias

AttributeValue: TypeAlias = (
    str | int | float | bool | None
    | list["AttributeValue"]
    | dict[str, "AttributeValue"]
)
EntityValue: TypeAlias = str | dict[str, AttributeValue] | None
HistoryChange = dict[str, str]
HistoryResult = list[list[HistoryChange]]
