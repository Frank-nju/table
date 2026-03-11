# CAC 分享会系统 - 未来改进方案

本文档详细说明了系统下一步的优化方向，用于解决"当前隐患"中的各项问题。

## 📋 隐患汇总与优化优先级

### 第一阶段（高优先级）：消息推送与通知

**关联隐患**：

- 隐患 #1：分享者不及时发布内容导致后续混乱
- 隐患 #2：忘记借教室
- 隐患 #3：全体社员需要不断访问链接获取信息

**改进方案**：

实现集成式消息推送系统，扩展现有API支持：

```python
# app.py 新增模块
class NotificationService:
    """支持多渠道消息推送"""
    
    def send_to_dingtalk(self, activity_id, message_type):
        """
        推送到钉钉
        message_type: 
            - 'activity_created': 新活动发布
            - 'reviewer_full': 评议员已满
            - 'activity_today': 今日活动提醒
            - 'boundary_warning': 越界社员警告
        """
        pass
    
    def send_to_wechat(self, activity_id, message_type):
        """企业微信推送"""
        pass
    
    def send_email(self, activity_id, message_type):
        """邮件推送"""
        pass

# 触发点：
# - POST /api/signup 成功后 → 通知评议员招募状态
# - 定时任务每晚8点 → 通知明天的活动
# - 越界检测时 → 通知相关人员
```

**环境配置示例**：

```env
# 钉钉配置
DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=xxx
DINGTALK_ENABLED=true

# 企业微信配置
WECHAT_CORP_ID=ww123456789
WECHAT_APP_ID=1000001
WECHAT_APP_SECRET=secret_here
WECHAT_ENABLED=false

# 邮件配置
SMTP_SERVER=mail.nju.edu.cn
SMTP_PORT=587
SMTP_USER=cac@nju.edu.cn
SMTP_PASSWORD=xxx
MAIL_ENABLED=false
```

---

### 第二阶段（中优先级）：教室集成与冲突检测

**关联隐患**：

- 隐患 #6：分享时间控不住，侵占后续教室
- 隐患 #7：活动时间冲突，想听的内容同时间
- 隐患 #8：分享活动与CAC有约冲突

**改进方案**：

1. **教室预订数据同步**

```python
class ClassroomIntegration:
    """与校内教室预订系统集成"""
    
    def fetch_bookings(self, classroom_id, date):
        """获取指定教室指定日期的预订情况"""
        # 调用校内API或数据库
        pass
    
    def check_availability(self, classroom_id, time_slot):
        """检查时间槽是否可用"""
        # 返回 (available, next_booking_time)
        pass
    
    def auto_suggest_classroom(self, activity_id, date, time_slot):
        """根据时间推荐可用教室"""
        pass
```

2. **时间冲突检测**

```python
def detect_time_conflicts(activities_list):
    """检测活动之间的时间冲突"""
    conflicts = []
    
    for i, act1 in enumerate(activities_list):
        for act2 in activities_list[i+1:]:
            if act1['date'] == act2['date']:
                if times_overlap(act1['time'], act2['time']):
                    conflicts.append({
                        'activity1': act1['id'],
                        'activity2': act2['id'],
                        'overlap_time': calculate_overlap(act1['time'], act2['time'])
                    })
    
    return conflicts
```

3. **CAC有约冲突检测**

```python
def check_cac_conflict(activity_date, activity_time):
    """
    检查是否与CAC有约活动时间冲突
    
    CAC有约：周五 18:00-19:00固定时间
    """
    if activity_date.weekday() == 4:  # 周五
        cac_fixed_time = ('18:00', '19:00')
        if times_overlap(activity_time, cac_fixed_time):
            return True, "与CAC有约冲突，请联系CAC"
    return False, None
```

---

### 第三阶段（低优先级）：参与度分析与预警

**关联隐患**：

- 隐患 #4：低质量报名评议员
- 隐患 #5：延迟症导致违规
- 隐患 #9：缺少技术统计
- 隐患 #10：缺少消亡兴趣组发现

**改进方案**（已基本实现检测，待完善分析）：

1. **详细参与度分析**

```python
class ParticipationAnalytics:
    """参与度深度分析"""
    
    def get_member_statistics(self, member_name):
        """获取成员的详细参与数据"""
        return {
            'total_participations': 12,
            'reviewer_count': 5,
            'listener_count': 7,
            'participation_timeline': [
                {'date': '2024-03-01', 'role': 'reviewer', 'activity': 'xxx'},
                # ...
            ],
            'average_review_quality': 3.8,  # 同侪评分
            'attendance_rate': 0.95,  # 实到率
            'violation_risk': 'high',  # 'low'/'medium'/'high'
        }
    
    def get_group_health_score(self, group_name):
        """获取兴趣组健康度评分"""
        return {
            'name': '计算机组',
            'active_members': 12,
            'recent_activities': 3,
            'health_score': 0.78,  # 0-1
            'status': 'healthy',  # 'healthy'/'at_risk'/'inactive'
            'recommendations': [
                '最近2周没有分享活动，建议组织分享',
                '核心成员参与度下降，需要激励',
            ]
        }
    
    def generate_monthly_report(self):
        """生成月度统计报告"""
        return {
            'period': '2024-03',
            'total_activities': 8,
            'total_participations': 120,
            'active_members': 45,
            'violation_members': {
                '张三': {'violations': 2, 'reason': 'over_participation'},
                '李四': {'violations': 1, 'reason': 'absence'},
            },
            'inactive_groups': ['AI组', '数据库组'],
            'recommendations': [...]
        }
```

2. **评议员质量评分系统**

```python
class ReviewerQualitySystem:
    """评议员质量评估"""
    
    def record_review_feedback(self, activity_id, reviewer_id, feedback):
        """记录评议反馈"""
        pass
    
    def calculate_reviewer_score(self, reviewer_id):
        """计算评议员综合评分"""
        # 基于：参与次数、评议深度、出席率、反馈评分
        pass
    
    def flag_low_quality_reviewers(self, activity_id):
        """标记该活动中的低质量评议员"""
        # 返回预警列表，供CAC人工审核
        pass
```

---

### 第四阶段（可选）：用户体验优化

**改进方案**：

1. **日历视图**

```html
<!-- 添加日历视图显示活动时间表 -->
<div class="calendar-view">
  <!-- 显示一周/一月的活动安排 -->
  <!-- 彩色块表示不同兴趣组 -->
  <!-- 点击显示详情 -->
</div>
```

2. **活动日志与评论**

```python
class ActivityLog:
    """活动实际发生后的反馈与总结"""
    
    def record_completion(self, activity_id, actual_duration, notes):
        """记录活动实际进行情况"""
        pass
    
    def get_activity_reviews(self, activity_id):
        """获取参与者对该活动的评价"""
        pass
```

3. **导出与分享**

```python
@app.get("/api/export/report")
def export_report():
    """导出月度或年度报告"""
    # 支持 PDF、Excel 格式
    pass

@app.get("/api/export/calendar")
def export_calendar():
    """导出为日历文件 (.ics)"""
    pass
```

---

## 🔧 技术栈建议

### 消息推送

- **钉钉集成**：`dingtalk-sdk-python`
- **企业微信**：`wechat-sdk-python`
- **定时任务**：`APScheduler`

### 教室数据

- 需与校内系统对接（具体方式待确认）
- 建议缓存教室数据，定期同步

### 数据分析

- **报表生成**：`pandas`, `openpyxl`
- **数据可视化**：前端使用 `Chart.js` 或 `ECharts`

---

## 📅 实现时间表建议

| 阶段 | 功能 | 工作量 | 时间 |
|------|------|--------|------|
| 1 | 钉钉通知集成 | 中 | 1-2 周 |
| 1 | 邮件/短信通知 | 小 | 1 周 |
| 2 | 教室数据对接 | 大 | 2-3 周 |
| 2 | 时间冲突检测 | 中 | 1 周 |
| 3 | 参与度分析面板 | 中 | 1-2 周 |
| 3 | 评议员质量评分 | 中 | 1-2 周 |
| 4 | 日历与导出功能 | 小 | 1 周 |

---

## 🎯 实现建议

1. **模块化设计**
   - 每个功能独立实现为 Python 类
   - 易于测试和维护

2. **环境配置管理**
   - 使用 `.env` 文件管理所有密钥和URL
   - 生产和开发环境分离

3. **数据库设计**
   - 考虑在 SeaTable 额外增加"反馈表"和"日志表"
   - 便于后续的数据分析

4. **前端增强**
   - 使用 Vue 或 React 改造前端，支持动态加载
   - 添加图表展示统计数据

---

## 💡 长期优化方向

- **人工智能辅助**：根据参与历史推荐感兴趣的活动
- **移动APP**：提升用户体验
- **社区评分系统**：鼓励高质量分享与评议
- **论文发表激励机制**：追踪分享话题演变成学术成果
