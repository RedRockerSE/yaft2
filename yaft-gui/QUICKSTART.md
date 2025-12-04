# YAFT GUI - Quick Start Guide

## Prerequisites

1. **Build YAFT Core Executable First**:
   ```bash
   cd ..  # Navigate to main YAFT directory
   python build_exe.py --clean
   # This creates: dist/yaft/yaft.exe
   ```

2. **Verify YAFT is Working**:
   ```bash
   dist/yaft/yaft.exe --version
   dist/yaft/yaft.exe list-plugins
   ```

## Development Setup

### Install Dependencies

```bash
cd yaft-gui

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.venv\Scripts\activate  # Windows
# or
source .venv/bin/activate  # Linux/macOS

# Install dependencies
pip install -r requirements-dev.txt

# Install package in editable mode
pip install -e .
```

### Run from Source

```bash
# Make sure you're in the yaft-gui directory with activated venv
python src/yaft_gui/main.py
```

The GUI will automatically search for `yaft.exe` in:
- Same directory as the GUI
- Parent directory (`../yaft.exe`)
- Build output directory (`../dist/yaft/yaft.exe`)

### Run Tests

```bash
pytest tests/ -v
```

## Building Standalone Executable

```bash
# Clean build
python build_exe.py --clean

# Output: dist/yaft-gui.exe (Windows) or dist/yaft-gui (Linux)
```

### Build Size

- **Windows**: ~25-30 MB (includes Qt6 runtime)
- **Linux**: ~30-35 MB (includes Qt6 runtime)

## Deployment

For deployment, you need both executables:

```
forensic-tools/
├── yaft.exe              # YAFT core executable
├── yaft-gui.exe          # YAFT GUI executable
└── plugins/              # Plugin directory
    ├── ios_device_info_extractor.py
    ├── android_app_info_extractor.py
    └── ...
```

**Recommended structure:**
```bash
# After building both executables
mkdir forensic-tools
copy ..\dist\yaft\yaft.exe forensic-tools\
copy dist\yaft-gui.exe forensic-tools\
xcopy /E /I ..\plugins forensic-tools\plugins
```

Then distribute the `forensic-tools/` directory to users.

## Testing the GUI with YAFT

1. **Build YAFT Core**:
   ```bash
   cd ..
   python build_exe.py --clean
   ```

2. **Copy YAFT to GUI Directory** (for testing):
   ```bash
   copy dist\yaft\yaft.exe yaft-gui\
   ```

3. **Run GUI from Source**:
   ```bash
   cd yaft-gui
   .venv\Scripts\activate
   python src/yaft_gui/main.py
   ```

4. **The GUI should now**:
   - Detect YAFT executable
   - Show YAFT version
   - Load available plugins
   - Allow you to select a ZIP file
   - Execute analysis with selected plugins

## Troubleshooting

### "YAFT executable not found"

**Solution**: Ensure `yaft.exe` is in one of these locations:
- Same directory as `yaft-gui.exe`
- Parent directory
- `../dist/yaft/yaft.exe`

### "No plugins loaded"

**Solution**:
1. Verify YAFT has plugins: `yaft.exe list-plugins`
2. Ensure `plugins/` directory exists next to `yaft.exe`
3. Click "Refresh Plugins" in GUI

### GUI won't start

**Windows**: Ensure you have Visual C++ Redistributable installed.
**Linux**: Install Qt6 dependencies:
```bash
sudo apt-get install -y \
    libxcb-cursor0 libxcb-icccm4 libxcb-image0 \
    libxcb-keysyms1 libxcb-randr0
```

## Development Workflow

1. **Make changes to GUI code** in `src/yaft_gui/`
2. **Test changes**:
   ```bash
   pytest tests/ -v
   python src/yaft_gui/main.py
   ```
3. **Build executable**:
   ```bash
   python build_exe.py --clean
   ```
4. **Test built executable**:
   - Copy `yaft.exe` to same directory
   - Run `yaft-gui.exe`

## Next Steps

- Read [README.md](README.md) for full documentation
- Check [GitHub Actions](.github/workflows/build-gui.yml) for CI/CD setup
- Review [architecture documentation](README.md#architecture)
