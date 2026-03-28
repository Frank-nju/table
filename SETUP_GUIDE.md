# 部署与验收手册

本文档用于把项目从 0 搭起来，并完成一次最小可用验收。

## 1. 前置条件

- 服务器（Linux 推荐 Ubuntu 22.04+，或 Windows Server）
- Python 3.10+
- Node.js 18+（用于前端构建）
- MySQL 8.0+ 数据库

## 2. 拉取代码并安装依赖

### Linux/Mac

```bash
git clone <your-repo-url> table
cd table

# 后端依赖
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 前端依赖
cd frontend
npm install
```

### Windows

```cmd
git clone <your-repo-url> table
cd table

# 后端依赖
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 前端依赖
cd frontend
npm install
```

## 3. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`：

```env
# 数据库（必填）
DB_BACKEND=mysql
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=table_user
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=table_signup

# 邮件通知（可选）
SMTP_HOST=smtp.example.com
SMTP_USER=noreply@example.com
SMTP_PASSWORD=***
```

## 4. 准备数据库

在 MySQL 中创建数据库：

```sql
CREATE DATABASE table_signup CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'table_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON table_signup.* TO 'table_user'@'localhost';
FLUSH PRIVILEGES;
```

应用首次启动会自动创建所需的物理表（`app_rows`、`app_table_columns`）。

## 5. 构建前端

```bash
cd frontend
npm run build
```

构建产物在 `frontend/dist/`，由后端自动提供静态文件服务。

## 6. 启动服务

### 开发模式

```bash
# 终端1：启动后端
python app.py

# 终端2：启动前端开发服务器
cd frontend
npm run dev
```

- 后端：http://localhost:8080
- 前端开发：http://localhost:5173（自动代理到后端）

### 生产模式

```bash
# 前端已构建，直接启动后端
python app.py
```

访问：http://localhost:8080

## 7. 最小验收

### 7.1 接口冒烟

```bash
curl -s http://localhost:8080/api/activities
curl -s http://localhost:8080/api/stats
curl -s http://localhost:8080/api/cac-admins
```

预期：返回 `{"ok": true, ...}`

### 7.2 页面验收

| 页面 | URL | 验收点 |
|-----|-----|--------|
| 首页 | `/` | 活动列表、排行榜显示 |
| 管理后台 | `/admin` | 三个标签页可切换、创建活动弹窗正常 |
| 个人中心 | `/profile` | 登录提示或个人信息显示 |

### 7.3 功能验收

- [ ] 创建活动（选择时间、教室）
- [ ] 查看活动详情
- [ ] 提交报名
- [ ] 管理后台添加 CAC 管理员
- [ ] 管理后台添加教室时间槽

## 8. 生产部署

### Linux (systemd + Nginx)

项目自带部署模板：

```bash
sudo bash deploy/deploy_prod.sh /opt/table
sudo vim /etc/table-signup.env
sudo systemctl restart table-signup
```

### Windows Server

参考 [deploy/DEPLOY_WINDOWS.md](deploy/DEPLOY_WINDOWS.md)

### Docker（可选）

```bash
docker build -t cac-signup .
docker run -d -p 8080:8080 --env-file .env cac-signup
```

## 9. 更新部署

```bash
# 拉取代码
git pull

# 更新后端依赖
source .venv/bin/activate
pip install -r requirements.txt

# 更新前端依赖并构建
cd frontend
npm install
npm run build

# 重启服务
sudo systemctl restart table-signup  # Linux
# 或手动重启 python app.py
```

**重要**：更新代码不会影响数据库中的数据，表名和列名保持兼容。

## 10. 运维排障

### 查看日志

```bash
# Linux
journalctl -u table-signup -f

# 直接运行时查看控制台输出
```

### 常见问题

| 问题 | 原因 | 解决 |
|-----|------|------|
| 前端页面空白 | 未构建前端 | `cd frontend && npm run build` |
| API 500 错误 | 数据库连接失败 | 检查 `.env` 中的 MYSQL_* 配置 |
| 页面样式异常 | 静态文件未加载 | 检查 `frontend/dist/` 是否存在 |
| 创建活动失败 | 缺少必填字段 | 检查请求参数是否完整 |

## 11. 安全建议

- `.env` 不要提交到代码仓库
- 定期轮换数据库密码
- 生产环境启用 HTTPS
- 邮件配置仅在需要时开启