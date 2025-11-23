@echo off
echo ========================================
echo   ChessMaster - Chess Learning System
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH.
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

REM Check if dependencies are installed
echo Checking dependencies...
pip show requests >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt
)

echo.
echo Starting ChessMaster...
echo.
echo Controls:
echo   Space   - Pause/Resume
echo   Left/Right arrows - Adjust speed
echo   Up/Down arrows - Adjust speed (larger)
echo   Esc or Q - Exit
echo.

REM Run with default speed (100)
python src/main.py %*

pause
