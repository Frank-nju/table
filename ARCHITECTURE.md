# 项目架构重构说明

## 新增模块结构

```
table-main/
├── app.py              # 主应用（待逐步迁移）
├── config.py           # 配置和常量 ✅ 新增
├── models/
│   ├── __init__.py     # 模型模块导出 ✅ 新增
│   └── database.py     # 数据库操作封装 ✅ 新增
├── routes/             # API 路由（待迁移）
├── services/
│   ├── __init__.py     # 服务模块导出 ✅ 新增
│   └── email.py        # 邮件服务 ✅ 新增
└── utils/
    └── __init__.py     # 异常处理工具 ✅ 已有
```

## 模块说明

### config.py
集中管理所有配置常量和环境变量，便于维护和测试。

```python
from config import ACTIVITY_TABLE_NAME, MYSQL_HOST
```

### models/database.py
封装所有数据库操作，提供统一的 CRUD 接口。

```python
from models import db

# 获取所有行
rows = db.list_rows("分享会活动")

# 新增行
row_id = db.append_row("分享会报名", {"姓名": "张三", "角色": "评议员"})

# 更新行
db.update_row("分享会报名", row_id, {"角色": "旁听"})

# 删除行
db.delete_row("分享会报名", row_id)
```

### services/email.py
封装邮件发送服务。

```python
from services import send_email, send_email_async

# 同步发送
send_email("user@example.com", "主题", "内容")

# 异步发送
send_email_async("user@example.com", "主题", "内容")
```

### utils/__init__.py
自定义异常类和响应工具。

```python
from utils import ValidationError, NotFoundError, success_response

# 抛出异常
raise ValidationError("姓名不能为空")

# 返回成功响应
return success_response({"id": "123"})
```

## 迁移进度

| 模块 | 状态 |
|------|------|
| config.py | ✅ 完成 |
| models/database.py | ✅ 完成 |
| services/email.py | ✅ 完成 |
| utils/__init__.py | ✅ 完成 |
| routes/ | ⏳ 待迁移 |

## 后续工作

1. 逐步将 API 路由迁移到 routes/ 目录
2. 改进异常处理，替换 `except Exception` 为具体异常类型
3. 添加单元测试