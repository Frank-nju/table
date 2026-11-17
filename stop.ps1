# CAC Share Session System — stop service script

Write-Host "Stopping CAC Share Session System..." -ForegroundColor Yellow

$pythonProcess = Get-Process -Name python -ErrorAction SilentlyContinue
if ($pythonProcess) {
    $pythonProcess | Stop-Process -Force
    Write-Host "Service stopped." -ForegroundColor Green
} else {
    Write-Host "No running service was found." -ForegroundColor Gray
}