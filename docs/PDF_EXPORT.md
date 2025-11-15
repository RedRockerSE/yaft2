# PDF Export Feature

YaFT supports **optional** PDF export of markdown reports with professional formatting.

## Installation

PDF export requires additional Python packages and system libraries. This feature is **completely optional** - YaFT works perfectly fine without it if you only need markdown reports.

### Quick Install

```bash
# Install with pip/uv (recommended)
uv pip install -e ".[pdf]"

# Or install from requirements file
uv pip install -r requirements-pdf.txt
```

### System Requirements

#### Windows

WeasyPrint requires GTK3 runtime libraries on Windows:

1. **Download GTK3 Runtime**: https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases
2. **Run Installer**: Download and run `gtk3-runtime-x.x.x-x64-en.exe`
3. **Add to PATH**: Add `C:\Program Files\GTK3-Runtime Win64\bin` to your system PATH
4. **Restart Terminal**: Close and reopen your terminal/command prompt
5. **Install Python Packages**: Run `uv pip install -e ".[pdf]"`

**Troubleshooting Windows:**
- If you get "cannot load library 'libgobject-2.0-0'" errors, GTK is not in your PATH
- Verify installation: `where gobject-2.0-0.dll` should return the DLL path
- Make sure to restart your terminal after modifying PATH

#### Linux (Debian/Ubuntu)

```bash
# Install system libraries
sudo apt-get update
sudo apt-get install libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev

# Install Python packages
uv pip install -e ".[pdf]"
```

#### macOS

```bash
# Install system libraries (requires Homebrew)
brew install pango gdk-pixbuf libffi

# Install Python packages
uv pip install -e ".[pdf]"
```

## Usage

### CLI

```bash
# Enable PDF export for any plugin
python -m yaft.cli run iOSDeviceInfoExtractorPlugin --zip evidence.zip --pdf

# Use with profiles
python -m yaft.cli run --zip evidence.zip --profile profiles/ios_full_analysis.toml --pdf
```

### Programmatic

```python
from yaft.core.api import CoreAPI

core_api = CoreAPI()

# Enable automatic PDF generation
core_api.enable_pdf_export(True)

# Generate report (PDF created automatically alongside markdown)
report_path = core_api.generate_report(
    plugin_name="MyPlugin",
    title="Analysis Report",
    sections=sections,
)

# Manual conversion of existing markdown
pdf_path = core_api.convert_markdown_to_pdf(Path("report.md"))

# Batch export all reports from session
pdf_paths = core_api.export_all_reports_to_pdf()
```

## Features

- **Professional Styling**: Blue color scheme, proper typography, A4 format
- **Full Markdown Support**: Tables, code blocks, lists, headings, emphasis
- **Automatic Generation**: PDFs created alongside markdown when enabled
- **Batch Conversion**: Convert all reports with one method call
- **Graceful Fallback**: Works without PDF packages (warnings instead of errors)

## Testing

Tests automatically skip PDF functionality if the required packages aren't installed:

```bash
# Run all tests (PDF tests will skip if packages not available)
pytest

# Run only PDF tests
pytest -k pdf
```

## Troubleshooting

### Import Errors

If you see `ModuleNotFoundError: No module named 'markdown'` or `weasyprint`:
```bash
uv pip install -e ".[pdf]"
```

### System Library Errors

**Windows**: "cannot load library 'libgobject-2.0-0'"
- Solution: Install GTK3 Runtime and add to PATH (see Windows installation above)

**Linux**: "cannot open shared object file: No such file or directory"
- Solution: Install system libraries with apt-get (see Linux installation above)

**macOS**: "library not loaded"
- Solution: Install libraries with Homebrew (see macOS installation above)

### Build/CI Issues

If running tests in CI/CD without GTK installed, PDF tests will automatically skip:
```
6 skipped - WeasyPrint not available: cannot load library...
```

This is expected and not an error. The tests gracefully skip when system libraries aren't available.

## Why Optional?

PDF export requires system-level libraries (GTK/Pango) that:
- Increase installation complexity
- May not be available in all environments (CI/CD, containers, etc.)
- Are not needed for core forensic analysis functionality

By making it optional, YaFT remains lightweight and easy to deploy while offering PDF export for users who need it.
