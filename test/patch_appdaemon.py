"""Patch the installed AppDaemon library to drop stale apps from its
in-memory config, to tolerate the resulting lookup miss in
``stop_app``, and to remove stopped apps from ``self.objects`` during
config-driven termination.

The upstream 4.5.13 release accumulates every app that has ever been
loaded in ``AppManagement.app_config.root`` because the line that
removes a deleted app is commented out. On the next config change
every stale app is re-instantiated as a side effect of restarting
its (also stale) dependency, which prevents the integration test
teardown from draining the running set within its 30s window.

A second issue (introduced post-4.5.13 by upstream commit e9480ecc)
changed ``resolve_thread_counts`` to count pinned apps from
``self.objects`` instead of ``app_config.root``.  ``_stop_apps``
calls ``stop_app`` with the default ``delete=False``, which leaves
terminated entries in ``self.objects``.  Once the first patch removes
the stale entries from ``app_config.root`` but not ``self.objects``,
the two counts diverge and ``assert total_threads >= pin_threads``
fires in ``threads.py``, preventing apps from loading.

The fix is to pass ``delete=True`` from ``_stop_apps`` so that
terminated apps are removed from ``self.objects`` as well, keeping
both counts in sync.  ``create_app_object`` unconditionally
overwrites ``self.objects[app_name]``, so reloading apps are not
affected.

This script applies the obvious upstream-style fix in place. It is
safe to re-run: all edits are no-ops once the patched source is in
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

    delete_needle = (
        "        for app_name in stop_order:\n"
        "            successfully_stopped = await self.stop_app(app_name)\n"
    )
    delete_replacement = (
        "        for app_name in stop_order:\n"
        "            successfully_stopped = await self.stop_app(app_name, delete=True)\n"
    )
    if delete_needle in src:
        src = src.replace(delete_needle, delete_replacement, 1)
        print("patched _stop_apps to delete objects on termination")
    elif delete_replacement in src:
        print("_stop_apps already patched")
    else:
        print(
            "error: could not locate the _stop_apps call; AppDaemon source may have changed",
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
