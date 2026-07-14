# YaFT MCP Server

MCP server exposing YaFT (yaft2) forensic capabilities to Claude Code, so Claude can
autonomously examine mobile device extraction archives (Cellebrite, UFADE, adb backup)
through case-scoped, read-only, audit-logged tools.

## Files

- `server.py` — the MCP server (stdio transport). Case management, chain-of-custody
  audit logging (JSONL), and the tool surface.
- `yaft_adapter.py` — the only file that touches YaFT. Three `TODO(n)` markers show
  where to wire your real Core API. Without YaFT installed it falls back to stdlib
  ZIP/SQLite handling, so everything except `run_yaft_plugin` works out of the box.

## Install

```bash
mkdir -p ~/tools/yaft-mcp && cp server.py yaft_adapter.py ~/tools/yaft-mcp/
python3 -m venv ~/tools/yaft-mcp/.venv
~/tools/yaft-mcp/.venv/bin/pip install mcp
# optional, to enable plugins:
~/tools/yaft-mcp/.venv/bin/pip install -e ~/path/to/yaft2
```

## Register with Claude Code

```bash
claude mcp add --transport stdio yaft -- \
  ~/tools/yaft-mcp/.venv/bin/python ~/tools/yaft-mcp/server.py
```
Or UV
```bash
cd ~/path/to/yaft2
uv add mcp

claude mcp add --transport stdio yaft -- \
  uv run --directory ~/path/to/yaft2 mcp/server.py
```

Add `--scope project` if you want it shared via a committed `.mcp.json` instead of
your personal config. Verify with `claude mcp list`, then inside a session run `/mcp`
— the `yaft` server should show as connected with 11 tools.

Optional: set where case working directories and audit logs land (default
`~/yaft-mcp-cases`):

```bash
claude mcp add --transport stdio yaft \
  --env YAFT_MCP_CASES=/cases/mcp-work -- \
  ~/tools/yaft-mcp/.venv/bin/python ~/tools/yaft-mcp/server.py
```

## Tool surface

| Tool | Purpose |
|---|---|
| `open_case` | Register evidence, SHA-256 it, detect extraction type, start audit log. Returns `case_id`. |
| `list_cases` | Cases open in this session. |
| `verify_evidence` | Re-hash evidence, compare to the hash recorded at open. |
| `get_audit_log` | Tail the chain-of-custody JSONL. |
| `list_yaft_plugins` | Enumerate YaFT plugins (via adapter). |
| `list_archive_contents` | Glob listing inside the ZIP, no extraction. |
| `search_archive_paths` | Regex search over member paths. |
| `read_archive_file` | Read ≤64KB of a member as text or hexdump. |
| `sqlite_schema` | Tables/indexes/triggers + row counts of an in-archive DB. |
| `query_sqlite` | SELECT-only queries against a private read-only copy. |
| `run_yaft_plugin` | Invoke a YaFT plugin (requires wiring TODO(3)). |
| `export_file` | Copy one member to the case workdir, returns its SHA-256. |

## YaFT wiring (done) and configuration

The adapter is wired to the real `PluginManager`/`PluginBase` contract:

- **Plugin names are class names.** `run_yaft_plugin` takes the registry key —
  the Python class name (e.g. `iOSbiomeDevWifiPlugin`), case-sensitive. Unknown
  names return the full list of available names so Claude self-corrects.
- **Calling contract from introspection.** `PluginMetadata` has no options schema,
  so `list_yaft_plugins` exposes each plugin's `execute()` signature and docstring.
  Options passed to `run_yaft_plugin` become `execute(**options)` kwargs — good
  docstrings on `execute()` directly improve how well Claude drives your plugins.
- **Documented lifecycle honored.** Each run does `load_plugin` → `execute_plugin`
  → `unload_plugin` in a `finally`, so `initialize()`/`cleanup()` always pair.
  `execute_plugin`'s re-raise is caught and returned as a structured
  `execute_error` result.
- **OS compatibility.** `list_yaft_plugins(case_id)` filters via
  `get_compatible_plugins()`; incompatible runs are blocked with a clear status.
- **Bounded results.** Plugin output is sanitized to JSON (pydantic models,
  dataclasses, bytes, Paths handled) and truncated (200 items/2000 chars per
  field) so a chatty plugin can't flood Claude's context.

Environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `YAFT_CONFIG_DIR` | `./config` | Passed to `CoreAPI(config_dir=...)` |
| `YAFT_PLUGIN_DIRS` | `./plugins` | Colon-separated plugin scan dirs |
| `YAFT_ZIP_LOAD_METHOD` | auto-probe | CoreAPI method that loads the extraction ZIP |
| `YAFT_MCP_CASES` | `~/yaft-mcp-cases` | Case workdirs and audit logs |

**One thing to confirm:** the registry doc doesn't name the `CoreAPI` method that
loads an extraction ZIP (implied by `get_detected_os()` reading "the currently
loaded ZIP"). The adapter probes `load_zip`, `load_extraction`, `open_zip`,
`load_file`, `open_extraction` in order. If your method is named differently —
or the probe could hit a wrong same-named method — pin it:
`YAFT_ZIP_LOAD_METHOD=your_method_name`.

## Security and forensic-soundness model

- **Evidence is never written.** SQLite access copies the DB (and `-wal`/`-shm`
  siblings) to a private tempdir and opens with `mode=ro` (`immutable=1` when no
  WAL is present). Non-SELECT SQL is rejected. File reads stream from the ZIP.
- **Chain of custody.** Every tool call is appended to `audit.jsonl` with UTC
  timestamp, operator, host, parameters, and a SHA-256 of the result — a
  replayable record of exactly what was examined, suitable as a report appendix.
- **Untrusted content.** The server instructions tell Claude to treat archive
  contents as data, never instructions. Evidence can contain adversarial text
  (a suspect's notes saying "ignore previous instructions..."); keep this in
  mind when reviewing Claude's conclusions, and review before acting on them.
- **Run against working copies.** Even with read-only enforcement, point
  `open_case` at your verified working copy, not the original — standard practice,
  and `verify_evidence` lets Claude confirm integrity mid-session.

## Example session

```
> Open a case on ~/cases/2026-071/extraction.zip and give me an overview
  of messaging databases. Check the sms database for activity gaps in the
  evenings during May.
```

Claude will `open_case` → `search_archive_paths` for messaging apps →
`sqlite_schema` on candidates → iterative `query_sqlite` with epoch conversions →
summarize, with every step in the audit log.
