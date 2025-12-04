# YAFT GUI - Graphical User Interface for YAFT Forensic Analysis Tool

A standalone graphical user interface for the [YAFT (Yet Another Forensic Tool)](../README.md) forensic analysis tool. YAFT GUI provides a user-friendly way to execute YAFT plugins without needing command-line experience.

![YAFT GUI Screenshot](docs/screenshot.png)

## Features

- **Visual Plugin Selection**: Browse and select available YAFT plugins with checkboxes
- **File Browser**: Easy selection of forensic extraction ZIP files
- **Export Options**: Toggle HTML and PDF export with simple checkboxes
- **Real-time Output**: View analysis progress and results in real-time with color-coded output
- **Cross-Platform**: Works on Windows and Linux
- **Standalone**: Completely separate from YAFT core - no code changes required
- **Professional UI**: Modern, native-looking interface built with Qt6

## Requirements

### Runtime Requirements
- YAFT executable (`yaft.exe` on Windows, `yaft` on Linux)
- The YAFT GUI executable (pre-built or built from source)

### Development Requirements
- Python 3.12 or higher
- PySide6 (Qt6 for Python)
- PyInstaller (for building executables)

## Installation

### Option 1: Download Pre-built Executable (Recommended)

1. Download the latest release from the [Releases page](https://github.com/RedRockerSE/yaft/releases)
2. Extract the executable to the same directory as your YAFT executable
3. Run `yaft-gui.exe` (Windows) or `yaft-gui` (Linux)

### Option 2: Build from Source

```bash
# Clone the repository
cd yaft-gui

# Install uv (if not installed)
# Windows: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
# Linux/macOS: curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment
uv venv

# Activate virtual environment
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate

# Install dependencies
uv pip install -r requirements-dev.txt

# Run from source
python src/yaft_gui/main.py

# Or build standalone executable
python build_exe.py --clean
```

## Usage

### Basic Workflow

1. **Launch YAFT GUI**
   - Place `yaft-gui.exe` in the same directory as `yaft.exe`
   - Double-click `yaft-gui.exe` to launch

2. **Select ZIP File**
   - Click "Browse..." to select your forensic extraction ZIP file
   - Supports Cellebrite and GrayKey extraction formats

3. **Select Plugins**
   - Check the plugins you want to execute
   - Use "Select All" / "Deselect All" for convenience
   - Plugin descriptions are shown for each option

4. **Configure Export Options**
   - Check "HTML Export" to generate HTML reports (always available)
   - Check "PDF Export" to generate PDF reports (requires WeasyPrint in YAFT)

5. **Execute Analysis**
   - Click "Execute Analysis" to start
   - Watch real-time progress in the output viewer
   - Results are saved to `yaft_output/` directory

6. **Review Results**
   - Output viewer shows color-coded messages (success in green, errors in red)
   - Reports are generated in markdown (and HTML/PDF if enabled)

### Screenshot Tour

#### Main Window
![Main Window](docs/main-window.png)

The main window includes:
- **Header**: YAFT version and application title
- **File Selection**: Browse for ZIP extraction files
- **Plugin List**: Multi-select plugin list with descriptions
- **Export Options**: HTML and PDF export toggles
- **Output Viewer**: Real-time color-coded output
- **Action Buttons**: Execute, Stop, Clear Output, Refresh Plugins

## YAFT Executable Location

YAFT GUI searches for the YAFT executable in the following locations (in order):

1. Same directory as the GUI executable
2. Parent directory
3. `../dist/yaft/` (build output directory)

If YAFT is not found, you'll see a warning message on startup.

**Recommended Setup:**
```
forensic-tools/
├── yaft.exe (or yaft)
├── yaft-gui.exe (or yaft-gui)
└── plugins/
    ├── ios_device_info_extractor.py
    ├── android_app_info_extractor.py
    └── ...
```

## Building Executables

### Windows

```bash
# Install dependencies
uv pip install -r requirements-dev.txt

# Build executable
python build_exe.py --clean

# Output: dist/yaft-gui.exe
```

### Linux

```bash
# Install system dependencies
sudo apt-get install -y \
    libxcb-cursor0 libxcb-icccm4 libxcb-image0 \
    libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 \
    libxcb-shape0 libxcb-xfixes0 libxcb-xinerama0 \
    libxkbcommon-x11-0 libdbus-1-3 libegl1 \
    libfontconfig1 libgl1

# Install dependencies
uv pip install -r requirements-dev.txt

# Build executable
python build_exe.py --clean

# Output: dist/yaft-gui
```

### Build Options

```bash
# Clean build (remove old build artifacts)
python build_exe.py --clean

# The build script automatically:
# - Creates a single-file executable
# - Removes console window (GUI only)
# - Optimizes size (strips debug symbols)
# - Includes all required Qt6 libraries
```

## Continuous Integration

YAFT GUI includes GitHub Actions workflows for automated building:

- **Workflow**: `.github/workflows/build-gui.yml`
- **Triggers**: Push to main, pull requests, manual dispatch
- **Platforms**: Windows and Linux
- **Artifacts**: Executables available for 90 days
- **Releases**: Automatic release creation on tags

## Architecture

### Project Structure

```
yaft-gui/
├── src/
│   └── yaft_gui/
│       ├── __init__.py
│       ├── main.py              # Entry point
│       ├── core/
│       │   ├── __init__.py
│       │   └── yaft_interface.py  # YAFT executable interface
│       ├── ui/
│       │   ├── __init__.py
│       │   ├── main_window.py     # Main application window
│       │   ├── plugin_list.py     # Plugin selection widget
│       │   └── output_viewer.py   # Real-time output display
│       └── utils/
│           └── __init__.py
├── resources/
│   ├── icons/                   # Application icons
│   └── styles/                  # Qt stylesheets
├── tests/                       # Unit tests
├── .github/
│   └── workflows/
│       └── build-gui.yml        # CI/CD workflow
├── build_exe.py                 # PyInstaller build script
├── pyproject.toml               # Project configuration
├── requirements.txt             # Runtime dependencies
├── requirements-dev.txt         # Development dependencies
└── README.md                    # This file
```

### Technology Stack

- **GUI Framework**: PySide6 (Qt6 for Python)
- **Process Management**: QProcess for subprocess execution
- **Build Tool**: PyInstaller
- **Package Manager**: uv (Astral's ultra-fast Python package manager)
- **Python Version**: 3.12+

### Design Principles

1. **Complete Independence**: No modifications to YAFT core code
2. **Subprocess Execution**: Executes YAFT as external process
3. **Dynamic Plugin Discovery**: Queries YAFT for available plugins
4. **Real-time Feedback**: Streams output as it's generated
5. **Professional UX**: Native look and feel with Qt6

## Development

### Running from Source

```bash
# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows

# Run GUI
python src/yaft_gui/main.py
```

### Testing

```bash
# Install test dependencies
uv pip install -r requirements-dev.txt

# Run tests
pytest

# Run with coverage
pytest --cov=src/yaft_gui --cov-report=html
```

### Code Quality

```bash
# Lint code
ruff check src/ tests/

# Format code
ruff format src/ tests/
```

## Troubleshooting

### YAFT Executable Not Found

**Problem**: GUI shows "YAFT executable not found" on startup.

**Solution**:
- Ensure `yaft.exe` is in the same directory as `yaft-gui.exe`
- Or place both executables in your PATH
- Or manually specify the path in the GUI (future feature)

### Plugins Not Loading

**Problem**: No plugins shown in the list.

**Solution**:
- Ensure YAFT has plugins in its `plugins/` directory
- Run `yaft.exe list-plugins` from command line to verify
- Click "Refresh Plugins" button in GUI
- Check YAFT executable permissions

### Process Won't Start

**Problem**: "Execute Analysis" button does nothing or shows errors.

**Solution**:
- Verify ZIP file is selected and valid
- Ensure at least one plugin is selected
- Check YAFT executable has execute permissions
- Review output viewer for error messages

### Linux: Missing Qt Libraries

**Problem**: `error while loading shared libraries: libxcb-cursor.so.0`

**Solution**:
```bash
sudo apt-get install -y \
    libxcb-cursor0 libxcb-icccm4 libxcb-image0 \
    libxcb-keysyms1 libxcb-randr0 libxcb-render-util0
```

## License

MIT License - See [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For issues, questions, or feature requests:
- Open an issue on GitHub
- Check existing issues for solutions
- Review YAFT core documentation

## Changelog

### v1.0.0 (2025-01-XX)
- Initial release
- Windows and Linux support
- Plugin selection with checkboxes
- ZIP file browser
- HTML/PDF export options
- Real-time output viewer
- Automated builds via GitHub Actions

## Acknowledgments

- Built with [PySide6](https://doc.qt.io/qtforpython/) (Qt for Python)
- Packaged with [PyInstaller](https://pyinstaller.org/)
- Part of the [YAFT](../README.md) forensic analysis ecosystem
