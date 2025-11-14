"""Tests for quota enforcement in views.

This module tests that quota limits are enforced in individual scan and quick scan views,
and that curated scans bypass quota checks.
"""

import pytest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from unittest.mock import patch, MagicMock
from django.urls import reverse
from django.test import Client
from django.core.cache import cache
from django.utils import timezone

from scanner.models import ScanUsage, UserQuota, SavedSearch
from tracker.factories import UserFactory


@pytest.mark.django_db
class TestQuotaEnforcement:
    """Tests for quota enforcement in views."""

    def setup_method(self):
        """Set up test client and clear cache before each test."""
        self.client = Client()
        cache.clear()

    def test_individual_scan_view_allows_scan_when_quota_available(self):
        """Test that individual_scan_view allows scan when quota is available."""
        # Arrange
        user = UserFactory()
        UserQuota.objects.create(user=user, daily_limit=25)
        self.client.force_login(user)

        form_data = {
            'ticker': 'AAPL',
            'option_type': 'put',
            'weeks': 4,
        }

        # Mock the background scan to avoid actual API calls
        with patch('scanner.views.run_individual_scan_in_background') as mock_scan:
            # Act
            response = self.client.post(
                reverse('scanner:individual_scan'),
                data=form_data
            )

        # Assert
        assert response.status_code == 200
        mock_scan.assert_called_once()

    def test_individual_scan_view_blocks_when_quota_exceeded(self):
        """Test that individual_scan_view blocks when quota is exceeded."""
        # Arrange
        user = UserFactory()
        UserQuota.objects.create(user=user, daily_limit=5)
        self.client.force_login(user)

        # Create 5 scans for today (at quota limit) - use US/Eastern timezone
        eastern = ZoneInfo('US/Eastern')
        today_start = datetime.now(eastern).replace(hour=0, minute=0, second=0, microsecond=0)
        for i in range(5):
            scan = ScanUsage.objects.create(user=user, scan_type='individual')
            scan.timestamp = today_start + timedelta(hours=i)
            scan.save()

        form_data = {
            'ticker': 'AAPL',
            'option_type': 'put',
            'weeks': 4,
        }

        # Act
        response = self.client.post(
            reverse('scanner:individual_scan'),
            data=form_data
        )

        # Assert
        # Note: Returns 200 (not 429) so HTMX will swap the content
        assert response.status_code == 200
        assert 'quota' in response.content.decode().lower() or 'limit' in response.content.decode().lower()

    def test_individual_scan_view_returns_200_with_error_when_blocked(self):
        """Test that individual_scan_view returns 200 with error HTML when blocked."""
        # Arrange
        user = UserFactory()
        UserQuota.objects.create(user=user, daily_limit=3)
        self.client.force_login(user)

        # Exceed quota - use US/Eastern timezone
        eastern = ZoneInfo('US/Eastern')
        today_start = datetime.now(eastern).replace(hour=0, minute=0, second=0, microsecond=0)
        for i in range(4):  # 4 scans, limit is 3
            scan = ScanUsage.objects.create(user=user, scan_type='individual')
            scan.timestamp = today_start + timedelta(hours=i)
            scan.save()

        form_data = {
            'ticker': 'MSFT',
            'option_type': 'call',
            'weeks': 8,
        }

        # Act
        response = self.client.post(
            reverse('scanner:individual_scan'),
            data=form_data
        )

        # Assert
        # Note: Returns 200 (not 429) so HTMX will swap the content
        assert response.status_code == 200
        # Verify it's the error page
        assert 'quota' in response.content.decode().lower() or 'limit' in response.content.decode().lower()

    def test_individual_scan_view_records_usage_after_passing_quota_check(self):
        """Test that individual_scan_view records ScanUsage after quota check passes."""
        # Arrange
        user = UserFactory()
        UserQuota.objects.create(user=user, daily_limit=25)
        self.client.force_login(user)

        form_data = {
            'ticker': 'TSLA',
            'option_type': 'put',
            'weeks': 4,
        }

        before_count = ScanUsage.objects.filter(user=user).count()

        # Mock the background scan
        with patch('scanner.views.run_individual_scan_in_background'):
            # Act
            response = self.client.post(
                reverse('scanner:individual_scan'),
                data=form_data
            )

        # Assert
        assert response.status_code == 200
        after_count = ScanUsage.objects.filter(user=user).count()
        assert after_count == before_count + 1

        latest = ScanUsage.objects.filter(user=user).latest('timestamp')
        assert latest.scan_type == 'individual'
        assert latest.ticker == 'TSLA'

    def test_quick_scan_view_enforces_quota(self):
        """Test that quick_scan_view enforces quota limits."""
        # Arrange
        user = UserFactory()
        UserQuota.objects.create(user=user, daily_limit=2)
        self.client.force_login(user)

        saved_search = SavedSearch.objects.create(
            user=user,
            ticker='NVDA',
            option_type='call'
        )

        # Use up quota - use US/Eastern timezone
        eastern = ZoneInfo('US/Eastern')
        today_start = datetime.now(eastern).replace(hour=0, minute=0, second=0, microsecond=0)
        for i in range(2):
            scan = ScanUsage.objects.create(user=user, scan_type='individual')
            scan.timestamp = today_start + timedelta(hours=i)
            scan.save()

        # Act
        response = self.client.post(
            reverse('scanner:quick_scan', kwargs={'pk': saved_search.pk})
        )

        # Assert
        # Note: Returns 200 (not 429) so HTMX will swap the content
        assert response.status_code == 200
        assert 'quota' in response.content.decode().lower() or 'limit' in response.content.decode().lower()

    def test_curated_scanner_bypasses_quota_check(self):
        """Test that curated scanner (manual scan) bypasses quota check."""
        # Arrange
        user = UserFactory()
        UserQuota.objects.create(user=user, daily_limit=2)
        self.client.force_login(user)

        # Use up quota with individual scans - use US/Eastern timezone
        eastern = ZoneInfo('US/Eastern')
        today_start = datetime.now(eastern).replace(hour=0, minute=0, second=0, microsecond=0)
        for i in range(2):
            scan = ScanUsage.objects.create(user=user, scan_type='individual')
            scan.timestamp = today_start + timedelta(hours=i)
            scan.save()

        # Mock the curated scan
        with patch('scanner.views.perform_scan') as mock_scan:
            mock_scan.return_value = []

            # Act
            response = self.client.post(reverse('scanner:scan'))

        # Assert
        # Curated scan should succeed even though individual quota is exceeded
        assert response.status_code == 200
        mock_scan.assert_called_once()
