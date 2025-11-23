@echo off
echo ========================================
echo   ChessMaster - Installation Script
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python 3.8+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo Python found:
python --version
echo.

echo Installing required packages...
echo.

pip install --upgrade pip
pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ERROR: Some packages failed to install.
    echo Try running: pip install requests beautifulsoup4 duckduckgo-search Pillow PyPDF2
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Installation Complete!
echo ========================================
echo.
echo To start ChessMaster, run:
echo   run.bat
echo.
echo Or with custom speed:
echo   python src/main.py --speed 150
echo.
echo Speed guide:
echo   1-50    = Very slow (10-30 seconds per slide)
echo   50-100  = Moderate (5-10 seconds per slide)
echo   100-150 = Fast (1-5 seconds per slide)
echo   150-200 = Very fast (0.2-2 seconds per slide)
echo.
pause
