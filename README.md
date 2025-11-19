# YAFT - Yet Another Forensic Tool

[![CI](https://github.com/RedRockerSE/yaft2/actions/workflows/ci.yml/badge.svg)](https://github.com/RedRockerSE/yaft2/actions/workflows/ci.yml)
[![Release](https://github.com/RedRockerSE/yaft2/actions/workflows/release.yml/badge.svg)](https://github.com/RedRockerSE/yaft2/actions/workflows/release.yml)
[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE.md)

A plugin-based forensic analysis tool for Python 3.12+ designed for processing and analyzing ZIP archives. Features dynamic plugin loading, beautiful CLI interface, and cross-platform executable builds. YaFT is not a full-fledged forensic solution but a modern plugin-based platform which makes developing forensic-focused plugins fast and easy. Please feel free to contribute!

Contact: magjon@gmail.com
[YaFT - Discord](https://discord.gg/8zA3ZCF3)

## Features

- **ZIP File Processing**: Built-in support for forensic analysis of ZIP archives with advanced file search capabilities
- **Forensic Format Support**: Automatic detection and handling of Cellebrite and GrayKey extraction formats (iOS/Android)
- **Dynamic Plugin System**: Load and manage forensic plugins at runtime without code changes
- **Plugin Profiles**: Run multiple plugins together using TOML configuration files for standard analysis workflows
- **Automatic Plugin Updates**: Built-in update system to sync plugins from GitHub with SHA256 verification and offline caching
- **Beautiful CLI**: Color-coded output with Rich and Typer for forensic reporting
- **Case Management**: Forensic case identifier support (Examiner ID, Case ID, Evidence ID) with automatic validation and report organization
- **PDF Export**: Automatically export markdown reports to professionally styled PDF documents
- **Production Forensic Plugins**: Ready-to-use iOS and Android analysis plugins for device info, apps, permissions, and call logs
- **Type-Safe**: Full type hints with Pydantic validation
- **Cross-Platform**: Build standalone executables for Windows and Linux
- **Forensic-Focused**: Designed for digital forensics workflows and evidence processing
- **Extensible**: Easy to create new forensic analysis plugins following a simple interface
- **Production-Ready**: Comprehensive testing, error handling, and logging

## Architecture Overview

YAFT follows a clean, layered architecture:

```
┌─────────────────────────────────────────┐
│           CLI Interface (Typer)          │
├─────────────────────────────────────────┤
│        Plugin Manager (Discovery)        │
├─────────────────────────────────────────┤
│      Core API (Shared Functionality)     │
├─────────────────────────────────────────┤
│          Plugin Base (Interface)         │
└─────────────────────────────────────────┘
```

### Key Components

1. **PluginBase**: Abstract base class defining the plugin interface
2. **PluginManager**: Handles plugin discovery, loading, and lifecycle
3. **CoreAPI**: Provides shared services (logging, I/O, formatting)
4. **CLI**: Command-line interface for interacting with plugins

## Quick Start

### Installation

#### Option 1: Download Pre-built Executable (Recommended)

Download the latest release for your platform from the [Releases page](https://github.com/RedRockerSE/yaft2/releases):

- **Windows**: `yaft-windows-x64.exe`
- **macOS**: `yaft-macos-x64`
- **Linux**: `yaft-linux-x64`

```bash
# Windows
yaft-windows-x64.exe --help

# macOS/Linux (make executable first)
chmod +x yaft-macos-x64
./yaft-macos-x64 --help
```

#### Option 2: Install from PyPI

```bash
pip install yaft
yaft --help
```

#### Option 3: Development Installation

```bash
# Clone the repository
git clone <repository-url>
cd yaft

# Install uv (if not already installed)
# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
# Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv
uv pip install -e ".[dev]"

# Or install from requirements files
uv pip install -r requirements-dev.txt
```

### Plugin Update System

YAFT includes a built-in plugin update system that automatically syncs plugins from the GitHub repository. This ensures you always have access to the latest forensic analysis plugins without manually downloading files.

> **⚠️ Important:** After installing YAFT for the first time, you must download the plugins using the update system. The plugins are not included in the base installation to keep it lightweight and allow you to always have the latest versions.

#### First-Time Setup: Download All Plugins

After installing YAFT, download all available plugins from the repository:

```bash
# Download all plugins from GitHub
python -m yaft.cli update-plugins

# This will:
# - Fetch the plugin manifest from GitHub
# - Download all available plugins
# - Verify file integrity with SHA256 hashes
# - Save plugins to the plugins/ directory
```

**What gets downloaded:**
- All iOS forensic plugins (device info, call logs, cellular info)
- All Android forensic plugins (device info, apps, permissions, call logs)
- Example plugins for learning and testing

#### Keeping Plugins Up to Date

Check for and install plugin updates regularly:

```bash
# Check for updates and download them
python -m yaft.cli update-plugins

# Check for updates without downloading (preview mode)
python -m yaft.cli update-plugins --check-only

# Force check (ignore cache, useful if you just heard about new plugins)
python -m yaft.cli update-plugins --force

# Update a specific plugin only
python -m yaft.cli update-plugins --plugin ios_device_info_extractor.py
```

#### Browsing Available Plugins

See what plugins are available in the repository before downloading:

```bash
# List all available plugins from GitHub repository
python -m yaft.cli list-available-plugins

# Filter by operating system
python -m yaft.cli list-available-plugins --os ios
python -m yaft.cli list-available-plugins --os android
```

**Output includes:**
- Plugin name and filename
- Version number
- Target OS (iOS, Android, or general)
- File size
- Whether plugin is required for basic functionality

#### How the Update System Works

**Security & Integrity:**
- All plugins are verified with SHA256 hashes before installation
- Downloads use HTTPS connections only
- No code is executed during download
- Existing plugins are backed up before overwriting

**Smart Caching:**
- Checks for updates at most once every 24 hours by default
- Cached manifest enables offline viewing of available plugins
- Use `--force` flag to bypass cache when needed

**Offline Friendly:**
- Once plugins are downloaded, no internet connection is needed for forensic analysis
- Cached manifests let you work completely offline
- Perfect for air-gapped forensic workstations

#### Update System Example Workflow

```bash
# Day 1: Initial setup
python -m yaft.cli update-plugins
# Output: Downloaded 14 plugins, verified 14 plugins

# Day 30: Check for new plugins
python -m yaft.cli update-plugins --check-only
# Output: Updates available:
#   New plugins: 2
#     • ios_app_privacy_extractor.py
#     • android_location_analyzer.py

# Download the new plugins
python -m yaft.cli update-plugins
# Output: Downloaded 2 plugins, verified 2 plugins

# Verify you have the new plugins
python -m yaft.cli list-plugins
```

#### Troubleshooting Plugin Updates

**"No plugins found in repository"**
- Check your internet connection
- Verify you can access GitHub: `https://github.com/RedRockerSE/yaft2`
- Try with `--force` flag to bypass cache

**"Failed to download plugin"**
- Temporary network issue - try again
- Check if your firewall blocks GitHub
- Verify you have write permissions to the `plugins/` directory

**"SHA256 mismatch"**
- Plugin file was corrupted during download
- Run the update command again to re-download
- If issue persists, report it on the GitHub repository

**"Updates available but download fails"**
- Check available disk space
- Verify `plugins/` directory exists and is writable
- Try updating one plugin at a time: `--plugin filename.py`

### Basic Usage

```bash
# List locally installed plugins
python -m yaft.cli list-plugins

# Show all plugins (including unloaded)
python -m yaft.cli list-plugins --all

# Get plugin information
python -m yaft.cli info ZipAnalyzerPlugin

# Analyze a ZIP file with a plugin (NOTE: use full class name with "Plugin" suffix)
python -m yaft.cli run ZipAnalyzerPlugin --zip evidence.zip

# iOS forensic analysis
python -m yaft.cli run iOSDeviceInfoExtractorPlugin --zip ios_extraction.zip
python -m yaft.cli run iOSCallLogAnalyzerPlugin --zip ios_extraction.zip

# Android forensic analysis
python -m yaft.cli run AndroidDeviceInfoExtractorPlugin --zip android_extraction.zip
python -m yaft.cli run AndroidCallLogAnalyzerPlugin --zip android_extraction.zip

# Run multiple plugins using a profile
python -m yaft.cli run --zip evidence.zip --profile profiles/ios_full_analysis.toml

# Enable PDF export
python -m yaft.cli run --zip evidence.zip --profile profiles/ios_full_analysis.toml --pdf

# Run other plugins
python -m yaft.cli run HelloWorldPlugin

# Run a plugin with arguments
python -m yaft.cli run HelloWorldPlugin YourName

# Load a plugin explicitly
python -m yaft.cli load ZipAnalyzerPlugin

# Unload a plugin
python -m yaft.cli unload ZipAnalyzerPlugin

# Reload all plugins
python -m yaft.cli reload

# Show version
python -m yaft.cli --version
```

### Case Identifier Management

YAFT includes built-in support for forensic case management. When running plugins, the tool prompts for case identifiers that are automatically included in reports and used to organize output files.

**Case Identifier Formats:**
- **Examiner ID**: User/investigator identifier (alphanumeric with underscores/hyphens, 2-50 characters - e.g., `john_doe`, `examiner-123`)
- **Case ID**: Case number (any alphanumeric string - e.g., `CASE2024-01`, `Case123`, `MyCase`)
- **Evidence ID**: Evidence number (any alphanumeric string - e.g., `EV123456-1`, `Evidence1`, `Ev-001`)

**Example Usage:**
```bash
# Run a plugin (will prompt for case identifiers)
python -m yaft.cli run iOSDeviceInfoExtractorPlugin --zip evidence.zip

# You will be prompted:
# Examiner ID (alphanumeric, 2-50 chars): john_doe
# Case ID (alphanumeric): CASE2024-01
# Evidence ID (alphanumeric): EV123456-1
```

**Output Organization:**
Reports and extracted data are automatically organized by case:
```
yaft_output/
├── CASE2024-01/              # Case ID
│   └── EV123456-1/           # Evidence ID
│       ├── reports/          # Generated reports
│       └── ios_extractions/  # Plugin-specific outputs
```

**Report Metadata:**
Case identifiers are automatically included in report metadata sections:
```markdown
## Metadata
- **Generated**: 2024-01-15 14:30:00
- **Examiner ID**: john_doe
- **Case ID**: CASE2024-01
- **Evidence ID**: EV123456-1
```

**Input Validation:**
The tool validates all case identifiers according to their required formats. Invalid formats will be rejected with clear error messages, and you'll be prompted to re-enter the value.

## Creating Plugins

### Plugin Structure

All plugins must:
1. Inherit from `PluginBase`
2. Implement all abstract methods
3. Provide metadata via the `metadata` property
4. Follow the plugin lifecycle

### Minimal Plugin Example

```python
from typing import Any
from yaft.core.api import CoreAPI
from yaft.core.plugin_base import PluginBase, PluginMetadata


class MyPlugin(PluginBase):
    """My custom plugin."""

    def __init__(self, core_api: CoreAPI) -> None:
        super().__init__(core_api)

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="MyPlugin",
            version="1.0.0",
            description="My custom plugin description",
            author="Your Name",
            requires_core_version=">=0.1.0",
            dependencies=[],
            enabled=True,
        )

    def initialize(self) -> None:
        """Initialize plugin resources."""
        self.core_api.log_info(f"Initializing {self.metadata.name}")

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        """Execute plugin functionality."""
        self.core_api.print_success("Plugin executed successfully!")
        return {"status": "success"}

    def cleanup(self) -> None:
        """Clean up plugin resources."""
        self.core_api.log_info(f"Cleaning up {self.metadata.name}")
```

### Plugin Lifecycle

1. **Instantiation**: Plugin class is instantiated with CoreAPI
2. **Initialize**: `initialize()` is called for setup
3. **Execute**: `execute()` is called when plugin runs
4. **Cleanup**: `cleanup()` is called on unload or exit

### Using Core API

The CoreAPI provides useful functionality to plugins:

```python
def execute(self, *args: Any, **kwargs: Any) -> Any:
    # Logging
    self.core_api.log_info("Information message")
    self.core_api.log_warning("Warning message")
    self.core_api.log_error("Error message")

    # Colored output
    self.core_api.print_success("Success message")
    self.core_api.print_error("Error message")
    self.core_api.print_warning("Warning message")
    self.core_api.print_info("Info message")

    # Case identifier management
    # Validation methods (returns True/False)
    is_valid = self.core_api.validate_examiner_id("john_doe")
    is_valid = self.core_api.validate_case_id("CASE2024-01")
    is_valid = self.core_api.validate_evidence_id("EV123456-1")

    # Setting case identifiers programmatically
    self.core_api.set_case_identifiers("john_doe", "CASE2024-01", "EV123456-1")

    # Getting case identifiers
    examiner, case, evidence = self.core_api.get_case_identifiers()

    # Get case-based output directory (automatically uses case identifiers if set)
    output_dir = self.core_api.get_case_output_dir("ios_extractions")
    # Returns: yaft_output/CASE2024-01/EV123456-1/ios_extractions

    # ZIP file handling (forensic analysis)
    zip_path = self.core_api.get_current_zip()
    files = self.core_api.list_zip_contents()
    content = self.core_api.read_zip_file("file.txt")
    text = self.core_api.read_zip_file_text("file.txt")
    self.core_api.extract_zip_file("file.txt", Path("output"))
    self.core_api.extract_all_zip(Path("output"))
    self.core_api.display_zip_contents()

    # ZIP file search with wildcards
    files = self.core_api.find_files_in_zip("*.db")  # Find all databases
    files = self.core_api.find_files_in_zip("*call*.db", search_path="data/data/")  # Find call logs
    files = self.core_api.find_files_in_zip("*.plist", search_path="System/Library/")  # Find plists

    # Forensic format detection (Cellebrite/GrayKey)
    format_type, prefix = self.core_api.detect_zip_format()
    normalized_path = self.core_api.normalize_zip_path("data/data/com.example/app.db", prefix)

    # OS detection (iOS/Android)
    os_type = self.core_api.get_detected_os()  # Returns ExtractionOS.IOS or ExtractionOS.ANDROID
    extraction_info = self.core_api.get_extraction_info()  # Includes OS version

    # Plist parsing (iOS forensics)
    plist_data = self.core_api.read_plist_from_zip("Info.plist")
    plist_content = self.core_api.parse_plist(raw_bytes)

    # XML parsing (Android forensics)
    xml_root = self.core_api.read_xml_from_zip("packages.xml")
    xml_content = self.core_api.parse_xml(raw_bytes)

    # SQLite querying from ZIP (iOS forensics)
    rows = self.core_api.query_sqlite_from_zip(
        "database.db",
        "SELECT * FROM table WHERE id = ?",
        params=(123,),
        fallback_query="SELECT * FROM old_table WHERE id = ?"  # Optional fallback for schema changes
    )
    # Or get results as dictionaries with column names
    dicts = self.core_api.query_sqlite_from_zip_dict(
        "database.db",
        "SELECT name, value FROM settings"
    )

    # Unified markdown report generation (automatically includes case identifiers)
    sections = [
        {"heading": "Summary", "content": "Analysis completed"},
        {"heading": "Findings", "content": ["Finding 1", "Finding 2"], "style": "list"},
        {"heading": "Statistics", "content": {"total": 10, "errors": 0}, "style": "table"},
    ]
    report_path = self.core_api.generate_report(
        plugin_name="MyPlugin",
        title="Analysis Report",
        sections=sections,
        metadata={"Status": "Complete"}
    )
    # Reports are saved to: yaft_output/CASE2024-01/EV123456-1/reports/

    # User input
    name = self.core_api.get_user_input("Enter your name")
    confirmed = self.core_api.confirm("Are you sure?")

    # File operations
    content = self.core_api.read_file(Path("file.txt"))
    self.core_api.write_file(Path("output.txt"), "content")

    # Shared data (inter-plugin communication)
    self.core_api.set_shared_data("key", "value")
    value = self.core_api.get_shared_data("key", default="default")

    # Configuration paths
    config_path = self.core_api.get_config_path("plugin.toml")

    # Rich console for advanced formatting
    self.core_api.console.print("[bold blue]Formatted text[/bold blue]")
```

### Production Forensic Plugins

YaFT includes production-ready forensic analysis plugins for both iOS and Android devices:

**iOS Forensic Plugins:**
1. **iOSDeviceInfoExtractorPlugin**: Extract comprehensive device information (UDID, IMEI, serial, carrier, timezone, backup info)
2. **iOSCallLogAnalyzerPlugin**: Analyze call history from CallHistory.storedata (regular calls, FaceTime, missed calls)
3. **iOSCellularInfoExtractorPlugin**: Extract cellular information from com.apple.commcenter.plist (IMSI, IMEI updates, ICCI, phone number)

**Android Forensic Plugins:**
4. **AndroidDeviceInfoExtractorPlugin**: Extract device information (manufacturer, model, Android version, IMEI, security settings)
5. **AndroidAppInfoExtractorPlugin**: Extract application metadata (packages.xml, usage statistics, categorization)
6. **AndroidAppPermissionsExtractorPlugin**: Analyze app permissions (runtime permissions, risk scoring, high-risk detection)
7. **AndroidCallLogAnalyzerPlugin**: Analyze call history from calllog.db (regular calls, video calls, pattern analysis)

**Forensic Format Support:**
- All plugins support both **Cellebrite** and **GrayKey** extraction formats
- Automatic format detection and path normalization
- Works with iOS and Android extractions

**General Purpose Plugins:**
8. **hello_world.py**: Simple greeting plugin (example)
9. **file_processor.py**: File processing with statistics (example)
10. **system_info.py**: System information display (example)

### Plugin Profiles

Pre-configured analysis workflows are available in the `profiles/` directory:

**iOS Profiles:**
- `ios_full_analysis.toml`: Complete iOS forensic analysis (device info, call logs)
- `ios_device_only.toml`: Quick device information extraction

**Android Profiles:**
- `android_full_analysis.toml`: Complete Android forensic analysis (device info, apps, permissions, call logs)
- `android_apps_analysis.toml`: Application-focused analysis (metadata and permissions)

Usage:
```bash
python -m yaft.cli run --zip evidence.zip --profile profiles/ios_full_analysis.toml
python -m yaft.cli run --zip android.zip --profile profiles/android_full_analysis.toml --pdf
```

## Advanced Features

### ZIP File Search

The Core API provides powerful file search capabilities with glob-style wildcard patterns:

```python
# Find specific files
files = self.core_api.find_files_in_zip("SystemVersion.plist")

# Find all files with specific extension
files = self.core_api.find_files_in_zip("*.db")

# Find files matching pattern
files = self.core_api.find_files_in_zip("*call*.db")

# Search within specific directory
files = self.core_api.find_files_in_zip("*.db", search_path="data/data/")

# Case-sensitive search
files = self.core_api.find_files_in_zip("File.TXT", case_sensitive=True)

# Limit results
files = self.core_api.find_files_in_zip("*.log", max_results=10)

# Complex patterns with wildcards in paths
files = self.core_api.find_files_in_zip("*/databases/*.db")
```

**Supported patterns:**
- `*` - Matches zero or more characters
- `?` - Matches exactly one character
- `*.ext` - All files with extension
- `name.*` - File with any extension
- `*pattern*` - Files containing pattern
- `path/*/file.ext` - Wildcards in paths

### PDF Export

Automatically export markdown reports to professionally styled PDFs:

**Installation (Optional):**
```bash
# Install PDF export dependencies
uv pip install -e ".[pdf]"

# Or install manually
uv pip install markdown weasyprint
```

**Windows Note:** WeasyPrint requires GTK libraries. Download GTK3 Runtime from [here](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases) and add to PATH.

**Usage:**
```bash
# Enable PDF export with --pdf flag
python -m yaft.cli run iOSDeviceInfoExtractorPlugin --zip evidence.zip --pdf
python -m yaft.cli run --zip evidence.zip --profile profiles/ios_full_analysis.toml --pdf
```

PDFs are generated with professional styling including:
- Blue color scheme with proper typography
- Tables, code blocks, lists, headings
- A4 page format with proper margins
- Automatic generation alongside markdown reports

### Forensic Format Detection

YaFT automatically detects and handles different extraction formats:

**Supported Formats:**
- **Cellebrite iOS**: `filesystem1/` or `filesystem/` prefix
- **Cellebrite Android**: `Dump/` or `fs/` prefix
- **GrayKey iOS**: No prefix (root-level iOS paths)
- **GrayKey Android**: No prefix (root-level Android paths)

Plugins automatically detect the format and normalize file paths:

```python
# Detect format
format_type, prefix = self.core_api.detect_zip_format()

# Normalize paths for access
path = self.core_api.normalize_zip_path("data/data/com.example/app.db", prefix)
```

## Building Executables

### Prerequisites

```bash
pip install pyinstaller
```

### Build Commands

```bash
# Build for current platform
python build_exe.py

# Clean build (removes old artifacts)
python build_exe.py --clean

# Or use platform-specific scripts
./build.sh          # Linux/macOS
build.bat           # Windows
```

### Build Output

```
dist/
└── yaft/
    ├── yaft.exe (Windows) or yaft (Linux)
    ├── plugins/
    │   ├── README.md
    │   ├── hello_world.py
    │   ├── file_processor.py
    │   └── system_info.py
    └── [runtime files]
```

### Adding Plugins to Built Executable

1. Place your plugin `.py` files in `dist/yaft/plugins/`
2. The executable will automatically discover and load them
3. No recompilation needed!

## Project Structure

```
yaft/
├── src/
│   └── yaft/
│       ├── __init__.py          # Package initialization
│       ├── cli.py               # CLI interface
│       └── core/
│           ├── __init__.py
│           ├── api.py           # Core API for plugins
│           ├── plugin_base.py   # Plugin interface
│           └── plugin_manager.py # Plugin management
├── plugins/
│   ├── hello_world.py           # Example: Simple plugin
│   ├── file_processor.py        # Example: File operations
│   └── system_info.py           # Example: System info
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Test fixtures
│   ├── test_core_api.py         # Core API tests
│   ├── test_plugin_base.py      # Plugin base tests
│   └── test_plugin_manager.py   # Plugin manager tests
├── docs/
│   └── SystemRequirements.md    # Project requirements
├── config/                       # Configuration files
├── build_exe.py                  # Build script for executables
├── build.sh                      # Linux/macOS build script
├── build.bat                     # Windows build script
├── pyproject.toml                # Project configuration
├── requirements.txt              # Production dependencies
├── requirements-dev.txt          # Development dependencies
├── Makefile                      # Build automation
└── README.md                     # This file
```

## Development Workflow

### Setup Development Environment

```bash
# Create virtual environment with uv
uv venv

# Activate virtual environment
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

# Install development dependencies
uv pip install -e ".[dev]"

# Or install from requirements files
uv pip install -r requirements-dev.txt
```

### Running Tests

```bash
# Run all tests with coverage
pytest

# Or with make
make test

# Run specific test file
pytest tests/test_core_api.py

# Run with verbose output
pytest -v
```

### Code Quality

```bash
# Lint code
ruff check src/ tests/ plugins/

# Format code
ruff format src/ tests/ plugins/

# Type checking
mypy src/

# Or use make
make lint
make format
make typecheck
```

### Running from Source

```bash
# Run CLI from source
python -m yaft.cli

# Or with make
make run
```

## Developer Tools

### Plugin Profile Editor (GUI)

A standalone GUI application for visually creating and editing plugin profiles. No need to manually edit TOML files!

**Features:**
- Visual plugin selection with descriptions
- Drag-and-drop plugin ordering
- Create, load, save, and edit profiles
- Automatic plugin discovery

**Launch:**
```bash
# Windows
tools\profile_editor\launch_editor.bat

# Linux/macOS
./tools/profile_editor/launch_editor.sh
```

**Documentation:** See [tools/profile_editor/README.md](tools/profile_editor/README.md) for detailed instructions and [QUICKSTART.md](tools/profile_editor/QUICKSTART.md) for a quick guide.

## Technology Stack Decisions

### Why These Tools?

**Typer (CLI)**
- Modern, type-safe CLI framework
- Automatic help generation
- Excellent user experience
- Native support for type hints

**Rich (Output)**
- Beautiful terminal output
- Tables, panels, progress bars
- Color support across platforms
- Extensive formatting options

**Pydantic (Validation)**
- Type-safe data validation
- Immutable configurations
- Excellent error messages
- Industry standard for Python 3.7+

**PyInstaller (Building)**
- Mature, stable executable builder
- Cross-platform support
- Supports dynamic imports (critical for plugins)
- Large community and documentation

**uv (Package Manager)**
- Extremely fast Python package installer (10-100x faster than pip)
- Modern dependency management
- Virtual environment management
- Drop-in replacement for pip and pip-tools

**Ruff (Code Quality)**
- Extremely fast linting and formatting
- Replaces multiple tools (black, isort, flake8)
- Native Python, no dependencies
- Active development

### Architectural Decisions

**Plugin Discovery**
- Uses `importlib` for dynamic imports
- Scans directories for `.py` files
- Runtime inspection for PluginBase subclasses
- Works in both source and built executables

**Type Safety**
- Full type hints throughout codebase
- Pydantic for runtime validation
- mypy for static type checking
- Prevents common bugs at development time

**Loose Coupling**
- Plugins only depend on PluginBase interface
- CoreAPI provides all shared functionality
- Plugins cannot directly access each other
- Clean separation of concerns

**Error Handling**
- Graceful degradation (failed plugins don't crash app)
- Comprehensive logging at all levels
- User-friendly error messages
- Status tracking for debugging

## Advanced Topics

### Plugin Dependencies

Plugins can specify dependencies on other plugins:

```python
@property
def metadata(self) -> PluginMetadata:
    return PluginMetadata(
        name="DependentPlugin",
        version="1.0.0",
        description="Depends on other plugins",
        dependencies=["HelloWorld", "SystemInfo"],
    )
```

### Inter-Plugin Communication

Use shared data for plugins to communicate:

```python
# Plugin A sets data
self.core_api.set_shared_data("user_name", "John")

# Plugin B reads data
name = self.core_api.get_shared_data("user_name", "Guest")
```

### Configuration Files

Store plugin configuration:

```python
def initialize(self) -> None:
    config_path = self.core_api.get_config_path("myplugin.toml")
    if config_path.exists():
        import toml
        self.config = toml.load(config_path)
```

### Hot Reloading (Development)

```bash
# Reload all plugins without restarting
python -m yaft.cli reload
```

## Testing Plugins

Create tests for your plugins:

```python
# tests/test_my_plugin.py
import pytest
from plugins.my_plugin import MyPlugin
from yaft.core.api import CoreAPI

def test_my_plugin(core_api):
    plugin = MyPlugin(core_api)
    plugin.initialize()
    result = plugin.execute()
    assert result is not None
    plugin.cleanup()
```

## Troubleshooting

### Plugin Not Discovered

- Ensure plugin file is in the `plugins/` directory
- Check that plugin file doesn't start with underscore
- Verify plugin class inherits from `PluginBase`
- Run `list-plugins --all` to see discovery status

### Build Fails

- Ensure PyInstaller is installed: `pip install pyinstaller`
- Check Python version (requires 3.13+)
- Clean build directory: `python build_exe.py --clean`
- Check for import errors in plugins

### Import Errors in Built Executable

- Verify all dependencies are listed in requirements.txt
- Check PyInstaller spec file includes all packages
- Test plugins work from source first

## Contributing

Contributions are welcome! Please:

1. Follow the existing code style (use ruff)
2. Add tests for new features
3. Update documentation
4. Ensure all tests pass

## License

[Your chosen license]

## Support

- Documentation: See `docs/` directory
- Issues: [Your issue tracker]
- Email: [Your email]

## Acknowledgments

Built with:
- [Typer](https://typer.tiangolo.com/)
- [Rich](https://rich.readthedocs.io/)
- [Pydantic](https://docs.pydantic.dev/)
- [PyInstaller](https://pyinstaller.org/)
