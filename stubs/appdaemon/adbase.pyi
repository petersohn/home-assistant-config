from __future__ import annotations
from typing import Any

class ADBase:
    AD: Any
    config: dict[str, Any]
    args: dict[str, Any]
    _namespace: str
    logger: Any
    err: Any
    lock: Any
    user_logs: dict[str, Any]
    constraints: list[Any]
    entities: Any
    name: str

    def __init__(self, ad: Any, config_model: Any) -> None: ...