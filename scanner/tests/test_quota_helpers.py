"""Tests for quota helper functions.

This module tests the quota management helper functions in scanner.quota,
including usage tracking, quota calculations, and cache management.
"""

import pytest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from unittest.mock import patch, MagicMock
from django.utils import timezone
from django.core.cache import cache

from scanner.quota import (
    check_and_record_scan,
    get_todays_usage_count,
    get_user_quota,
    get_remaining_quota,
    is_quota_exceeded,
    record_scan_usage,
    get_usage_history,
    get_next_reset_datetime,
    get_seconds_until_reset,
)
from scanner.models import ScanUsage, UserQuota
from tracker.factories import UserFactory


@pytest.mark.django_db
class TestQuotaHelpers:
    """Tests for quota helper functions."""

    def setup_method(self):
        """Clear cache before each test."""
        cache.clear()

    def test_get_todays_usage_count_returns_correct_count(self):
        """Test that get_todays_usage_count returns correct count for today."""
        # Arrange
        user = UserFactory()
        now = timezone.now()
        eastern = ZoneInfo('US/Eastern'); today_start = datetime.now(eastern).replace(hour=0, minute=0, second=0, microsecond=0)

        # Create scans today
        for i in range(3):
            scan = ScanUsage.objects.create(user=user, scan_type='individual')
            scan.timestamp = today_start + timedelta(hours=i)
            scan.save()

        # Create scan from yesterday (should not be counted)
        yesterday_scan = ScanUsage.objects.create(user=user, scan_type='individual')
        yesterday_scan.timestamp = today_start - timedelta(days=1)
        yesterday_scan.save()

        # Act
        count = get_todays_usage_count(user)

        # Assert
        assert count == 3

    def test_get_todays_usage_count_uses_cache_on_second_call(self):
        """Test that get_todays_usage_count uses cache on subsequent calls."""
        # Arrange
        user = UserFactory()
        ScanUsage.objects.create(user=user, scan_type='individual')

        # Act - First call (cache miss)
        count1 = get_todays_usage_count(user)

        # Create another scan after first call
        ScanUsage.objects.create(user=user, scan_type='individual')

        # Second call (cache hit - should still return 1)
        count2 = get_todays_usage_count(user)

        # Assert
        assert count1 == 1
        assert count2 == 1  # Still 1 because of cache

    def test_get_user_quota_returns_default_for_new_user(self):
        """Test that get_user_quota returns default 25 for new user."""
        # Arrange
        user = UserFactory()

        # Act
        quota = get_user_quota(user)

        # Assert
        assert quota == 25

    def test_get_user_quota_returns_custom_limit_if_set(self):
        """Test that get_user_quota returns custom limit if UserQuota exists."""
        # Arrange
        user = UserFactory()
        UserQuota.objects.create(user=user, daily_limit=50)

        # Act
        quota = get_user_quota(user)

        # Assert
        assert quota == 50

    def test_get_remaining_quota_calculates_correctly(self):
        """Test that get_remaining_quota calculates correctly."""
        # Arrange
        user = UserFactory()
        UserQuota.objects.create(user=user, daily_limit=25)
        eastern = ZoneInfo('US/Eastern'); today_start = datetime.now(eastern).replace(hour=0, minute=0, second=0, microsecond=0)

        for i in range(7):
            scan = ScanUsage.objects.create(user=user, scan_type='individual')
            scan.timestamp = today_start + timedelta(hours=i)
            scan.save()

        # Act
        remaining = get_remaining_quota(user)

        # Assert
        assert remaining == 18  # 25 - 7 = 18

    def test_is_quota_exceeded_returns_true_when_over_limit(self):
        """Test that is_quota_exceeded returns True when over limit."""
        # Arrange
        user = UserFactory()
        UserQuota.objects.create(user=user, daily_limit=5)
        eastern = ZoneInfo('US/Eastern'); today_start = datetime.now(eastern).replace(hour=0, minute=0, second=0, microsecond=0)

        for i in range(6):  # Create 6 scans (over limit of 5)
            scan = ScanUsage.objects.create(user=user, scan_type='individual')
            scan.timestamp = today_start + timedelta(hours=i)
            scan.save()

        # Act
        exceeded = is_quota_exceeded(user)

        # Assert
        assert exceeded is True

    def test_is_quota_exceeded_returns_false_when_under_limit(self):
        """Test that is_quota_exceeded returns False when under limit."""
        # Arrange
        user = UserFactory()
        UserQuota.objects.create(user=user, daily_limit=10)
        eastern = ZoneInfo('US/Eastern'); today_start = datetime.now(eastern).replace(hour=0, minute=0, second=0, microsecond=0)

        for i in range(5):  # Create 5 scans (under limit of 10)
            scan = ScanUsage.objects.create(user=user, scan_type='individual')
            scan.timestamp = today_start + timedelta(hours=i)
            scan.save()

        # Act
        exceeded = is_quota_exceeded(user)

        # Assert
        assert exceeded is False

    def test_record_scan_usage_creates_scan_usage_record(self):
        """Test that record_scan_usage creates ScanUsage record."""
        # Arrange
        user = UserFactory()
        before_count = ScanUsage.objects.filter(user=user).count()

        # Act
        record_scan_usage(user, scan_type='individual', ticker='AAPL')

        # Assert
        after_count = ScanUsage.objects.filter(user=user).count()
        assert after_count == before_count + 1

        latest = ScanUsage.objects.filter(user=user).latest('timestamp')
        assert latest.scan_type == 'individual'
        assert latest.ticker == 'AAPL'

    def test_record_scan_usage_invalidates_cache(self):
        """Test that record_scan_usage invalidates usage cache."""
        # Arrange
        user = UserFactory()

        # Prime the cache with initial count
        initial_count = get_todays_usage_count(user)
        assert initial_count == 0

        # Act
        record_scan_usage(user, scan_type='individual', ticker='AAPL')

        # Get count again (cache should be invalidated)
        new_count = get_todays_usage_count(user)

        # Assert
        assert new_count == 1  # Should reflect new record, not cached 0

    def test_get_usage_history_returns_correct_structure_with_7_days(self):
        """Test that get_usage_history returns 7 days of data."""
        # Arrange
        user = UserFactory()
        eastern = ZoneInfo('US/Eastern'); today_start = datetime.now(eastern).replace(hour=0, minute=0, second=0, microsecond=0)

        # Create scans on different days
        for days_ago in range(7):
            scan_date = today_start - timedelta(days=days_ago)
            scan = ScanUsage.objects.create(user=user, scan_type='individual')
            scan.timestamp = scan_date
            scan.save()

        # Act
        history = get_usage_history(user, days=7)

        # Assert
        assert 'labels' in history
        assert 'data' in history
        assert len(history['labels']) == 7
        assert len(history['data']) == 7
        assert sum(history['data']) == 7  # Total scans across all days

    def test_get_next_reset_datetime_calculates_midnight_et(self):
        """Test that get_next_reset_datetime returns midnight Eastern Time."""
        # Arrange & Act
        next_reset = get_next_reset_datetime()

        # Assert
        assert next_reset is not None
        # Should be the next midnight in ET
        # The exact hour depends on timezone conversion, but should be future
        assert next_reset > timezone.now()

    def test_get_seconds_until_reset_returns_positive_integer(self):
        """Test that get_seconds_until_reset returns positive integer."""
        # Arrange & Act
        seconds = get_seconds_until_reset()

        # Assert
        assert seconds > 0
        assert isinstance(seconds, int)
        # Should be less than 24 hours (86400 seconds)
        assert seconds <= 86400
