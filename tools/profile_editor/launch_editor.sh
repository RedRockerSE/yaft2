#!/bin/bash
#
# YAFT Plugin Profile Editor Launcher (Linux/macOS)
#
# This script launches the YAFT Plugin Profile Editor GUI application.
# It automatically navigates to the YAFT root directory before launching.

echo ""
echo "========================================"
echo "  YAFT Plugin Profile Editor"
echo "========================================"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Navigate to YAFT root (two levels up from tools/profile_editor)
cd "$SCRIPT_DIR/../.." || {
    echo "ERROR: Could not navigate to YAFT root directory"
    exit 1
}

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "ERROR: Python is not installed or not in PATH"
        echo "Please install Python 3.12+ and try again."
        exit 1
    else
        PYTHON_CMD="python"
    fi
else
    PYTHON_CMD="python3"
fi

echo "Using Python: $PYTHON_CMD"
$PYTHON_CMD --version

# Check if toml package is installed
$PYTHON_CMD -c "import toml" &> /dev/null
if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: The 'toml' package is required but not installed."
    echo ""
    echo "Installing toml package..."
    $PYTHON_CMD -m pip install toml

    if [ $? -ne 0 ]; then
        echo ""
        echo "Installation failed. Please install manually:"
        echo "  pip install toml"
        echo "  or"
        echo "  uv pip install toml"
        exit 1
    fi

    echo ""
    echo "toml package installed successfully!"
    echo ""
fi

# Launch the GUI application
echo "Starting Plugin Profile Editor..."
echo ""
$PYTHON_CMD tools/profile_editor/profile_editor.py

if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Failed to launch the application."
    exit 1
fi
