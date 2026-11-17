@echo off
chcp 65001 >nul
echo ==========================================
echo   CAC Share Session System — Windows Setup
echo ==========================================
echo.

:: Check for administrator privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Run this script as Administrator!
    pause
    exit /b 1
)

:: Set the project directory
set APP_DIR=C:\table-signup
set PROJECT_DIR=%~dp0..

:: 1. Create the project directory
echo [1/5] Creating the project directory...
if not exist "%APP_DIR%" mkdir "%APP_DIR%"

:: Copy project files
echo Copying project files...
xcopy /E /I /Y "%PROJECT_DIR%\*" "%APP_DIR%\"
if exist "%APP_DIR%\.venv" rmdir /S /Q "%APP_DIR%\.venv"
if exist "%APP_DIR%\__pycache__" rmdir /S /Q "%APP_DIR%\__pycache__"

:: 2. Create the Python virtual environment
echo [2/5] Creating the Python virtual environment...
cd /d "%APP_DIR%"
python -m venv .venv
call .venv\Scripts\activate.bat
pip install --upgrade pip -q
pip install -r requirements.txt -q

:: 3. Copy the environment configuration
echo [3/5] Configuring environment variables...
copy /Y "%APP_DIR%\deploy\env\table-signup.env.example" "%APP_DIR%\.env" >nul

:: 4. Create the startup script
echo [4/5] Creating the startup script...
echo @echo off > "%APP_DIR%\start.bat"
echo cd /d %APP_DIR% >> "%APP_DIR%\start.bat"
echo call .venv\Scripts\activate.bat >> "%APP_DIR%\start.bat"
echo python app.py >> "%APP_DIR%\start.bat"
echo pause >> "%APP_DIR%\start.bat"

:: Create the background startup script
echo @echo off > "%APP_DIR%\start_background.bat"
echo cd /d %APP_DIR% >> "%APP_DIR%\start_background.bat"
echo call .venv\Scripts\activate.bat >> "%APP_DIR%\start_background.bat"
echo start /b pythonw app.py >> "%APP_DIR%\start_background.bat"
echo echo Service started. Open http://47.102.100.9:8080 >> "%APP_DIR%\start_background.bat"

:: 5. Create the shutdown script
echo [5/5] Creating the shutdown script...
echo @echo off > "%APP_DIR%\stop.bat"
echo taskkill /F /IM pythonw.exe 2>nul >> "%APP_DIR%\stop.bat"
echo echo Service stopped >> "%APP_DIR%\stop.bat"

echo.
echo ==========================================
echo   Setup complete!
echo ==========================================
echo.
echo Project directory: %APP_DIR%
echo.
echo Next steps:
echo   1. Install MySQL if it is not already installed.
echo   2. Edit %APP_DIR%\.env and configure the database connection.
echo   3. Run %APP_DIR%\start.bat to start the service.
echo.
echo Application URL: http://47.102.100.9:8080
echo.
pause