# YAFT Plugin Profile Editor

A standalone GUI application for creating and editing YAFT plugin profiles. This tool provides a user-friendly interface for selecting plugins and creating TOML configuration files without manually editing text files.

## Features

- **Visual Plugin Selection**: Browse available plugins with descriptions
- **Drag-and-Drop Ordering**: Reorder plugins to control execution sequence
- **Profile Management**: Create, load, save, and edit profile files
- **Automatic Discovery**: Automatically finds all plugins in the plugins directory
- **Validation**: Ensures profile files are properly formatted
- **No Code Changes**: Standalone tool that doesn't modify YAFT codebase

## Requirements

- Python 3.12+
- tkinter (usually included with Python)
- toml package

### Installation

```bash
# Navigate to YAFT root directory
cd yaft

# Install the toml package
uv pip install toml

# Or with pip
pip install toml
```

**Note**: tkinter is typically included with Python installations. If not available:
- **Linux**: `sudo apt-get install python3-tk`
- **macOS**: Included with Python
- **Windows**: Included with Python

## Usage

### Starting the Application

From the YAFT root directory:

```bash
# Windows
python tools\profile_editor\profile_editor.py

# Linux/macOS
python tools/profile_editor/profile_editor.py
```

Or use the launcher script:

```bash
# Windows
tools\profile_editor\launch_editor.bat

# Linux/macOS
./tools/profile_editor/launch_editor.sh
```

### Creating a New Profile

1. **Click "New Profile"** to start with a blank profile
2. **Enter Profile Information**:
   - **Profile Name**: Descriptive name (e.g., "iOS Full Analysis")
   - **Description**: Optional description of what this profile does
3. **Select Plugins**:
   - Browse available plugins in the treeview
   - Select one or more plugins (Ctrl+Click for multiple)
   - Click "Add Selected →" to add them to your profile
   - Or click "Add All →" to add all available plugins
4. **Reorder Plugins** (if needed):
   - Select a plugin in the "Selected Plugins" list
   - Use "Move Up" or "Move Down" to change execution order
   - Plugins execute in the order shown (top to bottom)
5. **Save Profile**:
   - Click "Save As..." to save with a new filename
   - Choose the `profiles/` directory (recommended)
   - Use a descriptive filename (e.g., `ios_full_analysis.toml`)

### Loading an Existing Profile

1. Click "Load Profile..."
2. Navigate to the `profiles/` directory
3. Select a `.toml` profile file
4. The profile information and selected plugins will load

### Editing a Profile

1. Load the profile you want to edit
2. Make your changes:
   - Modify name or description
   - Add or remove plugins
   - Reorder plugins
3. Click "Save Profile" to update the file

### Saving Profiles

- **Save Profile**: Save to the current file (overwrites)
- **Save As...**: Save with a new filename (creates new file)

Profiles are saved in TOML format compatible with YAFT's `--profile` option.

## Interface Guide

### Main Window Sections

```
┌─────────────────────────────────────────────────────────┐
│  YAFT Plugin Profile Editor                             │
├─────────────────────────────────────────────────────────┤
│  Profile Information                                    │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Name:        [                              ]    │   │
│  │ Description: [                              ]    │   │
│  └─────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────┤
│  Available Plugins                                      │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Plugin Class Name  │ File        │ Description  │   │
│  │ ───────────────────┼─────────────┼──────────────│   │
│  │ iOSDeviceInfo...   │ ios_dev...  │ Extract...   │   │
│  │ AndroidCallLog...  │ android...  │ Analyze...   │   │
│  └─────────────────────────────────────────────────┘   │
│  [Add Selected →] [Add All →] [Refresh]                │
├─────────────────────────────────────────────────────────┤
│  Selected Plugins (Execution Order)                     │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 1. iOSDeviceInfoExtractorPlugin                 │   │
│  │ 2. iOSCallLogAnalyzerPlugin                     │   │
│  └─────────────────────────────────────────────────┘   │
│  [Move Up] [Move Down] [Remove] [Clear All]            │
├─────────────────────────────────────────────────────────┤
│  [New] [Load...] [Save] [Save As...] [Exit]           │
├─────────────────────────────────────────────────────────┤
│  Status: Ready                                          │
└─────────────────────────────────────────────────────────┘
```

### Available Plugins Treeview

- **Plugin Class Name**: The exact class name used in YAFT (use this name in profiles)
- **File**: The Python file containing the plugin
- **Description**: Plugin description extracted from docstring (if available)

**Selection**:
- Single click: Select one plugin
- Ctrl+Click: Select multiple plugins
- Shift+Click: Select range of plugins

### Selected Plugins List

Shows plugins that will be included in the profile. The order matters:
- Plugins execute from top to bottom
- Use "Move Up" / "Move Down" to reorder
- Use "Remove" to delete from profile
- Use "Clear All" to start over

### Action Buttons

- **New Profile**: Clear current profile and start fresh
- **Load Profile...**: Open an existing `.toml` profile
- **Save Profile**: Save to current file (if previously loaded/saved)
- **Save As...**: Save with a new filename
- **Exit**: Close the application

## Example Workflow

### Creating an iOS Analysis Profile

1. Start the application
2. Click "New Profile"
3. Enter:
   - Name: `iOS Full Analysis`
   - Description: `Complete forensic analysis for iOS devices`
4. In Available Plugins, select:
   - `iOSDeviceInfoExtractorPlugin`
   - `iOSCallLogAnalyzerPlugin`
5. Click "Add Selected →"
6. Verify the order in Selected Plugins
7. Click "Save As..."
8. Save as `profiles/ios_full_analysis.toml`

The resulting file:

```toml
[profile]
name = "iOS Full Analysis"
description = "Complete forensic analysis for iOS devices"
plugins = [
    "iOSDeviceInfoExtractorPlugin",
    "iOSCallLogAnalyzerPlugin",
]
```

### Creating an Android Apps Profile

1. Click "New Profile"
2. Enter:
   - Name: `Android Apps Analysis`
   - Description: `Application-focused analysis for Android`
3. Select:
   - `AndroidAppInfoExtractorPlugin`
   - `AndroidAppPermissionsExtractorPlugin`
4. Click "Add Selected →"
5. Save as `profiles/android_apps_analysis.toml`

## Using Created Profiles with YAFT

After creating a profile, use it with the YAFT CLI:

```bash
# Run iOS full analysis
python -m yaft.cli run --zip evidence.zip --profile profiles/ios_full_analysis.toml

# Run Android apps analysis
python -m yaft.cli run --zip android.zip --profile profiles/android_apps_analysis.toml

# With PDF export
python -m yaft.cli run --zip evidence.zip --profile profiles/ios_full_analysis.toml --pdf
```

## Plugin Discovery

The editor automatically discovers plugins by:

1. Scanning the `plugins/` directory for `.py` files
2. Reading each file to find classes inheriting from `PluginBase`
3. Extracting plugin metadata (class name, description, version, author)
4. Displaying plugins in the treeview

**Supported Plugin Files**:
- Any `.py` file in `plugins/` directory
- Must contain a class inheriting from `PluginBase`
- Class name should end with "Plugin" (convention)

**Private Files Excluded**:
- Files starting with underscore (`_`)
- `__init__.py`

## Troubleshooting

### "toml module not found"

Install the toml package:
```bash
uv pip install toml
# or
pip install toml
```

### "No plugins found"

- Ensure you're running from the YAFT root directory
- Check that `plugins/` directory exists and contains `.py` files
- Click "Refresh Plugin List" to reload

### "Invalid Profile" error when loading

- Ensure the profile file is valid TOML format
- Profile must contain a `[profile]` section
- Check that `name` and `plugins` fields are present

### GUI doesn't start (tkinter missing)

Install tkinter:
- **Linux**: `sudo apt-get install python3-tk`
- **macOS**: Usually included with Python
- **Windows**: Usually included with Python

### Plugin descriptions not showing

- Plugin descriptions are extracted from class docstrings
- If missing, the description field will be empty
- This doesn't affect functionality

## File Structure

```
yaft/
├── tools/
│   └── profile_editor/
│       ├── profile_editor.py    # Main GUI application
│       ├── README.md            # This file
│       ├── launch_editor.bat    # Windows launcher
│       └── launch_editor.sh     # Linux/macOS launcher
├── plugins/                     # Source directory for plugins
├── profiles/                    # Output directory for profiles
└── ...
```

## Technical Details

### Profile File Format (TOML)

```toml
[profile]
name = "Profile Name"                # Required: Profile name
description = "Optional description" # Optional: Profile description
plugins = [                          # Required: List of plugin class names
    "PluginClassName1",
    "PluginClassName2",
]
```

### Plugin Class Name Requirements

- Must be the exact class name as defined in the plugin file
- Case-sensitive
- Typically ends with "Plugin" (e.g., `iOSDeviceInfoExtractorPlugin`)
- Not the filename or metadata name

### Plugin Discovery Process

1. Scans `plugins/*.py` files
2. Reads file content to find `class ClassName(PluginBase)`
3. Extracts metadata from:
   - Class docstring (description)
   - `metadata` property (version, author)
4. Falls back to filename-based class name if inspection fails

## Keyboard Shortcuts

- **Ctrl+N**: New Profile
- **Ctrl+O**: Load Profile
- **Ctrl+S**: Save Profile
- **Ctrl+Q**: Exit (on some platforms)

## Tips and Best Practices

1. **Naming Convention**: Use descriptive profile names (e.g., "iOS Full Analysis" not "ios1")

2. **Plugin Order**: Order matters for execution:
   - Put device info extractors first
   - Put dependent plugins after their dependencies
   - Group related plugins together

3. **Save Location**: Always save profiles in the `profiles/` directory for consistency

4. **Filename Convention**: Use lowercase with underscores (e.g., `ios_full_analysis.toml`)

5. **Test Profiles**: Test new profiles with sample data before production use

6. **Backup**: Keep backup copies of important profiles

7. **Documentation**: Use the description field to document what the profile does

## Support

For issues or questions:
- Check this README for common solutions
- Review YAFT main documentation
- Ensure plugins are properly installed in `plugins/` directory

## License

This tool is part of the YAFT project and shares the same license.
