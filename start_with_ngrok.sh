#!/usr/bin/env bash
# 使用 ngrok 公开本地服务
# 前提：需要先安装 ngrok 并配置 authtoken

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
cd "${SCRIPT_DIR}"

if ! command -v ngrok &> /dev/null; then
    echo "ngrok 未安装，正在安装..."
    curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
    echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
    sudo apt update && sudo apt install ngrok
    echo "请先运行: ngrok config add-authtoken <你的token>"
    echo "注册获取 token: https://dashboard.ngrok.com/get-started/your-authtoken"
    exit 1
fi

# 后台启动 Flask
. .venv/bin/activate
python app.py &
APP_PID=$!

sleep 2

# 启动 ngrok
echo "正在启动 ngrok，公网链接即将生成..."
ngrok http 8080

# Ctrl+C 后清理
kill $APP_PID
