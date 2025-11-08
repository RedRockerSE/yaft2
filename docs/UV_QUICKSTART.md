# uv Quick Start Guide for YaFT

This guide shows you how to use `uv` (Astral's ultra-fast Python package manager) with the YaFT project.

## What is uv?

`uv` is a modern Python package manager that's 10-100x faster than pip. It's a drop-in replacement for pip, pip-tools, and virtualenv, written in Rust for maximum performance.

## Installation

### Windows
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Linux/macOS
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Quick Start

### 1. Create a Virtual Environment
```bash
# Create .venv directory
uv venv

# Using a specific Python version
uv venv --python 3.13
```

### 2. Activate Virtual Environment

**Windows (PowerShell):**
```powershell
.venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
.venv\Scripts\activate.bat
```

**Linux/macOS:**
```bash
source .venv/bin/activate
```

### 3. Install Dependencies

**Install with dev dependencies (recommended for development):**
```bash
uv pip install -e ".[dev]"
```

**Install from requirements files:**
```bash
# Production dependencies only
uv pip install -r requirements.txt

# Development dependencies (includes production)
uv pip install -r requirements-dev.txt
```

**Install project in editable mode:**
```bash
uv pip install -e .
```

## Common uv Commands

### Package Management

```bash
# Install a package
uv pip install package-name

# Install a specific version
uv pip install package-name==1.0.0

# Install from PyPI with version constraint
uv pip install "package-name>=1.0.0,<2.0.0"

# Uninstall a package
uv pip uninstall package-name

# List installed packages
uv pip list

# Show package information
uv pip show package-name

# Upgrade a package
uv pip install --upgrade package-name

# Upgrade all packages
uv pip install --upgrade -r requirements.txt
```

### Requirements Files

```bash
# Generate requirements.txt from current environment
uv pip freeze > requirements.txt

# Install from requirements file
uv pip install -r requirements.txt

# Compile requirements (like pip-compile)
uv pip compile pyproject.toml -o requirements.txt
```

### Virtual Environments

```bash
# Create virtual environment
uv venv

# Create with specific Python version
uv venv --python 3.13
uv venv --python python3.12

# Create with specific name
uv venv my-venv

# Remove virtual environment
rm -rf .venv  # Linux/macOS
rmdir /s .venv  # Windows
```

## YaFT Development Workflow

### Initial Setup

```bash
# 1. Clone repository
git clone <repository-url>
cd yaft

# 2. Create virtual environment
uv venv

# 3. Activate virtual environment
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate

# 4. Install development dependencies
uv pip install -e ".[dev]"
```

### Daily Development

```bash
# Activate environment (if not already active)
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Run the application
python -m yaft.cli list-plugins
python -m yaft.cli run ZipAnalyzerPlugin --zip evidence.zip

# Run tests
pytest

# Run tests with coverage
pytest --cov=src/yaft

# Format code
ruff format src/ tests/ plugins/

# Lint code
ruff check src/ tests/ plugins/

# Type check
mypy src/
```

### Adding New Dependencies

```bash
# Install new package
uv pip install new-package

# Update pyproject.toml manually to add to dependencies:
# dependencies = [
#     "new-package>=1.0.0",
# ]

# Or for dev dependencies:
# [project.optional-dependencies]
# dev = [
#     "new-package>=1.0.0",
# ]

# Regenerate requirements files
uv pip compile pyproject.toml -o requirements.txt
```

## Why uv?

### Speed Comparison

- **pip**: ~45 seconds to install dependencies
- **uv**: ~2 seconds to install dependencies

That's **20x faster** for typical projects!

### Key Advantages

1. **Blazingly Fast**: Written in Rust, optimized for performance
2. **Drop-in Replacement**: Compatible with pip, pip-tools, virtualenv
3. **Modern**: Built from the ground up with modern Python standards
4. **Reliable**: Uses the same resolution algorithm as pip
5. **No Configuration**: Works out of the box with existing projects

### uv vs pip vs Poetry

| Feature | uv | pip | Poetry |
|---------|-----|-----|--------|
| Speed | ⚡⚡⚡ | ⚡ | ⚡⚡ |
| Virtual Envs | ✅ | ❌ | ✅ |
| Lock Files | ✅ | ❌ | ✅ |
| Compatibility | ✅ pip-compatible | ✅ Standard | ⚠️ Own format |
| Installation | Single binary | System-wide | Python package |
| Cross-platform | ✅ | ✅ | ✅ |

## Troubleshooting

### uv command not found

**Solution**: Restart your terminal after installation, or add uv to PATH manually.

**Windows**: Check that `%USERPROFILE%\.cargo\bin` is in PATH
**Linux/macOS**: Check that `~/.cargo/bin` is in PATH

### Virtual environment activation issues

**Windows PowerShell**: You may need to enable script execution:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Package installation fails

**Solution**: Make sure you're in the project directory and the virtual environment is activated:
```bash
# Check current directory
pwd

# Check if venv is activated (should see (.venv) in prompt)
which python  # Linux/macOS
where python  # Windows
```

## Additional Resources

- **uv Documentation**: https://github.com/astral-sh/uv
- **uv Installation Guide**: https://astral.sh/uv
- **Python Packaging Guide**: https://packaging.python.org/

## Quick Reference Card

```bash
# Environment
uv venv                           # Create virtual environment
source .venv/bin/activate         # Activate (Linux/macOS)
.venv\Scripts\activate            # Activate (Windows)

# Installation
uv pip install -e ".[dev]"        # Install project with dev deps
uv pip install -r requirements.txt # Install from requirements
uv pip install package-name       # Install single package

# Package Management
uv pip list                       # List installed packages
uv pip show package-name          # Show package info
uv pip uninstall package-name     # Uninstall package
uv pip freeze > requirements.txt  # Export requirements

# YaFT Commands
python -m yaft.cli --help         # Show help
python -m yaft.cli list-plugins   # List plugins
python -m yaft.cli run Plugin --zip file.zip  # Analyze ZIP
pytest                            # Run tests
ruff format .                     # Format code
ruff check .                      # Lint code
```

---

**Happy forensic analysis with YaFT! 🔍**
