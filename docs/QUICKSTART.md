# YAFT Quick Start Guide

Get up and running with YAFT in under 5 minutes!

## Step 1: Install Dependencies

```bash
# Using pip
pip install -r requirements-dev.txt

# Or using Poetry (recommended)
poetry install
```

## Step 2: Verify Installation

```bash
# Run from source
python -m yaft.cli --version

# You should see:
# YAFT v0.1.0
```

## Step 3: Explore Example Plugins

```bash
# List all available plugins
python -m yaft.cli list-plugins --all

# You should see:
# - HelloWorldPlugin
# - FileProcessorPlugin
# - SystemInfoPlugin
```

## Step 4: Run Example Plugins

```bash
# Run the Hello World plugin
python -m yaft.cli run HelloWorldPlugin

# Run with a custom name
python -m yaft.cli run HelloWorldPlugin "Your Name"

# Get system information
python -m yaft.cli run SystemInfoPlugin

# Process a file (create a test file first)
echo "This is a test file" > test.txt
python -m yaft.cli run FileProcessorPlugin test.txt
```

## Step 5: Create Your First Plugin

Create a new file `plugins/my_first_plugin.py`:

```python
from typing import Any
from yaft.core.api import CoreAPI
from yaft.core.plugin_base import PluginBase, PluginMetadata


class MyFirstPlugin(PluginBase):
    """My first custom plugin."""

    def __init__(self, core_api: CoreAPI) -> None:
        super().__init__(core_api)

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="MyFirst",
            version="1.0.0",
            description="My first custom plugin",
            author="Your Name",
        )

    def initialize(self) -> None:
        self.core_api.log_info("Initializing MyFirst plugin")

    def execute(self, *args: Any, **kwargs: Any) -> str:
        message = "Hello from my first plugin!"
        self.core_api.print_success(message)
        return message

    def cleanup(self) -> None:
        self.core_api.log_info("Cleaning up MyFirst plugin")
```

## Step 6: Test Your Plugin

```bash
# Reload plugins to discover your new plugin
python -m yaft.cli reload

# Run your plugin
python -m yaft.cli run MyFirstPlugin

# You should see:
# ✓ Hello from my first plugin!
```

## Step 7: Build Executable (Optional)

```bash
# Build for your platform
python build.py

# Or use platform-specific scripts
./build.sh         # Linux/macOS
build.bat          # Windows

# The executable will be in: dist/yaft/
```

## Step 8: Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/yaft --cov-report=html

# View coverage report
# Open htmlcov/index.html in your browser
```

## Common Commands Cheat Sheet

```bash
# Plugin Management
python -m yaft.cli list-plugins              # List loaded plugins
python -m yaft.cli list-plugins --all        # List all plugins
python -m yaft.cli info <PluginName>         # Show plugin info
python -m yaft.cli load <PluginName>         # Load a plugin
python -m yaft.cli unload <PluginName>       # Unload a plugin
python -m yaft.cli reload                    # Reload all plugins

# Running Plugins
python -m yaft.cli run <PluginName>          # Run a plugin
python -m yaft.cli run <PluginName> arg1     # Run with arguments

# Development
pytest                                        # Run tests
ruff check .                                 # Lint code
ruff format .                                # Format code
mypy src/                                    # Type check

# Building
python build.py                              # Build executable
python build.py --clean                      # Clean build
```

## Next Steps

1. **Read the full documentation**: See `README.md`
2. **Study example plugins**: Check `plugins/` directory
3. **Learn plugin development**: Read `docs/PLUGIN_DEVELOPMENT.md`
4. **Understand architecture**: Read `docs/ARCHITECTURE.md`
5. **Create your own plugins**: Start building!

## Troubleshooting

### Plugin Not Found

```bash
# Make sure the plugin file is in plugins/
ls plugins/

# Reload plugins
python -m yaft.cli reload

# Check plugin status
python -m yaft.cli list-plugins --all
```

### Import Errors

```bash
# Make sure dependencies are installed
pip install -r requirements.txt

# Check Python version (needs 3.13+)
python --version
```

### Build Issues

```bash
# Install PyInstaller
pip install pyinstaller

# Clean and rebuild
python build.py --clean
```

## Getting Help

- Full Documentation: `README.md`
- Plugin Development: `docs/PLUGIN_DEVELOPMENT.md`
- Architecture: `docs/ARCHITECTURE.md`
- Examples: `plugins/` directory
- Tests: `tests/` directory

## What You Just Learned

- How to install and run YAFT
- How to use the CLI interface
- How to run example plugins
- How to create a custom plugin
- How to build executables
- How to run tests

Congratulations! You're ready to build with YAFT!
