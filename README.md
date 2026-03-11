# CAC 分享会报名系统

这是一个为 NJU CAC 社团分享会设计的报名和管理系统，基于 SeaTable 数据库。主要功能包括：

## ✨ 核心功能

### 0311 更新需求实现

1. **活动时间管理**
   - 时间档位从 30 分钟改为 **1 小时一档**
   - 配置灵活的时间槽（09:00-10:00, 10:00-11:00 等）
   - 便于教室管理和避免时间冲突

2. **旁听登记功能** ✨ NEW
   - 支持"评议员"和"旁听"两种角色
   - 旁听人数无限制，易于实现开放式分享

3. **自动计算拟参加人数** ✨ NEW
   - `拟参加人数 = 分享者数 + 旁听者数 + 3名评议员`
   - 动态更新，帮助主持人做准备工作
### 分享者自主管理** ✨ NEW
   - **分享者可自行创建活动**：访问 `/organizer` 创建和发布自己的分享会
   - **编辑活动信息**：更新日期、时间、教室等信息
   - **删除活动**：在有人报名前可删除活动
   - **简单身份验证**：输入学号即可管理自己的活动
### 隐患改进方案

1. **系统统计与预警** ✨ NEW
   - **消亡兴趣组检测**：统计活跃分享者数，发现无活动的兴趣组
   - **越界社员监控**：自动检测参与次数超过阈值的社员（默认10次）
   - 可视化展示在主页面

2. **未来优化方向**
   - 消息推送通知（集成钉钉/企业微信）
   - 教室预订状态集成
   - 时间冲突智能检测
   - 更细粒度的参与度分析

## 🔧 技术架构改进

原项目是简单的通用报名表，改造后支持：

- **两表设计**：分离"活动信息表"和"报名表"，各司其职
- **关联查询**：通过活动ID关联两表数据
- **灵活角色**：轻松扩展其他角色类型
- **自动统计**：后端计算，减轻前端负担

## 📋 数据表结构

### 活动信息表（`分享会活动`）

| 字段 | 类型 | 说明 |
|------|------|------|
| 活动日期 | 日期 | 分享会举办日期 |
| 活动时间 | 文本 | 时间段，如"10:00-11:00" |
| 分享者 | 文本 | 分享人姓名，支持多人（逗号分隔） |
| 活动主题 | 文本 | 分享主题 |
| 活动教室 | 文本 | 教室编号（后续确认） |
| 线上视频号 | 文本 | 腾讯会议/Zoom 号（选填） |

### 报名表（`分享会报名`）

| 字段 | 类型 | 说明 |
|------|------|------|
| 姓名 | 文本 | 报名者姓名 |
| 学号 | 文本 | 学号（去重） |
| 关联活动 | 链接 | 指向活动表的ID |
| 角色 | 单选 | "评议员" 或 "旁听" |
| 联系电话 | 电话 | 可选，便于通知 |

## 🚀 本地启动

### 1. 准备 SeaTable Base

在你的 Base 里创建两张表，对应上述结构。获取 **Base API Token**。

### 2. 配置环境

```bash
cd /path/to/table-signup
python3 -m venv .venv
source .venv/bin/activate  # 或 .venv\Scripts\activate (Windows)
pip install -r requirements.txt
cp .env.example .env
```

编辑 `.env` 至少填入：

```env
SEATABLE_API_TOKEN=你的base_api_token
SEATABLE_SERVER_URL=https://table.nju.edu.cn

# 表名（必须与 SeaTable 中的表名一致）
ACTIVITY_TABLE_NAME=分享会活动
SIGNUP_TABLE_NAME=分享会报名

# 列名（可选，默认如下）
ACTIVITY_COL_DATE=活动日期
ACTIVITY_COL_TIME=活动时间
ACTIVITY_COL_SPEAKERS=分享者
...

# 时间槽（小时为单位）
TIME_SLOTS=09:00,10:00,11:00,12:00,13:00,14:00,15:00,16:00,17:00,18:00,19:00,20:00,21:00,22:00
```

### 3. 启动服务

```bash
python app.py
# 访问 http://127.0.0.1:8080
```

## 📡 API 文档

### `GET /api/activities`

获取所有活动列表及实时报名统计。

**响应示例：**
```json
{
  "ok": true,
  "activities": [
    {
      "id": "xxx",
      "date": "2024-03-20",
      "time": "10:00-11:00",
      "speakers": "张三, 李四",
      "topic": "Python 异步编程",
      "classroom": "理科楼101",
      "videourl": "",
      "reviewers": 2,
      "listeners": 5,
      "expected_attendance": 10,
      "reviewer_full": false
    }
  ]
}
```

### `POST /api/signup`

提交报名（评议员或旁听）。

**请求：**
```json
{
  "name": "张三",
  "student_id": "PB20112233",
  "activity_id": "xxx",
  "role": "评议员",
  "phone": "13800138000"
}
```

**响应：**
```json
{
  "ok": true,
  "message": "评议员报名成功"
}
```

### `GET /api/stats`

获取全局统计和预警信息。

**响应示例：**
```json
{
  "ok": true,
  "inactive_groups": {
    "total_active_speakers": 5,
    "message": "当前有 5 个活跃的分享者/兴趣组"
  },
  "boundary_violations": {
    "warning_threshold": 10,
    "potential_violations": {
      "张三": 12,
      "李四": 11
    },
    "count": 2
  }
}
```

### 分享者管理 API ✨ NEW

#### `GET /api/my-activities/<student_id>`

获取某个分享者的活动列表。

**请求示例：**
```
GET /api/my-activities/PB20112233
```

**响应：**
```json
{
  "ok": true,
  "activities": [
    {
      "id": "xxx",
      "date": "2024-03-20",
      "time": "10:00-11:00",
      "speakers": "张三, 李四",
      "topic": "Python 异步编程",
      "classroom": "理科楼404",
      "creator_student_id": "PB20112233",
      "reviewers": 2,
      "listeners": 5,
      "expected_attendance": 10
    }
  ]
}
```

#### `POST /api/activity`

创建新活动（分享者）。

**请求：**
```json
{
  "date": "2024-03-20",
  "time": "10:00-11:00",
  "speakers": "张三, 李四",
  "topic": "Python 异步编程",
  "classroom": "理科楼404",
  "videourl": "https://meeting.tencent.com/...",
  "creator_student_id": "PB20112233"
}
```

**响应：**
```json
{
  "ok": true,
  "message": "活动创建成功"
}
```

#### `PUT /api/activity/<activity_id>`

编辑活动（仅限创建者）。

**请求：**
```json
{
  "creator_student_id": "PB20112233",
  "classroom": "理科楼505",
  "topic": "新的主题"
}
```

**响应：**
```json
{
  "ok": true,
  "message": "活动更新成功"
}
```

#### `DELETE /api/activity/<activity_id>`

删除活动（仅限创建者，且无报名时）。

**请求：**
```json
{
  "creator_student_id": "PB20112233"
}
```

**响应：**
```json
{
  "ok": true,
  "message": "活动删除成功"
}
```

## 🔐 生产部署

配置类似原项目，参考 `deploy/` 文件夹：

- `gunicorn.conf.py` – Gunicorn 配置
- `deploy/deploy_prod.sh` – 一键部署脚本
- `deploy/systemd/table-signup.service` – systemd 服务
- `deploy/nginx/table-signup.conf` – 反向代理配置

运行：
```bash
sudo bash deploy/deploy_prod.sh /opt/table
```

编辑 `/etc/table-signup.env` 配置生产环境变量。

## 📌 使用流程

### 分享者/兴趣组（创建活动） ✨ NEW

1. 打开链接：`https://yoursite.com/organizer`
2. **输入学号**进行身份验证（进入管理界面）
3. **"创建活动"标签页**填写：
   - 活动日期
   - 活动时间（1小时档位）
   - 分享者姓名（可多人）
   - 活动主题
   - 活动教室（可后续更新）
   - 线上视频号（可选）
4. **提交后**会出现在活动列表中
5. 社员可开始报名
6. **编辑/删除**：在"我的活动"列表中管理

### 社员（评议员或旁听）

1. 打开链接 → 浏览活动列表
2. 选中感兴趣的分享会
3. 选择角色（评议员/旁听）→ 填写信息 → 提交
4. 系统自动检查：
   - 评议员是否已满 3 人
   - 该学号是否已报名过该活动
5. 成功或失败信息提示，等待分享会

### CAC（监管者）

1. 定期访问主报名页面查看统计
2. 监控预警信息（消亡兴趣组、越界社员）
3. 若有必要，手动干预或发起讨论

## 🎯 隐患改进的技术方案总结

### 当前隐患与解决方案对应

| # | 隐患 | 改进方案 |
|----|------|--------|
| 1 | 分享者不及时发布内容 | 系统消息提醒（下一版） |
| 2 | 忘记借教室 | 教室预订集成、提醒通知 |
| 3 | 缺少消息推送 | 集成钉钉/企业微信通知 ✨ 规划中 |
| 4 | 低质量报名评议员 | 评议员评价机制（下一版） |
| 5 | 延迟症违规 | 参与度统计与分析面板 ✨ 已实现 |
| 6 | 分享时间超时 | 提醒机制、时间轴显示 |
| 7 | 活动时间冲突 | 冲突检测算法 ✨ 规划中 |
| 8 | 与 CAC 有约冲突 | 日历集成 |
| 9 | 缺少技术统计 | 越界社员检测算法 ✨ 已实现 |
| 10 | 消亡兴趣组难发现 | 活跃分享者统计 ✨ 已实现 |

**已实现** ✨ ：越界社员监控、消亡兴趣组检测  
**规划中** ：消息推送、冲突检测、时间提醒、教室集成

## 📄 许可证

基于原项目扩展，遵循相同许可证。
