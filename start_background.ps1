# CAC分享会系统 - 后台启动脚本

Write-Host "启动 CAC分享会系统..." -ForegroundColor Yellow

# 检查是否已运行
$running = Get-Process -Name python -ErrorAction SilentlyContinue
if ($running) {
    Write-Host "服务已在运行中" -ForegroundColor Green
    exit
}

# 后台启动
Start-Process python -ArgumentList "app.py" -WorkingDirectory "C:\table-main" -WindowStyle Hidden

Start-Sleep -Seconds 2

# 检查是否启动成功
$healthCheck = Invoke-WebRequest -Uri "http://localhost:8080/healthz" -UseBasicParsing -ErrorAction SilentlyContinue
if ($healthCheck -and $healthCheck.StatusCode -eq 200) {
    Write-Host "服务已启动" -ForegroundColor Green
    Write-Host "访问地址: http://47.102.100.9:8080" -ForegroundColor Cyan
} else {
    Write-Host "启动失败，请检查错误" -ForegroundColor Red
}