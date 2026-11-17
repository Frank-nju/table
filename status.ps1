# CAC Share Session System — check service status

Write-Host ""
Write-Host "=== CAC Share Session System — Status ===" -ForegroundColor Cyan
Write-Host ""

# Check the process.
$pythonProcess = Get-Process -Name python -ErrorAction SilentlyContinue
if ($pythonProcess) {
    Write-Host "Service status: " -NoNewline
    Write-Host "Running" -ForegroundColor Green
    Write-Host "Process ID: $($pythonProcess.Id)"
} else {
    Write-Host "Service status: " -NoNewline
    Write-Host "Not running" -ForegroundColor Red
}

# Check the port.
Write-Host ""
Write-Host "Checking port..." -ForegroundColor Yellow
$portCheck = netstat -ano | Select-String ":8080.*LISTENING"
if ($portCheck) {
    Write-Host "Port 8080: " -NoNewline
    Write-Host "Listening" -ForegroundColor Green
} else {
    Write-Host "Port 8080: " -NoNewline
    Write-Host "Not listening" -ForegroundColor Red
}

# Check the health endpoint.
Write-Host ""
Write-Host "Checking health..." -ForegroundColor Yellow
$healthCheck = Invoke-WebRequest -Uri "http://localhost:8080/healthz" -UseBasicParsing -ErrorAction SilentlyContinue
if ($healthCheck -and $healthCheck.StatusCode -eq 200) {
    Write-Host "API status: " -NoNewline
    Write-Host "Healthy" -ForegroundColor Green
    Write-Host "Response:   $($healthCheck.Content)"
} else {
    Write-Host "API status: " -NoNewline
    Write-Host "Unhealthy" -ForegroundColor Red
}

Write-Host ""