@echo off
REM Build script for Windows

echo Building YAFT for Windows...
python build_exe.py %*

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Build completed successfully!
    echo Executable: dist\yaft\yaft.exe
) else (
    echo.
    echo Build failed!
    exit /b 1
)
