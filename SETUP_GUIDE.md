# 部署与验收手册（SETUP GUIDE）

本文档用于把项目从 0 搭起来，并完成一次最小可用验收。

## 1. 前置条件

- Linux 服务器（Ubuntu 22.04+/24.04 推荐）
- Python 3.10+
- 可访问 SeaTable 服务
- 已准备 SeaTable Base API Token（不是账号 Token）

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
SEATABLE_SERVER_URL=https://table.nju.edu.cn
SEATABLE_API_TOKEN=your_base_api_token
```

然后确认以下内容与 SeaTable 完全一致：

- 表名（如 `分享会活动`、`分享会报名`、`评议评分` 等）
- 字段名（如 `活动日期`、`评议语雀链接`、`组名` 等）

如果你使用了自定义列名，请同步修改 `.env` 对应变量。

## 4. 准备 SeaTable 数据表

建议至少存在以下表：

- `分享会活动`
- `分享会报名`
- `评议评分`
- `输出活动记录`
- `用户档案`
- `兴趣组`
- `兴趣组成员`
- `评议邀请`

提示：

- 系统有 `POST /api/admin/init-phase1-schema` 可尝试补齐一期缺失列
- 若列名差异较大，仍建议手工检查并对齐 `.env`

## 5. 本地运行

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

- SeaTable 对应表有新增行
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

1. `SeaTable 认证失败`
原因：Token 错误或权限不足。
处理：确认使用 Base Token，并具有读写权限。

2. 某接口 400/500
原因：表名或字段名不匹配。
处理：逐项核对 `.env` 与 SeaTable 列名。

3. 看板无数据
原因：源表为空，或统计窗口内没有符合条件的数据。
处理：先写入测试数据，再查看统计结果。

## 9. 演示环境建议

- 使用独立 SeaTable Base 做演示
- 批量造数时加统一标记（例如 `[MVPTEST-YYYYMMDD]`）
- 演示后按标记回收，保持生产库干净

## 10. 安全建议

- `.env` 不要入库
- 定期轮换 `SEATABLE_API_TOKEN`
- 生产环境通过 Nginx 提供 HTTPS
- 邮件配置仅在需要时开启
