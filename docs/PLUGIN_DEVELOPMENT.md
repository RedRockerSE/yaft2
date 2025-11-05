# Plugin Development Guide

This guide covers everything you need to know to develop plugins for YAFT.

## Table of Contents

1. [Plugin Basics](#plugin-basics)
2. [Plugin Interface](#plugin-interface)
3. [Plugin Metadata](#plugin-metadata)
4. [Plugin Lifecycle](#plugin-lifecycle)
5. [Using Core API](#using-core-api)
6. [Best Practices](#best-practices)
7. [Advanced Topics](#advanced-topics)
8. [Testing Plugins](#testing-plugins)

## Plugin Basics

### What is a Plugin?

A plugin is a Python module that extends YAFT's functionality. Plugins are:
- **Dynamically loadable**: Discovered and loaded at runtime
- **Self-contained**: Include all their logic and dependencies
- **Loosely coupled**: Only depend on the PluginBase interface
- **Lifecycle-managed**: Have clear initialization, execution, and cleanup phases

### File Structure

```
plugins/
└── my_plugin.py       # Your plugin file
```

Each plugin file should contain one class that inherits from `PluginBase`.

## Plugin Interface

### Required Methods

Every plugin must implement these methods:

```python
from typing import Any
from yaft.core.api import CoreAPI
from yaft.core.plugin_base import PluginBase, PluginMetadata


class MyPlugin(PluginBase):
    """Your plugin description."""

    def __init__(self, core_api: CoreAPI) -> None:
        """Initialize with CoreAPI access."""
        super().__init__(core_api)
        # Your initialization here

    @property
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        return PluginMetadata(
            name="MyPlugin",
            version="1.0.0",
            description="What your plugin does",
            author="Your Name",
        )

    def initialize(self) -> None:
        """Setup resources, validate dependencies."""
        pass

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        """Main plugin logic."""
        pass

    def cleanup(self) -> None:
        """Release resources, save state."""
        pass
```

## Plugin Metadata

### PluginMetadata Fields

```python
PluginMetadata(
    name="MyPlugin",                    # Required: Unique identifier
    version="1.0.0",                    # Required: Semantic version
    description="Plugin description",   # Required: What it does
    author="Your Name",                 # Optional: Your name
    requires_core_version=">=0.1.0",   # Optional: Min core version
    dependencies=[],                    # Optional: Other plugins needed
    enabled=True,                       # Optional: Enable/disable
)
```

### Version Format

Use semantic versioning (MAJOR.MINOR.PATCH):
- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes

### Dependencies

List other plugins your plugin needs:

```python
PluginMetadata(
    name="DataProcessor",
    version="1.0.0",
    description="Processes data from other plugins",
    dependencies=["DataLoader", "DataValidator"],
)
```

## Plugin Lifecycle

### 1. Instantiation

```python
def __init__(self, core_api: CoreAPI) -> None:
    super().__init__(core_api)
    # Initialize instance variables
    self._counter = 0
    self._cache: dict[str, Any] = {}
```

**Do:**
- Initialize instance variables
- Store CoreAPI reference
- Set default values

**Don't:**
- Access external resources
- Perform I/O operations
- Validate dependencies (use initialize() for this)

### 2. Initialization

```python
def initialize(self) -> None:
    """Setup phase - called once after plugin is loaded."""
    self.core_api.log_info(f"Initializing {self.metadata.name}")

    # Load configuration
    config_path = self.core_api.get_config_path("my_plugin.toml")
    if config_path.exists():
        self._load_config(config_path)

    # Validate dependencies
    if not self._check_dependencies():
        raise RuntimeError("Dependencies not met")

    # Setup resources
    self._setup_resources()
```

**Do:**
- Load configuration files
- Validate dependencies
- Allocate resources
- Register event handlers
- Raise exceptions if setup fails

**Don't:**
- Perform the main plugin work (use execute() for this)
- Start long-running processes
- Assume resources exist (check first)

### 3. Execution

```python
def execute(self, *args: Any, **kwargs: Any) -> Any:
    """Main plugin logic - called when plugin runs."""
    # Parse arguments
    input_data = args[0] if args else kwargs.get("data")

    # Validate input
    if not self._validate_input(input_data):
        self.core_api.print_error("Invalid input")
        return None

    # Process
    result = self._process(input_data)

    # Display results
    self._display_results(result)

    return result
```

**Do:**
- Implement main plugin functionality
- Handle arguments gracefully
- Validate input
- Return meaningful results
- Use CoreAPI for output
- Handle errors gracefully

**Don't:**
- Rely on specific arguments without checking
- Print directly (use CoreAPI)
- Exit the application
- Leave resources open (close them)

### 4. Cleanup

```python
def cleanup(self) -> None:
    """Teardown phase - called when plugin unloads."""
    self.core_api.log_info(f"Cleaning up {self.metadata.name}")

    # Close file handles
    if hasattr(self, "_file_handle"):
        self._file_handle.close()

    # Save state
    self._save_state()

    # Clear cache
    self._cache.clear()

    # Release resources
    self._release_resources()
```

**Do:**
- Close file handles
- Release network connections
- Save state if needed
- Clear caches
- Log cleanup actions

**Don't:**
- Raise exceptions (log errors instead)
- Perform long operations
- Access already-cleaned resources

## Using Core API

### Logging

```python
# Different log levels
self.core_api.log_debug("Detailed diagnostic information")
self.core_api.log_info("General information")
self.core_api.log_warning("Warning messages")
self.core_api.log_error("Error messages")
```

### Colored Output

```python
# Status messages with colors
self.core_api.print_success("Operation completed")
self.core_api.print_error("Operation failed")
self.core_api.print_warning("Be careful")
self.core_api.print_info("For your information")
```

### User Input

```python
# Get text input
name = self.core_api.get_user_input("Enter your name")

# Get confirmation
if self.core_api.confirm("Delete all files?"):
    delete_files()
```

### File Operations

```python
from pathlib import Path

# Read file
try:
    content = self.core_api.read_file(Path("input.txt"))
except FileNotFoundError:
    self.core_api.log_error("File not found")

# Write file
self.core_api.write_file(Path("output.txt"), "content")
```

### Configuration Files

```python
# Get config path
config_path = self.core_api.get_config_path("my_plugin.toml")

# Read config
if config_path.exists():
    import toml
    config = toml.load(config_path)
```

### Shared Data (Inter-Plugin Communication)

```python
# Store data for other plugins
self.core_api.set_shared_data("user_preferences", preferences)

# Read data from other plugins
preferences = self.core_api.get_shared_data(
    "user_preferences",
    default={"theme": "dark"}
)

# Clear data
self.core_api.clear_shared_data("user_preferences")
```

### Rich Console (Advanced Formatting)

```python
from rich.table import Table
from rich.panel import Panel

# Create a table
table = Table(title="Results")
table.add_column("Name", style="cyan")
table.add_column("Value", style="magenta")
table.add_row("Item 1", "100")
self.core_api.console.print(table)

# Create a panel
panel = Panel("Important message", title="Alert", border_style="red")
self.core_api.console.print(panel)

# Rich formatting
self.core_api.console.print("[bold blue]Bold blue text[/bold blue]")
```

## Best Practices

### 1. Error Handling

```python
def execute(self, *args: Any, **kwargs: Any) -> Any:
    try:
        result = self._risky_operation()
        return result
    except ValueError as e:
        self.core_api.log_error(f"Invalid value: {e}")
        return None
    except Exception as e:
        self.core_api.log_error(f"Unexpected error: {e}")
        self.status = PluginStatus.ERROR
        raise
```

### 2. Type Hints

```python
from typing import Any, Optional
from pathlib import Path

def execute(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
    filepath: Optional[Path] = None

    if args:
        filepath = Path(args[0])

    result: dict[str, Any] = {
        "success": True,
        "filepath": str(filepath) if filepath else None,
    }

    return result
```

### 3. Docstrings

```python
class MyPlugin(PluginBase):
    """
    A plugin that processes data files.

    This plugin reads data files, validates their format,
    and generates statistical summaries.

    Example usage:
        yaft run MyPlugin input.csv
    """

    def execute(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """
        Process a data file and return statistics.

        Args:
            *args: First argument should be the file path
            **kwargs: Optional 'format' key for file format

        Returns:
            Dictionary containing processing statistics

        Raises:
            FileNotFoundError: If input file doesn't exist
            ValueError: If file format is invalid
        """
        pass
```

### 4. Resource Management

```python
from pathlib import Path

def initialize(self) -> None:
    """Initialize with resource management."""
    self._temp_dir = Path("temp")
    self._temp_dir.mkdir(exist_ok=True)

def cleanup(self) -> None:
    """Clean up temporary resources."""
    import shutil
    if self._temp_dir.exists():
        shutil.rmtree(self._temp_dir)
```

### 5. Configuration

```python
from pathlib import Path
import toml

def initialize(self) -> None:
    """Load configuration."""
    config_path = self.core_api.get_config_path("my_plugin.toml")

    # Create default config if doesn't exist
    if not config_path.exists():
        default_config = {
            "max_retries": 3,
            "timeout": 30,
            "enabled_features": ["feature1", "feature2"],
        }
        self.core_api.write_file(
            config_path,
            toml.dumps(default_config)
        )

    # Load config
    content = self.core_api.read_file(config_path)
    self.config = toml.loads(content)
```

## Advanced Topics

### Progress Bars

```python
from rich.progress import track

def execute(self, *args: Any, **kwargs: Any) -> Any:
    items = range(100)

    for item in track(items, description="Processing..."):
        process_item(item)
```

### Live Display

```python
from rich.live import Live
from rich.table import Table
import time

def execute(self, *args: Any, **kwargs: Any) -> Any:
    with Live(auto_refresh=False) as live:
        for i in range(10):
            table = Table(title=f"Progress: {i}/10")
            table.add_column("Step")
            table.add_column("Status")
            table.add_row(f"Step {i}", "Complete")

            live.update(table, refresh=True)
            time.sleep(0.5)
```

### Async Execution

```python
import asyncio

def execute(self, *args: Any, **kwargs: Any) -> Any:
    """Execute async operations."""
    return asyncio.run(self._async_execute(*args, **kwargs))

async def _async_execute(self, *args: Any, **kwargs: Any) -> Any:
    """Async implementation."""
    result = await self._fetch_data()
    return result
```

### Plugin State Persistence

```python
import json
from pathlib import Path

def cleanup(self) -> None:
    """Save plugin state."""
    state = {
        "counter": self._counter,
        "last_run": datetime.now().isoformat(),
        "cache": self._cache,
    }

    state_path = self.core_api.get_config_path("my_plugin_state.json")
    self.core_api.write_file(
        state_path,
        json.dumps(state, indent=2)
    )

def initialize(self) -> None:
    """Restore plugin state."""
    state_path = self.core_api.get_config_path("my_plugin_state.json")

    if state_path.exists():
        content = self.core_api.read_file(state_path)
        state = json.loads(content)
        self._counter = state.get("counter", 0)
        self._cache = state.get("cache", {})
```

## Testing Plugins

### Unit Tests

```python
# tests/test_my_plugin.py
import pytest
from pathlib import Path
from plugins.my_plugin import MyPlugin
from yaft.core.api import CoreAPI


def test_plugin_initialization(core_api):
    """Test plugin initializes correctly."""
    plugin = MyPlugin(core_api)
    plugin.initialize()

    assert plugin.metadata.name == "MyPlugin"
    assert plugin.status.value == "initialized"


def test_plugin_execution(core_api):
    """Test plugin executes correctly."""
    plugin = MyPlugin(core_api)
    plugin.initialize()

    result = plugin.execute("test_arg")

    assert result is not None
    assert isinstance(result, dict)


def test_plugin_cleanup(core_api):
    """Test plugin cleans up resources."""
    plugin = MyPlugin(core_api)
    plugin.initialize()
    plugin.cleanup()

    # Verify resources are released
    assert not hasattr(plugin, "_open_file")
```

### Integration Tests

```python
def test_plugin_integration(core_api, tmp_path):
    """Test plugin with actual files."""
    # Setup
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")

    # Execute
    plugin = MyPlugin(core_api)
    plugin.initialize()
    result = plugin.execute(str(test_file))

    # Verify
    assert result["success"] is True
    plugin.cleanup()
```

### Manual Testing

```bash
# Test plugin discovery
python -m yaft.cli list-plugins --all

# Test plugin loading
python -m yaft.cli load MyPlugin

# Test plugin execution
python -m yaft.cli run MyPlugin arg1 arg2

# Test plugin info
python -m yaft.cli info MyPlugin
```

## Common Patterns

### Command Pattern

```python
class CommandPlugin(PluginBase):
    """Plugin that executes commands."""

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        command = args[0] if args else "help"

        commands = {
            "help": self._show_help,
            "status": self._show_status,
            "process": self._process_data,
        }

        if command in commands:
            return commands[command](*args[1:], **kwargs)
        else:
            self.core_api.print_error(f"Unknown command: {command}")
            return None
```

### Menu Pattern

```python
def execute(self, *args: Any, **kwargs: Any) -> Any:
    """Display interactive menu."""
    while True:
        self.core_api.console.print("\n[bold]Menu:[/bold]")
        self.core_api.console.print("1. Option 1")
        self.core_api.console.print("2. Option 2")
        self.core_api.console.print("0. Exit")

        choice = self.core_api.get_user_input("Choose option")

        if choice == "0":
            break
        elif choice == "1":
            self._option1()
        elif choice == "2":
            self._option2()
```

## Troubleshooting

### Plugin Not Discovered

- File must be in `plugins/` directory
- File must not start with underscore
- Class must inherit from `PluginBase`
- Check for syntax errors

### Import Errors

- Ensure all imports are available
- Check requirements.txt for dependencies
- Verify imports work in Python environment

### Plugin Fails to Load

- Check `initialize()` method for exceptions
- Review logs for error messages
- Verify dependencies are loaded
- Check configuration files exist

## Resources

- Main README: `../README.md`
- Example plugins: `../plugins/`
- Core API source: `../src/yaft/core/api.py`
- Plugin base source: `../src/yaft/core/plugin_base.py`

## Getting Help

- Review example plugins
- Check test files for patterns
- Read the main documentation
- Open an issue on GitHub
