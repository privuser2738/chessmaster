#!/bin/bash

echo "========================================"
echo "  ChessMaster - Chess Learning System"
echo "========================================"
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed."
    echo "Please install Python 3.8+ and run install.sh first."
    exit 1
fi

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
else
    # Check if dependencies are installed globally
    echo "Checking dependencies..."
    if ! python3 -c "import requests" &> /dev/null; then
        echo "Dependencies not found. Running install.sh..."
        ./install.sh
        source venv/bin/activate
    fi
fi

echo
echo "Starting ChessMaster..."
echo
echo "Controls:"
echo "  Space   - Pause/Resume"
echo "  Left/Right arrows - Adjust speed"
echo "  Up/Down arrows - Adjust speed (larger)"
echo "  Esc or Q - Exit"
echo

# Run with any arguments passed to this script
python3 src/main.py "$@"
