#Requires -Version 5.1
<#
.SYNOPSIS
    Automated PostgreSQL Installation Script for Windows 10
    This script will download, install, and configure PostgreSQL on F: drive

.DESCRIPTION
    This script performs the following actions:
    1. Downloads PostgreSQL 16 installer
    2. Installs to F:\PostgreSQL directory
    3. Creates crypto_app user and crypto_checker database
    4. Tests the installation
    5. Creates environment configuration

.PARAMETER InstallPath
    Base installation directory (default: F:\)

.PARAMETER PostgreVersion
    PostgreSQL version to install (default: 16)

.PARAMETER Force
    Force reinstallation if PostgreSQL is already installed

.EXAMPLE
    .\install_postgresql_windows.ps1

.EXAMPLE
    .\install_postgresql_windows.ps1 -InstallPath "F:\" -PostgreVersion "15"

.NOTES
    Run as Administrator for best results
    Requires internet connection for download
#>

param(
    [string]$InstallPath = "F:\",
    [string]$PostgreVersion = "16",
    [switch]$Force
)

# Add type accelerators for better .NET interoperability
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Net

# Configuration Variables
$InstallerUrl = "https://get.enterprisedb.com/postgresql/postgresql-$PostgreVersion.4-1-windows-x64.exe"
$InstallerFile = "$env:TEMP\postgresql-installer.exe"
$PostgreSQLPath = Join-Path $InstallPath "PostgreSQL"
$DataDirectory = "$PostgreSQLPath\data"
$Password = "secure_password_2024"

# Database Connection Info
$DatabaseName = "crypto_checker"
$Username = "crypto_app"
$Port = "5432"

Write-Host "🚀 PostgreSQL Automated Setup for CryptoChecker" -ForegroundColor Cyan
Write-Host "Installation Path: $InstallPath" -ForegroundColor Yellow
Write-Host "PostgreSQL Version: $PostgreVersion" -ForegroundColor Yellow
Write-Host "─" * 60

# Function to test if PostgreSQL is already installed and running
function Test-PostgreSQLInstalled {
    try {
        $result = & "$PostgreSQLPath\bin\psql.exe" --version 2>$null
        if ($LASTEXITCODE -eq 0) {
            return $true
        }
    } catch {
        return $false
    }
    return $false
}

# Function to stop PostgreSQL service if running
function Stop-PostgreSQLService {
    Write-Host "⏹️ Stopping PostgreSQL service..." -ForegroundColor Yellow

    try {
        Stop-Service -Name "postgresql-x64-$PostgreVersion" -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    } catch {
        Write-Host "No existing PostgreSQL service found" -ForegroundColor Gray
    }
}

# Function to check if port is available
function Test-PortFree {
    param([int]$Port)
    $tcpConnections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    return ($tcpConnections.Count -eq 0)
}

# Function to download installer
function Download-Installer {
    Write-Host "⬇️ Downloading PostgreSQL installer..." -ForegroundColor Yellow

    if (Test-Path $InstallerFile) {
        Remove-Item $InstallerFile -Force
    }

    try {
        $webClient = New-Object System.Net.WebClient
        $webClient.DownloadFile($InstallerUrl, $InstallerFile)

        if (Test-Path $InstallerFile) {
            Write-Host "✅ Download completed: $(Get-Item $InstallerFile).Length bytes" -ForegroundColor Green
            return $true
        } else {
            throw "Download failed - file not found"
        }
    } catch {
        Write-Error "❌ Download failed: $_"
        return $false
    }
}

# Function to install PostgreSQL
function Install-PostgreSQL {
    Write-Host "📦 Installing PostgreSQL..." -ForegroundColor Yellow

    # Check if port 5432 is free
    if (-not (Test-PortFree -Port 5432)) {
        $response = Read-Host "Port 5432 appears to be in use. Continue anyway? (y/N)"
        if ($response.ToLower() -ne 'y') {
            throw "Installation cancelled - port in use"
        }
    }

    # Silent installation arguments
    $installArgs = @(
        "--mode", "unattended",
        "--prefix", $PostgreSQLPath,
        "--datadir", $DataDirectory,
        "--port", $Port,
        "--servicename", "PostgreSQL-CryptoChecker",
        "--superpassword", $Password,
        "--install_runtimes", "0",
        "--locale", "en_US"
    )

    Write-Host "Running installer with arguments: $($installArgs -join ' ')" -ForegroundColor Gray

    try {
        $process = Start-Process -FilePath $InstallerFile -ArgumentList $installArgs -Wait -NoNewWindow -PassThru

        if ($process.ExitCode -eq 0) {
            Write-Host "✅ PostgreSQL installation completed successfully" -ForegroundColor Green
            return $true
        } else {
            throw "Installer exited with code: $($process.ExitCode)"
        }
    } catch {
        Write-Error "❌ Installation failed: $_"
        return $false
    }
}

# Function to initialize PostgreSQL after installation
function Initialize-PostgreSQL {
    Write-Host "🔧 Initializing PostgreSQL..." -ForegroundColor Yellow

    $envPath = [Environment]::GetEnvironmentVariable("PATH", "Machine")
    if ("$PostgreSQLPath\bin" -notin $envPath.Split(";")) {
        $newPath = "$PostgreSQLPath\bin;$envPath"
        [Environment]::SetEnvironmentVariable("PATH", $newPath, "Machine")
        Write-Host "✅ Added PostgreSQL to system PATH" -ForegroundColor Green
    }

    # Create data directory if it doesn't exist
    if (-not (Test-Path $DataDirectory)) {
        New-Item -ItemType Directory -Path $DataDirectory -Force | Out-Null
        Write-Host "✅ Created data directory: $DataDirectory" -ForegroundColor Green
    }

    # Initialize database cluster if needed
    if (-not (Test-Path (Join-Path $DataDirectory "postgresql.conf"))) {
        Write-Host "🔧 Initializing database cluster..." -ForegroundColor Yellow

        $initProcess = & "$PostgreSQLPath\bin\initdb.exe" -D $DataDirectory -U postgres --encoding=UTF8 --locale=C 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Database cluster initialized successfully" -ForegroundColor Green
        } else {
            Write-Error "❌ Failed to initialize database cluster"
            Write-Host "initdb output: $initProcess" -ForegroundColor Red
            return $false
        }
    }

    return $true
}

# Function to start PostgreSQL service
function Start-PostgreSQL {
    Write-Host "▶️ Starting PostgreSQL service..." -ForegroundColor Yellow

    try {
        # Register service
        $svcProcess = & "$PostgreSQLPath\bin\pg_ctl.exe" register -D $DataDirectory -N "postgresql-x64-$PostgreVersion" -U "NT AUTHORITY\NetworkService" 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Service registration output: $svcProcess" -ForegroundColor Yellow
        }

        # Start service
        Start-Process -FilePath "$env:SYSTEMROOT\System32\net.exe" -ArgumentList "start", "postgresql-x64-$PostgreVersion" -Wait -NoNewWindow

        Start-Sleep -Seconds 5

        # Verify service is running
        $service = Get-Service -Name "postgresql-x64-$PostgreVersion" -ErrorAction SilentlyContinue
        if ($service -and $service.Status -eq "Running") {
            Write-Host "✅ PostgreSQL service started successfully" -ForegroundColor Green
            return $true
        } else {
            Write-Error "❌ Failed to start PostgreSQL service"
            Write-Host "Service status: $($service.Status)" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Error "❌ Failed to start PostgreSQL service: $_"
        return $false
    }
}

# Function to configure database and user
function Configure-Database {
    Write-Host "🔧 Configuring database and user..." -ForegroundColor Yellow

    try {
        # Wait for PostgreSQL to be ready
        Start-Sleep -Seconds 3

        $sqlScript = @"
CREATE DATABASE IF NOT EXISTS $DatabaseName;
DO \$\$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$Username') THEN
      CREATE USER $Username WITH PASSWORD '$Password';
   END IF;
END
\$\$;
GRANT ALL PRIVILEGES ON DATABASE $DatabaseName TO $Username;
ALTER USER $Username CONNECTION LIMIT 100;
"@

        # Execute SQL commands
        $tempSqlFile = "$env:TEMP\postgres_setup.sql"
        $sqlScript | Out-File -FilePath $tempSqlFile -Encoding UTF8 -Force

        $result = & "$PostgreSQLPath\bin\psql.exe" -U postgres -h localhost -f $tempSqlFile 2>&1

        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Database and user configured successfully" -ForegroundColor Green
            Remove-Item $tempSqlFile -Force -ErrorAction SilentlyContinue
            return $true
        } else {
            Write-Error "❌ Database configuration failed"
            Write-Host "psql output: $result" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Error "❌ Database configuration failed: $_"
        return $false
    }
}

# Function to test database connection
function Test-DatabaseConnection {
    Write-Host "🧪 Testing database connection..." -ForegroundColor Yellow

    try {
        # Test with postgres user
        $postgresTest = & "$PostgreSQLPath\bin\psql.exe" -U postgres -h localhost -d postgres -c "SELECT version();" 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ PostgreSQL server connection successful" -ForegroundColor Green
        } else {
            Write-Host "❌ PostgreSQL server connection failed" -ForegroundColor Red
            return $false
        }

        # Test with app user
        $userTest = & "$PostgreSQLPath\bin\psql.exe" -U $Username -h localhost -d $DatabaseName -c "SELECT current_database(), current_user;" 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Application user connection successful" -ForegroundColor Green
        } else {
            Write-Host "❌ Application user connection failed" -ForegroundColor Red
            return $false
        }

        return $true
    } catch {
        Write-Error "❌ Connection test failed: $_"
        return $false
    }
}

# Function to create Python connection test script
function Create-PythonTest {
    Write-Host "📄 Creating Python connection test script..." -ForegroundColor Yellow

    $testScript = @"
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine

# Set up.ps1 test connection
DATABASE_URL = f"postgresql://{globals()['Username']}:{globals()['Password']}@localhost:{globals()['Port']}/{globals()['DatabaseName']}"

async def test_connection():
    print("🧪 Testing PostgreSQL connection from Python...")
    engine = create_async_engine(DATABASE_URL, echo=False)
    try:
        async with engine.connect() as conn:
            result = await conn.execute('SELECT version()')
            version = result.scalar()
            print("✅ PostgreSQL connection successful!")
            print(f"Version: {version}")
            return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False
    finally:
        await engine.dispose()

if __name__ == "__main__":
    success = asyncio.run(test_connection())
    exit(0 if success else 1)
"@

    $testScriptPath = "F:\test_postgres_connection.py"
    $testScript | Out-File -FilePath $testScriptPath -Encoding UTF8 -Force
    Write-Host "✅ Created test script: $testScriptPath" -ForegroundColor Green
}

# Function to create .env file configuration
function Create-EnvironmentConfig {
    Write-Host "🔧 Creating environment configuration..." -ForegroundColor Yellow

    $envPath = "F:\.env"
    $envContent = @"
# Database Configuration
DATABASE_URL=postgresql://$Username`:$Password`@localhost:$Port/$DatabaseName

# Application Settings
DEBUG=True
SECRET_KEY=your-secure-secret-key-change-in-production-$((Get-Random -Maximum 999999))
HOST=localhost
PORT=8000
"@

    $envContent | Out-File -FilePath $envPath -Encoding UTF8 -Force
    Write-Host "✅ Created .env file: $envPath" -ForegroundColor Green

    # Also create or update existing .env if it exists in project directory
    $projectEnvPath = Join-Path (Get-Location).Path ".env"
    if (Test-Path $projectEnvPath) {
        Write-Host "🛠️ Project .env file exists, updating DATABASE_URL..." -ForegroundColor Blue
        $existingContent = Get-Content $projectEnvPath -Raw
        if ($existingContent -match "^DATABASE_URL=") {
            $existingContent = $existingContent -replace "^DATABASE_URL=.*$", "DATABASE_URL=postgresql://$Username`:$Password`@localhost:$Port/$DatabaseName"
        } else {
            $existingContent += "`nDATABASE_URL=postgresql://$Username`:$Password`@localhost:$Port/$DatabaseName`n"
        }
        $existingContent | Out-File -FilePath $projectEnvPath -Encoding UTF8 -Force
        Write-Host "✅ Updated project .env file: $projectEnvPath" -ForegroundColor Green
    }
}

# Function to create quick start script
function Create-QuickStart {
    Write-Host "📝 Creating quick start script..." -ForegroundColor Yellow

    $startScript = @"
@echo off
echo 🚀 Starting CryptoChecker with PostgreSQL...

cd /d "%~dp0"

REM Activate virtual environment (if exists)
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
    echo ✅ Virtual environment activated
) else (
    echo ⚠️ No virtual environment found, continuing...
)

REM Run application
python main.py
pause
"@

    $startScriptPath = "F:\start_cryptochecker.bat"
    $startScript | Out-File -FilePath $startScriptPath -Encoding ASCII -Force
    Write-Host "✅ Created start script: $startScriptPath" -ForegroundColor Green
    Write-Host "   Double-click to start your application after migration" -ForegroundColor Cyan
}

# Main execution
function Main {
    try {
        # Check if running as administrator
        $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
        $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
        $isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

        Write-Host "Administrator privileges: $(if ($isAdmin) {'✅ Yes'} else {'❌ No - consider running as Administrator'})" -ForegroundColor $(if ($isAdmin) {'Green'} else {'Yellow'})

        # Check if already installed
        if (Test-PostgreSQLInstalled -and -not $Force) {
            Write-Host "⚠️ PostgreSQL already appears to be installed on F: drive" -ForegroundColor Yellow
            $response = Read-Host "Reinstall? (y/N)"
            if ($response.ToLower() -ne 'y') {
                return
            }
            Stop-PostgreSQLService
        }

        # Check F: drive exists
        if (-not (Test-Path $InstallPath)) {
            throw "F: drive not found. Please ensure F: drive is mounted and accessible"
        }

        # Get available space on F: drive
        $driveInfo = Get-WmiObject -Class Win32_LogicalDisk -Filter "DeviceID='F:'"
        $freeSpaceGB = [math]::Round($driveInfo.FreeSpace / 1GB, 2)
        Write-Host "F: drive free space: $freeSpaceGB GB" -ForegroundColor Cyan

        if ($freeSpaceGB -lt 2) {
            throw "Not enough free space on F: drive (need at least 2GB)"
        }

        # Download installer
        if (-not (Download-Installer)) { return }

        # Install PostgreSQL
        if (-not (Install-PostgreSQL)) { return }

        # Initialize PostgreSQL
        if (-not (Initialize-PostgreSQL)) { return }

        # Start PostgreSQL
        if (-not (Start-PostgreSQL)) { return }

        # Configure database
        if (-not (Configure-Database)) { return }

        # Test connections
        if (-not (Test-DatabaseConnection)) {
            Write-Host "❌ Connection tests failed, but setup continued" -ForegroundColor Red
        } else {
            Write-Host "✅ All connection tests passed" -ForegroundColor Green
        }

        # Create configuration files
        Create-PythonTest
        Create-EnvironmentConfig
        Create-QuickStart

        Write-Host "" -ForegroundColor White
        Write-Host "🎉 PostgreSQL installation completed successfully!" -ForegroundColor Green
        Write-Host "📍 Installation location: $PostgreSQLPath" -ForegroundColor Cyan
        Write-Host "👤 Database user: $Username" -ForegroundColor Cyan
        Write-Host "🗄️ Database: $DatabaseName" -ForegroundColor Cyan
        Write-Host "" -ForegroundColor White
        Write-Host "🚀 Next Steps:" -ForegroundColor Yellow
        Write-Host "1. Run: python scripts/migrate_to_postgresql.py" -ForegroundColor Cyan
        Write-Host "2. Run: python main.py" -ForegroundColor Cyan
        Write-Host "3. Test simultaneous bot operations (no more lock errors!)" -ForegroundColor Cyan

    } catch {
        Write-Error "❌ Installation failed: $_"
        Write-Host "" -ForegroundColor Red
        Write-Host "📞 Troubleshooting:" -ForegroundColor Yellow
        Write-Host "- Check Windows Firewall settings" -ForegroundColor Cyan
        Write-Host "- Ensure F: drive has sufficient space" -ForegroundColor Cyan
        Write-Host "- Run as Administrator" -ForegroundColor Cyan
        Write-Host "- Check PostgreSQL logs in F:\\PostgreSQL\\data\\log" -ForegroundColor Cyan
    } finally {
        # Cleanup installer file
        if (Test-Path $InstallerFile) {
            Remove-Item $InstallerFile -Force -ErrorAction SilentlyContinue
        }
    }
}

# Execute main function
Main
