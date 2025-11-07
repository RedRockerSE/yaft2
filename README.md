# YAFT - Yet Another Forensic Tool

[![CI](https://github.com/RedRockerSE/yaft/actions/workflows/ci.yml/badge.svg)](https://github.com/RedRockerSE/yaft/actions/workflows/ci.yml)
[![Release](https://github.com/RedRockerSE/yaft/actions/workflows/release.yml/badge.svg)](https://github.com/RedRockerSE/yaft/actions/workflows/release.yml)
[![Python Version](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A plugin-based forensic analysis tool for Python 3.13+ designed for processing and analyzing ZIP archives. Features dynamic plugin loading, beautiful CLI interface, and cross-platform executable builds.

## Features

- **ZIP File Processing**: Built-in support for forensic analysis of ZIP archives
- **Dynamic Plugin System**: Load and manage forensic plugins at runtime without code changes
- **Beautiful CLI**: Color-coded output with Rich and Typer for forensic reporting
- **Case Management**: Forensic case identifier support (Examiner ID, Case ID, Evidence ID) with automatic validation and report organization
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

Download the latest release for your platform from the [Releases page](https://github.com/YOUR_USERNAME/yaft/releases):

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

### Basic Usage

```bash
# List available plugins
python -m yaft.cli list-plugins

# Show all plugins (including unloaded)
python -m yaft.cli list-plugins --all

# Get plugin information
python -m yaft.cli info ZipAnalyzerPlugin

# Analyze a ZIP file with a plugin (NOTE: use full class name with "Plugin" suffix)
python -m yaft.cli run ZipAnalyzerPlugin --zip evidence.zip

# iOS forensic analysis
python -m yaft.cli run iOSAppGUIDExtractorPlugin --zip ios_extraction.zip
python -m yaft.cli run iOSAppPermissionsExtractorPlugin --zip ios_extraction.zip

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
- **Examiner ID**: User/investigator identifier (format: alphanumeric with underscores/hyphens, 2-50 characters - e.g., `john_doe`, `examiner-123`)
- **Case ID**: Case number (format: 4+ uppercase alphanumeric characters, dash, 2+ digits - e.g., `CASE2024-01`, `K2024001-01`)
- **Evidence ID**: Evidence number (format: 2-4 uppercase letters, 4-8 digits, dash, 1-2 digits - e.g., `BG123456-1`, `EV123456-01`)

**Example Usage:**
```bash
# Run a plugin (will prompt for case identifiers)
python -m yaft.cli run iOSAppGUIDExtractorPlugin --zip evidence.zip

# You will be prompted:
# ? Examiner ID (alphanumeric, 2-50 chars): john_doe
# ? Case ID (format: CASE2024-01): CASE2024-01
# ? Evidence ID (format: BG123456-1): BG123456-1
```

**Output Organization:**
Reports and extracted data are automatically organized by case:
```
yaft_output/
├── CASE2024-01/              # Case ID
│   └── BG123456-1/           # Evidence ID
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
- **Evidence ID**: BG123456-1
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
    is_valid = self.core_api.validate_evidence_id("BG123456-1")

    # Setting case identifiers programmatically
    self.core_api.set_case_identifiers("john_doe", "CASE2024-01", "BG123456-1")

    # Getting case identifiers
    examiner, case, evidence = self.core_api.get_case_identifiers()

    # Get case-based output directory (automatically uses case identifiers if set)
    output_dir = self.core_api.get_case_output_dir("ios_extractions")
    # Returns: yaft_output/CASE2024-01/BG123456-1/ios_extractions

    # ZIP file handling (forensic analysis)
    zip_path = self.core_api.get_current_zip()
    files = self.core_api.list_zip_contents()
    content = self.core_api.read_zip_file("file.txt")
    text = self.core_api.read_zip_file_text("file.txt")
    self.core_api.extract_zip_file("file.txt", Path("output"))
    self.core_api.extract_all_zip(Path("output"))
    self.core_api.display_zip_contents()

    # Plist parsing (iOS forensics)
    plist_data = self.core_api.read_plist_from_zip("Info.plist")
    plist_content = self.core_api.parse_plist(raw_bytes)

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
    # Reports are saved to: yaft_output/CASE2024-01/BG123456-1/reports/

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

### Example Plugins

Six plugins are included:

**Forensic Analysis Plugins:**
1. **zip_analyzer.py**: General forensic analysis of ZIP archives
2. **ios_app_guid_extractor.py**: iOS application GUID and bundle ID extraction from filesystem extractions
3. **ios_app_permissions_extractor.py**: iOS application permissions, usage statistics, and privacy analysis

**General Purpose Plugins:**
4. **hello_world.py**: Simple greeting plugin
5. **file_processor.py**: File processing with statistics
6. **system_info.py**: System information display

The iOS forensic plugins are production-ready tools for analyzing iOS extractions (Cellebrite format supported).

## Building Executables

### Prerequisites

```bash
pip install pyinstaller
```

### Build Commands

```bash
# Build for current platform
python build.py

# Clean build (removes old artifacts)
python build.py --clean

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
├── build.py                      # Build script
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
- Clean build directory: `python build.py --clean`
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
