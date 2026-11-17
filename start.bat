@echo off
chcp 65001 >nul
cd /d "%~dp0.."
call .venv\Scripts\activate.bat
echo Starting CAC Share Session System...
echo Application URL: http://47.102.100.9:8080
echo Press Ctrl+C to stop the service
echo.
python app.py