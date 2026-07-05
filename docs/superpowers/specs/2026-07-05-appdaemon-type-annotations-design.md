# Add type annotations to AppDaemon apps

Date: 2026-07-05

## Goal

Annotate every AppDaemon app module under `home/.homeassistant/appdaemon/apps/`
so that `mypy` passes with zero errors using the existing config in
`pyproject.toml`:

```toml
[tool.mypy]
warn_no_return = true
disallow_untyped_defs = true
disallow_untyped_calls = true
```

## Scope

In scope (16 files):

- All 14 app modules in `home/.homeassistant/appdaemon/apps/`:
  `alert.py`, `auto_switch.py`, `cover.py`, `custom_icon.py`,
  `enabled_switch.py`, `enabler.py`, `expression.py`, `hass.py`,
  `history.py`, `locker.py`, `mutex_graph.py`, `temperature_basic.py`,
  `timer_switch.py`, `wind_direction.py`.
- `pyproject.toml`: extend `[tool.mypy]` with `mypy_path` and `files`.
- `test/AppDaemonUnitTest/apps/hass.py`: align the unit-test mock with the
  callback-shape change below.

Out of scope:

- appdaemon itself (third party, on `mypy_path`).
- `test/AppDaemonIntegrationTest/` and any other tests besides the mock.
- Behavioral changes to apps. Editing comments is out of scope.

## Setup

Extend `[tool.mypy]` in `pyproject.toml`:

```toml
[tool.mypy]
warn_no_return = true
disallow_untyped_defs = true
disallow_untyped_calls = true
files = ["home/.homeassistant/appdaemon/apps"]
```

Type checking must run from a dedicated Python 3.12 virtual environment
that has `appdaemon` and `python-dateutil` installed, because the
integration-test appdaemon venv bundles a `typing_extensions.py` (and
submodules named after stdlib modules, e.g. `appdaemon/types.py`) that
conflict with the system Python 3.14 `mypy`. Create it once:

```sh
uv venv --python 3.12 .typecheck-venv
.typecheck-venv/bin/python -m pip install appdaemon python-dateutil mypy
```

Run mypy from the venv:

```sh
.typecheck-venv/bin/mypy
```

When run from the venv, `appdaemon` and `dateutil` are on `sys.path` and
mypy resolves them with no `mypy_path` needed.

## Typing decisions

### Hass base class

Real appdaemon `appdaemon.plugins.hass.hassapi.Hass` extends `ADBase, ADAPI`.
The methods the apps call (`get_state`, `set_state`, `listen_state`, `run_in`,
`run_at`, `run_every`, `run_daily`, `cancel_timer`, `turn_on`, `turn_off`,
`select_option`, `get_app`, `log`, `error`, `call_service`) are wrapped with
`@utils.sync_decorator`, which rewrites `async def` to a sync `def` with the
same return type. So the apps' sync usage type-checks against the real async
signatures directly — no stub, no async/sync bridge needed.

`self.args` is `dict[str, Any]` on `ADAPI`; indexing yields `Any`, which we
narrow with explicit `str(...)` / `float(...)` / `bool(...)` / `dict(...)`
calls already present in the code or added minimally at read sites.

### get_state return type

`def get_state(...) -> str | dict[str, Any] | None` — matching the unit-test
mock (`test/AppDaemonUnitTest/apps/hass.py:441-445`). The real appdaemon
signature is wider (`Any | dict[str, Any] | None`); this annotation on the
*app-side* callbacks matches the mock so unit tests and the real base both
satisfy the type. **Narrow with `assert isinstance(x, dict)`, not `cast`.**

Call sites that index into a `dict` (e.g. `states["state"]`,
`states["attributes"]["icon"]`) get an `assert isinstance(x, dict)` guard
before the indexing. The mock test already uses `assert type(state) is
dict`; we follow the same pattern but with `isinstance` for typing.

`set_state(self, entity_id, state=..., attributes=...) -> None`. Per-file
typed as called. `attribute='all'` arg used by some apps is a literal the
real base accepts.

### listen_state callbacks — drop `kwargs`

All app `listen_state` callbacks currently have a final positional `kwargs`
parameter that is never read. **Remove it.** New signature shape:

```python
def on_change(self, entity: str, attribute: str | None, old: Any, new: Any) -> None: ...
```

(Individual sites may type `old`/`new` more specifically where helpful, but
`Any` is the default.)

This is compatible with appdaemon's `StateCallback` Protocol
(`__call__(self, entity, attribute, old, new, **kwargs: Any) -> None`): a
function that accepts *fewer* kwargs is still callable from a call site that
passes more. mypy's structural protocol check accepts this. No `# type:
ignore`.

Files with `listen_state` callbacks to update (drop `kwargs`, add types):
`wind_direction.py`, `custom_icon.py`, `temperature_basic.py`,
`auto_switch.py`, `enabled_switch.py`? (no — uses `get_app`), `cover.py`,
`timer_switch.py` (Trigger), `history.py` (HistoryManager/ChangeTracker),
`enabler.py` (EntityEnabler), `alert.py`? (no), `auto_switch.py`
(on_target_change/on_switch_change).

Scheduled callbacks (`run_in`/`run_every`/`run_daily` → `on_timeout`,
`on_delay`, `on_interval`, `on_timeout` in Timer/TimerSequence, `fire_callback`
in expression) **keep** their positional `kwargs` argument — `run_in`'s
callback is typed bare `Callable` (no Protocol), and these bodies read
`kwargs["value"]` (cover `on_delay`). They get `kwargs: dict[str, Any]`.

### get_app downcasts (via assert, not cast)

`get_app(name: str) -> ADAPI` returns the base `ADAPI`, which does not
declare `get_mutex`, `is_enabled`, `add_callback`, `remove_callback`,
`get_history`, `last_changed`, `last_updated`, `entity_id`, `mutex`. At each
call site that needs a specific app's API, do **runtime imports** of the
expected sibling app and `assert isinstance(...)`.

It is safe to import sibling apps at runtime: every app in `apps.yaml` that
calls `get_app("locker")` (or similar) already lists that sibling under
`dependencies:` or `global_dependencies:`, so AppDaemon guarantees it is
loaded first. A failure to import is a configuration error, and the
`ImportError` raised is **clearer** than a `get_app` returning `None`
mid-runtime. The assert catches a misuse of `get_app` that bypasses
dependency declaration.

Pattern:

```python
import locker
assert isinstance(self.get_app("locker"), locker.Locker)
app = self.get_app("locker")
assert isinstance(app, locker.Locker)
app.get_mutex("...")
```

`mypy` will then see `app: locker.Locker` and the subsequent attribute
access type-checks.

For type-checker-only names that would otherwise cause a real import of a
module AppDaemon hasn't loaded yet (e.g. an app referencing a sibling that
isn't in its `dependencies` — should not happen, but we keep the type
checker happy), use `from typing import TYPE_CHECKING` and a guarded
import:

```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import locker  # for type checking only
```

The `isinstance` assertion is the runtime narrowing mechanism. No `cast`.

### Dynamic / eval code

`expression.py` uses `eval(self.expr, self.evaluators)`. `Evaluator.__getattr__`
and `__getitem__` are inherently `Any`-returning. Annotate the obvious
signatures (`__init__(self, func: Callable[[str], Any], prefix: str = "")` —
the func is `_get_value` etc. which return `Any`), but the bodies stay
`Any`-flavored. `disallow_untyped_calls` is satisfied because calling an
`Any`-typed callable is allowed.

The bare `except:` clauses in `expression.py` (`_get`, `_get_app`,
`cleanup`), `history.py:69`, `enabler.py`, `cover.py`, `timer_switch.py`,
`locker.py`, etc. are replaced with `except Exception:`. This is a typing
requirement (mypy strict flags bare `except`) and an idiomatic
improvement. `traceback.format_exc()` returns `str`, passed to `self.error(...)`
(accepts `str`).

### Other

- `mutex_graph.py`: pure-Python graph helpers. `find_cycle`,
  `format_graph`, `append_graph`, `DFS`, `edge_target`, `edge_name`,
  `_list_to_set`. Annotate with `dict[str, set[tuple[str, str]]]` for graphs
  and `tuple[str, str]` for edges. `base_vertex: str = ""`.
- `locker.py`: `Lock`, `Mutex`, `Locker`. `threading.Lock()` return is
  `threading.Lock` (instance). `push_edge`/`pop_edge` take `str, str`.
- `imports`: add `from typing import Any, Callable` and
  `from __future__ import annotations` where forward refs / cleaner syntax
  help. Use modern syntax (`str | None` etc.). `from __future__ import
  annotations` is added to every app file to keep annotations lazy and avoid
  runtime-eval of forward-ref type names declared only under
  `TYPE_CHECKING`.

## Unit-test mock changes

`test/AppDaemonUnitTest/apps/hass.py`:

- `StateCallback` NamedTuple/alias currently expects a 5-arg callable. After
  we drop `kwargs` from app callbacks, the state-callback type becomes a
  4-arg callable: `Callable[[str, str | None, Any, Any], None]`. Update the
  alias and the `StateCallbackRecord` field type.
- `AppManager.set_state`'s inner `call_callback(f, name, attribute, old, new)`
  currently invokes `f(name, attribute, old, new, {})` — drop the trailing
  `{}` to call the 4-arg form. Same for `schedule_call`'s
  `call_callback(f, name, attribute, old, new)` (already 5-positional there;
  verify and align).
- Inner `SchedulerChallback` (scheduler callback) stays 1-arg
  `Callable[[dict[str, Any]], None]` as before.

Run unit tests after the change:

```sh
source test/.venv/bin/activate && cd test/AppDaemonUnitTest && rm -rf output && ./run-test -LTRACE
```

Expected: green (no behavioral change — callbacks already ignored `kwargs`).

## Verification

1. Unit tests pass after **every** step that touches the mock or app
   callbacks. (Most steps only annotate; only the mock alignment + state-
   callback shape change requires a test run.)
2. `mypy` from repo root — 0 errors.
3. Integration tests pass at the very end (single run).

## Non-goals / risks

- **No behavioral changes** to apps beyond the cosmetic kwarg-drop on state
  callbacks (which they ignored).
- **No new runtime imports** added to apps that change AppDaemon's load
  order. Sibling-app imports for `isinstance` checks match the
  `dependencies:` declarations in `apps.yaml` (already required by
  AppDaemon), so no load-order change is introduced.
- **No `# type: ignore`** unless absolutely unavoidable; aim for zero.
- **API stays sync**: appdaemon's `sync_decorator` makes the async base
  methods callable as sync at runtime, so no app rewrite for async is needed.