@echo off
REM YAFT Plugin Profile Editor Launcher (Windows)
REM
REM This script launches the YAFT Plugin Profile Editor GUI application.
REM It automatically navigates to the YAFT root directory before launching.

echo.
echo ========================================
echo   YAFT Plugin Profile Editor
echo ========================================
echo.

REM Save current directory
set "ORIGINAL_DIR=%CD%"

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"

REM Navigate to YAFT root (two levels up from tools/profile_editor)
cd /d "%SCRIPT_DIR%..\..\"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.12+ and try again.
    pause
    exit /b 1
)

REM Check if toml package is installed
python -c "import toml" >nul 2>&1
if errorlevel 1 (
    echo ERROR: The 'toml' package is required but not installed.
    echo.
    echo Installing toml package...
    python -m pip install toml
    if errorlevel 1 (
        echo.
        echo Installation failed. Please install manually:
        echo   pip install toml
        echo   or
        echo   uv pip install toml
        pause
        exit /b 1
    )
    echo.
    echo toml package installed successfully!
    echo.
)

REM Launch the GUI application
echo Starting Plugin Profile Editor...
echo.
python tools\profile_editor\profile_editor.py

REM Restore original directory
cd /d "%ORIGINAL_DIR%"

if errorlevel 1 (
    echo.
    echo ERROR: Failed to launch the application.
    pause
    exit /b 1
)
