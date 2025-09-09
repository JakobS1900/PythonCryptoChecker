param(
    [int]$Port = 8000,
    [switch]$Tree,              # Kill process tree
    [switch]$Aggressive         # Also match by command line
)

Write-Host "Stopping server on port $Port..." -ForegroundColor Cyan

function Kill-Pid([int]$pid, [switch]$TreeKill) {
    if ($TreeKill) {
        try { & taskkill /PID $pid /T /F | Out-Null } catch { }
    } else {
        try { Stop-Process -Id $pid -Force -ErrorAction Stop } catch { }
    }
}

try {
    $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    $pids = @()
    if ($connections) {
        $pids = $connections | Select-Object -ExpandProperty OwningProcess | Sort-Object -Unique
        foreach ($pid in $pids) {
            $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
            Write-Host ("Killing PID {0} ({1})" -f $pid, ($proc.ProcessName)) -ForegroundColor Yellow
            Kill-Pid -pid $pid -TreeKill:$Tree
        }
    }

    if ($Aggressive) {
        Write-Host "Aggressive mode: searching for uvicorn/python run processes..." -ForegroundColor Cyan
        $matches = Get-CimInstance Win32_Process | Where-Object {
            ($_.CommandLine -match 'uvicorn' -or $_.CommandLine -match 'web.main:app' -or $_.CommandLine -match 'run.py')
        }
        foreach ($m in $matches) {
            if ($pids -contains [int]$m.ProcessId) { continue }
            Write-Host ("Killing PID {0} (cmd: {1})" -f $m.ProcessId, ($m.CommandLine -replace '\s+', ' ').Substring(0, [Math]::Min(80, $m.CommandLine.Length))) -ForegroundColor Yellow
            Kill-Pid -pid $m.ProcessId -TreeKill:$Tree
        }
    }

    if (-not $pids -and -not $Aggressive) {
        Write-Host "No process is listening on port $Port. Try -Aggressive to match by command line." -ForegroundColor Yellow
    } else {
        Write-Host "Done." -ForegroundColor Green
    }
} catch {
    Write-Host "Error stopping server: $_" -ForegroundColor Red
    exit 1
}
