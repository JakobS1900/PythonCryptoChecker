# PowerShell activation script for Crypto Analytics Platform
# Usage: .\activate.ps1 or right-click -> Run with PowerShell

Write-Host "Activating Crypto Analytics Platform virtual environment..." -ForegroundColor Yellow

# Get script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Change to project directory
Set-Location $ScriptDir

# Check if virtual environment exists
if (-Not (Test-Path ".venv\Scripts\Activate.ps1")) {
    Write-Host "Virtual environment not found. Creating one..." -ForegroundColor Red
    python -m venv .venv
    Write-Host "Installing requirements..." -ForegroundColor Yellow
    & ".venv\Scripts\pip.exe" install -r requirements.txt
}

# Activate virtual environment
& ".venv\Scripts\Activate.ps1"

Write-Host ""
Write-Host "Virtual environment activated!" -ForegroundColor Green
Write-Host ""
Write-Host "You can now run:" -ForegroundColor Cyan
Write-Host "  python main.py              # Run the application" -ForegroundColor White
Write-Host "  python test_setup.py        # Test setup" -ForegroundColor White
Write-Host "  pip install <package>       # Install new packages" -ForegroundColor White
Write-Host ""
Write-Host "To deactivate, type: deactivate" -ForegroundColor Cyan
Write-Host ""

# Optional: Auto-run test to verify setup
$response = Read-Host "Run setup test? (y/n)"
if ($response -eq "y" -or $response -eq "Y" -or $response -eq "") {
    python test_setup.py
}