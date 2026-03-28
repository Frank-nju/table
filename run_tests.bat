@echo off
chcp 65001 >nul
cd /d %~dp0

echo ===== 运行测试 =====
echo.

echo 运行 bug 回归测试...
py -3 -m pytest tests/test_bugs.py -v --tb=short

echo.
echo ===== 运行所有测试 =====
py -3 -m pytest tests/ -v --tb=short

echo.
pause