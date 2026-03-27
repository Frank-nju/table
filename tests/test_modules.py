"""
单元测试

测试各个模块的功能
"""

import unittest
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestConfig(unittest.TestCase):
    """测试配置模块"""

    def test_import_config(self):
        """测试配置导入"""
        from config import ACTIVITY_TABLE_NAME, MYSQL_HOST
        self.assertIsInstance(ACTIVITY_TABLE_NAME, str)
        self.assertIsInstance(MYSQL_HOST, str)

    def test_table_names(self):
        """测试表名配置"""
        from config import (
            ACTIVITY_TABLE_NAME, SIGNUP_TABLE_NAME,
            REVIEW_RATING_TABLE_NAME, USER_PROFILE_TABLE_NAME
        )
        self.assertEqual(ACTIVITY_TABLE_NAME, "分享会活动")
        self.assertEqual(SIGNUP_TABLE_NAME, "分享会报名")


class TestModels(unittest.TestCase):
    """测试数据库模块"""

    def test_database_singleton(self):
        """测试数据库单例"""
        from models import db, Database
        self.assertIsInstance(db, Database)

    def test_list_rows(self):
        """测试列出行"""
        from models import db
        activities = db.list_rows("分享会活动")
        self.assertIsInstance(activities, list)


class TestActivityService(unittest.TestCase):
    """测试活动服务"""

    def test_list_activities(self):
        """测试列出活动"""
        from services import list_activities
        activities = list_activities()
        self.assertIsInstance(activities, list)

    def test_get_activity_details(self):
        """测试获取活动详情"""
        from services import list_activities, get_activity_details
        activities = list_activities()
        if activities:
            details = get_activity_details(activities[0])
            self.assertIsInstance(details, dict)
            self.assertIn('id', details)
            self.assertIn('topic', details)

    def test_get_signup_stats(self):
        """测试获取报名统计"""
        from services import list_activities, get_signup_stats
        activities = list_activities()
        if activities:
            stats = get_signup_stats(activities[0].get('_id'))
            self.assertIsInstance(stats, dict)
            self.assertIn('reviewers', stats)
            self.assertIn('listeners', stats)


class TestSignupService(unittest.TestCase):
    """测试报名服务"""

    def test_list_signups(self):
        """测试列出报名"""
        from services import list_signups
        signups = list_signups()
        self.assertIsInstance(signups, list)

    def test_serialize_signup(self):
        """测试序列化报名"""
        from services import list_signups, serialize_signup
        signups = list_signups()
        if signups:
            serialized = serialize_signup(signups[0])
            self.assertIsInstance(serialized, dict)
            self.assertIn('id', serialized)
            self.assertIn('name', serialized)


class TestGroupService(unittest.TestCase):
    """测试兴趣组服务"""

    def test_list_groups(self):
        """测试列出兴趣组"""
        from services.group import list_interest_groups
        groups = list_interest_groups()
        self.assertIsInstance(groups, list)

    def test_serialize_group(self):
        """测试序列化兴趣组"""
        from services.group import list_interest_groups, serialize_interest_group
        groups = list_interest_groups()
        if groups:
            serialized = serialize_interest_group(groups[0])
            self.assertIsInstance(serialized, dict)
            self.assertIn('id', serialized)
            self.assertIn('name', serialized)


class TestCACAdminService(unittest.TestCase):
    """测试CAC管理服务"""

    def test_list_cac_admins(self):
        """测试列出CAC管理员"""
        from services.cac_admin import list_cac_admins
        admins = list_cac_admins()
        self.assertIsInstance(admins, list)

    def test_is_cac_admin(self):
        """测试检查是否是管理员"""
        from services.cac_admin import is_cac_admin
        # 测试一个不存在的用户
        result = is_cac_admin("不存在的用户_12345")
        self.assertFalse(result)


class TestUtils(unittest.TestCase):
    """测试工具模块"""

    def test_exceptions(self):
        """测试异常类"""
        from utils import ValidationError, NotFoundError, DatabaseError
        try:
            raise ValidationError("测试验证错误")
        except ValidationError as e:
            self.assertEqual(str(e), "测试验证错误")

    def test_success_response(self):
        """测试成功响应"""
        from utils import success_response
        response = success_response({"id": "123"})
        self.assertTrue(response["ok"])


if __name__ == "__main__":
    unittest.main(verbosity=2)