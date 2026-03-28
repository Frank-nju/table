@echo off
chcp 65001 >nul
cd /d %~dp0

echo ===== 拉取代码 =====
git pull

echo.
echo ===== 检查前端是否需要构建 =====
REM 如果 frontend/dist 不存在，或者有前端源码更新
if not exist "frontend\dist\index.html" (
    echo dist目录不存在，需要构建...
    goto :build_frontend
)

REM 检查本次 pull 是否包含前端源码
git diff --name-only HEAD~1 HEAD 2>nul | findstr "frontend/src frontend/package" >nul
if %errorlevel% equ 0 (
    echo 前端源码有更新，正在构建...
    goto :build_frontend
)

echo 前端无需重新构建
goto :restart

:build_frontend
cd frontend
call npm install
call npm run build
cd ..

:restart
echo.
echo ===== 重启服务 =====
taskkill /f /im python.exe 2>nul
timeout /t 1 >nul
start "" pythonw.exe app.py

echo.
echo ===== 完成 =====
echo 服务已后台运行
timeout /t 2 >nul
tasklist | findstr python