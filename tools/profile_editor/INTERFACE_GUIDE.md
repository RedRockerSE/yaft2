# Plugin Profile Editor - Interface Guide

Visual guide to understanding and using the Plugin Profile Editor interface.

## Main Window Layout

```
╔═══════════════════════════════════════════════════════════════════════════╗
║  YAFT Plugin Profile Editor                                               ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                           ║
║  ┌─ Profile Information ─────────────────────────────────────────────┐   ║
║  │                                                                    │   ║
║  │  Profile Name:  [iOS Full Forensic Analysis                    ]  │   ║
║  │  Description:   [Complete iOS device extraction and analysis   ]  │   ║
║  │                                                                    │   ║
║  └────────────────────────────────────────────────────────────────────┘   ║
║                                                                           ║
║  ┌─ Available Plugins ────────────────────────────────────────────────┐  ║
║  │                                                                     │  ║
║  │  Plugin Class Name              │ File              │ Description  │  ║
║  │  ───────────────────────────────┼───────────────────┼──────────────│  ║
║  │  AndroidAppInfoExtractorPlugin  │ android_app_in... │ Extract...   │  ║
║  │  AndroidAppPermissionsExtrac... │ android_app_pe... │ Analyze...   │  ║
║  │  AndroidCallLogAnalyzerPlugin   │ android_call_l... │ Analyze...   │  ║
║  │  AndroidDeviceInfoExtractorP... │ android_device... │ Extract...   │  ║
║  │  iOSCallLogAnalyzerPlugin       │ ios_call_log_a... │ Analyze...   │  ║
║  │  iOSDeviceInfoExtractorPlugin   │ ios_device_inf... │ Extract...   │  ║
║  │  HelloWorldPlugin               │ hello_world.py    │ Simple...    │  ║
║  │  FileProcessorPlugin            │ file_processo...  │ File...      │  ║
║  │                                                                     │  ║
║  └────────────────────────────────────────────────────────────────────┘  ║
║                                                                           ║
║  [Add Selected →]  [Add All →]  [Refresh Plugin List]                    ║
║                                                                           ║
║  ┌─ Selected Plugins (Execution Order) ──────────────────────────────┐   ║
║  │                                                                    │   ║
║  │  1. iOSDeviceInfoExtractorPlugin                                  │   ║
║  │  2. iOSCallLogAnalyzerPlugin                                      │   ║
║  │                                                                    │   ║
║  └────────────────────────────────────────────────────────────────────┘   ║
║                                                                           ║
║  [Move Up]  [Move Down]  [Remove]  [Clear All]                           ║
║                                                                           ║
║  ────────────────────────────────────────────────────────────────────────║
║                                                                           ║
║  [New Profile] [Load Profile...] [Save Profile] [Save As...] [Exit]      ║
║                                                                           ║
║  ────────────────────────────────────────────────────────────────────────║
║  Status: Profile saved: ios_full_analysis.toml                            ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

## Section-by-Section Guide

### 1. Profile Information Section

```
┌─ Profile Information ──────────────────────────────────────┐
│                                                             │
│  Profile Name:  [iOS Full Forensic Analysis             ]  │
│  Description:   [Complete iOS device extraction          ]  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Purpose**: Define basic profile metadata

**Fields:**
- **Profile Name** (Required): Short, descriptive name for the profile
  - Examples: "iOS Full Analysis", "Android Quick Triage"
  - Used in TOML file and displayed in YAFT

- **Description** (Optional): Longer explanation of what the profile does
  - Examples: "Complete iOS device extraction and analysis"
  - Helps other users understand the profile's purpose

**Tips:**
✓ Use clear, descriptive names
✓ Keep names concise (under 50 characters)
✓ Describe the purpose in the description field

### 2. Available Plugins Section

```
┌─ Available Plugins ─────────────────────────────────────────┐
│                                                              │
│  Plugin Class Name              │ File        │ Description │
│  ───────────────────────────────┼─────────────┼─────────────│
│  iOSDeviceInfoExtractorPlugin   │ ios_dev...  │ Extract...  │ ← Click to select
│  iOSCallLogAnalyzerPlugin       │ ios_cal...  │ Analyze...  │
│  AndroidDeviceInfoExtractorP... │ android...  │ Extract...  │
│                                                              │
└──────────────────────────────────────────────────────────────┘

[Add Selected →]  [Add All →]  [Refresh Plugin List]
```

**Purpose**: Browse and select plugins from the plugins directory

**Columns:**
- **Plugin Class Name**: Exact class name used in code (this is what gets saved)
- **File**: Python file containing the plugin
- **Description**: Brief description of what the plugin does

**Selection Methods:**
- **Single Click**: Select one plugin
- **Ctrl+Click**: Select multiple plugins individually
- **Shift+Click**: Select a range of plugins
- **Double-Click**: No special action (use buttons to add)

**Buttons:**
- **Add Selected →**: Add selected plugins to your profile
- **Add All →**: Add all visible plugins to your profile
- **Refresh Plugin List**: Rescan plugins directory for new plugins

**Tips:**
✓ Read descriptions to understand what each plugin does
✓ Select multiple plugins at once using Ctrl+Click
✓ Use "Add All" for comprehensive analysis profiles

### 3. Selected Plugins Section

```
┌─ Selected Plugins (Execution Order) ───────────────────────┐
│                                                             │
│  1. iOSDeviceInfoExtractorPlugin         ← First to run    │
│  2. iOSCallLogAnalyzerPlugin             ← Second to run   │
│  3. AndroidDeviceInfoExtractorPlugin     ← Third to run    │
│                                                             │
└─────────────────────────────────────────────────────────────┘

[Move Up]  [Move Down]  [Remove]  [Clear All]
```

**Purpose**: Shows plugins that will be included in the profile and their execution order

**Important**: Order matters! Plugins execute from top to bottom.

**Workflow:**
1. Select a plugin by clicking on it
2. Use buttons to manage:
   - **Move Up**: Move selected plugin higher in list (runs earlier)
   - **Move Down**: Move selected plugin lower in list (runs later)
   - **Remove**: Delete selected plugin from profile
   - **Clear All**: Remove all plugins (start over)

**Order Best Practices:**
1. **Device Info Extractors** - Usually first (gather basic information)
2. **Data Extractors** - Extract files and databases
3. **Analyzers** - Analyze extracted data
4. **Report Generators** - Create final reports

**Example Good Order:**
```
1. iOSDeviceInfoExtractorPlugin    (Get device info first)
2. iOSCallLogAnalyzerPlugin        (Analyze call logs)
3. iOSAppPermissionsExtractorPlugin (Check app permissions)
```

### 4. Action Buttons Section

```
[New Profile] [Load Profile...] [Save Profile] [Save As...] [Exit]
```

**Buttons Explained:**

| Button | Action | When to Use |
|--------|--------|-------------|
| **New Profile** | Clear everything and start fresh | Beginning a new profile from scratch |
| **Load Profile...** | Open existing .toml file | Editing an existing profile |
| **Save Profile** | Save to current file | Quick save after making changes |
| **Save As...** | Save with new filename | Creating a variant or saving first time |
| **Exit** | Close the application | When finished working |

**Keyboard Shortcuts** (if available):
- Ctrl+N: New Profile
- Ctrl+O: Load Profile
- Ctrl+S: Save Profile
- Ctrl+Q: Exit

### 5. Status Bar

```
Status: Profile saved: ios_full_analysis.toml
```

**Purpose**: Displays current application status and feedback

**Common Messages:**
- `Ready` - Application is idle, waiting for input
- `Loaded 8 plugins from ...` - Plugin discovery complete
- `Added 2 plugin(s)` - Plugins added to profile
- `Profile saved: filename.toml` - Save successful
- `Loaded profile: filename.toml` - Load successful

## Common Workflows

### Workflow 1: Create New iOS Analysis Profile

```
1. Click "New Profile"
   ↓
2. Enter "iOS Full Analysis" in Profile Name
   ↓
3. In Available Plugins, Ctrl+Click:
   - iOSDeviceInfoExtractorPlugin
   - iOSCallLogAnalyzerPlugin
   ↓
4. Click "Add Selected →"
   ↓
5. Verify order in Selected Plugins
   ↓
6. Click "Save As..."
   ↓
7. Navigate to profiles/ directory
   ↓
8. Enter filename: ios_full_analysis.toml
   ↓
9. Click "Save"
```

### Workflow 2: Edit Existing Profile

```
1. Click "Load Profile..."
   ↓
2. Select profile from profiles/ directory
   ↓
3. Make changes:
   - Add/remove plugins
   - Reorder plugins
   - Update name/description
   ↓
4. Click "Save Profile" (or "Save As..." for new file)
```

### Workflow 3: Reorder Plugins

```
1. In Selected Plugins, click plugin to move
   ↓
2. Click "Move Up" or "Move Down"
   ↓
3. Repeat until desired order
   ↓
4. Click "Save Profile"
```

## Visual Indicators

### Selected Plugin Highlighting

```
Available Plugins:
┌──────────────────────────────────┐
│  iOSDeviceInfoExtractorPlugin    │ ← Normal
│  █ iOSCallLogAnalyzerPlugin █    │ ← Selected (highlighted)
│  AndroidDeviceInfoExtractor...   │ ← Normal
└──────────────────────────────────┘
```

### Selected Plugins List Item

```
Selected Plugins:
┌──────────────────────────────────┐
│  1. iOSDeviceInfoExtractorPlugin │ ← Normal
│  █ 2. iOSCallLogAnalyzerPlugin █ │ ← Selected (can move/remove)
└──────────────────────────────────┘
```

## Color Coding (if implemented)

- **Blue**: Active/selected items
- **Green**: Success messages in status bar
- **Red**: Error messages in status bar
- **Yellow**: Warning messages in dialogs

## Error States

### Missing Profile Name

```
┌─────────────────────────────────┐
│  ⚠ Warning                      │
├─────────────────────────────────┤
│  Please enter a profile name.   │
│                                 │
│          [OK]                   │
└─────────────────────────────────┘
```

### No Plugins Selected

```
┌─────────────────────────────────┐
│  ⚠ Warning                      │
├─────────────────────────────────┤
│  Please select at least one     │
│  plugin.                        │
│                                 │
│          [OK]                   │
└─────────────────────────────────┘
```

### Invalid Profile File

```
┌─────────────────────────────────┐
│  ✗ Error                        │
├─────────────────────────────────┤
│  Invalid Profile                │
│  Profile file must contain a    │
│  [profile] section.             │
│                                 │
│          [OK]                   │
└─────────────────────────────────┘
```

## Tips for Efficient Use

1. **Use keyboard shortcuts** for faster navigation
2. **Ctrl+Click multiple plugins** before clicking "Add Selected"
3. **Name profiles descriptively** for easy identification
4. **Test profiles** with sample data before production use
5. **Keep backups** of important profiles
6. **Document complex profiles** using the description field

## Getting Help

- Click `?` or `Help` menu (if implemented) for in-app help
- Read [README.md](README.md) for detailed documentation
- Check [QUICKSTART.md](QUICKSTART.md) for quick examples
- Refer to main [YAFT documentation](../../README.md)

## Interface Customization

The interface uses the system theme and can adapt to:
- **Light Mode**: Clean, bright appearance
- **Dark Mode**: Easy on the eyes (if system supports)
- **High DPI**: Scales properly on high-resolution displays
- **Accessibility**: Keyboard navigation fully supported
