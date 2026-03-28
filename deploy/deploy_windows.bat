@echo off
chcp 65001 >nul
echo ==========================================
echo   CAC分享会系统 Windows部署脚本
echo ==========================================
echo.

:: 检查管理员权限
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo 请以管理员身份运行此脚本！
    pause
    exit /b 1
)

:: 设置项目目录
set APP_DIR=C:\table-signup
set PROJECT_DIR=%~dp0..

:: 1. 创建项目目录
echo [1/5] 创建项目目录...
if not exist "%APP_DIR%" mkdir "%APP_DIR%"

:: 复制项目文件
echo 正在复制项目文件...
xcopy /E /I /Y "%PROJECT_DIR%\*" "%APP_DIR%\"
if exist "%APP_DIR%\.venv" rmdir /S /Q "%APP_DIR%\.venv"
if exist "%APP_DIR%\__pycache__" rmdir /S /Q "%APP_DIR%\__pycache__"

:: 2. 创建Python虚拟环境
echo [2/5] 创建Python虚拟环境...
cd /d "%APP_DIR%"
python -m venv .venv
call .venv\Scripts\activate.bat
pip install --upgrade pip -q
pip install -r requirements.txt -q

:: 3. 复制环境配置
echo [3/5] 配置环境变量...
copy /Y "%APP_DIR%\deploy\env\table-signup.env.example" "%APP_DIR%\.env" >nul

:: 4. 创建启动脚本
echo [4/5] 创建启动脚本...
echo @echo off > "%APP_DIR%\start.bat"
echo cd /d %APP_DIR% >> "%APP_DIR%\start.bat"
echo call .venv\Scripts\activate.bat >> "%APP_DIR%\start.bat"
echo python app.py >> "%APP_DIR%\start.bat"
echo pause >> "%APP_DIR%\start.bat"

:: 创建后台运行脚本
echo @echo off > "%APP_DIR%\start_background.bat"
echo cd /d %APP_DIR% >> "%APP_DIR%\start_background.bat"
echo call .venv\Scripts\activate.bat >> "%APP_DIR%\start_background.bat"
echo start /b pythonw app.py >> "%APP_DIR%\start_background.bat"
echo echo 服务已启动，访问 http://47.102.100.9:8080 >> "%APP_DIR%\start_background.bat"

:: 5. 创建停止脚本
echo [5/5] 创建停止脚本...
echo @echo off > "%APP_DIR%\stop.bat"
echo taskkill /F /IM pythonw.exe 2>nul >> "%APP_DIR%\stop.bat"
echo echo 服务已停止 >> "%APP_DIR%\stop.bat"

echo.
echo ==========================================
echo   部署完成！
echo ==========================================
echo.
echo 项目目录: %APP_DIR%
echo.
echo 后续步骤:
echo   1. 安装MySQL (如果未安装)
echo   2. 编辑 %APP_DIR%\.env 配置数据库连接
echo   3. 运行 %APP_DIR%\start.bat 启动服务
echo.
echo 访问地址: http://47.102.100.9:8080
echo.
pause