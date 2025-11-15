# YAFT Tools

This directory contains standalone utility tools for YAFT development and usage.

## Available Tools

### Plugin Profile Editor

**Location**: `tools/profile_editor/`

A GUI application for creating and editing YAFT plugin profiles. Provides a visual interface for selecting plugins and creating TOML configuration files.

**Features:**
- Visual plugin selection with descriptions
- Drag-and-drop plugin ordering
- Profile management (create, load, save, edit)
- Automatic plugin discovery
- No code changes required

**Quick Start:**
```bash
# Windows
tools\profile_editor\launch_editor.bat

# Linux/macOS
./tools/profile_editor/launch_editor.sh

# Or run directly
python tools/profile_editor/profile_editor.py
```

**Documentation:**
- [Full README](profile_editor/README.md)
- [Quick Start Guide](profile_editor/QUICKSTART.md)

**Requirements:**
- Python 3.12+
- tkinter (usually included)
- toml package (`pip install toml`)

## Adding New Tools

When creating new standalone tools for YAFT:

1. Create a subdirectory in `tools/` (e.g., `tools/my_tool/`)
2. Add the tool's main script and documentation
3. Create launcher scripts if appropriate
4. Update this README with tool information
5. Ensure the tool is standalone (no modifications to core YAFT code)

## Tool Guidelines

- **Standalone**: Tools should not modify the YAFT codebase
- **Documentation**: Include README.md with usage instructions
- **Dependencies**: Document all requirements clearly
- **Platform Support**: Provide launchers for Windows and Linux/macOS
- **Error Handling**: Include clear error messages and validation

## Support

For tool-specific issues, refer to the tool's individual README file.
For general YAFT questions, see the main [YAFT README](../README.md).
