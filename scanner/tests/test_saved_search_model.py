"""Tests for SavedSearch model.

This module tests the SavedSearch model including:
- Model creation and field validation
- Unique constraint enforcement
- Soft delete functionality
- Manager methods (active, for_user)
- Model methods (increment_scan_count, soft_delete)
- Cascade deletion behavior
"""

import pytest
from django.db import IntegrityError
from django.utils import timezone

from scanner.models import SavedSearch
from tracker.factories import UserFactory


@pytest.fixture
def user():
    """Create a test user."""
    return UserFactory()


@pytest.fixture
def another_user():
    """Create a second test user."""
    return UserFactory()


@pytest.fixture
def saved_search(user):
    """Create a test saved search."""
    return SavedSearch.objects.create(
        user=user,
        ticker='AAPL',
        option_type='put',
        notes='Test search'
    )


class TestSavedSearchModel:
    """Tests for SavedSearch model creation and fields."""

    @pytest.mark.django_db
    def test_saved_search_creation(self, user):
        """Test that SavedSearch can be created with required fields."""
        # Arrange & Act
        search = SavedSearch.objects.create(
            user=user,
            ticker='AAPL',
            option_type='put'
        )

        # Assert
        assert search.user == user
        assert search.ticker == 'AAPL'
        assert search.option_type == 'put'
        assert search.notes is None or search.notes == ''
        assert search.scan_count == 0
        assert search.last_scanned_at is None
        assert search.is_deleted is False
        assert search.created_at is not None

    @pytest.mark.django_db
    def test_saved_search_with_optional_notes(self, user):
        """Test that notes field is optional."""
        # Arrange & Act
        search = SavedSearch.objects.create(
            user=user,
            ticker='MSFT',
            option_type='call',
            notes='High volatility play'
        )

        # Assert
        assert search.notes == 'High volatility play'

    @pytest.mark.django_db
    @pytest.mark.parametrize("option_type", ['put', 'call'])
    def test_saved_search_option_type_choices(self, user, option_type):
        """Test that option_type accepts valid choices."""
        # Arrange & Act
        search = SavedSearch.objects.create(
            user=user,
            ticker='GOOGL',
            option_type=option_type
        )

        # Assert
        assert search.option_type == option_type

    @pytest.mark.django_db
    def test_saved_search_str_representation(self, saved_search):
        """Test string representation of SavedSearch."""
        # Act
        result = str(saved_search)

        # Assert
        assert saved_search.user.username in result
        assert saved_search.ticker in result
        assert saved_search.option_type in result

    @pytest.mark.django_db
    def test_saved_search_default_ordering(self, user):
        """Test that SavedSearch is ordered by -created_at by default."""
        # Arrange - create multiple searches
        search1 = SavedSearch.objects.create(
            user=user,
            ticker='AAA',
            option_type='put'
        )
        search2 = SavedSearch.objects.create(
            user=user,
            ticker='ZZZ',
            option_type='call'
        )

        # Act
        searches = SavedSearch.objects.filter(user=user)

        # Assert - most recent first
        assert searches[0] == search2
        assert searches[1] == search1


class TestSavedSearchUniqueConstraint:
    """Tests for unique constraint enforcement."""

    @pytest.mark.django_db
    def test_unique_constraint_user_ticker_option_type(self, user):
        """Test unique constraint on (user, ticker, option_type) for active searches."""
        # Arrange
        SavedSearch.objects.create(
            user=user,
            ticker='AAPL',
            option_type='put'
        )

        # Act & Assert
        with pytest.raises(IntegrityError):
            SavedSearch.objects.create(
                user=user,
                ticker='AAPL',
                option_type='put'
            )

    @pytest.mark.django_db
    def test_unique_constraint_allows_different_users(self, user, another_user):
        """Test that different users can save same ticker and option type."""
        # Arrange & Act
        search1 = SavedSearch.objects.create(
            user=user,
            ticker='AAPL',
            option_type='put'
        )
        search2 = SavedSearch.objects.create(
            user=another_user,
            ticker='AAPL',
            option_type='put'
        )

        # Assert
        assert search1.user != search2.user
        assert search1.ticker == search2.ticker
        assert search1.option_type == search2.option_type

    @pytest.mark.django_db
    def test_unique_constraint_allows_different_option_types(self, user):
        """Test that same ticker with different option types is allowed."""
        # Arrange & Act
        search_put = SavedSearch.objects.create(
            user=user,
            ticker='AAPL',
            option_type='put'
        )
        search_call = SavedSearch.objects.create(
            user=user,
            ticker='AAPL',
            option_type='call'
        )

        # Assert
        assert search_put.option_type == 'put'
        assert search_call.option_type == 'call'

    @pytest.mark.django_db
    def test_unique_constraint_ignores_deleted_searches(self, user):
        """Test that soft-deleted searches don't prevent new saves."""
        # Arrange
        search1 = SavedSearch.objects.create(
            user=user,
            ticker='AAPL',
            option_type='put'
        )
        search1.soft_delete()

        # Act - should NOT raise IntegrityError
        search2 = SavedSearch.objects.create(
            user=user,
            ticker='AAPL',
            option_type='put'
        )

        # Assert
        assert search1.is_deleted is True
        assert search2.is_deleted is False
        assert SavedSearch.objects.filter(
            user=user,
            ticker='AAPL',
            option_type='put'
        ).count() == 2


class TestSavedSearchModelMethods:
    """Tests for model instance methods."""

    @pytest.mark.django_db
    def test_increment_scan_count_method(self, saved_search):
        """Test increment_scan_count increments counter and updates timestamp."""
        # Arrange
        initial_count = saved_search.scan_count
        assert saved_search.last_scanned_at is None

        # Act
        saved_search.increment_scan_count()

        # Assert
        saved_search.refresh_from_db()
        assert saved_search.scan_count == initial_count + 1
        assert saved_search.last_scanned_at is not None
        assert isinstance(saved_search.last_scanned_at, timezone.datetime)

    @pytest.mark.django_db
    def test_increment_scan_count_multiple_times(self, saved_search):
        """Test increment_scan_count works correctly multiple times."""
        # Arrange & Act
        saved_search.increment_scan_count()
        first_timestamp = saved_search.last_scanned_at

        saved_search.increment_scan_count()
        second_timestamp = saved_search.last_scanned_at

        saved_search.increment_scan_count()
        third_timestamp = saved_search.last_scanned_at

        # Assert
        saved_search.refresh_from_db()
        assert saved_search.scan_count == 3
        assert second_timestamp >= first_timestamp
        assert third_timestamp >= second_timestamp

    @pytest.mark.django_db
    def test_soft_delete_method(self, saved_search):
        """Test soft_delete marks search as deleted."""
        # Arrange
        assert saved_search.is_deleted is False

        # Act
        saved_search.soft_delete()

        # Assert
        saved_search.refresh_from_db()
        assert saved_search.is_deleted is True

    @pytest.mark.django_db
    def test_soft_delete_preserves_other_fields(self, saved_search):
        """Test soft_delete only changes is_deleted flag."""
        # Arrange
        original_ticker = saved_search.ticker
        original_option_type = saved_search.option_type
        original_notes = saved_search.notes
        original_scan_count = saved_search.scan_count

        # Act
        saved_search.soft_delete()

        # Assert
        saved_search.refresh_from_db()
        assert saved_search.ticker == original_ticker
        assert saved_search.option_type == original_option_type
        assert saved_search.notes == original_notes
        assert saved_search.scan_count == original_scan_count


class TestSavedSearchManager:
    """Tests for custom manager methods."""

    @pytest.mark.django_db
    def test_manager_active_method_excludes_deleted(self, user):
        """Test that active() excludes soft-deleted searches."""
        # Arrange
        active_search = SavedSearch.objects.create(
            user=user,
            ticker='AAPL',
            option_type='put'
        )
        deleted_search = SavedSearch.objects.create(
            user=user,
            ticker='MSFT',
            option_type='call'
        )
        deleted_search.soft_delete()

        # Act
        active_searches = SavedSearch.objects.active()

        # Assert
        assert active_search in active_searches
        assert deleted_search not in active_searches

    @pytest.mark.django_db
    def test_manager_for_user_method(self, user, another_user):
        """Test that for_user() returns only searches for specific user."""
        # Arrange
        user1_search = SavedSearch.objects.create(
            user=user,
            ticker='AAPL',
            option_type='put'
        )
        user2_search = SavedSearch.objects.create(
            user=another_user,
            ticker='MSFT',
            option_type='call'
        )

        # Act
        user1_searches = SavedSearch.objects.for_user(user)
        user2_searches = SavedSearch.objects.for_user(another_user)

        # Assert
        assert user1_search in user1_searches
        assert user1_search not in user2_searches
        assert user2_search in user2_searches
        assert user2_search not in user1_searches

    @pytest.mark.django_db
    def test_manager_for_user_excludes_deleted(self, user):
        """Test that for_user() excludes soft-deleted searches."""
        # Arrange
        active_search = SavedSearch.objects.create(
            user=user,
            ticker='AAPL',
            option_type='put'
        )
        deleted_search = SavedSearch.objects.create(
            user=user,
            ticker='MSFT',
            option_type='call'
        )
        deleted_search.soft_delete()

        # Act
        user_searches = SavedSearch.objects.for_user(user)

        # Assert
        assert user_searches.count() == 1
        assert active_search in user_searches
        assert deleted_search not in user_searches


class TestSavedSearchCascadeDeletion:
    """Tests for cascade deletion behavior."""

    @pytest.mark.django_db
    def test_cascade_delete_when_user_deleted(self, user):
        """Test that SavedSearch is deleted when user is deleted."""
        # Arrange
        search = SavedSearch.objects.create(
            user=user,
            ticker='AAPL',
            option_type='put'
        )
        search_id = search.id

        # Act
        user.delete()

        # Assert
        assert not SavedSearch.objects.filter(id=search_id).exists()


class TestSavedSearchDatabaseIndexes:
    """Tests to verify database indexes exist (metadata checks)."""

    @pytest.mark.django_db
    def test_model_has_expected_indexes(self):
        """Test that SavedSearch model defines expected indexes."""
        # Arrange & Act
        indexes = SavedSearch._meta.indexes

        # Assert - verify indexes exist for performance
        index_fields = [idx.fields for idx in indexes]

        # Check for key indexes
        assert ['user', 'is_deleted'] in index_fields or any(
            set(fields) == {'user', 'is_deleted'} for fields in index_fields
        )
        assert ['created_at'] in index_fields or any(
            set(fields) == {'created_at'} for fields in index_fields
        )

    @pytest.mark.django_db
    def test_model_has_unique_constraint(self):
        """Test that SavedSearch model defines unique constraint."""
        # Arrange & Act
        constraints = SavedSearch._meta.constraints

        # Assert
        constraint_names = [c.name for c in constraints]
        assert 'unique_active_saved_search' in constraint_names
