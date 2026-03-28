#!/usr/bin/env bash
# 阿里云服务器一键部署脚本
# 使用方法: sudo bash deploy/deploy_aliyun.sh

set -e

APP_DIR="${1:-/opt/table}"
SERVER_IP="47.102.100.9"

echo "=========================================="
echo "  CAC分享会系统 阿里云部署脚本"
echo "=========================================="
echo ""

# 检查root权限
if [[ $EUID -ne 0 ]]; then
  echo "请使用root权限运行: sudo bash deploy/deploy_aliyun.sh" >&2
  exit 1
fi

# 1. 安装系统依赖
echo "[1/7] 安装系统依赖..."
apt-get update
apt-get install -y python3 python3-venv python3-pip nginx mysql-server

# 2. 配置MySQL
echo "[2/7] 配置MySQL..."
# 启动MySQL
systemctl start mysql
systemctl enable mysql

# 创建数据库和用户
MYSQL_PWD=$(openssl rand -base64 12)
mysql -u root <<EOF
CREATE DATABASE IF NOT EXISTS table_signup CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'table_user'@'localhost' IDENTIFIED BY '${MYSQL_PWD}';
GRANT ALL PRIVILEGES ON table_signup.* TO 'table_user'@'localhost';
FLUSH PRIVILEGES;
EOF

echo "MySQL用户: table_user"
echo "MySQL密码: ${MYSQL_PWD}"
echo "MySQL数据库: table_signup"

# 3. 复制项目文件
echo "[3/7] 复制项目文件..."
mkdir -p "${APP_DIR}"
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
SRC_DIR=$(cd "${SCRIPT_DIR}/.." && pwd)
rsync -av --delete --exclude '.git' --exclude '.venv' --exclude '__pycache__' "${SRC_DIR}/" "${APP_DIR}/"

# 4. 创建Python虚拟环境
echo "[4/7] 安装Python依赖..."
python3 -m venv "${APP_DIR}/.venv"
"${APP_DIR}/.venv/bin/pip" install --upgrade pip -q
"${APP_DIR}/.venv/bin/pip" install -r "${APP_DIR}/requirements.txt" -q

# 5. 创建环境配置文件
echo "[5/7] 创建环境配置..."
cat > /etc/table-signup.env <<ENVEOF
# MySQL配置
DB_BACKEND=mysql
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=table_user
MYSQL_PASSWORD=${MYSQL_PWD}
MYSQL_DATABASE=table_signup
MYSQL_CONNECT_TIMEOUT=5
MYSQL_READ_TIMEOUT=30
MYSQL_WRITE_TIMEOUT=30

# 兼容模式
SEATABLE_SERVER_URL=https://table.nju.edu.cn
SEATABLE_API_TOKEN=

# 表名配置
ACTIVITY_TABLE_NAME=分享会活动
SIGNUP_TABLE_NAME=分享会报名
REVIEW_RATING_TABLE_NAME=评议评分
OUTPUT_RECORD_TABLE_NAME=输出活动记录

# 活动字段
ACTIVITY_COL_DATE=活动日期
ACTIVITY_COL_TIME=活动时间
ACTIVITY_COL_SPEAKERS=分享者
ACTIVITY_COL_TOPIC=活动主题
ACTIVITY_COL_CLASSROOM=活动教室
ACTIVITY_COL_VIDEOURL=线上视频号
ACTIVITY_COL_CREATOR_NAME=组织者姓名
ACTIVITY_COL_CREATOR_EMAIL=组织者邮箱
ACTIVITY_COL_STATUS=活动状态
ACTIVITY_COL_CLOSED_AT=结项时间
ACTIVITY_COL_ON_TIME=准时结项
ACTIVITY_COL_CLOSER_NAME=结项人
ACTIVITY_COL_CREATOR_STUDENT_ID=组织者学号

# 报名字段
SIGNUP_COL_NAME=姓名
SIGNUP_COL_ACTIVITY_ID=关联活动
SIGNUP_COL_ROLE=角色
SIGNUP_COL_PHONE=联系电话
SIGNUP_COL_EMAIL=邮箱
SIGNUP_COL_REVIEW_DOC_URL=评议语雀链接
SIGNUP_COL_REVIEW_SUBMITTED_AT=评议提交时间
SIGNUP_COL_LAST_REVIEW_REMINDER_AT=上次评议提醒时间
SIGNUP_COL_STUDENT_ID=学号

# 评议评分字段
REVIEW_RATING_COL_SIGNUP_ID=评议报名ID
REVIEW_RATING_COL_ACTIVITY_ID=活动ID
REVIEW_RATING_COL_REVIEWER_NAME=评议者姓名
REVIEW_RATING_COL_RATER_NAME=评分人姓名
REVIEW_RATING_COL_SCORE=评分
REVIEW_RATING_COL_WEIGHT=权重
REVIEW_RATING_COL_COMMENT=评分备注

# 输出活动记录字段
OUTPUT_RECORD_COL_NAME=姓名
OUTPUT_RECORD_COL_TYPE=输出类型
OUTPUT_RECORD_COL_DATE=输出日期
OUTPUT_RECORD_COL_NOTE=备注

# 报名配置
REVIEWER_LIMIT=3
LISTENER_UNLIMITED=true

# 时间配置
TIME_SLOTS=09:00,10:00,11:00,12:00,13:00,14:00,15:00,16:00,17:00,18:00,19:00,20:00,21:00,22:00

# CAC有约配置
CAC_FIXED_WEEKDAY=4
CAC_FIXED_TIME=18:00-19:00

# Flask配置
FLASK_HOST=0.0.0.0
FLASK_PORT=8080
FLASK_DEBUG=false
TABLE_ROWS_CACHE_TTL_SECONDS=8

# 邮件配置 (请根据实际情况修改)
SMTP_HOST=smtp.exmail.qq.com
SMTP_PORT=465
SMTP_USERNAME=251880357@smail.nju.edu.cn
SMTP_PASSWORD=vnDao7ktf9iX8rMd
SMTP_USE_TLS=false
SMTP_USE_SSL=true
EMAIL_FROM=251880357@smail.nju.edu.cn

# 边界预警配置
BOUNDARY_REPORT_EMAIL=nova@nju.edu.cn
BOUNDARY_LOOKBACK_DAYS=14
BOUNDARY_FIRST_REPORT_AT=2026-03-22 22:00:00
BOUNDARY_WEEKLY_REPORT_WEEKDAY=6
BOUNDARY_WEEKLY_REPORT_HOUR=22
BOUNDARY_WEEKLY_REPORT_MINUTE=0

# CAC配置
CAC_NAME=cac
CAC_EMAIL=nova@nju.edu.cn

# 后台任务配置
ACTIVITY_CLOSE_GRACE_MINUTES=120
REVIEW_REMINDER_INTERVAL_HOURS=24
BACKGROUND_SCAN_INTERVAL_SECONDS=3600

# 个人工作台配置
PROFILE_EXPLORE_DEFAULT_PAGE_SIZE=10
PROFILE_EXPLORE_MAX_PAGE_SIZE=100
PROFILE_CACHE_TTL_SECONDS=20
PROFILE_FEED_DEFAULT_LIMIT=30

# 名单文件
ROSTER_FILE_PATH=./member_roster.local.txt
ENVEOF

chmod 600 /etc/table-signup.env
echo "环境配置已保存到: /etc/table-signup.env"

# 6. 配置systemd服务
echo "[6/7] 配置系统服务..."
cat > /etc/systemd/system/table-signup.service <<SVCEOF
[Unit]
Description=CAC Table Signup Flask Service
After=network.target mysql.service

[Service]
Type=simple
User=root
WorkingDirectory=${APP_DIR}
EnvironmentFile=/etc/table-signup.env
ExecStart=${APP_DIR}/.venv/bin/gunicorn -c ${APP_DIR}/gunicorn.conf.py app:app
Restart=always
RestartSec=3
KillSignal=SIGQUIT
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable table-signup

# 7. 配置Nginx
echo "[7/7] 配置Nginx..."
cat > /etc/nginx/sites-available/table-signup.conf <<NGINXEOF
server {
    listen 80;
    server_name ${SERVER_IP};

    client_max_body_size 2m;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 60s;
    }

    location = /healthz {
        proxy_pass http://127.0.0.1:8080/healthz;
        access_log off;
    }
}
NGINXEOF

ln -sf /etc/nginx/sites-available/table-signup.conf /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

nginx -t
systemctl reload nginx

# 启动应用
echo ""
echo "启动应用服务..."
systemctl restart table-signup
sleep 2

# 检查状态
if systemctl is-active --quiet table-signup; then
    echo ""
    echo "=========================================="
    echo "  部署成功!"
    echo "=========================================="
    echo ""
    echo "访问地址: http://${SERVER_IP}"
    echo ""
    echo "MySQL信息:"
    echo "  用户: table_user"
    echo "  密码: ${MYSQL_PWD}"
    echo "  数据库: table_signup"
    echo ""
    echo "配置文件: /etc/table-signup.env"
    echo ""
    echo "常用命令:"
    echo "  查看状态: systemctl status table-signup"
    echo "  查看日志: journalctl -u table-signup -f"
    echo "  重启服务: systemctl restart table-signup"
    echo ""
else
    echo "警告: 服务启动失败，请检查日志"
    echo "journalctl -u table-signup -n 50"
fi