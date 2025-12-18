# VS Code IntelliSense Setup for Plugin Developers

This guide explains how to enable VS Code IntelliSense, autocomplete, and type checking for plugin developers working against a YAFT PyInstaller executable rather than the source code.

## Table of Contents

1. [Overview](#overview)
2. [Recommended Approach](#recommended-approach)
3. [Implementation Guide](#implementation-guide)
4. [Alternative Approaches](#alternative-approaches)
5. [Testing the Setup](#testing-the-setup)
6. [Troubleshooting](#troubleshooting)
7. [References](#references)

---

## Overview

### The Challenge

Plugin developers receive:
- `yaft-windows-x64.exe` (PyInstaller executable)
- `plugins/` directory for their custom plugins

They need IntelliSense for:
```python
from yaft.core.api import CoreAPI
from yaft.core.plugin_base import PluginBase, PluginMetadata
```

However, the actual Python source code is bundled inside the PyInstaller executable and not directly accessible to VS Code's Python language server (Pylance).

### Solution Approaches Evaluated

| Approach | Pros | Cons | Recommended |
|----------|------|------|-------------|
| **1. Type Stub Files (.pyi)** | Clean, small footprint, standard Python practice | Requires generation, maintenance | ✅ **YES** |
| **2. Include Source Files** | Full source available, no stub generation | Larger distribution, potential IP concerns | ❌ No |
| **3. Stub-only Package** | Easy pip install, version control | Requires PyPI setup, extra dependency | ⚠️ Optional |
| **4. No Setup (docs only)** | Simple, no extra files | Poor developer experience | ❌ No |

---

## Recommended Approach

**Use Type Stub Files (.pyi) with VS Code Configuration**

This approach provides:
- ✅ Professional developer experience with full IntelliSense
- ✅ Small distribution footprint (stubs are ~10% of source size)
- ✅ No exposure of full implementation details
- ✅ Standard Python type hinting practice
- ✅ Works offline without internet connectivity
- ✅ Compatible with all Python IDEs (VS Code, PyCharm, etc.)

---

## Implementation Guide

### Step 1: Generate Type Stub Files

Type stub files (.pyi) are interface definitions that provide type hints without implementation code.

**Prerequisites:**
```bash
# Install mypy (includes stubgen tool)
pip install mypy
```

**Generate stubs for YAFT core modules:**

```bash
# Navigate to project root
cd C:\Users\Forensic\Desktop\dev\yaft

# Generate stubs for core modules
stubgen -p yaft.core -o dist\yaft\yaft-stubs

# This creates:
# dist/yaft/yaft-stubs/yaft/core/api.pyi
# dist/yaft/yaft-stubs/yaft/core/plugin_base.pyi
# dist/yaft/yaft-stubs/yaft/core/plugin_manager.pyi
# dist/yaft/yaft-stubs/yaft/core/__init__.pyi
```

**Alternative - Manual stub generation (for specific modules):**

```bash
# Generate stubs for specific files
stubgen src/yaft/core/api.py -o dist/yaft/yaft-stubs
stubgen src/yaft/core/plugin_base.py -o dist/yaft/yaft-stubs
```

### Step 2: Organize Stub Files

**Recommended Distribution Structure:**

```
yaft-windows-x64/
├── yaft.exe                          # PyInstaller executable
├── plugins/                          # User plugins directory
│   ├── README.md                     # Plugin development guide
│   ├── hello_world.py                # Example plugin
│   └── my_custom_plugin.py           # User's plugin
├── yaft-stubs/                       # Type stubs for IntelliSense
│   └── yaft/
│       ├── __init__.pyi
│       └── core/
│           ├── __init__.pyi
│           ├── api.pyi               # CoreAPI type hints
│           ├── plugin_base.pyi       # PluginBase type hints
│           └── plugin_manager.pyi
├── .vscode/                          # VS Code configuration (optional)
│   └── settings.json
├── pyrightconfig.json                # Pylance/Pyright configuration
└── PLUGIN_DEVELOPMENT.md             # Setup instructions
```

### Step 3: Create Pylance Configuration

**Create `pyrightconfig.json` in distribution root:**

```json
{
  "$schema": "https://raw.githubusercontent.com/microsoft/pyright/main/packages/pyright/schemas/pyrightconfig.schema.json",
  "include": [
    "plugins"
  ],
  "stubPath": "yaft-stubs",
  "typeCheckingMode": "basic",
  "reportMissingImports": true,
  "reportMissingTypeStubs": false,
  "pythonVersion": "3.12",
  "pythonPlatform": "Windows"
}
```

**Explanation:**
- `include`: Only analyze plugin files
- `stubPath`: Location of type stub files (relative to config file)
- `typeCheckingMode`: "basic" provides helpful hints without being overly strict
- `reportMissingTypeStubs`: Disabled to avoid warnings for third-party packages

### Step 4: Create VS Code Settings (Optional)

**Create `.vscode/settings.json` in distribution root:**

```json
{
  "python.analysis.typeCheckingMode": "basic",
  "python.analysis.stubPath": "yaft-stubs",
  "python.analysis.autoSearchPaths": true,
  "python.analysis.diagnosticMode": "workspace",
  "python.analysis.extraPaths": [
    "${workspaceFolder}/yaft-stubs"
  ],
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true,
    "yaft.exe": true
  }
}
```

**Note:** VS Code automatically discovers `pyrightconfig.json`, so this file is optional but provides additional workspace-specific settings.

### Step 5: Automate Stub Generation in Build Script

**Update `build_exe.py` to automatically generate stubs:**

```python
def generate_type_stubs(dist_dir: Path) -> None:
    """Generate type stub files for plugin development."""
    import subprocess
    import sys

    print("Generating type stub files for plugin development...")

    stubs_dir = dist_dir / "yaft" / "yaft-stubs"
    stubs_dir.mkdir(parents=True, exist_ok=True)

    # Generate stubs for yaft.core package
    cmd = [
        sys.executable,
        "-m",
        "stubgen",
        "-p", "yaft.core",
        "-o", str(stubs_dir),
        "--include-private",
    ]

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        print(f"Type stubs generated at: {stubs_dir}")
    except subprocess.CalledProcessError as e:
        print(f"Warning: Stub generation failed: {e}")
        print(e.stdout)
        print(e.stderr)
    except FileNotFoundError:
        print("Warning: stubgen not found. Install mypy: pip install mypy")


def create_pylance_config(dist_dir: Path) -> None:
    """Create Pylance configuration for plugin development."""
    config_content = """{
  "$schema": "https://raw.githubusercontent.com/microsoft/pyright/main/packages/pyright/schemas/pyrightconfig.schema.json",
  "include": [
    "plugins"
  ],
  "stubPath": "yaft-stubs",
  "typeCheckingMode": "basic",
  "reportMissingImports": true,
  "reportMissingTypeStubs": false,
  "pythonVersion": "3.12",
  "pythonPlatform": "Windows"
}
"""
    config_file = dist_dir / "yaft" / "pyrightconfig.json"
    config_file.write_text(config_content, encoding="utf-8")
    print(f"Created Pylance config at: {config_file}")


def create_vscode_settings(dist_dir: Path) -> None:
    """Create VS Code workspace settings for plugin development."""
    vscode_dir = dist_dir / "yaft" / ".vscode"
    vscode_dir.mkdir(parents=True, exist_ok=True)

    settings_content = """{
  "python.analysis.typeCheckingMode": "basic",
  "python.analysis.stubPath": "yaft-stubs",
  "python.analysis.autoSearchPaths": true,
  "python.analysis.diagnosticMode": "workspace",
  "python.analysis.extraPaths": [
    "${workspaceFolder}/yaft-stubs"
  ],
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true,
    "yaft.exe": true
  }
}
"""
    settings_file = vscode_dir / "settings.json"
    settings_file.write_text(settings_content, encoding="utf-8")
    print(f"Created VS Code settings at: {settings_file}")


# Add to main() function after successful build:
if success:
    # ... existing code ...

    # Generate development support files
    generate_type_stubs(dist_dir)
    create_pylance_config(dist_dir)
    create_vscode_settings(dist_dir)
    create_plugin_readme(dist_dir)  # existing function
```

---

## Alternative Approaches

### Approach 2: Include Source Files

**When to use:** If you want to provide full source code access for learning purposes.

**Pros:**
- Plugin developers can read implementation code
- No stub generation needed
- Easier to debug plugin issues

**Cons:**
- Larger distribution size
- Exposes implementation details
- Potential IP concerns
- May confuse developers about which files to modify

### Approach 3: Stub-only Package

**When to use:** If you want to distribute stubs via PyPI for easier installation.

**Pros:**
- Standard Python packaging
- Easy version management
- Automatic updates via pip

**Cons:**
- Requires PyPI account and maintenance
- Network dependency
- May create confusion about runtime vs. development dependencies

---

## Testing the Setup

### Manual Testing Checklist

**Open VS Code and verify:**

1. **Import Resolution**
   - [ ] No red squiggles under `from yaft.core.api import CoreAPI`
   - [ ] No red squiggles under `from yaft.core.plugin_base import PluginBase`

2. **Autocomplete**
   - [ ] Type `self.core_api.` and autocomplete menu appears
   - [ ] Autocomplete shows method names (e.g., `log_info`, `print_success`)
   - [ ] Autocomplete shows method signatures

3. **Hover Information**
   - [ ] Hover over `CoreAPI` shows class documentation
   - [ ] Hover over `core_api.log_info` shows method signature and docstring

4. **Go to Definition (F12)**
   - [ ] F12 on `CoreAPI` navigates to `api.pyi`
   - [ ] F12 on `PluginBase` navigates to `plugin_base.pyi`

5. **Type Checking**
   - [ ] Incorrect method calls show type errors
   - [ ] Missing required parameters show warnings

---

## Troubleshooting

### Issue: No Autocomplete Appearing

**Solutions:**

1. **Reload VS Code:**
   - Press `Ctrl+Shift+P`
   - Type "Developer: Reload Window"
   - Press Enter

2. **Check Pylance extension is active:**
   - Open Command Palette (`Ctrl+Shift+P`)
   - Type "Python: Select Interpreter"
   - Verify Python interpreter is selected

3. **Verify pyrightconfig.json exists:**
```bash
# Check file exists
ls pyrightconfig.json
```

### Issue: Import Errors (Red Squiggles)

**Solutions:**

1. **Check stub directory structure:**
```
yaft-stubs/
└── yaft/
    ├── __init__.pyi
    └── core/
        ├── __init__.pyi
        └── api.pyi
```

2. **Ensure `__init__.pyi` files exist:**
```bash
# Create if missing
touch yaft-stubs/yaft/__init__.pyi
touch yaft-stubs/yaft/core/__init__.pyi
```

---

## Technical Details

### How Type Stubs Work

Type stub files (`.pyi`) are Python's standard way to provide type information without implementation:

**Source file (api.py):**
```python
class CoreAPI:
    def log_info(self, message: str) -> None:
        """Log an informational message."""
        self._logger.info(message)
        # ... implementation code ...
```

**Stub file (api.pyi):**
```python
class CoreAPI:
    def log_info(self, message: str) -> None:
        """Log an informational message."""
        ...
```

The stub file:
- Contains **only signatures** (no implementation)
- Includes **type annotations** for parameters and return values
- Preserves **docstrings** for documentation
- Uses **`...`** (ellipsis) for method bodies

### Why Stubs Work with PyInstaller

When PyInstaller creates an executable:
1. Python source files are compiled to bytecode
2. Bytecode is bundled into the executable
3. Original `.py` files are **not included**
4. VS Code **cannot access** bundled code

Type stubs solve this by:
1. Providing type information in **separate files**
2. Living **outside the executable** where VS Code can read them
3. Following standard Python typing conventions
4. Being discovered by Pylance via `stubPath` configuration

---

## References

### Official Documentation

- [Mypy Stub Files](https://mypy.readthedocs.io/en/stable/stubs.html) - Official stub file documentation
- [Mypy stubgen Tool](https://mypy.readthedocs.io/en/stable/stubgen.html) - Automatic stub generation guide
- [Pyright Configuration](https://github.com/microsoft/pyright/blob/main/docs/configuration.md) - Complete pyrightconfig.json reference
- [VS Code Python Editing](https://code.visualstudio.com/docs/python/editing) - VS Code Python features guide

### Related GitHub Issues

- [Pylance extraPaths Issues (2025)](https://github.com/microsoft/pylance-release/issues/7301) - Recent extraPaths configuration challenges
- [VSCode .pyi Files Support](https://github.com/microsoft/python-language-server/issues/1866) - Discussion on stub file support

### Community Resources

- [Micropython Stubs Documentation](https://micropython-stubs.readthedocs.io/en/main/22_vscode.html) - Example of stub files for embedded Python
- [Pylance Settings Override](https://github.com/microsoft/pylance-release/wiki/Settings.json-overridden-by-Pyrightconfig.json-or-Pyproject.toml) - Understanding settings precedence

---

## Best Practices

### For YAFT Maintainers

1. **Automate stub generation in build process**
   - Include stub generation in `build_exe.py`
   - Test stubs before distribution
   - Version stubs alongside executable

2. **Keep stubs synchronized with API changes**
   - Regenerate stubs after modifying CoreAPI
   - Test that new methods appear in IntelliSense
   - Document breaking changes

3. **Include example workspace**
   - Distribute with working `pyrightconfig.json`
   - Include `.vscode/settings.json` template
   - Provide test plugin demonstrating IntelliSense

### For Plugin Developers

1. **Always open workspace folder**
   - Open the `yaft-windows-x64/` folder, not individual files
   - This ensures VS Code finds `pyrightconfig.json`

2. **Verify IntelliSense before development**
   - Test autocomplete works
   - Test with example plugin first

3. **Use type hints in your plugins**
   - Add type annotations to function parameters
   - Use return type hints
   - This improves IntelliSense for your own code

---

## FAQ

### Q: Do I need to install the yaft package via pip?

**A:** No! The type stubs provide IntelliSense without requiring the actual package to be installed. The executable contains all runtime code.

### Q: Can I run plugins from VS Code?

**A:** No, plugins must be run using the `yaft.exe` executable. VS Code provides development support (IntelliSense, type checking) only.

### Q: What if I see import errors in VS Code?

**A:** This is expected. The import may show as unresolved in the editor, but IntelliSense will still work and plugins will run correctly with the executable.

### Q: Can I use other IDEs besides VS Code?

**A:** Yes! Type stubs work with any Python IDE that supports `.pyi` files (PyCharm, Sublime Text, Vim/Neovim with LSP, etc.)

---

## Conclusion

Using type stub files provides the best developer experience for YAFT plugin developers:

✅ **Professional IntelliSense** - Full autocomplete and type checking
✅ **Small Footprint** - Minimal distribution size
✅ **Standard Practice** - Follows Python typing conventions
✅ **Easy Maintenance** - Automated stub generation
✅ **IDE Agnostic** - Works with all major Python IDEs

---

**Last Updated:** December 2025
**YAFT Version:** 0.5.0+
**Tested With:** VS Code 1.95+, Python 3.12+, Pylance 2024.12+
