# NJU Table 报名表（代码版）

这个项目提供一个可部署的小服务，用于在 `https://table.nju.edu.cn/` 的 Base 上实现报名表，满足以下需求：

1. 统计填写人的姓名、学号。
2. 实时显示 A/B/C 三个子项的已报名人数。
3. 当任一子项报名人数达到 15 人后，自动停止该子项报名。

## 1. 先在 NJU Table 建好 Base 和数据表

在你的 Base 里创建一张表（默认表名：`报名表`），至少包含以下列：

- `姓名`（文本）
- `学号`（文本）
- `子项`（单选或文本，值为 `A`/`B`/`C`）

然后在 Base 的 API/Integration 页面生成 **Base API Token**（不是账号登录令牌）。

## 2. 本地启动

```bash
cd /workspaces/table
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

编辑 `.env`，至少填入：

- `SEATABLE_API_TOKEN`
- 如果你的表名/列名和默认不同，也要同步修改：
	- `SEATABLE_TABLE_NAME`
	- `COL_NAME`
	- `COL_STUDENT_ID`
	- `COL_ITEM`

启动服务：

```bash
python app.py
```

默认访问：`http://127.0.0.1:8080`

### 2.1 让其他人通过链接访问报名页面

**在 GitHub Codespaces 中：**
1. 打开底部 "PORTS" 面板
2. 找到 8080 端口，右键选择 "Port Visibility" → "Public"
3. 复制该端口的转发地址（类似 `https://xxx-8080.preview.app.github.dev`）
4. 把链接分享给报名者即可

**使用 ngrok（本地或其他环境）：**
```bash
# 注册 ngrok：https://dashboard.ngrok.com/signup
# 获取 authtoken 并配置：ngrok config add-authtoken <你的token>
bash start_with_ngrok.sh
```
ngrok 会生成一个公网链接（如 `https://abc123.ngrok.io`），直接分享即可。

## 3. 功能说明

- 页面会每 5 秒拉取一次 `/api/stats`，实时刷新 A/B/C 已报名人数。
- 提交时调用 `/api/submit`：
	- 必填校验：姓名、学号、子项。
	- 限额校验：子项人数达到 `ITEM_LIMIT`（默认 15）后拒绝报名。
	- 学号去重：同一学号不允许重复提交。
- 前端会把满员子项禁用并显示“已满，停止报名”。

## 4. 生产部署（gunicorn + systemd + nginx）

仓库已提供生产配置文件：

- `gunicorn.conf.py`
- `deploy/systemd/table-signup.service`
- `deploy/nginx/table-signup.conf`
- `deploy/env/table-signup.env.example`
- `deploy/deploy_prod.sh`

### 4.1 服务器一键安装

在 Ubuntu 服务器执行：

```bash
cd /opt
git clone <你的仓库地址> table
cd table
sudo bash deploy/deploy_prod.sh /opt/table
```

### 4.2 配置生产环境变量（含 API Token）

编辑：`/etc/table-signup.env`

至少确认：

- `SEATABLE_API_TOKEN=你的真实token`
- `SEATABLE_SERVER_URL=https://table.nju.edu.cn`
- `SEATABLE_TABLE_NAME` 与你的实际表名一致
- `COL_NAME` / `COL_STUDENT_ID` / `COL_ITEM` 与实际列名一致

重启服务：

```bash
sudo systemctl restart table-signup
sudo systemctl status table-signup --no-pager
```

### 4.3 检查服务

```bash
curl -s http://127.0.0.1:8080/healthz
curl -I http://服务器IP/
```

### 4.4 查看日志

```bash
sudo journalctl -u table-signup -f
sudo tail -f /var/log/nginx/access.log /var/log/nginx/error.log
```

## 5. 长期使用建议

如果要持续对外提供服务，推荐部署到独立服务器：
- 按"4. 生产部署"章节在服务器执行 `deploy_prod.sh`
- 配置域名 + HTTPS（用 `certbot`）
- 使用 `systemd` 自动重启，避免依赖 Codespaces/ngrok 临时会话

## 6. 安全建议

- 不要把真实 `SEATABLE_API_TOKEN` 写入 Git 仓库。
- 只在服务器的 `/etc/table-signup.env` 或本地 `.env` 中保存 token。
- 对外网开放时建议配置 HTTPS（可用 `certbot`）。
- 多进程（gunicorn workers > 1）或多实例部署时，**必须**配置 `REDIS_URL` 以启用分布式锁，否则并发提交可能导致超额。

## 7. Redis 分布式锁（多进程部署必读）

默认情况下，应用使用 `threading.Lock()` 保护提交逻辑，**仅在单进程内有效**。

生产环境推荐使用 gunicorn 多 worker（`gunicorn.conf.py` 默认 `workers = 2`），此时必须启用 Redis 分布式锁：

### 7.1 安装并启动 Redis

```bash
sudo apt-get install -y redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

### 7.2 配置 REDIS_URL

在 `/etc/table-signup.env`（或本地 `.env`）中添加：

```
REDIS_URL=redis://127.0.0.1:6379/0
REDIS_LOCK_KEY=table_signup_lock
REDIS_LOCK_TIMEOUT=10
```

重启服务后生效：

```bash
sudo systemctl restart table-signup
```

### 7.3 验证

启动日志中若无 "Redis 连接失败" 警告，则说明分布式锁已生效。若 Redis 不可用，应用会自动回退到本地锁，并在日志中打印警告。