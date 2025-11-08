# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**YAFT (Yet Another Forensic Tool)** is a Python-based forensic analysis tool designed for processing and analyzing ZIP archives through a plugin architecture. The tool provides built-in ZIP file handling capabilities that are exposed to plugins through the Core API, enabling forensic analysts to create custom analysis plugins without worrying about low-level ZIP operations.

YaFT includes production-ready mobile forensic analysis plugins for both iOS and Android platforms, extracting device information, application metadata, permissions, and usage statistics from full filesystem extractions (supports Cellebrite and GrayKey formats).

## Technology Stack

- **Python Version**: 3.13+
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
   - **XML parsing**: parse XML files from ZIP archives (Android forensics)
   - **SQLite querying**: execute SQL queries on databases from ZIP archives (iOS & Android forensics)
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

- **Examiner ID**: User/investigator identifier (format: alphanumeric with underscores/hyphens, 2-50 characters - e.g., `john_doe`, `examiner-123`)
- **Case ID**: Case number (format: 4+ uppercase alphanumeric characters, dash, 2+ digits - e.g., `CASE2024-01`, `K2024001-01`)
- **Evidence ID**: Evidence number (format: 2-4 uppercase letters, 4-8 digits, dash, 1-2 digits - e.g., `BG123456-1`, `EV123456-01`)

### Core API Methods

```python
# Validation (returns True/False)
self.core_api.validate_examiner_id("john_doe")
self.core_api.validate_case_id("CASE2024-01")
self.core_api.validate_evidence_id("BG123456-1")

# Set case identifiers programmatically
self.core_api.set_case_identifiers("john_doe", "CASE2024-01", "BG123456-1")

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
│   └── BG123456-1/           # Evidence ID
│       ├── reports/          # Generated reports (includes case IDs in metadata)
│       └── ios_extractions/  # Plugin-specific outputs
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

## ZIP File Handling

The Core API exposes comprehensive ZIP handling capabilities to plugins:

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

## Data Format Support (Plist, XML, SQLite)

The Core API provides built-in support for parsing plist files, XML files, and querying SQLite databases from ZIP archives. This eliminates the need for plugins to manage temporary files manually or import parsing libraries.

### Plist Parsing (iOS)

```python
# Parse plist from ZIP (returns dict or list)
data = self.core_api.read_plist_from_zip("path/to/file.plist")

# Or parse plist from bytes
raw_content = self.core_api.read_zip_file("file.plist")
data = self.core_api.parse_plist(raw_content)
```

### XML Parsing (Android)

```python
# Parse XML from ZIP (returns xml.etree.ElementTree.Element)
root = self.core_api.read_xml_from_zip("path/to/file.xml")

# Parse packages.xml example
root = self.core_api.read_xml_from_zip("data/system/packages.xml")
for package in root.findall('.//package'):
    package_name = package.get('name')
    version = package.get('version')

# Or parse XML from bytes/string
raw_content = self.core_api.read_zip_file("file.xml")
root = self.core_api.parse_xml(raw_content)
```

### SQLite Querying (iOS & Android)

```python
# Query database from ZIP (returns list of tuples)
rows = self.core_api.query_sqlite_from_zip(
    "path/to/database.db",
    "SELECT name, value FROM settings WHERE id = ?",
    params=(123,)
)

# Query with fallback for schema differences (e.g., iOS versions)
rows = self.core_api.query_sqlite_from_zip(
    "TCC.db",
    "SELECT service, client, auth_value, last_modified FROM access",
    fallback_query="SELECT service, client, auth_value, NULL FROM access"  # Older iOS schema
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
- Plugins remain focused on forensic logic, not data format handling

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

- **Automatic Metadata**: Includes plugin name, timestamp, source ZIP
- **Consistent Formatting**: All reports follow the same markdown structure
- **Multiple Content Styles**: text, list, table, code blocks
- **Timestamped Filenames**: Reports won't overwrite each other
- **Standard Location**: `yaft_output/reports/PluginName_YYYYMMDD_HHMMSS.md`

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

# Analyze a ZIP file
python -m yaft.cli run ZipAnalyzerPlugin --zip evidence.zip

# Run tests
pytest

# Run tests with coverage
pytest --cov=src/yaft --cov-report=html

# Lint code
ruff check src/ tests/ plugins/

# Format code
ruff format src/ tests/ plugins/

# Build executables
python build.py

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
        )

    def initialize(self) -> None:
        # Setup resources
        pass

    def execute(self, *args, **kwargs) -> Any:
        # Main logic - access ZIP via self.core_api
        if not self.core_api.get_current_zip():
            self.core_api.print_error("No ZIP file loaded")
            return None

        # Analyze ZIP contents
        files = self.core_api.list_zip_contents()
        # ... forensic analysis logic ...

        return results

    def cleanup(self) -> None:
        # Clean up resources
        pass
```

## Mobile Forensic Analysis Plugins

YaFT includes production-ready forensic analysis plugins for iOS and Android platforms:

### iOS Forensic Plugins

#### 1. iOSDeviceInfoExtractorPlugin

Extracts comprehensive device metadata from iOS filesystem extractions:
- System version information (iOS version, build)
- Device identifiers (UDID, serial number)
- Cellular information (IMEI, MEID, ICCID)
- Carrier information (phone number, operator name)
- iCloud account information
- Backup information and locale settings
- Supports Cellebrite and GrayKey extraction formats

**Usage:**
```bash
python -m yaft.cli run iOSDeviceInfoExtractorPlugin --zip ios_extraction.zip
```

#### 2. iOSAppGUIDExtractorPlugin

Extracts application metadata from iOS filesystem extractions:
- Bundle identifiers and container GUIDs
- App metadata (display name, version, etc.)
- Data from MobileInstallation.plist, applicationState.db, and filesystem enumeration
- Supports Cellebrite and GrayKey extraction formats

**Usage:**
```bash
python -m yaft.cli run iOSAppGUIDExtractorPlugin --zip ios_extraction.zip
```

#### 3. iOSAppPermissionsExtractorPlugin

Extracts application permissions, usage statistics, and privacy data:
- Permission grants from TCC.db (Camera, Location, Contacts, etc.)
- App usage statistics from knowledgeC.db (launches, duration)
- Notification settings from applicationState.plist
- Risk scoring based on permission types and patterns
- High-risk permission identification

**Usage:**
```bash
python -m yaft.cli run iOSAppPermissionsExtractorPlugin --zip ios_extraction.zip
```

### Android Forensic Plugins

#### 1. AndroidDeviceInfoExtractorPlugin

Extracts comprehensive device metadata from Android filesystem extractions:
- Build properties (manufacturer, model, Android version)
- Device identifiers (Android ID, serial number)
- Network information (WiFi/Bluetooth MAC addresses)
- SIM card and carrier information
- Account information (Google accounts, etc.)
- Security settings (ADB enabled, developer mode)
- Bluetooth paired devices
- Supports Cellebrite and GrayKey extraction formats

**Usage:**
```bash
python -m yaft.cli run AndroidDeviceInfoExtractorPlugin --zip android_extraction.zip
```

**Output:**
- Markdown report with device summary
- JSON export with complete device metadata
- Security warnings for ADB/developer mode
- Extracted to `yaft_output/android_device_info/`

#### 2. AndroidAppInfoExtractorPlugin

Extracts application information from Android filesystem extractions:
- Package names, versions, and installation dates
- App metadata from packages.xml and packages.list
- Usage statistics (launch counts, usage time)
- App categorization (system, user-installed, messaging, etc.)
- Suspicious app detection (debuggable, no installer, temp location)
- Supports Cellebrite and GrayKey extraction formats

**Usage:**
```bash
python -m yaft.cli run AndroidAppInfoExtractorPlugin --zip android_extraction.zip
```

**Output:**
- Markdown report with app listing and categories
- JSON export with complete app metadata
- Flagged suspicious applications
- Extracted to `yaft_output/android_extractions/`

#### 3. AndroidAppPermissionsExtractorPlugin

Extracts application permissions and privacy data from Android filesystem extractions:
- Declared permissions from packages.xml
- Runtime permissions from runtime-permissions.xml
- App ops (permission usage tracking)
- Usage statistics (app launches, foreground time)
- Risk scoring based on permission types
- High-risk permission identification (location, camera, microphone, etc.)
- Supports Cellebrite and GrayKey extraction formats

**Usage:**
```bash
python -m yaft.cli run AndroidAppPermissionsExtractorPlugin --zip android_extraction.zip
```

**Output:**
- Markdown report with permission analysis and risk assessment
- JSON export with detailed permission data
- Identified high-risk applications
- Apps with background location access highlighted
- Extracted to `yaft_output/android_extractions/`

### Common Plugin Features

**All mobile forensic plugins:**
- Auto-detect Cellebrite (fs/ or filesystem1/ prefix) and GrayKey formats (no prefix)
- Handle SQLite databases via temporary extraction (auto-cleaned)
- Parse XML configuration files
- Generate professional markdown reports with forensic notes
- Export JSON for further processing and integration
- Comprehensive error handling with detailed error logs
- Support case-based output organization

## Important Implementation Details

- **ZIP File Lifecycle**: ZIP files are loaded before plugin execution and closed after
- **Plugin Discovery**: Uses file system scanning + importlib (works in dev and built executables)
- **Plugin Naming**: Plugins are registered and accessed by **class name** (e.g., `iOSAppGUIDExtractorPlugin`), not metadata name
- **Error Handling**: Plugins fail gracefully; errors don't crash the app
- **Forensic Focus**: Plugins should assume they're processing evidence and handle data carefully
- **Case Identifiers**: CLI prompts for case identifiers (Examiner ID, Case ID, Evidence ID) before plugin execution
- **Output Directory**: Use `core_api.get_case_output_dir(subdir)` for case-organized output paths (falls back to `yaft_output/` if no case IDs)
- **Report Generation**: All plugins MUST use `core_api.generate_report()` for consistent markdown reporting
- **Report Location**: Reports are saved to `yaft_output/<case_id>/<evidence_id>/reports/` with case identifiers in metadata
- **iOS/Android Analysis**: Mobile plugins use temporary directories for SQLite database extraction (auto-cleaned)
- **Windows Compatibility**: CoreAPI uses ASCII-safe output markers ([OK], [ERROR], [WARNING], [INFO]) instead of Unicode symbols for Windows console compatibility
- **XML Parsing**: Android plugins use CoreAPI's `read_xml_from_zip()` and `parse_xml()` methods - no direct ElementTree imports needed
- **Data Format Abstraction**: Plugins never import `plistlib`, `xml.etree.ElementTree`, or `sqlite3` directly - all handled via CoreAPI
- **Permission Risk Scoring**: Both iOS and Android permissions plugins implement risk scoring based on permission sensitivity

## Building Executables

```bash
python build.py  # Build for current platform
python build.py --clean  # Clean build
```

Output: `dist/yaft/` containing executable and `plugins/` directory. New plugins can be added to built executables without recompilation.
