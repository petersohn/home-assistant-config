from __future__ import annotations

from typing import Any

EntityValue = str | dict[str, Any] | None
HistoryChange = dict[str, str]
HistoryResult = list[list[HistoryChange]]