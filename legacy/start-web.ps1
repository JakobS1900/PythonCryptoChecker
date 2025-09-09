# PowerShell script to start the Crypto Analytics Platform Web Interface
# Usage: .\start-web.ps1

Write-Host "Starting Crypto Analytics Platform Web Interface..." -ForegroundColor Yellow

# Get script directory and change to project directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Check if virtual environment exists
if (-Not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Virtual environment not found! Please run .\activate.ps1 first." -ForegroundColor Red
    exit 1
}

# Activate virtual environment and start web server
Write-Host "Activating virtual environment..." -ForegroundColor Green
& ".venv\Scripts\Activate.ps1"

Write-Host ""
Write-Host "🚀 Starting web server..." -ForegroundColor Green
Write-Host "📡 Web Interface: http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "📚 API Documentation: http://127.0.0.1:8000/api/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ("=" * 50) -ForegroundColor Gray

# Start the web application
.venv\Scripts\python.exe start-web.py