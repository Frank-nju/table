# CAC Share Session System — background startup script

Write-Host "Starting CAC Share Session System..." -ForegroundColor Yellow

# Check whether the service is already running.
$running = Get-Process -Name python -ErrorAction SilentlyContinue
if ($running) {
    Write-Host "The service is already running." -ForegroundColor Green
    exit
}

# Start the service in the background.
Start-Process python -ArgumentList "app.py" -WorkingDirectory "C:\table-main" -WindowStyle Hidden

Start-Sleep -Seconds 2

# Check whether startup succeeded.
$healthCheck = Invoke-WebRequest -Uri "http://localhost:8080/healthz" -UseBasicParsing -ErrorAction SilentlyContinue
if ($healthCheck -and $healthCheck.StatusCode -eq 200) {
    Write-Host "Service started." -ForegroundColor Green
    Write-Host "Application URL: http://47.102.100.9:8080" -ForegroundColor Cyan
} else {
    Write-Host "Startup failed. Check the error output." -ForegroundColor Red
}