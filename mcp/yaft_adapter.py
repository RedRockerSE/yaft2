"""
yaft_adapter.py — Bridge between the MCP server and YaFT (yaft2).

The MCP server never imports YaFT directly; it goes through this adapter.
Wire the three TODO sections to your actual Core API and everything else
keeps working unchanged. If YaFT is not importable, the adapter degrades
to stdlib-only behaviour (ZIP listing, file reads, SQLite queries) so the
server is testable immediately.

All evidence access is READ-ONLY by construction.
"""

from __future__ import annotations

import dataclasses
import fnmatch
import inspect
import io
import os
import re
import sqlite3
import tempfile
import zipfile
from dataclasses import dataclass, field
from typing import Any, Iterator

try:
    from yaft.core.api import CoreAPI
    from yaft.core.plugin_manager import PluginManager
    HAS_YAFT = True
except ImportError:
    HAS_YAFT = False

# --- YaFT environment configuration (override via env) ---------------------
# YAFT_CONFIG_DIR       CoreAPI config directory      (default: ./config)
# YAFT_PLUGIN_DIRS      colon-separated plugin dirs   (default: ./plugins)
# YAFT_ZIP_LOAD_METHOD  CoreAPI method that loads the extraction ZIP,
#                       if auto-probing fails (e.g. "load_zip")
YAFT_CONFIG_DIR = os.environ.get("YAFT_CONFIG_DIR", os.path.join(os.getcwd(), "config"))
YAFT_PLUGIN_DIRS = [
    p for p in os.environ.get("YAFT_PLUGIN_DIRS", os.path.join(os.getcwd(), "plugins")).split(":") if p
]
_ZIP_LOAD_CANDIDATES = ("load_zip", "load_extraction", "open_zip", "load_file", "open_extraction")


# --------------------------------------------------------------------------
# Extraction type detection
# --------------------------------------------------------------------------

_SIGNATURES = {
    "cellebrite": ("ExtractionSummary", "UFDR", "report.xml", "DumpData.dat"),
    "ufade": ("ufade", "Media/", "iTunes_Backup", "Manifest.db"),
    "adb_backup": ("apps/", "shared/", ".ab"),
}


def detect_extraction_type(zip_path: str) -> dict[str, Any]:
    """Best-effort detection of the extraction source from archive contents."""
    ext = os.path.splitext(zip_path)[1].lower()
    if ext == ".ab":
        return {"type": "adb_backup", "confidence": "high", "hint": "file extension .ab"}
    if ext == ".ufdr":
        return {"type": "cellebrite", "confidence": "high", "hint": "file extension .ufdr"}

    scores: dict[str, int] = {k: 0 for k in _SIGNATURES}
    hits: dict[str, list[str]] = {k: [] for k in _SIGNATURES}
    try:
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()[:5000]
        for name in names:
            for etype, sigs in _SIGNATURES.items():
                for sig in sigs:
                    if sig.lower() in name.lower():
                        scores[etype] += 1
                        if len(hits[etype]) < 5:
                            hits[etype].append(name)
    except zipfile.BadZipFile:
        return {"type": "unknown", "confidence": "none", "hint": "not a valid ZIP archive"}

    best = max(scores, key=lambda k: scores[k])
    if scores[best] == 0:
        return {"type": "generic_zip", "confidence": "low", "hint": "no known signatures found"}
    return {
        "type": best,
        "confidence": "high" if scores[best] >= 3 else "medium",
        "matched_paths": hits[best],
    }


# --------------------------------------------------------------------------
# Plugin registry
# --------------------------------------------------------------------------

@dataclass
class PluginInfo:
    name: str                      # class name == registry key; use this in run_yaft_plugin
    description: str
    version: str = ""
    author: str = ""
    target_os: list = field(default_factory=lambda: ["any"])
    enabled: bool = True
    execute_signature: str = ""    # how to call it: kwargs map to options{}
    execute_doc: str = ""


# One CoreAPI+PluginManager pair per evidence archive (CoreAPI holds loaded-ZIP state)
_MANAGERS: dict[str, tuple[Any, Any]] = {}


def _new_manager() -> tuple[Any, Any]:
    from pathlib import Path

    core_api = CoreAPI(config_dir=Path(YAFT_CONFIG_DIR))
    manager = PluginManager(core_api=core_api, plugin_dirs=[Path(p) for p in YAFT_PLUGIN_DIRS])
    manager.discover_plugins()
    return core_api, manager


def _load_zip_into(core_api: Any, zip_path: str) -> None:
    """Load the extraction into CoreAPI. Method name is probed; pin it with
    YAFT_ZIP_LOAD_METHOD if probing picks wrong or fails."""
    pinned = os.environ.get("YAFT_ZIP_LOAD_METHOD")
    candidates = (pinned,) if pinned else _ZIP_LOAD_CANDIDATES
    for name in candidates:
        method = getattr(core_api, name or "", None)
        if callable(method):
            method(zip_path)
            return
    raise RuntimeError(
        "Could not find the CoreAPI method that loads an extraction ZIP "
        f"(tried: {', '.join(c for c in candidates if c)}). "
        "Set YAFT_ZIP_LOAD_METHOD to the correct method name."
    )


def _manager_for(zip_path: str) -> tuple[Any, Any]:
    pair = _MANAGERS.get(zip_path)
    if pair is None:
        core_api, manager = _new_manager()
        _load_zip_into(core_api, zip_path)
        _MANAGERS[zip_path] = pair = (core_api, manager)
    return pair


def _jsonable(obj: Any, depth: int = 0, max_items: int = 200, max_str: int = 2000) -> Any:
    """Convert arbitrary plugin results to bounded, JSON-serializable data."""
    if depth > 6:
        return f"<max depth: {type(obj).__name__}>"
    if obj is None or isinstance(obj, (bool, int, float)):
        return obj
    if isinstance(obj, str):
        return obj if len(obj) <= max_str else obj[:max_str] + f"... <truncated {len(obj)} chars>"
    if isinstance(obj, bytes):
        return {"_bytes": len(obj), "hex_preview": obj[:64].hex()}
    if hasattr(obj, "model_dump"):          # pydantic v2
        return _jsonable(obj.model_dump(), depth + 1, max_items, max_str)
    if hasattr(obj, "dict") and callable(getattr(obj, "dict", None)) and hasattr(obj, "__fields__"):
        return _jsonable(obj.dict(), depth + 1, max_items, max_str)   # pydantic v1
    if isinstance(obj, dict):
        return {str(k): _jsonable(v, depth + 1, max_items, max_str) for k, v in list(obj.items())[:max_items]}
    if isinstance(obj, (list, tuple, set, frozenset)):
        seq = list(obj)
        out = [_jsonable(v, depth + 1, max_items, max_str) for v in seq[:max_items]]
        if len(seq) > max_items:
            out.append(f"<truncated: {len(seq) - max_items} more items>")
        return out
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return _jsonable(dataclasses.asdict(obj), depth + 1, max_items, max_str)
    return str(obj)


def list_plugins(zip_path: str | None = None) -> list[PluginInfo]:
    """Enumerate discovered YaFT plugins with metadata and calling contract.
    If zip_path is given, restrict to plugins compatible with its detected OS."""
    if not HAS_YAFT:
        return [
            PluginInfo(
                name="_adapter_fallback_info",
                description=(
                    "YaFT is not importable in this environment. Only generic ZIP/SQLite "
                    "tools are available. Install yaft2 (pip install -e <repo>) to enable plugins."
                ),
            )
        ]
    if zip_path:
        core_api, manager = _manager_for(zip_path)
        classes = manager.get_compatible_plugins()
    else:
        core_api, manager = _new_manager()
        classes = dict(manager._plugin_classes)

    infos: list[PluginInfo] = []
    for cls_name, cls in classes.items():
        try:
            tmp = cls(core_api)          # metadata is an instance property
            md = tmp.metadata
            sig = str(inspect.signature(cls.execute)).replace("(self, ", "(").replace("(self)", "()")
            infos.append(
                PluginInfo(
                    name=cls_name,
                    description=md.description,
                    version=md.version,
                    author=md.author,
                    target_os=list(md.target_os),
                    enabled=md.enabled,
                    execute_signature=f"execute{sig}",
                    execute_doc=inspect.getdoc(cls.execute) or "",
                )
            )
        except Exception as e:
            infos.append(PluginInfo(name=cls_name, description=f"<metadata unavailable: {e}>", enabled=False))
    return infos


def run_plugin(zip_path: str, plugin_name: str, options: dict | None = None) -> dict[str, Any]:
    """Run a YaFT plugin against the extraction. Follows the documented CLI
    lifecycle: load -> execute -> unload (cleanup) in finally. Read-only:
    plugins receive the ZIP through CoreAPI, which never mutates evidence.
    NOTE: plugin_name is the plugin CLASS name (registry key), e.g.
    'iOSbiomeDevWifiPlugin'."""
    if not HAS_YAFT:
        return {
            "status": "unavailable",
            "plugin": plugin_name,
            "error": "YaFT not importable; generic tools (list/read/query) still work.",
        }
    core_api, manager = _manager_for(zip_path)

    if plugin_name not in manager._plugin_classes:
        known = sorted(manager._plugin_classes)
        return {
            "status": "not_found",
            "plugin": plugin_name,
            "error": "Unknown plugin class name. Names are case-sensitive class names.",
            "available": known,
        }

    detected_os = None
    try:
        detected_os = core_api.get_detected_os()
        if not manager.is_plugin_compatible(manager._plugin_classes[plugin_name], detected_os):
            return {
                "status": "incompatible",
                "plugin": plugin_name,
                "detected_os": detected_os,
                "error": f"Plugin does not target detected OS '{detected_os}'.",
            }
    except Exception:
        pass  # compatibility check is advisory; fail open like the registry does

    instance = manager.load_plugin(plugin_name)
    if instance is None:
        return {
            "status": "load_failed",
            "plugin": plugin_name,
            "error": "load_plugin returned None (disabled, or initialize() raised — check YaFT logs).",
        }
    try:
        result = manager.execute_plugin(plugin_name, **(options or {}))
        return {
            "status": "ok",
            "plugin": plugin_name,
            "detected_os": detected_os,
            "result": _jsonable(result),
        }
    except Exception as e:
        return {"status": "execute_error", "plugin": plugin_name, "error": f"{type(e).__name__}: {e}"}
    finally:
        manager.unload_plugin(plugin_name)


# --------------------------------------------------------------------------
# Generic read-only archive access (stdlib, always available)
# --------------------------------------------------------------------------

MAX_LIST = 500


def list_archive(zip_path: str, pattern: str = "*", limit: int = MAX_LIST) -> dict[str, Any]:
    limit = max(1, min(limit, MAX_LIST))
    entries = []
    total = 0
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            if fnmatch.fnmatch(info.filename, pattern) or fnmatch.fnmatch(
                os.path.basename(info.filename), pattern
            ):
                total += 1
                if len(entries) < limit:
                    entries.append(
                        {
                            "path": info.filename,
                            "size": info.file_size,
                            "modified": "%04d-%02d-%02d %02d:%02d:%02d" % info.date_time,
                        }
                    )
    return {"matches": total, "returned": len(entries), "entries": entries}


def search_archive(zip_path: str, regex: str, limit: int = 100) -> dict[str, Any]:
    """Regex match against member *paths* (not contents)."""
    rx = re.compile(regex, re.IGNORECASE)
    out = []
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            if rx.search(name):
                out.append(name)
                if len(out) >= limit:
                    break
    return {"pattern": regex, "returned": len(out), "paths": out}


def read_member(
    zip_path: str, member: str, offset: int = 0, length: int = 4096, mode: str = "auto"
) -> dict[str, Any]:
    """Read a slice of a file inside the archive without extracting to disk."""
    length = max(1, min(length, 65536))
    with zipfile.ZipFile(zip_path) as zf:
        info = zf.getinfo(member)
        with zf.open(member) as fh:
            if offset:
                fh.read(offset)  # ZipExtFile is not seekable; skip forward
            data = fh.read(length)

    is_binary = b"\x00" in data[:1024]
    if mode == "hex" or (mode == "auto" and is_binary):
        hexdump = []
        for i in range(0, len(data), 16):
            chunk = data[i : i + 16]
            hx = " ".join(f"{b:02x}" for b in chunk)
            asc = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            hexdump.append(f"{offset + i:08x}  {hx:<47}  {asc}")
        body: Any = "\n".join(hexdump)
        rendered = "hex"
    else:
        body = data.decode("utf-8", errors="replace")
        rendered = "text"
    return {
        "path": member,
        "file_size": info.file_size,
        "offset": offset,
        "bytes_read": len(data),
        "rendered": rendered,
        "content": body,
    }


# --------------------------------------------------------------------------
# Read-only SQLite access
# --------------------------------------------------------------------------

_FORBIDDEN_SQL = re.compile(
    r"^\s*(insert|update|delete|drop|alter|create|replace|attach|detach|pragma|vacuum|reindex)\b",
    re.IGNORECASE,
)


class _MemberDB:
    """Copies a DB (plus -wal/-shm siblings if present) from the archive to a
    private temp dir and opens it read-only + immutable. Evidence untouched."""

    def __init__(self, zip_path: str, member: str):
        self.tmp = tempfile.TemporaryDirectory(prefix="yaftmcp_db_")
        base = os.path.join(self.tmp.name, os.path.basename(member))
        with zipfile.ZipFile(zip_path) as zf:
            names = set(zf.namelist())
            for suffix in ("", "-wal", "-shm"):
                src = member + suffix
                if src in names:
                    with zf.open(src) as fh, open(base + suffix, "wb") as out:
                        while chunk := fh.read(1 << 20):
                            out.write(chunk)
        # If a WAL exists we cannot use immutable=1 (WAL frames would be
        # invisible); read-only mode still guarantees no writes to our copy.
        has_wal = os.path.exists(base + "-wal")
        uri = f"file:{base}?mode=ro" + ("" if has_wal else "&immutable=1")
        self.conn = sqlite3.connect(uri, uri=True)
        self.conn.row_factory = sqlite3.Row

    def close(self):
        self.conn.close()
        self.tmp.cleanup()


def query_sqlite(zip_path: str, member: str, sql: str, max_rows: int = 200) -> dict[str, Any]:
    if _FORBIDDEN_SQL.match(sql):
        return {"error": "read-only enforcement: only SELECT/CTE statements are permitted"}
    if not re.match(r"^\s*(select|with)\b", sql, re.IGNORECASE):
        return {"error": "only SELECT (or WITH ... SELECT) statements are permitted"}
    max_rows = max(1, min(max_rows, 1000))
    db = _MemberDB(zip_path, member)
    try:
        cur = db.conn.execute(sql)
        cols = [d[0] for d in cur.description] if cur.description else []
        rows = []
        truncated = False
        for i, row in enumerate(cur):
            if i >= max_rows:
                truncated = True
                break
            rows.append({c: row[c] for c in cols})
        return {"columns": cols, "row_count": len(rows), "truncated": truncated, "rows": rows}
    except sqlite3.Error as e:
        return {"error": f"sqlite error: {e}"}
    finally:
        db.close()


def sqlite_schema(zip_path: str, member: str) -> dict[str, Any]:
    db = _MemberDB(zip_path, member)
    try:
        cur = db.conn.execute(
            "SELECT type, name, sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY type, name"
        )
        objects = [{"type": r["type"], "name": r["name"], "sql": r["sql"]} for r in cur]
        counts = {}
        for obj in objects:
            if obj["type"] == "table":
                try:
                    counts[obj["name"]] = db.conn.execute(
                        f'SELECT COUNT(*) FROM "{obj["name"]}"'
                    ).fetchone()[0]
                except sqlite3.Error:
                    counts[obj["name"]] = None
        return {"objects": objects, "table_row_counts": counts}
    except sqlite3.Error as e:
        return {"error": f"sqlite error: {e}"}
    finally:
        db.close()
