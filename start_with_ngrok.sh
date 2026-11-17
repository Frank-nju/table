#!/usr/bin/env bash
# Expose the local service with ngrok.
# Prerequisite: install ngrok and configure an auth token first.

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
cd "${SCRIPT_DIR}"

if ! command -v ngrok &> /dev/null; then
    echo "ngrok is not installed. Installing it now..."
    curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
    echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
    sudo apt update && sudo apt install ngrok
    echo "First run: ngrok config add-authtoken <your-token>"
    echo "Get a token at: https://dashboard.ngrok.com/get-started/your-authtoken"
    exit 1
fi

# Start Flask in the background.
. .venv/bin/activate
python app.py &
APP_PID=$!

sleep 2

# Start ngrok.
echo "Starting ngrok; the public URL will appear shortly..."
ngrok http 8080

# Clean up after Ctrl+C.
kill $APP_PID
