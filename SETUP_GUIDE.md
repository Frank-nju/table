# CAC 分享会系统 - 快速开始指南

## 📖 概述

这个系统有三个角色：

1. **分享者/兴趣组（创建活动）**：在网站的"分享者管理"页面创建和编辑自己的活动
2. **社员（报名参加）**：在主报名页面选择活动，报名为评议员或旁听
3. **CAC（监管者）**：查看系统预警，监控社团健康度

本指南帮助你快速搭建和部署系统。

---

## 🚀 快速部署（5分钟）

### 步骤1：准备 SeaTable Base

1. 登录 `https://table.nju.edu.cn/`
2. 创建新 Base（名称任意）
3. 在该 Base 中创建两张表：

#### 表1：分享会活动

创建以下列（按顺序）：

| 列名 | 类型 | 说明 | 示例 |
|------|------|------|------|
| 活动日期 | 日期 | 活动举办日期 | 2024-03-15 |
| 活动时间 | 文本 | 时间段（小时为单位） | 10:00-11:00 |
| 分享者 | 文本 | 分享人姓名，多人用逗号分隔 | 张三, 李四 |
| 活动主题 | 文本 | 分享主题 | Python 异步编程 |
| 活动教室 | 文本 | 教室编号 | 理科楼404 |
| 线上视频号 | 文本 | 腾讯会议/Zoom 号（可选） | https://meeting.tencent.com/... |
| 组织者学号 | 文本 | 活动创建者的学号（权限控制） | PB20112233 |

#### 表2：分享会报名

创建以下列（按顺序）：

| 列名 | 类型 | 说明 | 示例 |
|------|------|------|------|
| 姓名 | 文本 | 报名者姓名 | 王五 |
| 学号 | 文本 | 学号（唯一） | PB20112233 |
| 关联活动 | 链接 | 链接到"分享会活动"表 | （自动链接） |
| 角色 | 单选 | 选项：评议员, 旁听 | 评议员 |
| 联系电话 | 电话 | 联系方式（可选） | 13800138000 |

### 步骤2：获取 API Token

1. 打开你创建的 Base
2. 左侧菜单 → **API与集成** （或 **Integration**）
3. 点击 **生成 API Token**（注意：是 Base Token，不是账号 Token）
4. 复制 Token

### 步骤3：配置服务

在服务器上运行：

```bash
# Linux/Mac
cd /opt/table-signup
cp .env.example .env

# 编辑 .env
nano .env
```

关键配置项：

```env
SEATABLE_API_TOKEN=<粘贴你的Token>
SEATABLE_SERVER_URL=https://table.nju.edu.cn

ACTIVITY_TABLE_NAME=分享会活动
SIGNUP_TABLE_NAME=分享会报名

# 保持表名与 SeaTable 中的完全一致！
```

### 步骤4：启动服务

```bash
# 本地测试
python app.py
# 访问 http://127.0.0.1:8080

# 生产部署
sudo bash deploy/deploy_prod.sh /opt/table-signup
```

---

## 📱 前端界面使用

### 分享者的工作流 ✨ NEW

1. **打开链接**：`https://yoursite.com/organizer`
2. **输入学号**进行身份验证
3. **在"创建活动"标签页填写**：
   - 活动日期
   - 活动时间（1小时档位：09:00-10:00等）
   - 分享者姓名（支持多人，逗号分隔）
   - 活动主题
   - 活动教室（可选，后续也可编辑更新）
   - 线上视频号（可选）
4. **点击"创建活动"**后会进入活动列表
5. **管理活动**：
   - 在"我的活动"标签页查看自己创建的活动
   - 点击"编辑"更新活动信息（如借到教室后更新教室号）
   - 点击"删除"移除活动（仅在无人报名时可删除）

### 社员的报名流程

1. **打开链接**
2. **左侧选择**感兴趣的分享会
3. **右侧表单填写**：
   - 姓名
   - 学号
   - 联系电话（可选）
   - 选择角色：**评议员**（3人限额）或 **旁听**（无限制）
4. **提交**
5. **看到成功提示**则报名完成

### 系统预警提示

主页面会实时显示：

- **拟参加人数**：= 分享者数 + 旁听者数 + 3名评议员
- **评议员报名情况**：0/3、1/3、2/3 或已满
- **旁听人数**：实时显示
- **系统预警**（页面下方）：
  - 🟡 消亡兴趣组：提醒参与度过低的兴趣组
  - 🔴 越界社员：提醒参与过度的社员（>10次）

---

## 🔧 常见问题

### Q1：为什么表格没有显示数据？

**A：** 检查以下几点：

1. **API Token 是否正确？**
   - 确认是 Base API Token（不是账号令牌）
   - 不要复制错了空格或特殊字符

2. **表名是否一致？**
   - `.env` 中的 `ACTIVITY_TABLE_NAME` 必须与 SeaTable 中的表名完全相同
   - 包括空格和大小写

3. **Token 权限？**
   - 确保 Token 有读写权限
   - 尝试重新生成一个新 Token

### Q2：报名成功但表里没有数据？

**A：** 检查"分享会报名"表的权限。API Token 必须对该表有写权限。

### Q3：为什么评议员超过3人还能报名？

**A：** 可能原因：

1. 页面没有刷新，加载的是旧数据
2. 多个人同时点击提交，没有防并发
3. 检查后端日志是否有报错

建议的解决：

```bash
# 查看实时日志
tail -f /var/log/table-signup.log
```

### Q4：如何统计某个时间段的活动？

**A：** 在 SeaTable 的"分享会活动"表中，使用"筛选"功能：

1. 点击列头的漏斗图标
2. 筛选日期范围
3. 导出为 CSV 或 Excel

或使用系统 API：

```bash
curl https://yoursite.com/api/activities
```

---

## 🛠 故障排查

### 日志检查

```bash
# 本地运行时
# 日志直接在终端输出

# 生产环境（systemd）
journalctl -u table-signup -f      # 实时日志
journalctl -u table-signup -n 100  # 最近100行日志

# 检查服务状态
systemctl status table-signup
```

### 常见错误信息

| 错误 | 原因 | 解决 |
|------|------|------|
| `SeaTable 认证失败` | Token 错误或无效 | 重新获取 Token |
| `活动不存在` | 活动 ID 无效 | 检查链接中的 activity_id |
| `学号已报名过该活动` | 重复报名 | 正常，系统防止重复 |
| `评议员已满，无法报名` | 评议员达到3人 | 只能改为旁听 |

### 数据库连接问题

```bash
# 测试连接
python3 -c "
from seatable_api import Base
import os
from dotenv import load_dotenv

load_dotenv()
base = Base(os.getenv('SEATABLE_API_TOKEN'), os.getenv('SEATABLE_SERVER_URL'))
base.auth()
print('连接成功')
"
```

---

## 📊 数据导出与统计

### 方案1：SeaTable 导出

在 SeaTable 界面：

1. 打开表格
2. 点击右上角 **⋮** → **导出**
3. 选择格式（CSV、Excel）
4. 下载文件

### 方案2：调用 API

```bash
# 获取所有活动
curl https://yoursite.com/api/activities | python -m json.tool

# 获取统计预警
curl https://yoursite.com/api/stats | python -m json.tool
```

### 方案3：自定义报表（规划中）

未来版本会支持：

```python
GET /api/export/monthly_report?month=2024-03
# 返回：月度活动统计、参与度分析、预警列表
```

---

## 🔐 安全建议

### 本地开发

```env
FLASK_DEBUG=true  # 仅在开发时启用
```

### 生产环境

```env
FLASK_DEBUG=false
# 配置 HTTPS（通过 nginx）
# 使用强密码和密钥管理
```

### API Token 安全

- ❌ 不要在代码/日志中暴露 Token
- ❌ 不要在 GitHub 上提交包含 Token 的 `.env` 文件
- ✅ 使用 `.gitignore` 排除 `.env`
- ✅ 定期更换 Token（如3个月一次）

---

## 📞 技术支持

有问题？

1. 查看本指南的**常见问题**和**故障排查**
2. 查看项目根目录的 [README.md](README.md)
3. 查看 [IMPROVEMENTS.md](IMPROVEMENTS.md) 了解未来功能
4. 联系 CAC 技术负责人

---

## ✅ 检查清单

启动前确认：

- [ ] 两张 SeaTable 表已创建，列名完全一致
- [ ] Base API Token 已获取（不是账号 Token）
- [ ] `.env` 文件已配置，Token 正确
- [ ] 服务可正常启动（无 Python 报错）
- [ ] 浏览器能访问 http://localhost:8080
- [ ] 表格能正常加载活动列表
- [ ] 可成功提交报名

---

**祝您使用愉快！** 🎉
