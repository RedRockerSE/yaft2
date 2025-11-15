# Plugin Profile Editor - Quick Start Guide

Get started with the YAFT Plugin Profile Editor in 5 minutes!

## Step 1: Install Requirements

```bash
# Make sure you have Python 3.12+
python --version

# Install the toml package (if not already installed)
pip install toml
# or
uv pip install toml
```

## Step 2: Launch the Editor

**Windows:**
```bash
# Double-click or run from command line
tools\profile_editor\launch_editor.bat
```

**Linux/macOS:**
```bash
# Make executable (first time only)
chmod +x tools/profile_editor/launch_editor.sh

# Run
./tools/profile_editor/launch_editor.sh
```

**Or run directly:**
```bash
python tools/profile_editor/profile_editor.py
```

## Step 3: Create Your First Profile

### Example: iOS Forensic Analysis Profile

1. **Click "New Profile"**

2. **Enter Information:**
   - Profile Name: `iOS Full Analysis`
   - Description: `Complete iOS device forensic analysis`

3. **Select Plugins:**
   - In the "Available Plugins" section, find:
     - `iOSDeviceInfoExtractorPlugin`
     - `iOSCallLogAnalyzerPlugin`
   - Select both (Ctrl+Click for multiple)
   - Click **"Add Selected →"**

4. **Verify Order:**
   - Check "Selected Plugins" list shows:
     ```
     1. iOSDeviceInfoExtractorPlugin
     2. iOSCallLogAnalyzerPlugin
     ```
   - Use "Move Up" / "Move Down" if needed

5. **Save Profile:**
   - Click **"Save As..."**
   - Navigate to `profiles/` directory
   - Filename: `ios_full_analysis.toml`
   - Click **"Save"**

Done! Your profile is ready to use.

## Step 4: Use Your Profile with YAFT

```bash
# Run the profile
python -m yaft.cli run --zip evidence.zip --profile profiles/ios_full_analysis.toml

# With PDF export
python -m yaft.cli run --zip evidence.zip --profile profiles/ios_full_analysis.toml --pdf
```

## Common Tasks

### Add All iOS Plugins

1. Click "New Profile"
2. Name: `iOS Complete`
3. In Available Plugins, select all iOS plugins:
   - `iOSDeviceInfoExtractorPlugin`
   - `iOSCallLogAnalyzerPlugin`
4. Click **"Add Selected →"**
5. Save as `profiles/ios_complete.toml`

### Add All Android Plugins

1. Click "New Profile"
2. Name: `Android Full Analysis`
3. Select all Android plugins:
   - `AndroidDeviceInfoExtractorPlugin`
   - `AndroidAppInfoExtractorPlugin`
   - `AndroidAppPermissionsExtractorPlugin`
   - `AndroidCallLogAnalyzerPlugin`
4. Click **"Add Selected →"**
5. Save as `profiles/android_full_analysis.toml`

### Edit Existing Profile

1. Click **"Load Profile..."**
2. Select the `.toml` file
3. Make changes (add/remove/reorder plugins)
4. Click **"Save Profile"** (overwrites)
   - Or **"Save As..."** to create a new version

### Change Plugin Order

1. In "Selected Plugins" list, click a plugin
2. Use **"Move Up"** or **"Move Down"**
3. Repeat until desired order
4. Save profile

## Interface Overview

```
┌────────────────────────────────────────┐
│  Profile Information                   │
│  Name: [iOS Full Analysis          ]   │
│  Desc: [Complete iOS analysis      ]   │
└────────────────────────────────────────┘

┌────────────────────────────────────────┐
│  Available Plugins                     │
│  ┌──────────────────────────────────┐ │
│  │ iOSDeviceInfoExtractorPlugin     │ │ ← Select plugins here
│  │ iOSCallLogAnalyzerPlugin         │ │
│  │ AndroidDeviceInfoExtractorPlugin │ │
│  └──────────────────────────────────┘ │
│  [Add Selected →] [Add All →]         │
└────────────────────────────────────────┘

┌────────────────────────────────────────┐
│  Selected Plugins (Execution Order)    │
│  ┌──────────────────────────────────┐ │
│  │ 1. iOSDeviceInfoExtractorPlugin  │ │ ← Reorder/remove here
│  │ 2. iOSCallLogAnalyzerPlugin      │ │
│  └──────────────────────────────────┘ │
│  [Move Up] [Move Down] [Remove]       │
└────────────────────────────────────────┘

[New] [Load...] [Save] [Save As...] [Exit]
```

## Tips

✅ **Save to profiles/ directory** - Keeps profiles organized
✅ **Use descriptive names** - Makes profiles easy to identify
✅ **Test with sample data** - Verify profiles work before production
✅ **Order matters** - Device info plugins usually go first
✅ **Keep backups** - Save important profiles in version control

## Troubleshooting

**Problem**: "toml module not found"
**Solution**: `pip install toml` or `uv pip install toml`

**Problem**: No plugins showing
**Solution**: Click "Refresh Plugin List" or check `plugins/` directory

**Problem**: Can't save profile
**Solution**: Enter a profile name and select at least one plugin

**Problem**: GUI won't start
**Solution**: Install tkinter (`sudo apt-get install python3-tk` on Linux)

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Explore the [YAFT main documentation](../../README.md)
- Try creating custom profiles for your workflows
- Share profiles with your team

## Example Profiles to Create

1. **iOS Device Only**: Just device info extraction
2. **Android Apps**: App info + permissions analysis
3. **Quick Triage**: Essential plugins for rapid assessment
4. **Full Forensics**: All available plugins for thorough analysis

Happy profiling! 🎯
