# Contributing to YAFT

Thank you for your interest in contributing to YAFT! This document provides guidelines for contributing to the project.

## Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/RedRockerSE/yaft2.git
   cd yaft
   ```

2. **Install Dependencies**
   ```bash
   # Install uv if not already installed
   # Windows
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   # Linux/macOS
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Create virtual environment and install dev dependencies
   uv venv
   uv pip install -e ".[dev]"
   ```

3. **Create a Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Workflow

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/yaft --cov-report=html

# Run specific test file
pytest tests/test_core_api.py

# Run specific test
pytest tests/test_core_api.py::test_validate_case_id
```

### Code Quality

```bash
# Format code with ruff
ruff format src/ tests/

# Lint code
ruff check src/ tests/

# Fix auto-fixable issues
ruff check --fix src/ tests/

# Type checking
mypy src/
```

### Running YAFT Locally

```bash
# Run from source
python -m yaft.cli --help

# List plugins
python -m yaft.cli list-plugins --all

# Run a plugin
python -m yaft.cli run YourPlugin --zip test.zip
```

## Creating a New Plugin

1. **Create Plugin File**

   Create a new file in the `plugins/` directory:
   ```python
   # plugins/my_forensic_plugin.py
   from typing import Any, Dict
   from yaft.core.api import CoreAPI
   from yaft.core.plugin_base import PluginBase, PluginMetadata

   class MyForensicPlugin(PluginBase):
       def __init__(self, core_api: CoreAPI) -> None:
           super().__init__(core_api)

       @property
       def metadata(self) -> PluginMetadata:
           return PluginMetadata(
               name="MyForensicPlugin",
               version="1.0.0",
               description="Description of what your plugin does",
               author="Your Name",
               requires_core_version=">=0.1.0",
               dependencies=[],
               enabled=True,
               target_os=["ios"]  # or ["android"], ["any"], or ["ios", "android"]
           )

       def initialize(self) -> None:
           """Initialize the plugin."""
           self.core_api.log_info(f"Initializing {self.metadata.name}")

       def execute(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
           """Execute the plugin's main functionality."""
           # Your forensic analysis logic here
           self.core_api.print_info("Running analysis...")

           # Example: Read a file from ZIP
           current_zip = self.core_api.get_current_zip()
           if not current_zip:
               return {"success": False, "error": "No ZIP file loaded"}

           # Your analysis code here

           return {"success": True}

       def cleanup(self) -> None:
           """Clean up resources."""
           self.core_api.log_info(f"Cleaning up {self.metadata.name}")
   ```

2. **Test Your Plugin**
   ```bash
   python -m yaft.cli list-plugins --all
   python -m yaft.cli run MyForensicPlugin --zip test.zip
   ```

3. **Add Tests**

   Create a test file in `tests/`:
   ```python
   # tests/test_my_forensic_plugin.py
   import pytest
   from plugins.my_forensic_plugin import MyForensicPlugin
   from yaft.core.api import CoreAPI

   def test_my_forensic_plugin():
       core_api = CoreAPI()
       plugin = MyForensicPlugin(core_api)

       assert plugin.metadata.name == "MyForensicPlugin"
       plugin.initialize()
       # Add more tests
   ```

## Pull Request Guidelines

1. **Before Submitting**
   - Ensure all tests pass: `pytest`
   - Run linting: `ruff check src/ tests/`
   - Run type checking: `mypy src/`
   - Update documentation if needed
   - Add tests for new features

2. **PR Description**
   - Describe what changes you made
   - Explain why the changes are needed
   - Reference any related issues
   - Include screenshots for UI changes

3. **Commit Messages**

   Follow conventional commits:
   ```
   feat: add support for Android extractions
   fix: resolve issue with ZIP path handling
   docs: update plugin development guide
   test: add tests for core API
   chore: bump version to 0.2.0
   ```

4. **Code Review**
   - Address reviewer feedback
   - Keep the PR focused on a single feature/fix
   - Rebase on main if needed

## CI/CD Pipeline

All pull requests and commits trigger automated checks:

- **Linting**: Code style and quality checks with ruff
- **Type Checking**: Static type analysis with mypy
- **Testing**: Full test suite on Windows, macOS, and Linux
- **Coverage**: Code coverage reporting

## Release Process

Releases are automated via GitHub Actions. See [.github/RELEASE.md](.github/RELEASE.md) for details.

To create a new release:
1. Update version in `pyproject.toml` and `src/yaft/__init__.py`
2. Commit and create a version tag: `git tag v0.2.0`
3. Push the tag: `git push origin v0.2.0`
4. GitHub Actions will build and release automatically

## Getting Help

- **Issues**: Report bugs or request features via [GitHub Issues](https://github.com/YOUR_USERNAME/yaft/issues)
- **Discussions**: Ask questions in [GitHub Discussions](https://github.com/YOUR_USERNAME/yaft/discussions)
- **Documentation**: Check the [README](README.md) and [CLAUDE.md](CLAUDE.md)

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on the code, not the person
- Help others learn and grow

Thank you for contributing to YAFT! 🚀
