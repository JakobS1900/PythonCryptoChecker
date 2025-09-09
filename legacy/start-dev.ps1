# Development environment startup script
# Opens new PowerShell windows with venv activated

Write-Host "Starting Crypto Analytics Platform Development Environment..." -ForegroundColor Yellow

$ProjectPath = Split-Path -Parent $MyInvocation.MyCommand.Path

# Start main development window
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ProjectPath'; & '.\.venv\Scripts\Activate.ps1'; Write-Host 'Main Development Window - Ready!' -ForegroundColor Green"

# Optional: Start additional windows for different tasks
$response = Read-Host "Start additional terminal windows? (y/n)"
if ($response -eq "y" -or $response -eq "Y") {
    # Testing window
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ProjectPath'; & '.\.venv\Scripts\Activate.ps1'; Write-Host 'Testing Window - Ready!' -ForegroundColor Blue"
    
    # Monitoring/logs window  
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ProjectPath'; & '.\.venv\Scripts\Activate.ps1'; Write-Host 'Monitoring Window - Ready!' -ForegroundColor Magenta"
}

Write-Host "Development environment started!" -ForegroundColor Green