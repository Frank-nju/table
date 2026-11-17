"""Unit tests.
Tests the application's modules."""

import unittest
import sys
import os

# Add the project root to the import path.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestConfig(unittest.TestCase):
    """Test configuration module."""

    def test_import_config(self):
        """Test importing configuration."""
        from config import ACTIVITY_TABLE_NAME, MYSQL_HOST
        self.assertIsInstance(ACTIVITY_TABLE_NAME, str)
        self.assertIsInstance(MYSQL_HOST, str)

    def test_table_names(self):
        """Test table name configuration."""
        from config import (
            ACTIVITY_TABLE_NAME, SIGNUP_TABLE_NAME,
            REVIEW_RATING_TABLE_NAME, USER_PROFILE_TABLE_NAME
        )
        self.assertEqual(ACTIVITY_TABLE_NAME, "分享会活动")
        self.assertEqual(SIGNUP_TABLE_NAME, "分享会报名")


class TestModels(unittest.TestCase):
    """Test database module."""

    def test_database_singleton(self):
        """Test the database singleton."""
        from models import db, Database
        self.assertIsInstance(db, Database)

    def test_list_rows(self):
        """Test listing rows."""
        from models import db
        activities = db.list_rows("分享会活动")
        self.assertIsInstance(activities, list)


class TestActivityService(unittest.TestCase):
    """Test the activity service."""

    def test_list_activities(self):
        """Test listing activities."""
        from services import list_activities
        activities = list_activities()
        self.assertIsInstance(activities, list)

    def test_get_activity_details(self):
        """Test retrieving activity details."""
        from services import list_activities, get_activity_details
        activities = list_activities()
        if activities:
            details = get_activity_details(activities[0])
            self.assertIsInstance(details, dict)
            self.assertIn('id', details)
            self.assertIn('topic', details)

    def test_get_signup_stats(self):
        """Test counting signups."""
        from services import list_activities, get_signup_stats
        activities = list_activities()
        if activities:
            stats = get_signup_stats(activities[0].get('_id'))
            self.assertIsInstance(stats, dict)
            self.assertIn('reviewers', stats)
            self.assertIn('listeners', stats)


class TestSignupService(unittest.TestCase):
    """Test the signup service."""

    def test_list_signups(self):
        """Test listing signups."""
        from services import list_signups
        signups = list_signups()
        self.assertIsInstance(signups, list)

    def test_serialize_signup(self):
        """Test signup serialization."""
        from services import list_signups, serialize_signup
        signups = list_signups()
        if signups:
            serialized = serialize_signup(signups[0])
            self.assertIsInstance(serialized, dict)
            self.assertIn('id', serialized)
            self.assertIn('name', serialized)


class TestGroupService(unittest.TestCase):
    """Test the interest group service."""

    def test_list_groups(self):
        """Test listing interest groups."""
        from services.group import list_interest_groups
        groups = list_interest_groups()
        self.assertIsInstance(groups, list)

    def test_serialize_group(self):
        """Test interest group serialization."""
        from services.group import list_interest_groups, serialize_interest_group
        groups = list_interest_groups()
        if groups:
            serialized = serialize_interest_group(groups[0])
            self.assertIsInstance(serialized, dict)
            self.assertIn('id', serialized)
            self.assertIn('name', serialized)


class TestCACAdminService(unittest.TestCase):
    """Test the CAC admin service."""

    def test_list_cac_admins(self):
        """Test listing CAC administrators."""
        from services.cac_admin import list_cac_admins
        admins = list_cac_admins()
        self.assertIsInstance(admins, list)

    def test_is_cac_admin(self):
        """Test whether a user is an administrator."""
        from services.cac_admin import is_cac_admin
        # Test a user who does not exist.
        result = is_cac_admin("nonexistent_user_12345")
        self.assertFalse(result)


class TestUtils(unittest.TestCase):
    """Test utility helpers."""

    def test_exceptions(self):
        """Test the exception class."""
        from utils import ValidationError, NotFoundError, DatabaseError
        try:
            raise ValidationError("Expected validation error")
        except ValidationError as e:
            self.assertEqual(str(e), "测试验证错误")

    def test_success_response(self):
        """Test a successful response."""
        from utils import success_response
        response = success_response({"id": "123"})
        self.assertTrue(response["ok"])


class TestProfileService(unittest.TestCase):
    """Test the user profile service."""

    def test_list_profiles(self):
        """Test listing user profiles."""
        from services.profile import list_user_profiles
        profiles = list_user_profiles()
        self.assertIsInstance(profiles, list)

    def test_get_profile(self):
        """Test retrieving a user profile."""
        from services.profile import get_user_profile
        # Test a user who does not exist.
        profile = get_user_profile("不存在的用户_12345")
        self.assertIsNone(profile)


class TestInviteService(unittest.TestCase):
    """Test the review invitation service."""

    def test_list_invites(self):
        """Test listing invitations."""
        from services.invite import list_review_invites
        invites = list_review_invites()
        self.assertIsInstance(invites, list)

    def test_serialize_invite(self):
        """Test invitation serialization."""
        from services.invite import list_review_invites, serialize_review_invite
        invites = list_review_invites()
        if invites:
            serialized = serialize_review_invite(invites[0])
            self.assertIsInstance(serialized, dict)
            self.assertIn('id', serialized)


class TestRatingService(unittest.TestCase):
    """Test the review rating service."""

    def test_list_ratings(self):
        """Test listing ratings."""
        from services.rating import list_review_ratings
        ratings = list_review_ratings()
        self.assertIsInstance(ratings, list)

    def test_serialize_rating(self):
        """Test rating serialization."""
        from services.rating import list_review_ratings, serialize_rating
        ratings = list_review_ratings()
        if ratings:
            serialized = serialize_rating(ratings[0])
            self.assertIsInstance(serialized, dict)
            self.assertIn('id', serialized)
            self.assertIn('score', serialized)


class TestStatsService(unittest.TestCase):
    """Test the statistics service."""

    def test_build_share_leaderboard(self):
        """Test building the sharing leaderboard."""
        from services.stats import build_share_leaderboard
        leaderboard = build_share_leaderboard()
        self.assertIsInstance(leaderboard, list)

    def test_build_participation_leaderboard(self):
        """Test building the participation leaderboard."""
        from services.stats import build_participation_leaderboard
        leaderboard = build_participation_leaderboard()
        self.assertIsInstance(leaderboard, list)

    def test_build_punctuality_leaderboard(self):
        """Test building the on-time closeout leaderboard."""
        from services.stats import build_punctuality_leaderboard
        leaderboard = build_punctuality_leaderboard()
        self.assertIsInstance(leaderboard, list)


class TestCacheUtils(unittest.TestCase):
    """Test the cache utility."""

    def test_cached_build(self):
        """Test building a cached value."""
        from utils.cache import cached_build, clear_cache

        call_count = 0

        def builder():
            nonlocal call_count
            call_count += 1
            return {"value": call_count}

        # firstcall
        result1 = cached_build("test_key", 60, builder)
        self.assertEqual(result1["value"], 1)

        # The second call should use the cached value.
        result2 = cached_build("test_key", 60, builder)
        self.assertEqual(result2["value"], 1)

        # Clear the cache before calling again.
        clear_cache("test_key")
        result3 = cached_build("test_key", 60, builder)
        self.assertEqual(result3["value"], 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)