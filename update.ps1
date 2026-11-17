# CAC Share Session System update script
# Usage: Right-click the file and select Run with PowerShell.

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   CAC Share Session System — Update" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Set the application paths.
$AppDir = "C:\table-main"
$BackupDir = "C:\table-backup"
$MysqlPath = "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe"

# Change to the project directory.
Set-Location $AppDir

# 1. Stop the service.
Write-Host "[1/5] Stopping the service..." -ForegroundColor Yellow
$pythonProcess = Get-Process -Name python -ErrorAction SilentlyContinue
if ($pythonProcess) {
    $pythonProcess | Stop-Process -Force
    Start-Sleep -Seconds 1
    Write-Host "      Service stopped." -ForegroundColor Green
} else {
    Write-Host "      No running service was found." -ForegroundColor Gray
}

# 2. Back up the database.
Write-Host "[2/5] Backing up the database..." -ForegroundColor Yellow
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupFile = "$BackupDir\table_signup_$timestamp.sql"

if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
}

if (Test-Path $MysqlPath) {
    Write-Host "      Enter the MySQL root password:" -ForegroundColor Gray
    & $MysqlPath -u root -p table_signup > $backupFile 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "      Database backup saved to: $backupFile" -ForegroundColor Green
    } else {
        Write-Host "      Database backup failed (the password may be incorrect)." -ForegroundColor Red
    }
} else {
    Write-Host "      MySQL was not found; skipping the backup." -ForegroundColor Gray
}

# 3. Update the code.
Write-Host ""
Write-Host "[3/5] Updating the code" -ForegroundColor Yellow
Write-Host "      Copy the updated code to $AppDir using Remote Desktop." -ForegroundColor White
Write-Host "      Press any key when the copy is complete..." -ForegroundColor White
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
Write-Host "      Code updated." -ForegroundColor Green

# 4. Update dependencies.
Write-Host "[4/5] Updating dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple -q 2>$null
Write-Host "      Dependencies updated." -ForegroundColor Green

# 5. Start the service.
Write-Host "[5/5] Starting the service..." -ForegroundColor Yellow
Start-Process python -ArgumentList "app.py" -WorkingDirectory $AppDir -WindowStyle Normal
Start-Sleep -Seconds 2

# checkservicestatus
$healthCheck = Invoke-WebRequest -Uri "http://localhost:8080/healthz" -UseBasicParsing -ErrorAction SilentlyContinue
if ($healthCheck -and $healthCheck.StatusCode -eq 200) {
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host "   Update complete. The service is running." -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Application URL: http://47.102.100.9:8080" -ForegroundColor Cyan
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "Warning: the service may not have started correctly. Check the logs." -ForegroundColor Red
    Write-Host "Run python app.py to inspect error output." -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "Press any key to exit..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")