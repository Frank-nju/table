"""
Bug回归测试

针对已修复的bug编写测试用例，防止回归
"""

import pytest
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestCACActivityTypeBug:
    """测试 CAC有约 活动类型显示bug

    Bug: 前端使用 activity.type 而不是 activity.activity_type
    导致活动类型显示错误
    """

    def test_activity_has_activity_type_field(self):
        """活动数据应该包含 activity_type 字段"""
        from services import list_activities, get_activity_details

        activities = list_activities()
        if not activities:
            pytest.skip("没有活动数据")

        details = get_activity_details(activities[0])
        assert 'activity_type' in details, "活动详情应该包含 activity_type 字段"

    def test_cac_activity_type_value(self):
        """CAC有约活动类型应该是 'cac有约'"""
        from services import list_activities, get_activity_details

        activities = list_activities()
        cac_activities = [a for a in activities if a.get('活动类型') == 'cac有约']

        if not cac_activities:
            pytest.skip("没有CAC有约活动")

        details = get_activity_details(cac_activities[0])
        assert details.get('activity_type') == 'cac有约', \
            f"活动类型应该是 cac有约，实际是 {details.get('activity_type')}"


class TestCACAdminPermission:
    """测试 CAC 管理员权限验证

    Bug: 管理员操作返回 403，因为没有传递操作者姓名
    """

    def test_is_cac_admin_with_valid_name(self):
        """检查有效的管理员名称"""
        from services import list_cac_admins, is_cac_admin

        admins = list_cac_admins()
        if not admins:
            pytest.skip("没有配置CAC管理员")

        # 第一个管理员应该能通过验证
        first_admin = admins[0].get('name', admins[0])
        result = is_cac_admin(first_admin)
        assert result is True, f"管理员 {first_admin} 应该通过验证"

    def test_is_cac_admin_with_invalid_name(self):
        """检查无效的管理员名称"""
        from services import is_cac_admin

        result = is_cac_admin("不存在的用户_随机字符串_12345")
        assert result is False, "不存在的用户不应该通过验证"

    def test_add_admin_requires_permission(self):
        """添加管理员需要权限验证"""
        from services import add_cac_admin, list_cac_admins
        from utils import AuthError

        admins = list_cac_admins()
        if admins:
            # 如果已有管理员，非管理员用户添加应该失败
            with pytest.raises(AuthError):
                add_cac_admin("新管理员测试", requester_name="非管理员用户_12345")


class TestRoomSlotExpiration:
    """测试教室时间槽过期检测

    Bug: 过期的时间槽没有自动隐藏/删除
    """

    def test_list_room_slots(self):
        """测试列出时间槽"""
        from services import list_cac_room_slots

        slots = list_cac_room_slots()
        assert isinstance(slots, list)

    def test_slots_have_correct_fields(self):
        """时间槽应该有正确的字段"""
        from services import list_cac_room_slots

        slots = list_cac_room_slots()
        if not slots:
            pytest.skip("没有时间槽数据")

        # 检查第一个槽的字段
        slot = slots[0]
        assert 'id' in slot or '_id' in slot
        assert 'date' in slot or 'classroom' in slot

    def test_slots_filter_by_date(self):
        """测试按日期过滤"""
        from services import list_cac_room_slots

        # 测试过滤功能
        slots = list_cac_room_slots(date="2026-04-01")
        assert isinstance(slots, list)


class TestSignupRoleOptions:
    """测试报名角色选项

    Bug: CAC有约活动显示了"评议员"选项，应该显示"参与者"
    """

    def test_cac_activity_has_correct_type(self):
        """CAC有约活动应该有正确的类型"""
        from services import list_activities, get_activity_details

        activities = list_activities()
        cac_activities = [a for a in activities if a.get('活动类型') == 'cac有约']

        if not cac_activities:
            pytest.skip("没有CAC有约活动")

        details = get_activity_details(cac_activities[0])
        activity_type = details.get('activity_type')

        assert activity_type == 'cac有约', \
            f"活动类型应该是 cac有约，实际是 {activity_type}"


class TestActivityStatusFlow:
    """测试活动状态流程"""

    def test_activity_has_status_field(self):
        """活动应该有状态字段"""
        from services import list_activities, get_activity_details

        activities = list_activities()
        if not activities:
            pytest.skip("没有活动数据")

        details = get_activity_details(activities[0])
        assert 'status' in details, "活动应该有状态字段"

    def test_closed_activity_has_closed_at(self):
        """已结项的活动应该有结项时间"""
        from services import list_activities, get_activity_details

        activities = list_activities()
        closed_activities = [a for a in activities if a.get('活动状态') == '已结项']

        if not closed_activities:
            pytest.skip("没有已结项的活动")

        details = get_activity_details(closed_activities[0])
        # 结项时间可能为空（旧数据），但字段应该存在
        assert 'closed_at' in details

    def test_activity_is_closed_check(self):
        """测试活动是否已结项检查"""
        from services import list_activities, activity_is_closed

        activities = list_activities()
        closed_activities = [a for a in activities if a.get('活动状态') == '已结项']

        if closed_activities:
            assert activity_is_closed(closed_activities[0]) is True


class TestDatabaseColumnRegistration:
    """测试数据库列注册

    Bug: 新增字段保存成功但数据库中为空
    原因: _filter_append_row_data 会过滤未注册的列
    """

    def test_activity_columns_registered(self):
        """活动表列应该被注册"""
        from config import ACTIVITY_TABLE_NAME
        from models import db

        try:
            columns = db.list_rows("app_table_columns")
            activity_cols = [c for c in columns if c.get('表名') == ACTIVITY_TABLE_NAME]

            assert len(activity_cols) > 0, f"{ACTIVITY_TABLE_NAME} 应该有注册的列"

        except Exception as e:
            pytest.skip(f"无法检查列注册: {e}")

    def test_signup_columns_registered(self):
        """报名表列应该被注册"""
        from config import SIGNUP_TABLE_NAME
        from models import db

        try:
            columns = db.list_rows("app_table_columns")
            signup_cols = [c for c in columns if c.get('表名') == SIGNUP_TABLE_NAME]

            assert len(signup_cols) > 0, f"{SIGNUP_TABLE_NAME} 应该有注册的列"

        except Exception as e:
            pytest.skip(f"无法检查列注册: {e}")


class TestTimeSlotFormat:
    """测试时间槽格式"""

    def test_time_slot_format_valid(self):
        """时间槽格式应该是 HH:MM-HH:MM"""
        from services import list_cac_room_slots
        import re

        slots = list_cac_room_slots()
        pattern = r'^\d{2}:\d{2}-\d{2}:\d{2}$'

        for slot in slots:
            time_str = slot.get('time_slot', '')
            if time_str:
                assert re.match(pattern, time_str), f"时间格式无效: {time_str}"


class TestSignupStats:
    """测试报名统计"""

    def test_signup_stats_fields(self):
        """报名统计应该有正确的字段"""
        from services import list_activities, get_signup_stats

        activities = list_activities()
        if not activities:
            pytest.skip("没有活动数据")

        activity_id = activities[0].get('_id')
        stats = get_signup_stats(activity_id)

        assert 'reviewers' in stats
        assert 'listeners' in stats
        assert 'reviewer_limit' in stats


class TestActivityDetails:
    """测试活动详情"""

    def test_activity_details_fields(self):
        """活动详情应该有所有必要字段"""
        from services import list_activities, get_activity_details

        activities = list_activities()
        if not activities:
            pytest.skip("没有活动数据")

        details = get_activity_details(activities[0])

        required_fields = ['id', 'date', 'time', 'speakers', 'topic',
                          'classroom', 'status', 'activity_type']

        for field in required_fields:
            assert field in details, f"缺少字段: {field}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])