"""Tests for ScanUsage model.

This module tests the ScanUsage model for tracking user scan activity,
including creation, validation, ordering, and cascade deletion.
"""

import pytest
from django.db import IntegrityError
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch

from scanner.models import ScanUsage
from tracker.factories import UserFactory


@pytest.mark.django_db
class TestScanUsageModel:
    """Tests for the ScanUsage model."""

    def test_creation_with_all_fields(self):
        """Test that ScanUsage can be created with all fields populated."""
        # Arrange
        user = UserFactory()

        # Act
        scan_usage = ScanUsage.objects.create(
            user=user,
            scan_type='individual',
            ticker='AAPL'
        )

        # Assert
        assert scan_usage.id is not None
        assert scan_usage.user == user
        assert scan_usage.scan_type == 'individual'
        assert scan_usage.ticker == 'AAPL'
        assert scan_usage.timestamp is not None
        assert isinstance(scan_usage.timestamp, timezone.datetime)

    def test_creation_without_ticker_curated_scan(self):
        """Test that ScanUsage can be created without ticker for curated scans."""
        # Arrange
        user = UserFactory()

        # Act
        scan_usage = ScanUsage.objects.create(
            user=user,
            scan_type='curated',
            ticker=None
        )

        # Assert
        assert scan_usage.id is not None
        assert scan_usage.user == user
        assert scan_usage.scan_type == 'curated'
        assert scan_usage.ticker is None

    def test_str_method_with_ticker(self):
        """Test __str__ method returns correct format with ticker."""
        # Arrange
        user = UserFactory(username='testuser')
        scan_usage = ScanUsage.objects.create(
            user=user,
            scan_type='individual',
            ticker='AAPL'
        )

        # Act
        result = str(scan_usage)

        # Assert
        assert 'testuser' in result
        assert 'individual' in result
        assert 'AAPL' in result

    def test_str_method_without_ticker(self):
        """Test __str__ method returns correct format without ticker."""
        # Arrange
        user = UserFactory(username='testuser')
        scan_usage = ScanUsage.objects.create(
            user=user,
            scan_type='curated',
            ticker=None
        )

        # Act
        result = str(scan_usage)

        # Assert
        assert 'testuser' in result
        assert 'curated' in result

    def test_ordering_by_timestamp_desc(self):
        """Test that ScanUsage queryset is ordered by -timestamp."""
        # Arrange
        user = UserFactory()
        now = timezone.now()

        # Create scans at different times
        scan1 = ScanUsage.objects.create(user=user, scan_type='individual')
        scan1.timestamp = now - timedelta(hours=4)
        scan1.save()

        scan2 = ScanUsage.objects.create(user=user, scan_type='individual')
        scan2.timestamp = now
        scan2.save()

        scan3 = ScanUsage.objects.create(user=user, scan_type='individual')
        scan3.timestamp = now - timedelta(hours=2)
        scan3.save()

        # Act
        scans = ScanUsage.objects.filter(
            id__in=[scan1.id, scan2.id, scan3.id]
        )

        # Assert
        assert scans[0].id == scan2.id  # newest first
        assert scans[1].id == scan3.id
        assert scans[2].id == scan1.id  # oldest last

    def test_cascade_delete_when_user_deleted(self):
        """Test that ScanUsage records are deleted when user is deleted."""
        # Arrange
        user = UserFactory()
        scan_usage = ScanUsage.objects.create(user=user, scan_type='individual')
        scan_usage_id = scan_usage.id

        # Act
        user.delete()

        # Assert
        assert not ScanUsage.objects.filter(id=scan_usage_id).exists()

    def test_timestamps_auto_populated(self):
        """Test that timestamp is automatically set on creation."""
        # Arrange
        user = UserFactory()
        before = timezone.now()

        # Act
        scan_usage = ScanUsage.objects.create(user=user, scan_type='individual')
        after = timezone.now()

        # Assert
        assert scan_usage.timestamp is not None
        assert before <= scan_usage.timestamp <= after

    def test_scan_type_choices_validation(self):
        """Test that scan_type field validates against SCAN_TYPE_CHOICES."""
        # Arrange
        user = UserFactory()

        # Act - Create with valid choices
        individual = ScanUsage.objects.create(user=user, scan_type='individual')
        curated = ScanUsage.objects.create(user=user, scan_type='curated')

        # Assert
        assert individual.scan_type == 'individual'
        assert curated.scan_type == 'curated'

    def test_index_on_user_and_timestamp(self):
        """Test that composite index exists on (user, timestamp)."""
        # This test verifies the index exists in the model's Meta class
        # Arrange & Act
        indexes = ScanUsage._meta.indexes

        # Assert
        # Find index with both user and timestamp fields
        found_index = False
        for index in indexes:
            # Index fields can be strings or field objects
            if hasattr(index, 'fields'):
                field_names = []
                for field in index.fields:
                    if isinstance(field, str):
                        field_names.append(field)
                    else:
                        field_names.append(field.name)

                if 'user' in field_names and 'timestamp' in field_names:
                    found_index = True
                    break

        assert found_index, "Expected index on (user, timestamp) not found"
