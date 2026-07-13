from __future__ import annotations
import copy
import sys
from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from dateutil import tz

if TYPE_CHECKING:
    from apps import hass as hass_module
else:
    hass_module = sys.modules.get("hass") or __import__("hass")


def _to_utc_timestamp_string(naive_local: datetime) -> str:
    utc_time = naive_local.replace(tzinfo=tz.tzlocal()).astimezone(
        tz.tzutc()
    )
    return utc_time.strftime("%Y-%m-%dT%H:%M:%S")


def patch_load_history(
    app_manager: hass_module.AppManager,
    history: Sequence[Sequence[tuple[datetime, str | int]]],
    race_value: str | None = None,
) -> None:
    converted: list[list[dict[str, str]]] = [
        [
            {
                "last_changed": _to_utc_timestamp_string(item[0]),
                "state": str(item[1]),
            }
            for item in entity_history
        ]
        for entity_history in history
    ]

    def patched_load_history(
        self: hass_module.Hass, _entity_id: str, _max_interval: timedelta
    ) -> list[list[dict[str, str]]]:
        if race_value is not None:
            app_manager.set_state("patch_load_history", _entity_id, race_value)
        return copy.deepcopy(converted)

    hass_module.Hass.load_history = patched_load_history  # type: ignore[method-assign, assignment]
