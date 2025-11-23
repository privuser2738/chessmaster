# ChessMaster - PowerShell Launcher
# Usage: .\run.ps1 [-Speed 100]

param(
    [int]$Speed = 100
)

Write-Host "========================================"
Write-Host "  ChessMaster - Chess Learning System"
Write-Host "========================================"
Write-Host ""

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Using: $pythonVersion"
} catch {
    Write-Host "Python is not installed or not in PATH."
    Write-Host "Please install Python 3.8+ from https://python.org"
    exit 1
}

# Install dependencies if needed
Write-Host "Checking dependencies..."
$pipCheck = pip show requests 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing dependencies..."
    pip install -r requirements.txt
}

Write-Host ""
Write-Host "Starting ChessMaster with speed: $Speed"
Write-Host ""
Write-Host "Controls:"
Write-Host "  Space        - Pause/Resume"
Write-Host "  Left/Right   - Adjust speed (±10)"
Write-Host "  Up/Down      - Adjust speed (±25)"
Write-Host "  Esc or Q     - Exit"
Write-Host ""

# Run the application
python src/main.py --speed $Speed
