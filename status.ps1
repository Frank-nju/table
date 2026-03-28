# CAC分享会系统 - 服务状态检查

Write-Host ""
Write-Host "=== CAC分享会系统 状态检查 ===" -ForegroundColor Cyan
Write-Host ""

# 检查进程
$pythonProcess = Get-Process -Name python -ErrorAction SilentlyContinue
if ($pythonProcess) {
    Write-Host "服务状态: " -NoNewline
    Write-Host "运行中" -ForegroundColor Green
    Write-Host "进程ID:   $($pythonProcess.Id)"
} else {
    Write-Host "服务状态: " -NoNewline
    Write-Host "未运行" -ForegroundColor Red
}

# 检查端口
Write-Host ""
Write-Host "端口检查..." -ForegroundColor Yellow
$portCheck = netstat -ano | Select-String ":8080.*LISTENING"
if ($portCheck) {
    Write-Host "端口 8080: " -NoNewline
    Write-Host "已监听" -ForegroundColor Green
} else {
    Write-Host "端口 8080: " -NoNewline
    Write-Host "未监听" -ForegroundColor Red
}

# 检查健康接口
Write-Host ""
Write-Host "健康检查..." -ForegroundColor Yellow
$healthCheck = Invoke-WebRequest -Uri "http://localhost:8080/healthz" -UseBasicParsing -ErrorAction SilentlyContinue
if ($healthCheck -and $healthCheck.StatusCode -eq 200) {
    Write-Host "API状态:  " -NoNewline
    Write-Host "正常" -ForegroundColor Green
    Write-Host "响应:     $($healthCheck.Content)"
} else {
    Write-Host "API状态:  " -NoNewline
    Write-Host "异常" -ForegroundColor Red
}

Write-Host ""