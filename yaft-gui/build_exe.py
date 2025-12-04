"""Build script for YAFT GUI standalone executable."""

import argparse
import shutil
import sys
from pathlib import Path

import PyInstaller.__main__


def clean_build_dirs():
    """Clean build and dist directories."""
    dirs_to_clean = ["build", "dist"]

    for dir_name in dirs_to_clean:
        dir_path = Path(dir_name)
        if dir_path.exists():
            print(f"Cleaning {dir_name}/ directory...")
            shutil.rmtree(dir_path)


def build_gui():
    """Build YAFT GUI standalone executable."""
    print("=" * 80)
    print("Building YAFT GUI Executable")
    print("=" * 80)

    # Determine platform-specific settings
    is_windows = sys.platform == "win32"

    # Base PyInstaller arguments
    args = [
        "src/yaft_gui/main.py",
        "--name=yaft-gui",
        "--windowed",  # No console window
        "--onefile",  # Single executable
        # Hidden imports
        "--hidden-import=PySide6.QtCore",
        "--hidden-import=PySide6.QtWidgets",
        "--hidden-import=PySide6.QtGui",
        # Optimization
        "--strip",  # Strip debug symbols (Linux/macOS)
        "--noupx",  # Don't use UPX (better compatibility)
        # Output directories
        "--distpath=dist",
        "--workpath=build",
        "--specpath=build",
        # Clean build
        "--clean",
    ]

    # Platform-specific icon
    if is_windows:
        icon_path = Path("resources/icons/yaft.ico")
        if icon_path.exists():
            args.append(f"--icon={icon_path}")
    else:
        icon_path = Path("resources/icons/yaft.icns")
        if icon_path.exists():
            args.append(f"--icon={icon_path}")

    print("\nPyInstaller arguments:")
    for arg in args:
        print(f"  {arg}")
    print()

    # Run PyInstaller
    try:
        PyInstaller.__main__.run(args)
        print("\n" + "=" * 80)
        print("Build completed successfully!")
        print("=" * 80)
        print(f"\nExecutable location: dist/yaft-gui{'exe' if is_windows else ''}")
        return 0
    except Exception as e:
        print("\n" + "=" * 80)
        print(f"Build failed: {e}")
        print("=" * 80)
        return 1


def main():
    """Main build script entry point."""
    parser = argparse.ArgumentParser(description="Build YAFT GUI executable")
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean build directories before building",
    )
    args = parser.parse_args()

    if args.clean:
        clean_build_dirs()

    return build_gui()


if __name__ == "__main__":
    sys.exit(main())
