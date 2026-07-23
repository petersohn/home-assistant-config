from __future__ import annotations

import re

import psutil


def find_processes_matching_cmdline(pattern: str) -> list[tuple[int, str]]:
    regex = re.compile(pattern)
    matches: list[tuple[int, str]] = []
    for proc in psutil.process_iter(["pid", "cmdline"]):
        cmdline = [c for c in proc.info.get("cmdline") or [] if c is not None]
        if not cmdline:
            continue
        cmdline_str = " ".join(cmdline)
        if regex.search(cmdline_str):
            matches.append((proc.info["pid"], cmdline_str))
    return matches
