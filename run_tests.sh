#!/bin/bash
# 服务器测试脚本

cd "$(dirname "$0")"

echo "===== 安装测试依赖 ====="
pip install pytest pytest-cov -q

echo ""
echo "===== 运行 Bug 回归测试 ====="
pytest tests/test_bugs.py -v --tb=short

echo ""
echo "===== 运行所有测试 ====="
pytest tests/ -v --tb=short --cov=services --cov=models --cov=routes

echo ""
echo "===== 完成 ====="