@echo off
chcp 65001 >nul
cd /d "%~dp0.."
call .venv\Scripts\activate.bat
echo 启动CAC分享会系统...
echo 访问地址: http://47.102.100.9:8080
echo 按 Ctrl+C 停止服务
echo.
python app.py