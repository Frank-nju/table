# CAC 分享会系统（SeaTable 驱动）

面向社团活动的轻量管理系统，支持三类入口：

- 首页报名：`/`
- 分享者工作台：`/organizer`
- 个人工作台：`/profile`

系统以 SeaTable 作为主数据库，后端为 Flask，前端为原生 HTML + JavaScript，适合在校内服务器快速部署和持续迭代。

## 功能总览

### 1. 活动与报名

- 活动创建、编辑、删除、结项
- 支持 `normal` 与 `cac有约` 两类活动
- 角色报名：评议员 / 旁听 / 参与者（按活动类型约束）
- 评议员名额限制、旁听可放开

### 2. 评议闭环

- 评议员可提交评议文档链接（语雀等）
- 评议文档可被他人评分
- 自动汇总评议质量、评分数量、待交文档预警

### 3. 组织治理

- 治理看板（`/organizer`）聚合：
  - 月报
  - 兴趣组健康度
  - 评议质量预警
  - 边界预警
  - 时间冲突检测
- 支持兴趣组、兴趣组成员、评议邀请等管理能力

### 4. 个人工作台

- 个人战绩汇总、动态流、探索活动
- 待办任务聚合（邀请处理、补交评议、结项等）
- 推荐活动与快速报名

## 技术架构

- 后端：Flask
- 数据层：SeaTable API
- 模板：Jinja2
- 部署：Gunicorn + systemd + Nginx（见 `deploy/`）

关键文件：

- `app.py`：核心业务与 API
- `templates/index.html`：首页
- `templates/organizer.html`：分享者与治理看板
- `templates/profile.html`：个人工作台

## 快速启动（本地）

### 1. 安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

至少确保以下配置正确：

- `SEATABLE_SERVER_URL`
- `SEATABLE_API_TOKEN`
- 各表名和字段名（需与 SeaTable 完全一致）

### 3. 启动服务

```bash
python app.py
```

默认访问：`http://127.0.0.1:8080`

健康检查：`GET /healthz`

## 生产部署

项目内置部署模板：

- `deploy/deploy_prod.sh`
- `deploy/systemd/table-signup.service`
- `deploy/nginx/table-signup.conf`
- `deploy/env/table-signup.env.example`

典型流程：

```bash
sudo bash deploy/deploy_prod.sh /opt/table
sudo vim /etc/table-signup.env
sudo systemctl restart table-signup
sudo systemctl status table-signup --no-pager
```

## SeaTable 数据表（建议）

系统默认使用以下表：

- `分享会活动`
- `分享会报名`
- `评议评分`
- `输出活动记录`
- `用户档案`
- `兴趣组`
- `兴趣组成员`
- `评议邀请`

注意：字段名可通过环境变量覆盖，但必须与实际 SeaTable 列名对应。

## 主要页面

- `/`：报名与我的报名/邀请、榜单与预警
- `/organizer`：创建活动、管理活动、治理看板
- `/profile`：个人画像、任务、推荐、探索与动态

## 主要 API（按模块）

### 基础

- `GET /healthz`
- `GET /api/activities`
- `GET /api/activities/filter`
- `GET /api/activity/<activity_id>`

### 报名与评议

- `POST /api/signup`
- `GET /api/my-signups/<name>`
- `DELETE /api/signup/<signup_id>`
- `POST /api/signup/<signup_id>/review-doc`
- `POST /api/review-rating`
- `GET /api/reviewer-submitted-docs`

### 分享者与活动管理

- `GET /api/my-activities/<name>`
- `POST /api/activity`
- `PUT /api/activity/<activity_id>`
- `POST /api/activity/<activity_id>/close`
- `DELETE /api/activity/<activity_id>`
- `POST /api/output-record`

### 兴趣组与邀请

- `GET /api/groups`
- `GET /api/group/<group_id>`
- `GET /api/my-groups/<name>`
- `POST /api/group`
- `POST /api/group/<group_id>/join`
- `POST /api/group/<group_id>/leave`
- `POST /api/invite-reviewer`
- `GET /api/activity/<activity_id>/invites`
- `GET /api/my-invites/<name>`
- `POST /api/invite/<invite_id>/status`

### 治理与个人工作台

- `GET /api/stats`
- `GET /api/leaderboards`
- `GET /api/admin/dashboard`
- `POST /api/admin/init-phase1-schema`
- `POST /api/profile/upsert`
- `GET /api/profile/<name>`
- `GET /api/profile-summary/<name>`
- `GET /api/profile-feed/<name>`
- `GET /api/profile-tasks/<name>`
- `GET /api/profile-recommendations/<name>`

## 开发约定

- 所有写操作在成功后会触发内部缓存版本更新
- 部分读接口带短 TTL 缓存，减少 SeaTable 访问压力
- 前端不引入框架，优先保持可读与低维护成本

## 测试数据策略

- 建议直接写入 SeaTable 测试库，而非本地文件
- 通过统一标记（例如 `[MVPTEST-YYYYMMDD]`）隔离测试数据
- 演示后按标记回收，避免污染长期统计

## 文档目录

- `README.md`：项目总览、架构、部署与 API 总入口（本文件）
- `SETUP_GUIDE.md`：从 0 到可运行的操作手册
- `CHANGELOG.md`：版本与重要变更记录

## 许可与说明

本仓库当前未显式附加开源许可证；如需公开发布，建议补充 LICENSE 与贡献指南。
