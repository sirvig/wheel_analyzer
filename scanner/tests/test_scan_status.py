"""Tests for ScanStatus model and staff monitoring views."""

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone

from scanner.models import ScanStatus

User = get_user_model()


@pytest.fixture
def staff_user(db):
    """Create a staff user for testing."""
    return User.objects.create_user(
        username='staffuser',
        email='staff@example.com',
        password='testpass123',
        is_staff=True
    )


@pytest.fixture
def regular_user(db):
    """Create a regular non-staff user for testing."""
    return User.objects.create_user(
        username='regularuser',
        email='user@example.com',
        password='testpass123',
        is_staff=False
    )


@pytest.fixture
def scan_status(db):
    """Create a sample ScanStatus for testing."""
    return ScanStatus.objects.create(
        scan_type='curated',
        status='in_progress',
        tickers_scanned=10
    )


class TestScanStatusModel:
    """Test the ScanStatus model."""

    def test_create_scan_status(self, db):
        """Test creating a ScanStatus record."""
        scan = ScanStatus.objects.create(
            scan_type='curated',
            status='pending'
        )
        assert scan.id is not None
        assert scan.status == 'pending'
        assert scan.scan_type == 'curated'
        assert scan.start_time is not None
        assert scan.end_time is None
        assert scan.result_count is None
        assert scan.tickers_scanned == 0
        assert scan.error_message == ''

    def test_scan_status_str(self, scan_status):
        """Test string representation."""
        expected = f"curated scan - in_progress ({scan_status.start_time})"
        assert str(scan_status) == expected

    def test_mark_completed(self, scan_status):
        """Test marking a scan as completed."""
        scan_status.mark_completed(result_count=50, tickers_scanned=26)

        assert scan_status.status == 'completed'
        assert scan_status.end_time is not None
        assert scan_status.result_count == 50
        assert scan_status.tickers_scanned == 26

    def test_mark_failed(self, scan_status):
        """Test marking a scan as failed."""
        error_msg = "Market is closed"
        scan_status.mark_failed(error_message=error_msg)

        assert scan_status.status == 'failed'
        assert scan_status.end_time is not None
        assert scan_status.error_message == error_msg

    def test_mark_aborted(self, scan_status):
        """Test marking a scan as aborted."""
        reason = "Manually aborted by staff user admin"
        scan_status.mark_aborted(reason=reason)

        assert scan_status.status == 'aborted'
        assert scan_status.end_time is not None
        assert scan_status.error_message == reason

    def test_duration_completed(self, db):
        """Test duration calculation for completed scan."""
        scan = ScanStatus.objects.create(
            scan_type='curated',
            status='in_progress'
        )
        # Mark as completed (which sets end_time)
        scan.mark_completed(result_count=10, tickers_scanned=5)

        # Duration should be a positive number
        assert scan.duration is not None
        assert scan.duration >= 0

    def test_duration_in_progress(self, scan_status):
        """Test duration calculation for in-progress scan."""
        # Scan is in_progress with no end_time
        assert scan_status.end_time is None
        assert scan_status.duration is not None
        assert scan_status.duration >= 0

    def test_duration_none(self, db):
        """Test duration is None for scans without end_time and not in_progress."""
        scan = ScanStatus.objects.create(
            scan_type='curated',
            status='pending'  # Not in_progress, no end_time
        )
        assert scan.duration is None

    def test_is_active(self, db):
        """Test is_active property."""
        pending_scan = ScanStatus.objects.create(
            scan_type='curated',
            status='pending'
        )
        assert pending_scan.is_active is True

        in_progress_scan = ScanStatus.objects.create(
            scan_type='individual',
            status='in_progress'
        )
        assert in_progress_scan.is_active is True

        completed_scan = ScanStatus.objects.create(
            scan_type='curated',
            status='completed',
            result_count=10
        )
        completed_scan.mark_completed(result_count=10, tickers_scanned=5)
        assert completed_scan.is_active is False

    def test_ordering(self, db):
        """Test that scans are ordered by -start_time."""
        scan1 = ScanStatus.objects.create(scan_type='curated', status='completed')
        scan2 = ScanStatus.objects.create(scan_type='curated', status='in_progress')
        scan3 = ScanStatus.objects.create(scan_type='individual', status='pending')

        # Most recent should be first
        scans = list(ScanStatus.objects.all())
        assert scans[0].id == scan3.id
        assert scans[1].id == scan2.id
        assert scans[2].id == scan1.id


class TestScanMonitorView:
    """Test the staff scan monitoring view."""

    def test_scan_monitor_access_staff(self, client, staff_user, scan_status):
        """Test that staff users can access the scan monitor page."""
        client.force_login(staff_user)
        url = reverse('scanner:scan_monitor')
        response = client.get(url)

        assert response.status_code == 200
        assert b'Scan Monitor' in response.content
        assert b'Staff-only diagnostic page' in response.content

    def test_scan_monitor_access_non_staff(self, client, regular_user):
        """Test that non-staff users cannot access the scan monitor page."""
        client.force_login(regular_user)
        url = reverse('scanner:scan_monitor')
        response = client.get(url)

        # Should redirect to admin login page
        assert response.status_code == 302
        assert '/admin/login/' in response.url

    def test_scan_monitor_not_logged_in(self, client):
        """Test that unauthenticated users are redirected."""
        url = reverse('scanner:scan_monitor')
        response = client.get(url)

        # Should redirect to admin login
        assert response.status_code == 302
        assert '/admin/login/' in response.url

    def test_scan_monitor_shows_latest_scan(self, client, staff_user, scan_status):
        """Test that the page shows the latest scan status."""
        client.force_login(staff_user)
        url = reverse('scanner:scan_monitor')
        response = client.get(url)

        assert response.status_code == 200
        assert 'latest_scan' in response.context
        assert response.context['latest_scan'].id == scan_status.id
        assert response.context['latest_scan'].status == 'in_progress'

    def test_scan_monitor_redis_lock_state(self, client, staff_user, settings):
        """Test that the page shows Redis lock state correctly."""
        client.force_login(staff_user)

        # Set a lock in cache
        lock_key = f"{settings.CACHE_KEY_PREFIX_SCANNER}:scan_in_progress"
        cache.set(lock_key, True, timeout=600)

        url = reverse('scanner:scan_monitor')
        response = client.get(url)

        assert response.status_code == 200
        assert response.context['lock_exists'] is True

        # Clean up
        cache.delete(lock_key)

    def test_scan_monitor_no_scans(self, client, staff_user, db):
        """Test page when no scans exist."""
        client.force_login(staff_user)
        url = reverse('scanner:scan_monitor')
        response = client.get(url)

        assert response.status_code == 200
        assert response.context['latest_scan'] is None


class TestClearScanLockView:
    """Test the clear scan lock view."""

    def test_clear_lock_staff(self, client, staff_user, settings):
        """Test that staff users can clear the lock."""
        client.force_login(staff_user)

        # Set a lock in cache
        lock_key = f"{settings.CACHE_KEY_PREFIX_SCANNER}:scan_in_progress"
        cache.set(lock_key, True, timeout=600)

        # Create an in-progress scan
        scan = ScanStatus.objects.create(
            scan_type='curated',
            status='in_progress'
        )

        url = reverse('scanner:clear_scan_lock')
        response = client.post(url)

        assert response.status_code == 200

        # Lock should be cleared
        assert cache.get(lock_key) is None

        # Scan should be marked as aborted
        scan.refresh_from_db()
        assert scan.status == 'aborted'
        assert 'Manually aborted by staff user' in scan.error_message

    def test_clear_lock_non_staff(self, client, regular_user):
        """Test that non-staff users cannot clear the lock."""
        client.force_login(regular_user)
        url = reverse('scanner:clear_scan_lock')
        response = client.post(url)

        # Should redirect to admin login
        assert response.status_code == 302
        assert '/admin/login/' in response.url

    def test_clear_lock_not_logged_in(self, client):
        """Test that unauthenticated users cannot clear the lock."""
        url = reverse('scanner:clear_scan_lock')
        response = client.post(url)

        # Should redirect to admin login
        assert response.status_code == 302
        assert '/admin/login/' in response.url

    def test_clear_lock_get_not_allowed(self, client, staff_user):
        """Test that GET requests are not allowed."""
        client.force_login(staff_user)
        url = reverse('scanner:clear_scan_lock')
        response = client.get(url)

        # POST is required
        assert response.status_code == 405

    def test_clear_lock_aborts_multiple_scans(self, client, staff_user, db):
        """Test that clearing lock aborts all active scans."""
        client.force_login(staff_user)

        # Create multiple active scans
        scan1 = ScanStatus.objects.create(scan_type='curated', status='in_progress')
        scan2 = ScanStatus.objects.create(scan_type='individual', status='pending')
        scan3 = ScanStatus.objects.create(scan_type='curated', status='completed')

        url = reverse('scanner:clear_scan_lock')
        response = client.post(url)

        assert response.status_code == 200

        # First two should be aborted
        scan1.refresh_from_db()
        scan2.refresh_from_db()
        scan3.refresh_from_db()

        assert scan1.status == 'aborted'
        assert scan2.status == 'aborted'
        assert scan3.status == 'completed'  # Should remain unchanged
