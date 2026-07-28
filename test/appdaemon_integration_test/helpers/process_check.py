from __future__ import annotations

import re

import psutil


def find_processes_matching_cmdline(pattern: str) -> list[tuple[int, str]]:
    regex = re.compile(pattern)
    matches: list[tuple[int, str]] = []
    for proc in psutil.process_iter(["pid", "cmdline"]):
        raw_cmdline: list[str] = proc.info.get("cmdline") or []
        if not raw_cmdline:
            continue
        cmdline_str = " ".join(raw_cmdline)
        if regex.search(cmdline_str):
            matches.append((proc.info["pid"], cmdline_str))
    return matches
