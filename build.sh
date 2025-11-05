#!/bin/bash
# Build script for Linux/macOS

echo "Building YAFT for $(uname -s)..."
python build.py "$@"

if [ $? -eq 0 ]; then
    echo ""
    echo "Build completed successfully!"
    echo "Executable: dist/yaft/yaft"
else
    echo ""
    echo "Build failed!"
    exit 1
fi
