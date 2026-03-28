# CAC 分享会报名系统

面向社团活动的轻量管理系统，支持活动创建、报名、评议闭环和组织治理。

## 技术栈

| 层级 | 技术 |
|-----|------|
| 前端 | Vue 3 + Vite + Element Plus + Pinia |
| 后端 | Flask (模块化架构) |
| 数据库 | MySQL / SeaTable |
| 部署 | Gunicorn + Nginx |

## 项目结构

```
table-main/
├── app.py                 # Flask 主应用入口
├── config.py              # 配置常量
├── models/                # 数据模型层
│   ├── database.py        # 数据库操作封装
│   └── __init__.py
├── services/              # 业务逻辑层
│   ├── activity.py        # 活动业务
│   ├── signup.py          # 报名业务
│   ├── cac_admin.py       # CAC管理
│   ├── stats.py           # 统计服务
│   └── ...
├── routes/                # API 路由层
│   ├── activity.py        # 活动 API
│   ├── signup.py          # 报名 API
│   ├── cac.py             # CAC管理 API
│   └── ...
├── utils/                 # 工具函数
├── frontend/              # Vue 3 前端
│   ├── src/
│   │   ├── api/           # API 封装
│   │   ├── views/         # 页面组件
│   │   ├── stores/        # Pinia 状态
│   │   └── router/        # 路由配置
│   ├── dist/              # 构建产物
│   └── vite.config.js
├── templates/             # 旧版前端（已废弃）
├── deploy/                # 部署配置
└── tests/                 # 单元测试
```

## 功能模块

### 1. 活动管理
- 创建/编辑/删除活动
- 支持普通活动和 CAC有约 两种类型
- 时间选择（半小时一档，支持合并）
- 教室联动（自动查询可用教室）
- 冲突检测（同类型活动教室冲突强制拦截）

### 2. 报名系统
- 角色报名：评议员（限制3人）/ 旁听
- 评议员需提交评议内容方向
- 支持取消报名

### 3. CAC 管理
- CAC 管理员维护
- 教室时间槽预设
- 时间槽状态追踪（可用/已预约）

### 4. 治理看板
- 分享/参与排行榜
- 边界预警（成员活跃度）
- 时间冲突检测报告

### 5. 个人中心
- 个人信息展示
- 我的报名记录
- 我的邀请记录

## 快速启动

### 1. 后端

```bash
# 安装依赖
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 配置数据库连接

# 启动服务
python app.py
```

后端运行在 `http://localhost:8080`

### 2. 前端

```bash
cd frontend
npm install
npm run dev
```

前端运行在 `http://localhost:5173`，自动代理到后端。

### 3. 生产构建

```bash
cd frontend
npm run build
```

构建产物在 `frontend/dist/`，由后端提供静态文件服务。

## 环境配置

### 必要配置

```env
# 数据库
DB_BACKEND=mysql
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=table_user
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=table_signup
```

### 可选配置

```env
# 邮件通知
SMTP_HOST=smtp.example.com
SMTP_USER=noreply@example.com
SMTP_PASSWORD=***

# CAC有约配置
CAC_FIXED_WEEKDAY=6      # 周日 = 6
CAC_FIXED_TIME=14:00-18:00
```

## API 概览

### 活动
| 方法 | 路径 | 说明 |
|-----|------|------|
| GET | `/api/activities` | 活动列表 |
| GET | `/api/activity/<id>` | 活动详情 |
| POST | `/api/activity` | 创建活动 |
| PUT | `/api/activity/<id>` | 编辑活动 |
| DELETE | `/api/activity/<id>` | 删除活动 |
| POST | `/api/activity/<id>/close` | 结项活动 |

### 报名
| 方法 | 路径 | 说明 |
|-----|------|------|
| POST | `/api/signup` | 创建报名 |
| DELETE | `/api/signup/<id>` | 取消报名 |
| GET | `/api/my-signups/<name>` | 我的报名 |

### CAC 管理
| 方法 | 路径 | 说明 |
|-----|------|------|
| GET | `/api/cac-admins` | 管理员列表 |
| POST | `/api/cac-admin` | 添加管理员 |
| DELETE | `/api/cac-admin/<name>` | 移除管理员 |
| GET | `/api/cac-room-slots` | 时间槽列表 |
| POST | `/api/cac-room-slot` | 添加时间槽 |
| DELETE | `/api/cac-room-slot/<id>` | 删除时间槽 |

### 统计
| 方法 | 路径 | 说明 |
|-----|------|------|
| GET | `/api/stats` | 统计数据 |
| GET | `/api/leaderboards` | 排行榜 |

## 页面路由

| 路径 | 页面 | 说明 |
|-----|------|------|
| `/` | Home | 首页、活动列表、排行榜 |
| `/activity/:id` | ActivityDetail | 活动详情、报名表单 |
| `/admin` | Admin | 管理后台 |
| `/profile` | Profile | 个人中心 |

## 冲突检测规则

| 场景 | 行为 |
|-----|------|
| 同类型活动 + 同教室 + 时间重叠 | 🚫 强制拦截 |
| 不同类型活动 + 同教室 + 时间重叠 | ⚠️ 仅警告 |
| 时间重叠（无教室冲突） | ⚠️ 仅警告 |

## 数据表

系统自动管理以下逻辑表：

| 表名 | 说明 |
|-----|------|
| 分享会活动 | 活动信息 |
| 分享会报名 | 报名记录 |
| CAC管理员 | 管理员名单 |
| CAC教室时间槽 | 预设时间槽 |
| 评议评分 | 评分记录 |
| 用户档案 | 用户信息 |
| 兴趣组 | 兴趣组信息 |
| 兴趣组成员 | 成员关系 |
| 评议邀请 | 邀请记录 |

## 文档

| 文件 | 说明 |
|-----|------|
| [SETUP_GUIDE.md](SETUP_GUIDE.md) | 部署验收手册 |
| [CHANGELOG.md](CHANGELOG.md) | 版本变更记录 |
| [frontend/VUE_DEV_GUIDE.md](frontend/VUE_DEV_GUIDE.md) | 前端开发规范 |
| [deploy/DEPLOY_WINDOWS.md](deploy/DEPLOY_WINDOWS.md) | Windows 部署指南 |

## 开发命令

```bash
# 后端开发
python app.py              # 启动开发服务器

# 前端开发
cd frontend
npm run dev                # 启动开发服务器
npm run build              # 构建生产版本

# 测试
python tests/test_modules.py

# 代码检查
pylint app.py services/ routes/
```

## 更新部署

```bash
# 拉取代码
git pull

# 更新依赖
pip install -r requirements.txt
cd frontend && npm install

# 构建前端
npm run build

# 重启后端
ps aux | grep python | grep -v grep | awk '{print $1}' | xargs -r kill -9
python app.py &
```

**数据完全兼容**：代码更新不影响数据库中的数据，表名和列名未变化。

## 许可证

本项目未附加开源许可证。