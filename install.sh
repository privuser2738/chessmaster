#!/bin/bash

echo "========================================"
echo "  ChessMaster - Installation Script"
echo "========================================"
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed."
    echo "Please install Python 3.8+ using your package manager:"
    echo "  Arch/Manjaro: sudo pacman -S python python-pip"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
    echo "  Fedora: sudo dnf install python3 python3-pip"
    exit 1
fi

echo "Python found:"
python3 --version
echo

# Check for tkinter (required for GUI)
echo "Checking for tkinter..."
if ! python3 -c "import tkinter" &> /dev/null; then
    echo "WARNING: tkinter is not installed."
    echo "Please install it using your package manager:"
    echo "  Arch/Manjaro: sudo pacman -S tk"
    echo "  Ubuntu/Debian: sudo apt install python3-tk"
    echo "  Fedora: sudo dnf install python3-tkinter"
    echo
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to create virtual environment."
        echo "Make sure python3-venv is installed:"
        echo "  Arch/Manjaro: sudo pacman -S python"
        echo "  Ubuntu/Debian: sudo apt install python3-venv"
        exit 1
    fi
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo
echo "Installing required packages..."
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo
    echo "ERROR: Some packages failed to install."
    echo "Try running: pip install requests beautifulsoup4 duckduckgo-search Pillow PyPDF2"
    exit 1
fi

echo
echo "========================================"
echo "  Installation Complete!"
echo "========================================"
echo
echo "To start ChessMaster, run:"
echo "  ./run.sh"
echo
echo "Or with custom speed:"
echo "  ./run.sh --speed 150"
echo
echo "Speed guide:"
echo "  1-50    = Very slow (10-30 seconds per slide)"
echo "  50-100  = Moderate (5-10 seconds per slide)"
echo "  100-150 = Fast (1-5 seconds per slide)"
echo "  150-200 = Very fast (0.2-2 seconds per slide)"
echo
