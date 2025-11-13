# YaFT Plugin Profiles

This directory contains example plugin profile files in TOML format. Plugin profiles allow you to specify a set of plugins to run together, making it easy to perform standard analysis workflows.

## Usage

Run a profile using the `--profile` option:

```bash
yaft run --zip evidence.zip --profile profiles/ios_full_analysis.toml
```

## Available Profiles

### iOS Profiles

- **ios_full_analysis.toml** - Complete iOS forensic analysis
  - Device information extraction
  - App GUID extraction
  - App permissions analysis
  - Call log analysis

- **ios_device_only.toml** - Quick device information extraction
  - Useful for initial device identification

### Android Profiles

- **android_full_analysis.toml** - Complete Android forensic analysis
  - Device information extraction
  - App metadata extraction
  - App permissions analysis
  - Call log analysis

- **android_apps_analysis.toml** - Application-focused analysis
  - App metadata extraction
  - App permissions analysis

## Creating Custom Profiles

Create a new `.toml` file with the following structure:

```toml
[profile]
name = "My Custom Profile"
description = "Description of what this profile does"

plugins = [
    "PluginClassName1",
    "PluginClassName2",
    "PluginClassName3",
]
```

### Profile Fields

- **name** (required): Display name for the profile
- **description** (optional): Description of the profile's purpose
- **plugins** (required): Array of plugin class names to execute (in order)

### Notes

- Plugin names must match the exact class name (e.g., `iOSDeviceInfoExtractorPlugin`, not just `iOSDeviceInfo`)
- Plugins are executed in the order they appear in the list
- All plugins in the profile must be available in the `plugins/` directory
- Invalid plugin names will cause the profile to fail
