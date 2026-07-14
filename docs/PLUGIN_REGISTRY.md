# Plugin Registry Interface

This document describes YaFT2's **plugin registry** — the runtime component responsible for discovering, loading, executing, and unloading plugins. It is implemented by `PluginManager` in `src/yaft/core/plugin_manager.py`, operating on the plugin contract defined in `src/yaft/core/plugin_base.py`.

## Two things named "registry" — which one is this?

YaFT2 has two distinct systems that could be called a "plugin registry." This document covers the first one.

1. **In-process registry (`PluginManager`)** — this document. Tracks which plugin *classes* have been discovered on disk (in `plugins/*.py`) and which plugin *instances* are currently loaded/initialized in the running process. Purely in-memory; rebuilt every time the CLI runs.
2. **Distribution registry (`PluginUpdater` + `plugins_manifest.json`)** — a separate system (`src/yaft/core/plugin_updater.py`) that downloads plugin *files* from a GitHub repository (or a local/network folder), verifying them via SHA256 against a manifest. This is about getting plugin `.py` files onto disk in the first place, not about managing them once there. See `yaft update-plugins` / `yaft list-available-plugins` and `config/plugin_updater.toml`.

## `PluginManager`

### Construction

```python
PluginManager(core_api: CoreAPI, plugin_dirs: list[Path] | None = None)
```

- `core_api` — the `CoreAPI` instance passed to every plugin it loads.
- `plugin_dirs` — directories to scan for plugin files. Defaults to `[Path.cwd() / "plugins"]`. Each directory is created if it doesn't exist.

### Internal state

- `self.plugins: dict[str, PluginBase]` — **loaded/initialized instances**, keyed by plugin **class name** (e.g. `"iOSbiomeDevWifiPlugin"`).
- `self._plugin_classes: dict[str, type[PluginBase]]` — **all discovered classes** (whether loaded or not), also keyed by class name.

Both dicts use the plugin's Python **class name** as the key — not `metadata.name` (though in practice every shipped plugin sets `metadata.name` equal to its class name, e.g. `iOSbiomeDevWifiPlugin`). This is worth knowing since it's the most common source of "plugin not found" confusion when adding a new plugin.

### Method reference

```python
discover_plugins() -> dict[str, type[PluginBase]]
```
Scans every directory in `plugin_dirs` for `*.py` files (skipping any file whose name starts with `_`), dynamically imports each via `importlib.util`, and inspects the resulting module for `PluginBase` subclasses. The first matching class found in a file is used. Populates and returns `self._plugin_classes`. Import or inspection failures for a single file are logged and skipped — they don't stop discovery of the rest.

```python
load_plugin(plugin_name: str) -> PluginBase | None
```
Instantiates the named class (must already be in `self._plugin_classes` — i.e. `discover_plugins()` must have run first), checks `metadata.enabled`, and if enabled calls `initialize()` and stores the instance in `self.plugins`. Returns the existing instance (with a warning logged) if already loaded. Returns `None` and logs an error if the class isn't discovered, is disabled, or `initialize()` raises — in the raise case the plugin's `status` is set to `PluginStatus.ERROR` first.

```python
load_all_plugins() -> None
```
Runs `discover_plugins()` then calls `load_plugin()` for every discovered class name. Per-plugin failures don't stop the loop.

```python
unload_plugin(plugin_name: str) -> bool
```
Calls `cleanup()` on the loaded instance, sets its status to `PluginStatus.UNLOADED`, and removes it from `self.plugins`. Returns `False` (and logs) if the plugin wasn't loaded, or if `cleanup()` raises.

```python
unload_all_plugins() -> None
```
Calls `unload_plugin()` for every currently-loaded plugin name.

```python
get_plugin(plugin_name: str) -> PluginBase | None
```
Simple lookup into `self.plugins`. Returns `None` if not loaded.

```python
execute_plugin(plugin_name: str, *args, **kwargs) -> Any
```
Looks up the loaded plugin, sets status to `PluginStatus.ACTIVE`, calls `plugin.execute(*args, **kwargs)`, then resets status to `PluginStatus.INITIALIZED` on success. **On exception, sets status to `PluginStatus.ERROR`, logs the error, and re-raises** — unlike `load_plugin`/`unload_plugin`, which swallow exceptions and return `None`/`False`, callers of `execute_plugin` must handle the exception themselves. Returns `None` (without raising) if the plugin isn't loaded at all.

```python
is_plugin_compatible(plugin_class: type[PluginBase], detected_os: str) -> bool
```
Instantiates a temporary instance of `plugin_class` to read its `metadata.target_os` list. Returns `True` if `"any"` is in that list, `False` if `detected_os == "unknown"` and the plugin doesn't target `"any"`, otherwise checks membership. If instantiation itself fails, compatibility is assumed `True` (fails open).

```python
get_compatible_plugins(detected_os: str | None = None) -> dict[str, type[PluginBase]]
```
Filters `self._plugin_classes` by `is_plugin_compatible()`. If `detected_os` is omitted, it's auto-detected from the currently loaded ZIP via `core_api.get_detected_os()`; if no ZIP is loaded, all plugins are returned (treated as `"any"`).

```python
list_plugins(show_all: bool = False, filter_by_os: bool = False) -> None
```
Renders a Rich table to `core_api.console` (name, version, status, target OS, description). `show_all=False` restricts the table to currently-loaded plugins; `filter_by_os=True` additionally restricts to plugins compatible with the detected OS of the loaded ZIP. Does not return data — console output only. This backs `yaft list-plugins`.

```python
get_plugin_count() -> dict[str, int]
```
Returns `{"total_discovered": int, "loaded": int, "active": int, "error": int}`, computed from `self._plugin_classes` and `self.plugins`.

## The plugin contract (`PluginBase`)

Every class the registry can load must subclass `PluginBase` (`src/yaft/core/plugin_base.py`):

```python
class PluginBase(ABC):
    def __init__(self, core_api: Any) -> None: ...  # sets self.core_api, self._status = PluginStatus.LOADED

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata: ...

    @abstractmethod
    def initialize(self) -> None: ...

    @abstractmethod
    def execute(self, *args: Any, **kwargs: Any) -> Any: ...

    @abstractmethod
    def cleanup(self) -> None: ...

    @property
    def status(self) -> PluginStatus: ...
    @status.setter
    def status(self, value: PluginStatus) -> None: ...
```

### `PluginMetadata`

A frozen (immutable) Pydantic model returned by the `metadata` property:

| Field | Type | Default | Notes |
|---|---|---|---|
| `name` | `str` | — required | Plugin identifier (convention: same as class name) |
| `version` | `str` | — required | Semver recommended |
| `description` | `str` | — required | Human-readable |
| `author` | `str` | `"Unknown"` | |
| `requires_core_version` | `str` | `">=0.1.0"` | Not currently enforced by `PluginManager` itself |
| `dependencies` | `list[str]` | `[]` | Declarative only — not auto-resolved by the registry |
| `enabled` | `bool` | `True` | Checked in `load_plugin()`; `False` prevents loading |
| `target_os` | `list[str]` | `["any"]` | `"ios"`, `"android"`, `"any"`, or a combination — used by `is_plugin_compatible()` |

### `PluginStatus` (lifecycle enum)

```
UNLOADED → LOADED → INITIALIZED → ACTIVE
                          ↑____________|
                (ERROR / DISABLED are side-states reachable from most points)
```

- `LOADED` — set in `PluginBase.__init__`, before `initialize()` runs.
- `INITIALIZED` — set by `PluginManager.load_plugin()` after `initialize()` succeeds; also the "idle/ready" state `execute_plugin()` returns to after a successful run.
- `ACTIVE` — set by `execute_plugin()` for the duration of `execute()`.
- `ERROR` — set by `load_plugin()` or `execute_plugin()` when the plugin raises.
- `DISABLED` — set by `load_plugin()` when `metadata.enabled` is `False`.
- `UNLOADED` — set by `unload_plugin()` after `cleanup()` runs.

## End-to-end lifecycle

```
discover_plugins()
    → scans plugin_dirs, populates self._plugin_classes

load_plugin(name)
    → instantiate class(core_api)              [status: LOADED]
    → check metadata.enabled                    (False → status DISABLED, return None)
    → initialize()                              [status: INITIALIZED]
    → store in self.plugins[name]

execute_plugin(name, *args, **kwargs)   (repeatable)
    → status ACTIVE
    → execute(*args, **kwargs)
    → status back to INITIALIZED on success, or ERROR + re-raise on exception

unload_plugin(name)
    → cleanup()
    → status UNLOADED
    → remove from self.plugins
```

Error isolation differs by stage: a failure during `discover_plugins()`, `load_plugin()`, or `unload_plugin()` is caught, logged, and reported via a return value (`None`/`False`) — one bad plugin doesn't stop the batch (`load_all_plugins()`/`unload_all_plugins()`). A failure during `execute_plugin()` is caught just long enough to record `PluginStatus.ERROR`, then **re-raised** to the caller.

## Usage example

Mirrors how `src/yaft/cli.py` drives the registry (see `get_plugin_manager()` and the `run` command):

```python
from pathlib import Path
from yaft.core.api import CoreAPI
from yaft.core.plugin_manager import PluginManager

core_api = CoreAPI(config_dir=Path.cwd() / "config")
manager = PluginManager(core_api=core_api, plugin_dirs=[Path.cwd() / "plugins"])

manager.discover_plugins()
plugin = manager.load_plugin("iOSbiomeDevWifiPlugin")

if plugin:
    try:
        result = manager.execute_plugin("iOSbiomeDevWifiPlugin")
    except Exception as e:
        core_api.print_error(f"Plugin failed: {e}")
    finally:
        manager.unload_plugin("iOSbiomeDevWifiPlugin")
```
