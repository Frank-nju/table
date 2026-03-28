@echo off
chcp 65001 >nul
cd /d %~dp0

echo ===== 启动服务 =====
taskkill /f /im python.exe 2>nul
timeout /t 1 >nul
start "" pythonw.exe app.py
echo 服务已后台运行
timeout /t 2 >nul
tasklist | findstr python
pause