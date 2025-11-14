"""Tests for usage dashboard view.

This module tests the usage dashboard view that displays scan quota information,
including percentage calculations, progress color assignment, and scan type breakdowns.
"""

import pytest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from django.urls import reverse
from django.test import Client
from django.utils import timezone

from scanner.models import ScanUsage, UserQuota
from tracker.factories import UserFactory


@pytest.mark.django_db
class TestUsageDashboard:
    """Tests for the usage dashboard view."""

    def setup_method(self):
        """Set up test client before each test."""
        self.client = Client()

    def test_usage_dashboard_view_renders_correctly(self):
        """Test that usage_dashboard_view renders correctly for authenticated user."""
        # Arrange
        user = UserFactory()
        UserQuota.objects.create(user=user, daily_limit=25)
        self.client.force_login(user)

        # Create some scan usage
        eastern = ZoneInfo('US/Eastern'); today_start = datetime.now(eastern).replace(hour=0, minute=0, second=0, microsecond=0)
        for i in range(5):
            scan = ScanUsage.objects.create(user=user, scan_type='individual')
            scan.timestamp = today_start + timedelta(hours=i)
            scan.save()

        # Act
        response = self.client.get(reverse('scanner:usage_dashboard'))

        # Assert
        assert response.status_code == 200
        assert 'limit' in response.context
        assert 'used' in response.context
        assert 'remaining' in response.context
        assert 'percentage' in response.context

    def test_dashboard_calculates_percentage_correctly(self):
        """Test that dashboard calculates usage percentage correctly."""
        # Arrange
        user = UserFactory()
        UserQuota.objects.create(user=user, daily_limit=20)
        self.client.force_login(user)

        # Create 5 scans (25% of 20)
        eastern = ZoneInfo('US/Eastern'); today_start = datetime.now(eastern).replace(hour=0, minute=0, second=0, microsecond=0)
        for i in range(5):
            scan = ScanUsage.objects.create(user=user, scan_type='individual')
            scan.timestamp = today_start + timedelta(hours=i)
            scan.save()

        # Act
        response = self.client.get(reverse('scanner:usage_dashboard'))

        # Assert
        assert response.context['percentage'] == 25
        assert response.context['used'] == 5
        assert response.context['limit'] == 20
        assert response.context['remaining'] == 15

    def test_progress_color_green_when_below_50_percent(self):
        """Test that progress_color is green when usage is below 50%."""
        # Arrange
        user = UserFactory()
        UserQuota.objects.create(user=user, daily_limit=25)
        self.client.force_login(user)

        # Create 10 scans (40% of 25)
        eastern = ZoneInfo('US/Eastern'); today_start = datetime.now(eastern).replace(hour=0, minute=0, second=0, microsecond=0)
        for i in range(10):
            scan = ScanUsage.objects.create(user=user, scan_type='individual')
            scan.timestamp = today_start + timedelta(hours=i)
            scan.save()

        # Act
        response = self.client.get(reverse('scanner:usage_dashboard'))

        # Assert
        assert response.context['progress_color'] == 'green'

    def test_progress_color_yellow_when_50_to_80_percent(self):
        """Test that progress_color is yellow when usage is 50-80%."""
        # Arrange
        user = UserFactory()
        UserQuota.objects.create(user=user, daily_limit=20)
        self.client.force_login(user)

        # Create 15 scans (75% of 20)
        eastern = ZoneInfo('US/Eastern'); today_start = datetime.now(eastern).replace(hour=0, minute=0, second=0, microsecond=0)
        for i in range(15):
            scan = ScanUsage.objects.create(user=user, scan_type='individual')
            scan.timestamp = today_start + timedelta(hours=i)
            scan.save()

        # Act
        response = self.client.get(reverse('scanner:usage_dashboard'))

        # Assert
        assert response.context['progress_color'] == 'yellow'

    def test_progress_color_red_when_above_80_percent(self):
        """Test that progress_color is red when usage is above 80%."""
        # Arrange
        user = UserFactory()
        UserQuota.objects.create(user=user, daily_limit=10)
        self.client.force_login(user)

        # Create 9 scans (90% of 10)
        eastern = ZoneInfo('US/Eastern'); today_start = datetime.now(eastern).replace(hour=0, minute=0, second=0, microsecond=0)
        for i in range(9):
            scan = ScanUsage.objects.create(user=user, scan_type='individual')
            scan.timestamp = today_start + timedelta(hours=i)
            scan.save()

        # Act
        response = self.client.get(reverse('scanner:usage_dashboard'))

        # Assert
        assert response.context['progress_color'] == 'red'

    def test_breakdown_by_scan_type_accurate(self):
        """Test that breakdown by scan type is accurate."""
        # Arrange
        user = UserFactory()
        UserQuota.objects.create(user=user, daily_limit=25)
        self.client.force_login(user)

        # Create mixed scan types
        eastern = ZoneInfo('US/Eastern'); today_start = datetime.now(eastern).replace(hour=0, minute=0, second=0, microsecond=0)
        for i in range(7):
            scan = ScanUsage.objects.create(user=user, scan_type='individual')
            scan.timestamp = today_start + timedelta(hours=i)
            scan.save()
        for i in range(3):
            scan = ScanUsage.objects.create(user=user, scan_type='curated')
            scan.timestamp = today_start + timedelta(hours=7+i)
            scan.save()

        # Act
        response = self.client.get(reverse('scanner:usage_dashboard'))

        # Assert
        assert response.context['individual_count'] == 7
        assert response.context['curated_count'] == 3

    def test_authentication_required(self):
        """Test that usage dashboard requires authentication."""
        # Arrange - No login

        # Act
        response = self.client.get(reverse('scanner:usage_dashboard'))

        # Assert
        assert response.status_code == 302  # Redirect to login
        assert '/accounts/login/' in response.url
