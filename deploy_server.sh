#!/bin/bash
# 服务器部署脚本

set -e
cd "$(dirname "$0")"

echo "===== 拉取代码 ====="
git fetch origin
OLD_COMMIT=$(git rev-parse HEAD)
git pull origin main
NEW_COMMIT=$(git rev-parse HEAD)

echo ""
echo "===== 检查前端是否需要构建 ====="

# 如果 frontend/dist 不存在，必须构建
if [ ! -f "frontend/dist/index.html" ]; then
    echo "dist目录不存在，需要构建..."
    cd frontend
    npm install
    npm run build
    cd ..
else
    # 检查是否有前端源码更新
    if [ "$OLD_COMMIT" != "$NEW_COMMIT" ]; then
        CHANGED=$(git diff --name-only $OLD_COMMIT $NEW_COMMIT | grep -E "frontend/src|frontend/package.json|frontend/vite.config" || true)
        if [ -n "$CHANGED" ]; then
            echo "前端源码有更新，正在构建..."
            cd frontend
            npm install
            npm run build
            cd ..
        else
            echo "前端无需重新构建"
        fi
    else
        echo "代码无更新"
    fi
fi

echo ""
echo "===== 安装测试依赖 ====="
pip install pytest pytest-cov -q

echo ""
echo "===== 运行测试 ====="
pytest tests/ -v --tb=short -q || echo "测试有失败，请检查"

echo ""
echo "===== 重启服务 ====="
# 杀死旧进程
pkill -f "python.*app.py" || true
sleep 1

# 启动新进程
nohup python app.py > logs/app.log 2>&1 &
echo "服务已启动，日志: logs/app.log"

echo ""
echo "===== 完成 ====="
sleep 2
ps aux | grep "python.*app.py" | grep -v grep || echo "服务未运行"