# CAC分享会系统 - 停止服务脚本

Write-Host "停止 CAC分享会系统..." -ForegroundColor Yellow

$pythonProcess = Get-Process -Name python -ErrorAction SilentlyContinue
if ($pythonProcess) {
    $pythonProcess | Stop-Process -Force
    Write-Host "服务已停止" -ForegroundColor Green
} else {
    Write-Host "没有运行中的服务" -ForegroundColor Gray
}