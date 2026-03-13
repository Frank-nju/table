# 部署与验收手册（SETUP GUIDE）

本文档用于把项目从 0 搭起来，并完成一次最小可用验收。

## 1. 前置条件

- Linux 服务器（Ubuntu 22.04+/24.04 推荐）
- Python 3.10+
- 可访问 MySQL 8.0+ 数据库
- 数据库账号具备建库建表与读写权限

## 2. 拉取代码并安装依赖

```bash
git clone <your-repo-url> table
cd table
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. 配置环境变量

```bash
cp .env.example .env
```

重点配置：

```env
DB_BACKEND=mysql
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=table_user
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=table_signup
```

然后确认以下逻辑表名与字段名配置正确：

- 表名（如 `分享会活动`、`分享会报名`、`评议评分` 等）
- 字段名（如 `活动日期`、`评议语雀链接`、`组名` 等）

如果你使用了自定义列名，请同步修改 `.env` 对应变量。

名单文件请使用本地私有文件：

- 复制 `member_roster.example.txt` 为 `member_roster.local.txt`
- 在 `.env` 中设置 `ROSTER_FILE_PATH=./member_roster.local.txt`
- `member_roster.local.txt` 已被 `.gitignore` 忽略，不会进入仓库

## 4. 准备数据库

应用首次启动会自动创建物理表：

- `app_rows`
- `app_table_columns`

系统默认逻辑表名：

- `分享会活动`
- `分享会报名`
- `评议评分`
- `输出活动记录`
- `用户档案`
- `兴趣组`
- `兴趣组成员`
- `评议邀请`

提示：

- 系统有 `POST /api/admin/init-phase1-schema` 可补齐一期缺失列元数据
- 若列名差异较大，仍建议手工检查并对齐 `.env`

## 5. 本地运行

如果你已有 SeaTable 历史数据，先执行一次迁移：

```bash
python scripts/migrate_seatable_to_mysql.py
```

再启动服务：

```bash
python app.py
```

默认监听：`0.0.0.0:8080`

访问：

- 首页：`http://127.0.0.1:8080/`
- 分享者管理：`http://127.0.0.1:8080/organizer`
- 个人工作台：`http://127.0.0.1:8080/profile`

## 6. 最小验收（建议 5 分钟）

### 6.1 接口冒烟

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8080/
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8080/organizer
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8080/profile
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8080/api/activities
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8080/api/admin/dashboard
```

预期：全部 `200`。

### 6.2 页面验收

- 首页可看到活动列表、报名表单、新手规则说明
- `/organizer` 可创建活动并看到治理看板
- `/profile` 可加载个人摘要、任务与推荐

### 6.3 数据验收

- MySQL 的 `app_rows` 中有新增记录
- 报名后可在 `我的报名` 查看并取消
- 评议员可提交文档链接并进入评分流程

## 7. 生产部署（systemd + Nginx）

项目自带一键部署脚本：

```bash
sudo bash deploy/deploy_prod.sh /opt/table
```

部署后：

```bash
sudo vim /etc/table-signup.env
sudo systemctl restart table-signup
sudo systemctl status table-signup --no-pager
sudo nginx -t
```

## 8. 运维与排障

### 查看服务日志

```bash
journalctl -u table-signup -f
```

### 常见问题

1. `MySQL 连接失败`
原因：连接参数错误、端口不可达或账号权限不足。
处理：核对 `MYSQL_*` 配置，确认数据库账号权限。

2. 某接口 400/500
原因：逻辑表名或字段名不匹配。
处理：逐项核对 `.env` 业务表/字段配置。

3. 看板无数据
原因：源表为空，或统计窗口内没有符合条件的数据。
处理：先写入测试数据，再查看统计结果。

## 9. 演示环境建议

- 使用独立 MySQL 测试库做演示
- 批量造数时加统一标记（例如 `[MVPTEST-YYYYMMDD]`）
- 演示后按标记回收，保持生产库干净

## 10. 安全建议

- `.env` 不要入库
- 定期轮换数据库账号密码
- 生产环境通过 Nginx 提供 HTTPS
- 邮件配置仅在需要时开启
