# YAFT Scripts

This directory contains utility scripts for YAFT development and maintenance.

## Scripts

### create_plugin.py

Helper script to create a new plugin from a template.

**Usage:**

```bash
# Interactive mode (prompts for details)
python scripts/create_plugin.py

# Non-interactive mode with arguments
python scripts/create_plugin.py --name MyPlugin --author "Your Name" --description "My plugin description"

# Specify output directory
python scripts/create_plugin.py --name MyPlugin --output-dir custom_plugins/
```

**Arguments:**

| Argument | Description | Default |
|----------|-------------|---------|
| `--name` | Plugin name (e.g., 'MyPlugin' or 'My Plugin') | Prompted |
| `--description` | Plugin description | `A plugin for {name}` |
| `--author` | Plugin author name | `Unknown` |
| `--output-dir` | Output directory | `plugins/` |
| `--no-interactive` | Non-interactive mode (use provided arguments only) | False |

**Output:**

Creates a new Python file in the plugins directory with:
- Plugin class inheriting from `PluginBase`
- Properly formatted metadata
- Template methods (`initialize`, `execute`, `cleanup`)
- Example code comments

---

### generate_manifest.py

Generates `plugins_manifest.json` from the plugins directory. This manifest is used by the plugin update system to track available plugins, versions, and checksums.

**Usage:**

```bash
python scripts/generate_manifest.py
```

**What it does:**

1. Scans the `plugins/` directory for Python files
2. Extracts metadata from each plugin (name, version, description, target OS)
3. Calculates SHA256 hash for integrity verification
4. Generates `plugins_manifest.json` in the repository root

**Manifest Format:**

```json
{
  "manifest_version": "1.0.0",
  "last_updated": "2025-01-17T10:00:00+00:00",
  "repository": "RedRockerSE/yaft2",
  "branch": "main",
  "plugins": [
    {
      "name": "iOSDeviceInfoExtractorPlugin",
      "filename": "ios_device_info_extractor.py",
      "version": "1.1.0",
      "description": "Extract comprehensive device metadata from iOS filesystem extractions",
      "sha256": "abc123...",
      "size": 20940,
      "required": true,
      "os_target": ["ios"],
      "dependencies": []
    }
  ]
}
```

**Automatic Updates:**

The manifest is automatically regenerated via GitHub Actions when plugins are modified on the main branch. See `.github/workflows/update-manifest.yml`.

---

## Development Workflow

### Creating a New Plugin

1. Run the plugin generator:
   ```bash
   python scripts/create_plugin.py --name iOSMyFeatureExtractor
   ```

2. Edit the generated file in `plugins/`

3. Implement the `execute()` method with your logic

4. Test the plugin:
   ```bash
   python -m yaft.cli run iOSMyFeatureExtractorPlugin --zip evidence.zip
   ```

5. Regenerate the manifest:
   ```bash
   python scripts/generate_manifest.py
   ```

### Updating the Manifest

After modifying any plugin files, regenerate the manifest to update version numbers and checksums:

```bash
python scripts/generate_manifest.py
```

This ensures the plugin update system can correctly identify changes and verify downloaded plugins.
