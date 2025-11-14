"""Tests for UserQuota model.

This module tests the UserQuota model for managing per-user scan limits,
including creation, defaults, and helper methods.
"""

import pytest

from scanner.factories import UserQuotaFactory
from scanner.models import UserQuota
from tracker.factories import UserFactory


@pytest.mark.django_db
class TestUserQuotaModel:
    """Tests for the UserQuota model."""

    def test_creation_with_default_limit(self):
        """Test that UserQuota can be created with default daily limit."""
        # Arrange
        user = UserFactory()

        # Act
        quota = UserQuotaFactory(user=user, daily_limit=25)

        # Assert
        assert quota.id is not None
        assert quota.user == user
        assert quota.daily_limit == 25

    def test_get_quota_for_user_creates_if_not_exists(self):
        """Test that get_quota_for_user creates UserQuota if it doesn't exist."""
        # Arrange
        user = UserFactory()
        assert not UserQuota.objects.filter(user=user).exists()

        # Act
        quota = UserQuota.get_quota_for_user(user)

        # Assert
        assert quota is not None
        assert quota.user == user
        assert quota.daily_limit == 25  # Default value
        assert UserQuota.objects.filter(user=user).exists()

    def test_get_quota_for_user_retrieves_existing(self):
        """Test that get_quota_for_user retrieves existing UserQuota."""
        # Arrange
        user = UserFactory()
        existing_quota = UserQuotaFactory(user=user, daily_limit=50)

        # Act
        retrieved_quota = UserQuota.get_quota_for_user(user)

        # Assert
        assert retrieved_quota.id == existing_quota.id
        assert retrieved_quota.daily_limit == 50
        assert UserQuota.objects.filter(user=user).count() == 1

    def test_cascade_delete_when_user_deleted(self):
        """Test that UserQuota is deleted when user is deleted."""
        # Arrange
        user = UserFactory()
        quota = UserQuotaFactory(user=user)
        quota_id = quota.id

        # Act
        user.delete()

        # Assert
        assert not UserQuota.objects.filter(id=quota_id).exists()

    def test_str_method(self):
        """Test __str__ method returns correct format."""
        # Arrange
        user = UserFactory(username='testuser')
        quota = UserQuotaFactory(user=user, daily_limit=30)

        # Act
        result = str(quota)

        # Assert
        assert 'testuser' in result
        assert '30' in result
