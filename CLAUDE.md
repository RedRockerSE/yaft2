# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**YAFT (Yet Another Forensic Tool)** is a Python-based forensic analysis tool designed for processing and analyzing ZIP archives through a plugin architecture. The tool provides built-in ZIP file handling capabilities that are exposed to plugins through the Core API, enabling forensic analysts to create custom analysis plugins without worrying about low-level ZIP operations.

YaFT includes production-ready iOS forensic analysis plugins for extracting application metadata, permissions, and usage statistics from iOS filesystem extractions (supports Cellebrite format).

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

## iOS Forensic Analysis Plugins

YaFT includes two specialized plugins for iOS forensic analysis:

### 1. iOSAppGUIDExtractorPlugin

Extracts application metadata from iOS filesystem extractions:
- Bundle identifiers and container GUIDs
- App metadata (display name, version, etc.)
- Data from MobileInstallation.plist, applicationState.db, and filesystem enumeration
- Supports Cellebrite extraction format (filesystem1/ prefix)

**Usage:**
```bash
python -m yaft.cli run iOSAppGUIDExtractorPlugin --zip ios_extraction.zip
```

**Output:**
- Markdown report with comprehensive app listing
- JSON export with all app metadata
- Extracted to `yaft_output/ios_extractions/`

### 2. iOSAppPermissionsExtractorPlugin

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

**Output:**
- Markdown report with risk analysis
- JSON export with detailed permission data
- Identified high-risk applications
- Extracted to `yaft_output/ios_extractions/`

**Both plugins:**
- Auto-detect Cellebrite filesystem prefix
- Handle SQLite databases via temporary extraction
- Generate professional markdown reports
- Export JSON for further processing

## Important Implementation Details

- **ZIP File Lifecycle**: ZIP files are loaded before plugin execution and closed after
- **Plugin Discovery**: Uses file system scanning + importlib (works in dev and built executables)
- **Plugin Naming**: Plugins are registered and accessed by **class name** (e.g., `iOSAppGUIDExtractorPlugin`), not metadata name
- **Error Handling**: Plugins fail gracefully; errors don't crash the app
- **Forensic Focus**: Plugins should assume they're processing evidence and handle data carefully
- **Output Directory**: Use `Path.cwd() / "yaft_output"` for extracted files and reports
- **Report Generation**: All plugins MUST use `core_api.generate_report()` for consistent markdown reporting
- **Report Location**: Reports are automatically saved to `yaft_output/reports/` with timestamps
- **iOS Analysis**: iOS plugins use temporary directories for SQLite database extraction (auto-cleaned)
- **Windows Compatibility**: CoreAPI uses ASCII-safe output markers ([OK], [ERROR], [WARNING], [INFO]) instead of Unicode symbols for Windows console compatibility

## Building Executables

```bash
python build.py  # Build for current platform
python build.py --clean  # Clean build
```

Output: `dist/yaft/` containing executable and `plugins/` directory. New plugins can be added to built executables without recompilation.
