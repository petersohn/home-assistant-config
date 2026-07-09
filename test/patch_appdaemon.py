"""Patch the installed AppDaemon library to drop stale apps from its
in-memory config and to tolerate the resulting lookup miss in
``stop_app``.

The upstream 4.5.13 release accumulates every app that has ever been
loaded in ``AppManagement.app_config.root`` because the line that
removes a deleted app is commented out. On the next config change
every stale app is re-instantiated as a side effect of restarting
its (also stale) dependency, which prevents the integration test
teardown from draining the running set within its 30s window.

This script applies the obvious upstream-style fix in place. It is
safe to re-run: both edits are no-ops once the patched source is in
place.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


def main(app_management_path: Path) -> int:
    src = app_management_path.read_text()

    deletion_needle = (
        "            for name in deleted_apps:\n"
        "                # del self.app_config.root[name]\n"
        "                self.logger.info(\"App config deleted: %s\", name)\n"
    )
    deletion_replacement = (
        "            for name in deleted_apps:\n"
        "                self.app_config.root.pop(name, None)\n"
        "                self.logger.info(\"App config deleted: %s\", name)\n"
    )
    if deletion_needle in src:
        src = src.replace(deletion_needle, deletion_replacement, 1)
        print("patched check_app_config_files to drop deleted apps")
    elif deletion_replacement in src:
        print("check_app_config_files already patched")
    else:
        print(
            "error: could not locate the deletion site; AppDaemon source may have changed",
            file=sys.stderr,
        )
        return 1

    stop_needle = (
        "        try:\n"
        "            if isinstance(self.app_config[app_name], AppConfig):\n"
    )
    stop_replacement = (
        "        try:\n"
        "            if isinstance(self.app_config.root.get(app_name), AppConfig):\n"
    )
    if stop_needle in src and stop_replacement not in src:
        src = src.replace(stop_needle, stop_replacement, 1)
        print("patched stop_app to tolerate missing config entries")
    elif stop_replacement in src:
        print("stop_app already patched")
    else:
        print(
            "error: could not locate the stop_app lookup; AppDaemon source may have changed",
            file=sys.stderr,
        )
        return 1

    app_management_path.write_text(src)
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <path-to-app_management.py>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(Path(sys.argv[1])))
