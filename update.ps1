# CAC分享会系统更新脚本
# 使用方法: 右键 -> 使用 PowerShell 运行

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   CAC分享会系统 更新脚本" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# 设置路径
$AppDir = "C:\table-main"
$BackupDir = "C:\table-backup"
$MysqlPath = "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe"

# 进入项目目录
Set-Location $AppDir

# 1. 停止服务
Write-Host "[1/5] 停止服务..." -ForegroundColor Yellow
$pythonProcess = Get-Process -Name python -ErrorAction SilentlyContinue
if ($pythonProcess) {
    $pythonProcess | Stop-Process -Force
    Start-Sleep -Seconds 1
    Write-Host "      服务已停止" -ForegroundColor Green
} else {
    Write-Host "      没有运行中的服务" -ForegroundColor Gray
}

# 2. 备份数据库
Write-Host "[2/5] 备份数据库..." -ForegroundColor Yellow
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupFile = "$BackupDir\table_signup_$timestamp.sql"

if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
}

if (Test-Path $MysqlPath) {
    Write-Host "      请输入MySQL root密码:" -ForegroundColor Gray
    & $MysqlPath -u root -p table_signup > $backupFile 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "      数据库已备份: $backupFile" -ForegroundColor Green
    } else {
        Write-Host "      数据库备份失败（可能密码错误）" -ForegroundColor Red
    }
} else {
    Write-Host "      未找到MySQL，跳过备份" -ForegroundColor Gray
}

# 3. 更新代码
Write-Host ""
Write-Host "[3/5] 更新代码" -ForegroundColor Yellow
Write-Host "      请通过远程桌面将新代码复制到 $AppDir" -ForegroundColor White
Write-Host "      复制完成后按任意键继续..." -ForegroundColor White
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
Write-Host "      代码已更新" -ForegroundColor Green

# 4. 更新依赖
Write-Host "[4/5] 更新依赖..." -ForegroundColor Yellow
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple -q 2>$null
Write-Host "      依赖已更新" -ForegroundColor Green

# 5. 启动服务
Write-Host "[5/5] 启动服务..." -ForegroundColor Yellow
Start-Process python -ArgumentList "app.py" -WorkingDirectory $AppDir -WindowStyle Normal
Start-Sleep -Seconds 2

# 检查服务状态
$healthCheck = Invoke-WebRequest -Uri "http://localhost:8080/healthz" -UseBasicParsing -ErrorAction SilentlyContinue
if ($healthCheck -and $healthCheck.StatusCode -eq 200) {
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host "   更新完成！服务运行正常" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "访问地址: http://47.102.100.9:8080" -ForegroundColor Cyan
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "警告: 服务可能未正常启动，请检查" -ForegroundColor Red
    Write-Host "运行: python app.py 查看错误信息" -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "按任意键退出..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")