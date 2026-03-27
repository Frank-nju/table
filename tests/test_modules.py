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


class TestProfileService(unittest.TestCase):
    """测试用户档案服务"""

    def test_list_profiles(self):
        """测试列出用户档案"""
        from services.profile import list_user_profiles
        profiles = list_user_profiles()
        self.assertIsInstance(profiles, list)

    def test_get_profile(self):
        """测试获取用户档案"""
        from services.profile import get_user_profile
        # 测试不存在的用户
        profile = get_user_profile("不存在的用户_12345")
        self.assertIsNone(profile)


class TestInviteService(unittest.TestCase):
    """测试评议邀请服务"""

    def test_list_invites(self):
        """测试列出邀请"""
        from services.invite import list_review_invites
        invites = list_review_invites()
        self.assertIsInstance(invites, list)

    def test_serialize_invite(self):
        """测试序列化邀请"""
        from services.invite import list_review_invites, serialize_review_invite
        invites = list_review_invites()
        if invites:
            serialized = serialize_review_invite(invites[0])
            self.assertIsInstance(serialized, dict)
            self.assertIn('id', serialized)


class TestRatingService(unittest.TestCase):
    """测试评议评分服务"""

    def test_list_ratings(self):
        """测试列出评分"""
        from services.rating import list_review_ratings
        ratings = list_review_ratings()
        self.assertIsInstance(ratings, list)

    def test_serialize_rating(self):
        """测试序列化评分"""
        from services.rating import list_review_ratings, serialize_rating
        ratings = list_review_ratings()
        if ratings:
            serialized = serialize_rating(ratings[0])
            self.assertIsInstance(serialized, dict)
            self.assertIn('id', serialized)
            self.assertIn('score', serialized)


class TestStatsService(unittest.TestCase):
    """测试统计服务"""

    def test_build_share_leaderboard(self):
        """测试构建分享排行榜"""
        from services.stats import build_share_leaderboard
        leaderboard = build_share_leaderboard()
        self.assertIsInstance(leaderboard, list)

    def test_build_participation_leaderboard(self):
        """测试构建参与排行榜"""
        from services.stats import build_participation_leaderboard
        leaderboard = build_participation_leaderboard()
        self.assertIsInstance(leaderboard, list)

    def test_build_punctuality_leaderboard(self):
        """测试构建准时率排行榜"""
        from services.stats import build_punctuality_leaderboard
        leaderboard = build_punctuality_leaderboard()
        self.assertIsInstance(leaderboard, list)


class TestCacheUtils(unittest.TestCase):
    """测试缓存工具"""

    def test_cached_build(self):
        """测试缓存构建"""
        from utils.cache import cached_build, clear_cache

        call_count = 0

        def builder():
            nonlocal call_count
            call_count += 1
            return {"value": call_count}

        # 第一次调用
        result1 = cached_build("test_key", 60, builder)
        self.assertEqual(result1["value"], 1)

        # 第二次调用应该使用缓存
        result2 = cached_build("test_key", 60, builder)
        self.assertEqual(result2["value"], 1)

        # 清除缓存后再调用
        clear_cache("test_key")
        result3 = cached_build("test_key", 60, builder)
        self.assertEqual(result3["value"], 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)