"""
Build script for creating standalone executables.

This script uses PyInstaller to create executables for Windows and Linux
that can dynamically load plugins at runtime.
"""

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def get_platform_name() -> str:
    """Get normalized platform name."""
    system = platform.system().lower()
    if system == "windows":
        return "windows"
    elif system == "linux":
        return "linux"
    elif system == "darwin":
        return "macos"
    return system


def create_spec_file(output_dir: Path) -> Path:
    """
    Create PyInstaller spec file with plugin support.

    The spec file configures PyInstaller to:
    - Include all necessary dependencies
    - Set up plugin directory for runtime discovery
    - Configure hooks for dynamic imports
    """
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules

# Collect all yaft modules
datas = []
binaries = []
hiddenimports = []

# Collect yaft package
tmp_ret = collect_all('yaft')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

# Collect dependencies
for package in ['typer', 'rich', 'pydantic', 'pydantic_settings', 'toml', 'markdown']:
    tmp_ret = collect_all(package)
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]

# Add plugins directory
datas += [('plugins', 'plugins')]

a = Analysis(
    ['src/yaft/cli.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports + [
        'yaft.core.api',
        'yaft.core.plugin_base',
        'yaft.core.plugin_manager',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='yaft',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='yaft',
)
'''
    spec_file = output_dir / "yaft.spec"
    spec_file.write_text(spec_content, encoding="utf-8")
    return spec_file


def build_executable(spec_file: Path, dist_dir: Path, build_dir: Path) -> bool:
    """
    Build executable using PyInstaller.

    Args:
        spec_file: Path to the spec file
        dist_dir: Output directory for the built executable
        build_dir: Temporary build directory

    Returns:
        bool: True if build succeeded, False otherwise
    """
    print(f"Building executable for {get_platform_name()}...")

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        f"--distpath={dist_dir}",
        f"--workpath={build_dir}",
        str(spec_file),
    ]

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        print(e.stdout)
        print(e.stderr)
        return False


def create_plugin_readme(dist_dir: Path) -> None:
    """Create a README in the plugins directory explaining how to add plugins."""
    plugins_dir = dist_dir / "yaft" / "plugins"
    plugins_dir.mkdir(parents=True, exist_ok=True)

    readme_content = """# YAFT Plugins Directory

This directory is where you can add custom plugins for YAFT.

## Adding Plugins

To add a new plugin:

1. Create a Python file in this directory (e.g., `my_plugin.py`)
2. Implement a class that inherits from `PluginBase`
3. Implement all required methods: `metadata`, `initialize`, `execute`, `cleanup`
4. The plugin will be automatically discovered when YAFT starts

## Plugin Template

```python
from typing import Any
from yaft.core.api import CoreAPI
from yaft.core.plugin_base import PluginBase, PluginMetadata


class MyPlugin(PluginBase):
    def __init__(self, core_api: CoreAPI) -> None:
        super().__init__(core_api)

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="MyPlugin",
            version="1.0.0",
            description="My custom plugin",
            author="Your Name",
            requires_core_version=">=0.1.0",
            dependencies=[],
            enabled=True,
        )

    def initialize(self) -> None:
        self.core_api.log_info("Initializing MyPlugin")

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        self.core_api.print_success("MyPlugin executed!")
        return "Success"

    def cleanup(self) -> None:
        self.core_api.log_info("Cleaning up MyPlugin")
```

## Example Plugins

See the included example plugins for more detailed examples:
- hello_world.py - Simple greeting plugin
- file_processor.py - File processing with statistics
- system_info.py - System information display

## Documentation

For more information, see the main documentation at:
https://github.com/yourusername/yaft
"""
    readme_file = plugins_dir / "README.md"
    readme_file.write_text(readme_content, encoding="utf-8")
    print(f"Created plugin README at: {readme_file}")


def main() -> int:
    """Main build function."""
    parser = argparse.ArgumentParser(description="Build YAFT executable")
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean build directories before building",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("dist"),
        help="Output directory for built executable (default: dist)",
    )
    args = parser.parse_args()

    # Get project root
    project_root = Path(__file__).parent
    build_dir = project_root / "build"
    dist_dir = args.output_dir
    spec_dir = project_root

    # Clean if requested
    if args.clean:
        print("Cleaning build directories...")
        shutil.rmtree(build_dir, ignore_errors=True)
        shutil.rmtree(dist_dir, ignore_errors=True)

    # Create output directories
    dist_dir.mkdir(parents=True, exist_ok=True)

    # Create spec file
    print("Creating PyInstaller spec file...")
    spec_file = create_spec_file(spec_dir)

    # Build executable
    success = build_executable(spec_file, dist_dir, build_dir)

    if success:
        print(f"\nBuild successful!")
        print(f"Executable location: {dist_dir / 'yaft'}")
        print(f"Platform: {get_platform_name()}")

        # Create plugin readme
        create_plugin_readme(dist_dir)

        # Show instructions
        print("\nTo run the executable:")
        if platform.system() == "Windows":
            print(f"  {dist_dir / 'yaft' / 'yaft.exe'}")
        else:
            print(f"  {dist_dir / 'yaft' / 'yaft'}")

        print("\nTo add custom plugins:")
        print(f"  Place .py files in: {dist_dir / 'yaft' / 'plugins'}")

        return 0
    else:
        print("\nBuild failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
