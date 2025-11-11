# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**YAFT (Yet Another Forensic Tool)** is a Python-based forensic analysis tool designed for processing and analyzing ZIP archives through a plugin architecture. The tool provides built-in ZIP file handling capabilities that are exposed to plugins through the Core API, enabling forensic analysts to create custom analysis plugins without worrying about low-level ZIP operations.

YaFT includes production-ready forensic analysis plugins for both iOS and Android devices, supporting extraction formats from Cellebrite and GrayKey tools.

## Technology Stack

- **Python Version**: 3.12+ (supports both 3.12 and 3.13)
- **Package Manager**: uv (Astral's ultra-fast Python package installer)
- **CLI Framework**: Typer (type-safe CLI framework)
- **Terminal Output**: Rich (color-coded, formatted output)
- **Validation**: Pydantic v2 (type-safe data validation)
- **Build System**: PyInstaller (Windows and Linux executables)
- **Testing**: pytest with coverage
- **Code Quality**: Ruff (linting and formatting)

## Core Architecture

### Layered Architecture
```
CLI (Presentation) → Plugin Manager (Application) → Core API (Service) → Plugin Base (Domain)
```

### Key Components

1. **Plugin Base** (`src/yaft/core/plugin_base.py`)
   - Abstract base class for all plugins
   - Defines plugin interface: metadata, initialize(), execute(), cleanup()
   - Plugin lifecycle state management

2. **Core API** (`src/yaft/core/api.py`)
   - Service layer providing shared functionality
   - **ZIP file handling**: load, read, extract, analyze ZIP archives
   - **Case identifier management**: Forensic case identifiers (Examiner ID, Case ID, Evidence ID)
   - **Plist parsing**: parse plist files from ZIP archives (iOS forensics)
   - **SQLite querying**: execute SQL queries on databases from ZIP archives (iOS/Android forensics)
   - **XML parsing**: parse XML files from ZIP archives (Android forensics)
   - Logging, file I/O, user input, configuration management
   - Inter-plugin communication via shared data store

3. **Plugin Manager** (`src/yaft/core/plugin_manager.py`)
   - Dynamic plugin discovery using importlib
   - Plugin lifecycle management
   - Error isolation (failed plugins don't crash app)

4. **CLI** (`src/yaft/cli.py`)
   - Typer-based command-line interface
   - Commands: list-plugins, info, load, unload, run, reload
   - `run` command accepts `--zip` option for forensic analysis

## Case Identifier Management

YaFT includes built-in support for forensic case identifier management. The CLI automatically prompts for case identifiers when running plugins, and these are included in reports and used to organize output files.

### Case Identifier Formats

- **Examiner ID**: User/investigator identifier (alphanumeric with underscores/hyphens, 2-50 characters - e.g., `john_doe`, `examiner-123`)
- **Case ID**: Case number (any alphanumeric string - e.g., `CASE2024-01`, `Case123`, `MyCase`)
- **Evidence ID**: Evidence number (any alphanumeric string - e.g., `BG123456-1`, `Evidence1`, `Ev-001`)

### Core API Methods

```python
# Validation (returns True/False)
self.core_api.validate_examiner_id("john_doe")
self.core_api.validate_case_id("CASE2024-01")
self.core_api.validate_evidence_id("EV123456-1")

# Set case identifiers programmatically
self.core_api.set_case_identifiers("john_doe", "CASE2024-01", "EV123456-1")

# Get current case identifiers (returns tuple of strings or None values)
examiner, case, evidence = self.core_api.get_case_identifiers()

# Get case-based output directory (automatically uses case identifiers if set)
output_dir = self.core_api.get_case_output_dir("ios_extractions")
# Returns: yaft_output/CASE2024-01/BG123456-1/ios_extractions
# Or falls back to: yaft_output/ios_extractions (if identifiers not set)
```

### Output Organization

When case identifiers are set, all plugin outputs are organized in case-based directories:
```
yaft_output/
├── CASE2024-01/              # Case ID
│   └── EV123456-1/           # Evidence ID
│       ├── reports/          # Generated reports (includes case IDs in metadata)
│       ├── ios_extractions/  # Plugin-specific outputs
│       └── android_extractions/
```

### Plugin Integration

**Recommended approach for plugins:**
```python
def execute(self, *args, **kwargs):
    # Use get_case_output_dir() for all output paths
    output_dir = self.core_api.get_case_output_dir("my_plugin_outputs")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Your plugin logic...

    # Reports automatically include case identifiers in metadata
    report_path = self.core_api.generate_report(
        plugin_name="MyPlugin",
        title="Analysis Report",
        sections=sections,
    )
```

**Note:** The CLI automatically prompts for case identifiers before plugin execution. Plugins don't need to prompt - just use `get_case_output_dir()` and `generate_report()` which handle case identifiers automatically.

## Data Format Support

The Core API exposes comprehensive data format parsing capabilities to plugins for forensic analysis:

### ZIP File Handling

```python
# In plugin execute() method:
current_zip = self.core_api.get_current_zip()  # Get current ZIP path
files = self.core_api.list_zip_contents()  # List all files
content = self.core_api.read_zip_file("file.txt")  # Read as bytes
text = self.core_api.read_zip_file_text("file.txt")  # Read as text
self.core_api.extract_zip_file("file.txt", output_dir)  # Extract single file
self.core_api.extract_all_zip(output_dir)  # Extract all files
self.core_api.display_zip_contents()  # Display formatted table
```

### Plist Parsing (iOS Forensics)

```python
# Parse plist from ZIP (returns dict or list)
data = self.core_api.read_plist_from_zip("path/to/file.plist")

# Or parse plist from bytes
raw_content = self.core_api.read_zip_file("file.plist")
data = self.core_api.parse_plist(raw_content)
```

### XML Parsing (Android Forensics)

```python
# Parse XML from ZIP (returns ElementTree root)
root = self.core_api.read_xml_from_zip("path/to/file.xml")

# Or parse XML from bytes/string
content = self.core_api.read_zip_file("file.xml")
root = self.core_api.parse_xml(content)

# Use standard ElementTree methods
for elem in root.findall('.//package'):
    name = elem.get('name')
```

### SQLite Querying

```python
# Query database from ZIP (returns list of tuples)
rows = self.core_api.query_sqlite_from_zip(
    "path/to/database.db",
    "SELECT name, value FROM settings WHERE id = ?",
    params=(123,)
)

# Query with fallback for schema differences (e.g., iOS/Android versions)
rows = self.core_api.query_sqlite_from_zip(
    "TCC.db",
    "SELECT service, client, auth_value, last_modified FROM access",
    fallback_query="SELECT service, client, auth_value, NULL FROM access"  # Older schema
)

# Query and get results as dictionaries with column names
dicts = self.core_api.query_sqlite_from_zip_dict(
    "database.db",
    "SELECT * FROM apps WHERE bundle_id LIKE ?",
    params=("com.apple.%",)
)
# Returns: [{"id": 1, "bundle_id": "com.apple.safari", ...}, ...]
```

**Benefits:**
- Automatic temporary file management (created and cleaned up automatically)
- Support for fallback queries (useful for iOS/Android version differences)
- No need for `tempfile`, `sqlite3`, `plistlib`, or `xml.etree.ElementTree` imports in plugins
- Consistent error handling across all plugins

### Forensic ZIP Format Detection

The Core API automatically detects the format of forensic ZIP extractions from different tools (Cellebrite, GrayKey) and operating systems (iOS, Android):

```python
# Detect extraction format
format_type, prefix = self.core_api.detect_zip_format()
# Returns: ("cellebrite_ios", "filesystem1/") or ("graykey_android", "") etc.

# Normalize a filesystem path with the detected prefix
full_path = self.core_api.normalize_zip_path("data/data/com.example.app/databases/app.db", prefix)
# Returns: "Dump/data/data/com.example.app/databases/app.db" (Cellebrite Android)
# Or: "data/data/com.example.app/databases/app.db" (GrayKey Android)
```

**Supported Formats:**

| Format Type | OS | Tool | Root Folders | Path Prefix |
|-------------|-----|------|--------------|-------------|
| `cellebrite_ios` | iOS | Cellebrite | `filesystem1/` or `filesystem/` | `filesystem1/` or `filesystem/` |
| `cellebrite_android` | Android | Cellebrite | `Dump/` and `extra/` | `Dump/` |
| `cellebrite_android` | Android | Cellebrite (legacy) | `fs/` | `fs/` |
| `graykey_ios` | iOS | GrayKey | `private/`, `System/`, `Library/`, etc. | (no prefix) |
| `graykey_android` | Android | GrayKey | `apex/`, `data/`, `system/`, `cache/`, etc. | (no prefix) |
| `unknown` | Any | Unknown | Various | (no prefix) |

**Detection Logic:**
1. Scans root-level folders in the ZIP archive (first 100 entries)
2. Identifies characteristic folder patterns for each format:
   - **Cellebrite Android**: `Dump/` and/or `extra/` folders
   - **Cellebrite iOS**: `filesystem1/` or `filesystem/` folder
   - **GrayKey Android**: 3+ matches from `apex/`, `bootstrap-apex/`, `cache/`, `data/`, `data-mirror/`, `efs/`, `system/`
   - **GrayKey iOS**: 2+ matches from `private/`, `System/`, `Library/`, `Applications/`, `var/`
3. Falls back to deeper file structure analysis if root folders don't match

**Plugin Usage:**
```python
def execute(self, *args, **kwargs):
    # Detect format
    format_type, prefix = self.core_api.detect_zip_format()

    # Use the prefix for all file paths
    if "android" in format_type:
        db_path = self.core_api.normalize_zip_path("data/data/com.example/databases/app.db", prefix)
    elif "ios" in format_type:
        plist_path = self.core_api.normalize_zip_path("System/Library/CoreServices/SystemVersion.plist", prefix)

    # Read files with normalized paths
    data = self.core_api.read_plist_from_zip(plist_path)
```

## Unified Report Generation

All plugins should use the CoreAPI's `generate_report()` method for consistent markdown report generation:

```python
# In plugin execute() method:
sections = [
    {
        "heading": "Executive Summary",
        "content": "Summary text here",
        "level": 2,  # Optional, default 2
    },
    {
        "heading": "Findings",
        "content": ["Finding 1", "Finding 2", "Finding 3"],
        "style": "list",  # Options: text, list, table, code
    },
    {
        "heading": "Statistics",
        "content": {
            "Total Files": 100,
            "Suspicious": 5,
            "Clean": 95,
        },
        "style": "table",
    },
]

metadata = {
    "Analysis Type": "Forensic ZIP Analysis",
    "Duration": "2.5 seconds",
}

report_path = self.core_api.generate_report(
    plugin_name="MyPlugin",
    title="Analysis Report Title",
    sections=sections,
    metadata=metadata,
)
# Returns: Path to generated markdown report in yaft_output/reports/
```

### Report Features

- **Automatic Metadata**: Includes plugin name, timestamp, source ZIP, case identifiers
- **Consistent Formatting**: All reports follow the same markdown structure
- **Multiple Content Styles**: text, list, table, code blocks
- **Timestamped Filenames**: Reports won't overwrite each other
- **Standard Location**: `yaft_output/<case_id>/<evidence_id>/reports/PluginName_YYYYMMDD_HHMMSS.md`

## Forensic Analysis Plugins

YaFT includes production-ready forensic analysis plugins for both iOS and Android devices:

### iOS Plugins

1. **iOSDeviceInfoExtractorPlugin** - Extract comprehensive device information
   - System version, device identifiers (UDID, IMEI, serial)
   - Carrier info, timezone, locale, backup information
   - Supports both Cellebrite and GrayKey extraction formats

2. **iOSCallLogAnalyzerPlugin** - Analyze call history
   - Extracts from CallHistory.storedata
   - Supports regular calls, FaceTime (audio/video), missed calls
   - Handles Core Data timestamps (seconds since 2001-01-01)
   - Call pattern analysis and frequent contact detection

### Android Plugins

1. **AndroidDeviceInfoExtractorPlugin** - Extract comprehensive device information
   - Build properties (manufacturer, model, Android version)
   - Device identifiers (Android ID, IMEI, serial number)
   - SIM card info, accounts, Bluetooth devices
   - Security settings (ADB enabled, developer mode)

2. **AndroidAppInfoExtractorPlugin** - Extract application metadata
   - Parses packages.xml, packages.list, usage statistics
   - App categorization (system, user, suspicious)
   - Launch counts and install timestamps

3. **AndroidAppPermissionsExtractorPlugin** - Analyze application permissions
   - Runtime permissions, declared permissions, app ops
   - Risk scoring based on permission types
   - High-risk permission detection (SMS, location, camera, etc.)

4. **AndroidCallLogAnalyzerPlugin** - Analyze call history
   - Extracts from calllog.db
   - Supports regular calls, video calls, missed/rejected calls
   - Handles Unix millisecond timestamps
   - Call pattern analysis and video call detection

### ZIP Format Support

All forensic plugins support both **Cellebrite** and **GrayKey** extraction formats:
- **Cellebrite**: Files prefixed with `fs/` or `filesystem1/`
- **GrayKey**: No prefix, files at root level

Plugins use CoreAPI methods to automatically detect and handle both formats:
```python
# Detect format
self.extraction_type, self.zip_prefix = self.core_api.detect_zip_format()

# Normalize paths for ZIP access
normalized_path = self.core_api.normalize_zip_path(path, self.zip_prefix)
```

## Development Commands

### Environment Setup with uv

```bash
# Install uv (if not installed)
# Windows: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
# Linux/macOS: curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment
uv venv

# Activate virtual environment
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate

# Install dependencies (editable mode with dev dependencies)
uv pip install -e ".[dev]"

# Or install from requirements files
uv pip install -r requirements-dev.txt
```

### Common Commands

```bash
# List available plugins
python -m yaft.cli list-plugins

# Analyze a ZIP file (NOTE: use full class name with "Plugin" suffix)
python -m yaft.cli run iOSDeviceInfoExtractorPlugin --zip evidence.zip
python -m yaft.cli run AndroidCallLogAnalyzerPlugin --zip android_extraction.zip

# Run tests
pytest

# Run specific test file
pytest tests/test_android_call_log_analyzer.py

# Run single test
pytest tests/test_android_call_log_analyzer.py::test_parse_call_log_cellebrite

# Run tests with coverage
pytest --cov=src/yaft --cov-report=html

# Run tests with verbose output
pytest -v

# Run tests without coverage report
pytest --no-cov

# Lint code
ruff check src/ tests/ plugins/

# Format code
ruff format src/ tests/ plugins/

# Type checking
mypy src/

# Build executables
python build_exe.py

# Install/update a single package with uv
uv pip install package-name
```

## Plugin Development

### Creating a New Plugin

1. Create a new file in `plugins/` directory
2. Inherit from `PluginBase`
3. Implement required methods: metadata, initialize(), execute(), cleanup()
4. Use Core API for ZIP handling and other shared functionality

### Example Plugin Structure

```python
from yaft.core.api import CoreAPI
from yaft.core.plugin_base import PluginBase, PluginMetadata

class MyForensicPlugin(PluginBase):
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="MyForensicPlugin",
            version="1.0.0",
            description="Description",
            author="Your Name",
            target_os=["ios", "android"],  # Optional: specify target OS
        )

    def initialize(self) -> None:
        # Setup resources
        pass

    def execute(self, *args, **kwargs) -> Any:
        # Main logic - access ZIP via self.core_api
        if not self.core_api.get_current_zip():
            self.core_api.print_error("No ZIP file loaded")
            return None

        # Detect ZIP format (Cellebrite vs GrayKey)
        extraction_type, zip_prefix = self.core_api.detect_zip_format()

        # Normalize paths for ZIP access
        path = self.core_api.normalize_zip_path("path/to/file", zip_prefix)

        # Parse data formats
        plist_data = self.core_api.read_plist_from_zip(path)
        xml_root = self.core_api.read_xml_from_zip(path)
        db_rows = self.core_api.query_sqlite_from_zip_dict(path, "SELECT * FROM table")

        # Generate report
        report_path = self.core_api.generate_report(
            plugin_name=self.metadata.name,
            title="Analysis Report",
            sections=sections,
        )

        return results

    def cleanup(self) -> None:
        # Clean up resources
        pass
```

### Forensic Plugin Pattern

For forensic analysis plugins, follow this pattern:

```python
def execute(self, *args, **kwargs) -> Dict[str, Any]:
    # 1. Check ZIP file is loaded
    if not self.core_api.get_current_zip():
        return {"success": False, "error": "No ZIP file loaded"}

    # 2. Detect ZIP structure (Cellebrite/GrayKey)
    self.extraction_type, self.zip_prefix = self.core_api.detect_zip_format()

    # 3. Extract data from ZIP
    data = self._parse_forensic_artifacts()

    # 4. Analyze and process data
    self._analyze_data()

    # 5. Generate report
    report_path = self._generate_report()

    # 6. Export to JSON
    output_dir = self.core_api.get_case_output_dir("plugin_outputs")
    json_path = output_dir / "data.json"
    self._export_to_json(json_path)

    return {
        "success": True,
        "report_path": str(report_path),
        "json_path": str(json_path),
    }
```

## Important Implementation Details

- **ZIP File Lifecycle**: ZIP files are loaded before plugin execution and closed after
- **Plugin Discovery**: Uses file system scanning + importlib (works in dev and built executables)
- **Plugin Naming**: Plugins are registered and accessed by **class name** (e.g., `iOSDeviceInfoExtractorPlugin`), not metadata name
- **Error Handling**: Plugins fail gracefully; errors don't crash the app
- **Forensic Focus**: Plugins should assume they're processing evidence and handle data carefully
- **Case Identifiers**: CLI prompts for case identifiers (Examiner ID, Case ID, Evidence ID) before plugin execution
- **Output Directory**: Use `core_api.get_case_output_dir(subdir)` for case-organized output paths (falls back to `yaft_output/` if no case IDs)
- **Report Generation**: All plugins MUST use `core_api.generate_report()` for consistent markdown reporting
- **Report Location**: Reports are saved to `yaft_output/<case_id>/<evidence_id>/reports/` with case identifiers in metadata
- **iOS/Android Analysis**: Forensic plugins use temporary directories for SQLite database extraction (auto-cleaned)
- **Windows Compatibility**: CoreAPI uses ASCII-safe output markers ([OK], [ERROR], [WARNING], [INFO]) instead of Unicode symbols for Windows console compatibility

## Testing Plugins

Create comprehensive tests for forensic plugins:

```python
# tests/test_my_plugin.py
import pytest
import zipfile
import sqlite3
from pathlib import Path

from yaft.core.api import CoreAPI
from plugins.my_plugin import MyPlugin

@pytest.fixture
def core_api(tmp_path):
    api = CoreAPI()
    api.base_output_dir = tmp_path / "yaft_output"
    api.base_output_dir.mkdir(parents=True, exist_ok=True)
    return api

@pytest.fixture
def plugin(core_api):
    return MyPlugin(core_api)

@pytest.fixture
def mock_zip_cellebrite(tmp_path):
    """Create mock ZIP in Cellebrite format."""
    zip_path = tmp_path / "extraction.zip"

    # Create mock database
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE data (id INTEGER, value TEXT)")
    cursor.execute("INSERT INTO data VALUES (1, 'test')")
    conn.commit()
    conn.close()

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(db_path, "fs/path/to/test.db")  # Cellebrite format

    return zip_path

def test_plugin_execution(plugin, core_api, mock_zip_cellebrite):
    core_api.set_zip_file(mock_zip_cellebrite)

    result = plugin.execute()

    assert result["success"] is True
    assert Path(result["report_path"]).exists()
```

### Test Coverage Guidelines

For forensic plugins, create tests covering:
- Plugin metadata and initialization
- ZIP structure detection (Cellebrite/GrayKey)
- Data parsing from forensic artifacts
- Analysis and pattern detection
- Full extraction workflow
- JSON export and report generation
- Error handling (missing files, malformed data)
- Edge cases specific to forensic data

## Building Executables

```bash
# Build for current platform
python build_exe.py

# Clean build
python build_exe.py --clean
```

Output: `dist/yaft/` containing executable and `plugins/` directory. New plugins can be added to built executables without recompilation.

## Important Notes

- **Plugin File Naming**: Plugins are discovered by class name, not filename. Use descriptive class names ending with "Plugin"
- **Unicode Output**: Always use `encoding='utf-8'` when reading/writing files to avoid Windows encoding issues
- **Timestamp Handling**: iOS uses Core Data timestamps (seconds since 2001-01-01), Android uses Unix milliseconds
- **Fallback Queries**: Always provide fallback SQL queries for older iOS/Android versions with different schemas
- **Data Validation**: Validate all extracted data before including in reports
- **Error Tracking**: Store errors in `self.errors` list and include in reports
- **Clean Imports**: Don't import temporary/test modules in production code
