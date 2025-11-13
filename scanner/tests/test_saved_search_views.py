"""Tests for SavedSearch views.

This module tests the view functions for Phase 7.1 Saved Searches:
- saved_searches_view (list with sorting)
- save_search_view (create with duplicate handling)
- delete_search_view (soft delete)
- quick_scan_view (trigger scan + increment counter)
- edit_search_notes_view (HTMX update)
"""

import pytest
from unittest.mock import Mock, patch
from django.contrib.messages import get_messages
from django.urls import reverse

from scanner.models import SavedSearch
from tracker.factories import UserFactory


@pytest.fixture
def user():
    """Create authenticated test user."""
    return UserFactory()


@pytest.fixture
def another_user():
    """Create second test user for isolation testing."""
    return UserFactory()


@pytest.fixture
def authenticated_client(client, user):
    """Client authenticated with test user."""
    client.force_login(user)
    return client


@pytest.fixture
def saved_search(user):
    """Create test saved search."""
    return SavedSearch.objects.create(
        user=user,
        ticker='AAPL',
        option_type='put',
        notes='Test search',
        scan_count=5
    )


class TestSavedSearchesView:
    """Tests for saved_searches_view (list page)."""

    @pytest.mark.django_db
    def test_requires_authentication(self, client):
        """Test that view requires authentication."""
        # Arrange
        url = reverse('scanner:saved_searches')

        # Act
        response = client.get(url)

        # Assert
        assert response.status_code == 302  # Redirect to login
        assert '/accounts/login/' in response.url

    @pytest.mark.django_db
    def test_displays_users_searches_only(self, authenticated_client, user, another_user):
        """Test that view displays only current user's searches."""
        # Arrange
        user_search = SavedSearch.objects.create(
            user=user,
            ticker='AAPL',
            option_type='put'
        )
        other_search = SavedSearch.objects.create(
            user=another_user,
            ticker='MSFT',
            option_type='call'
        )
        url = reverse('scanner:saved_searches')

        # Act
        response = authenticated_client.get(url)

        # Assert
        assert response.status_code == 200
        assert user_search in response.context['searches']
        assert other_search not in response.context['searches']

    @pytest.mark.django_db
    def test_excludes_soft_deleted_searches(self, authenticated_client, user):
        """Test that view excludes soft-deleted searches."""
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
        url = reverse('scanner:saved_searches')

        # Act
        response = authenticated_client.get(url)

        # Assert
        assert response.status_code == 200
        assert active_search in response.context['searches']
        assert deleted_search not in response.context['searches']

    @pytest.mark.django_db
    def test_empty_state_handling(self, authenticated_client, user):
        """Test view handles empty search list."""
        # Arrange
        url = reverse('scanner:saved_searches')

        # Act
        response = authenticated_client.get(url)

        # Assert
        assert response.status_code == 200
        assert response.context['searches'].count() == 0

    @pytest.mark.django_db
    def test_sorting_by_date(self, authenticated_client, user):
        """Test default sorting by date (newest first)."""
        # Arrange
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
        url = reverse('scanner:saved_searches')

        # Act
        response = authenticated_client.get(url, {'sort': 'date'})

        # Assert
        assert response.status_code == 200
        searches = list(response.context['searches'])
        assert searches[0] == search2  # Most recent first
        assert searches[1] == search1

    @pytest.mark.django_db
    def test_sorting_by_name(self, authenticated_client, user):
        """Test sorting by ticker name (alphabetical)."""
        # Arrange
        search_z = SavedSearch.objects.create(
            user=user,
            ticker='ZZZZ',
            option_type='put'
        )
        search_a = SavedSearch.objects.create(
            user=user,
            ticker='AAAA',
            option_type='call'
        )
        url = reverse('scanner:saved_searches')

        # Act
        response = authenticated_client.get(url, {'sort': 'name'})

        # Assert
        assert response.status_code == 200
        searches = list(response.context['searches'])
        assert searches[0] == search_a  # Alphabetically first
        assert searches[1] == search_z

    @pytest.mark.django_db
    def test_sorting_by_frequency(self, authenticated_client, user):
        """Test sorting by scan frequency (most scanned first)."""
        # Arrange
        search_low = SavedSearch.objects.create(
            user=user,
            ticker='LOW',
            option_type='put',
            scan_count=2
        )
        search_high = SavedSearch.objects.create(
            user=user,
            ticker='HIGH',
            option_type='call',
            scan_count=10
        )
        url = reverse('scanner:saved_searches')

        # Act
        response = authenticated_client.get(url, {'sort': 'frequency'})

        # Assert
        assert response.status_code == 200
        searches = list(response.context['searches'])
        assert searches[0] == search_high  # Highest frequency first
        assert searches[1] == search_low

    @pytest.mark.django_db
    def test_sorting_by_recent(self, authenticated_client, user):
        """Test sorting by last scanned (most recent first)."""
        # Arrange
        from django.utils import timezone
        from datetime import timedelta

        old_search = SavedSearch.objects.create(
            user=user,
            ticker='OLD',
            option_type='put',
            last_scanned_at=timezone.now() - timedelta(days=5)
        )
        recent_search = SavedSearch.objects.create(
            user=user,
            ticker='RECENT',
            option_type='call',
            last_scanned_at=timezone.now()
        )
        url = reverse('scanner:saved_searches')

        # Act
        response = authenticated_client.get(url, {'sort': 'recent'})

        # Assert
        assert response.status_code == 200
        searches = list(response.context['searches'])
        assert searches[0] == recent_search  # Most recently scanned first
        assert searches[1] == old_search

    @pytest.mark.django_db
    def test_sort_context_variable(self, authenticated_client, user):
        """Test that sort_by is passed to template context."""
        # Arrange
        url = reverse('scanner:saved_searches')

        # Act
        response = authenticated_client.get(url, {'sort': 'frequency'})

        # Assert
        assert response.status_code == 200
        assert response.context['sort_by'] == 'frequency'

    @pytest.mark.django_db
    def test_default_sort_is_date(self, authenticated_client, user):
        """Test default sort when no parameter provided."""
        # Arrange
        url = reverse('scanner:saved_searches')

        # Act
        response = authenticated_client.get(url)

        # Assert
        assert response.status_code == 200
        assert response.context['sort_by'] == 'date'


class TestSaveSearchView:
    """Tests for save_search_view (create saved search)."""

    @pytest.mark.django_db
    def test_requires_authentication(self, client):
        """Test that view requires authentication."""
        # Arrange
        url = reverse('scanner:save_search')

        # Act
        response = client.post(url, {'ticker': 'AAPL', 'option_type': 'put'})

        # Assert
        assert response.status_code == 302  # Redirect to login

    @pytest.mark.django_db
    def test_requires_post_method(self, authenticated_client):
        """Test that view requires POST method."""
        # Arrange
        url = reverse('scanner:save_search')

        # Act
        response = authenticated_client.get(url)

        # Assert
        assert response.status_code == 405  # Method not allowed

    @pytest.mark.django_db
    def test_creates_new_search_successfully(self, authenticated_client, user):
        """Test creating a new saved search."""
        # Arrange
        url = reverse('scanner:save_search')
        data = {'ticker': 'AAPL', 'option_type': 'put'}

        # Act
        response = authenticated_client.post(url, data)

        # Assert
        assert response.status_code == 200
        assert SavedSearch.objects.filter(
            user=user,
            ticker='AAPL',
            option_type='put'
        ).exists()

    @pytest.mark.django_db
    def test_returns_success_message_on_create(self, authenticated_client, user):
        """Test that success message is returned on creation."""
        # Arrange
        url = reverse('scanner:save_search')
        data = {'ticker': 'AAPL', 'option_type': 'put'}

        # Act
        response = authenticated_client.post(url, data)

        # Assert
        assert response.status_code == 200
        content = response.content.decode()
        # Check for "Saved" word in success message
        assert 'saved' in content.lower()
        assert 'AAPL' in content.upper()
        assert 'put' in content.lower()

    @pytest.mark.django_db
    def test_handles_duplicate_search(self, authenticated_client, user, saved_search):
        """Test that duplicate save returns appropriate message."""
        # Arrange
        url = reverse('scanner:save_search')
        data = {
            'ticker': saved_search.ticker,
            'option_type': saved_search.option_type
        }

        # Act
        response = authenticated_client.post(url, data)

        # Assert
        assert response.status_code == 200
        content = response.content.decode()
        assert 'already' in content.lower() or 'duplicate' in content.lower()

    @pytest.mark.django_db
    def test_normalizes_ticker_to_uppercase(self, authenticated_client, user):
        """Test that ticker is normalized to uppercase."""
        # Arrange
        url = reverse('scanner:save_search')
        data = {'ticker': 'aapl', 'option_type': 'put'}  # lowercase

        # Act
        response = authenticated_client.post(url, data)

        # Assert
        assert response.status_code == 200
        search = SavedSearch.objects.get(user=user, ticker='AAPL')
        assert search.ticker == 'AAPL'  # Uppercase

    @pytest.mark.django_db
    def test_validates_ticker_required(self, authenticated_client):
        """Test that ticker is required."""
        # Arrange
        url = reverse('scanner:save_search')
        data = {'ticker': '', 'option_type': 'put'}

        # Act
        response = authenticated_client.post(url, data)

        # Assert
        assert response.status_code == 200
        content = response.content.decode()
        assert 'error' in content.lower() or 'invalid' in content.lower()

    @pytest.mark.django_db
    def test_validates_option_type_choices(self, authenticated_client):
        """Test that option_type must be put or call."""
        # Arrange
        url = reverse('scanner:save_search')
        data = {'ticker': 'AAPL', 'option_type': 'invalid'}

        # Act
        response = authenticated_client.post(url, data)

        # Assert
        assert response.status_code == 200
        content = response.content.decode()
        assert 'error' in content.lower() or 'invalid' in content.lower()

    @pytest.mark.django_db
    def test_user_isolation(self, authenticated_client, user, another_user):
        """Test that searches are user-specific."""
        # Arrange
        SavedSearch.objects.create(
            user=another_user,
            ticker='AAPL',
            option_type='put'
        )
        url = reverse('scanner:save_search')
        data = {'ticker': 'AAPL', 'option_type': 'put'}

        # Act - should NOT trigger duplicate error (different user)
        response = authenticated_client.post(url, data)

        # Assert
        assert response.status_code == 200
        content = response.content.decode()
        # Should be successful, not duplicate
        assert 'saved' in content.lower()


class TestDeleteSearchView:
    """Tests for delete_search_view (soft delete)."""

    @pytest.mark.django_db
    def test_requires_authentication(self, client, saved_search):
        """Test that view requires authentication."""
        # Arrange
        url = reverse('scanner:delete_search', kwargs={'pk': saved_search.pk})

        # Act
        response = client.post(url)

        # Assert
        assert response.status_code == 302  # Redirect to login

    @pytest.mark.django_db
    def test_requires_post_method(self, authenticated_client, saved_search):
        """Test that view requires POST method."""
        # Arrange
        url = reverse('scanner:delete_search', kwargs={'pk': saved_search.pk})

        # Act
        response = authenticated_client.get(url)

        # Assert
        assert response.status_code == 405  # Method not allowed

    @pytest.mark.django_db
    def test_soft_deletes_search(self, authenticated_client, saved_search):
        """Test that delete view soft deletes the search."""
        # Arrange
        url = reverse('scanner:delete_search', kwargs={'pk': saved_search.pk})

        # Act
        response = authenticated_client.post(url)

        # Assert
        saved_search.refresh_from_db()
        assert saved_search.is_deleted is True

    @pytest.mark.django_db
    def test_redirects_to_saved_searches_list(self, authenticated_client, saved_search):
        """Test that delete redirects to saved searches list."""
        # Arrange
        url = reverse('scanner:delete_search', kwargs={'pk': saved_search.pk})

        # Act
        response = authenticated_client.post(url)

        # Assert
        assert response.status_code == 302
        assert response.url == reverse('scanner:saved_searches')

    @pytest.mark.django_db
    def test_displays_success_message(self, authenticated_client, saved_search):
        """Test that success message is displayed after deletion."""
        # Arrange
        url = reverse('scanner:delete_search', kwargs={'pk': saved_search.pk})

        # Act
        response = authenticated_client.post(url, follow=True)

        # Assert
        messages = list(get_messages(response.wsgi_request))
        assert len(messages) == 1
        assert 'removed' in str(messages[0]).lower()

    @pytest.mark.django_db
    def test_returns_404_for_nonexistent_search(self, authenticated_client):
        """Test that 404 is returned for non-existent search."""
        # Arrange
        url = reverse('scanner:delete_search', kwargs={'pk': 99999})

        # Act
        response = authenticated_client.post(url)

        # Assert
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_user_isolation(self, authenticated_client, another_user):
        """Test that user cannot delete another user's search."""
        # Arrange
        other_search = SavedSearch.objects.create(
            user=another_user,
            ticker='AAPL',
            option_type='put'
        )
        url = reverse('scanner:delete_search', kwargs={'pk': other_search.pk})

        # Act
        response = authenticated_client.post(url)

        # Assert
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_cannot_delete_already_deleted_search(self, authenticated_client, saved_search):
        """Test that already-deleted searches return 404."""
        # Arrange
        saved_search.soft_delete()
        url = reverse('scanner:delete_search', kwargs={'pk': saved_search.pk})

        # Act
        response = authenticated_client.post(url)

        # Assert
        assert response.status_code == 404


class TestQuickScanView:
    """Tests for quick_scan_view (trigger scan from saved search)."""

    @pytest.mark.django_db
    def test_requires_authentication(self, client, saved_search):
        """Test that view requires authentication."""
        # Arrange
        url = reverse('scanner:quick_scan', kwargs={'pk': saved_search.pk})

        # Act
        response = client.post(url)

        # Assert
        assert response.status_code == 302  # Redirect to login

    @pytest.mark.django_db
    def test_requires_post_method(self, authenticated_client, saved_search):
        """Test that view requires POST method."""
        # Arrange
        url = reverse('scanner:quick_scan', kwargs={'pk': saved_search.pk})

        # Act
        response = authenticated_client.get(url)

        # Assert
        assert response.status_code == 405  # Method not allowed

    @pytest.mark.django_db
    @patch('scanner.views.threading.Thread')
    @patch('scanner.views.cache')
    def test_increments_scan_count(self, mock_cache, mock_thread, authenticated_client, saved_search):
        """Test that scan increments scan_count."""
        # Arrange
        mock_cache.get.return_value = None  # No lock
        mock_cache.set.return_value = True
        initial_count = saved_search.scan_count
        url = reverse('scanner:quick_scan', kwargs={'pk': saved_search.pk})

        # Act
        response = authenticated_client.post(url)

        # Assert
        saved_search.refresh_from_db()
        assert saved_search.scan_count == initial_count + 1

    @pytest.mark.django_db
    @patch('scanner.views.threading.Thread')
    @patch('scanner.views.cache')
    def test_updates_last_scanned_at(self, mock_cache, mock_thread, authenticated_client, saved_search):
        """Test that scan updates last_scanned_at timestamp."""
        # Arrange
        mock_cache.get.return_value = None  # No lock
        mock_cache.set.return_value = True
        assert saved_search.last_scanned_at is None
        url = reverse('scanner:quick_scan', kwargs={'pk': saved_search.pk})

        # Act
        response = authenticated_client.post(url)

        # Assert
        saved_search.refresh_from_db()
        assert saved_search.last_scanned_at is not None

    @pytest.mark.django_db
    @patch('scanner.views.threading.Thread')
    @patch('scanner.views.cache')
    def test_starts_background_thread(self, mock_cache, mock_thread, authenticated_client, saved_search):
        """Test that scan starts background thread."""
        # Arrange
        mock_cache.get.return_value = None  # No lock
        mock_cache.set.return_value = True
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance
        url = reverse('scanner:quick_scan', kwargs={'pk': saved_search.pk})

        # Act
        response = authenticated_client.post(url)

        # Assert
        mock_thread.assert_called_once()
        mock_thread_instance.start.assert_called_once()

    @pytest.mark.django_db
    @patch('scanner.views.cache')
    def test_returns_polling_partial(self, mock_cache, authenticated_client, saved_search):
        """Test that view returns polling partial template."""
        # Arrange
        mock_cache.get.return_value = None  # No lock
        mock_cache.set.return_value = True
        url = reverse('scanner:quick_scan', kwargs={'pk': saved_search.pk})

        # Act
        response = authenticated_client.post(url)

        # Assert
        assert response.status_code == 200
        # Check if template name contains the partial path
        template_names = [t.name for t in response.templates if t.name]
        assert any('search_polling' in name for name in template_names)

    @pytest.mark.django_db
    @patch('scanner.views.cache')
    def test_handles_scan_already_in_progress(self, mock_cache, authenticated_client, saved_search):
        """Test that view handles concurrent scan gracefully."""
        # Arrange
        # Mock: Return True only for lock key, default/None for others
        def cache_get_side_effect(key, default=None):
            if 'individual_scan_lock' in key:
                return True
            return default
        mock_cache.get.side_effect = cache_get_side_effect
        mock_cache.set.return_value = True
        url = reverse('scanner:quick_scan', kwargs={'pk': saved_search.pk})

        # Act
        response = authenticated_client.post(url)

        # Assert
        assert response.status_code == 200
        # Check if template name contains the partial path
        template_names = [t.name for t in response.templates if t.name]
        assert any('search_polling' in name for name in template_names)

    @pytest.mark.django_db
    def test_returns_404_for_nonexistent_search(self, authenticated_client):
        """Test that 404 is returned for non-existent search."""
        # Arrange
        url = reverse('scanner:quick_scan', kwargs={'pk': 99999})

        # Act
        response = authenticated_client.post(url)

        # Assert
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_user_isolation(self, authenticated_client, another_user):
        """Test that user cannot scan another user's search."""
        # Arrange
        other_search = SavedSearch.objects.create(
            user=another_user,
            ticker='AAPL',
            option_type='put'
        )
        url = reverse('scanner:quick_scan', kwargs={'pk': other_search.pk})

        # Act
        response = authenticated_client.post(url)

        # Assert
        assert response.status_code == 404


class TestEditSearchNotesView:
    """Tests for edit_search_notes_view (HTMX notes update)."""

    @pytest.mark.django_db
    def test_requires_authentication(self, client, saved_search):
        """Test that view requires authentication."""
        # Arrange
        url = reverse('scanner:edit_search_notes', kwargs={'pk': saved_search.pk})

        # Act
        response = client.post(url, {'notes': 'Updated notes'})

        # Assert
        assert response.status_code == 302  # Redirect to login

    @pytest.mark.django_db
    def test_requires_post_method(self, authenticated_client, saved_search):
        """Test that view requires POST method."""
        # Arrange
        url = reverse('scanner:edit_search_notes', kwargs={'pk': saved_search.pk})

        # Act
        response = authenticated_client.get(url)

        # Assert
        assert response.status_code == 405  # Method not allowed

    @pytest.mark.django_db
    def test_updates_notes_successfully(self, authenticated_client, saved_search):
        """Test that notes are updated successfully."""
        # Arrange
        url = reverse('scanner:edit_search_notes', kwargs={'pk': saved_search.pk})
        new_notes = 'Updated earnings play'

        # Act
        response = authenticated_client.post(url, {'notes': new_notes})

        # Assert
        assert response.status_code == 200
        saved_search.refresh_from_db()
        assert saved_search.notes == new_notes

    @pytest.mark.django_db
    def test_handles_empty_notes(self, authenticated_client, saved_search):
        """Test that empty notes are handled correctly."""
        # Arrange
        url = reverse('scanner:edit_search_notes', kwargs={'pk': saved_search.pk})

        # Act
        response = authenticated_client.post(url, {'notes': ''})

        # Assert
        assert response.status_code == 200
        saved_search.refresh_from_db()
        assert saved_search.notes == ''

    @pytest.mark.django_db
    def test_strips_whitespace_from_notes(self, authenticated_client, saved_search):
        """Test that whitespace is stripped from notes."""
        # Arrange
        url = reverse('scanner:edit_search_notes', kwargs={'pk': saved_search.pk})
        notes_with_whitespace = '  Test notes  '

        # Act
        response = authenticated_client.post(url, {'notes': notes_with_whitespace})

        # Assert
        assert response.status_code == 200
        saved_search.refresh_from_db()
        assert saved_search.notes == 'Test notes'

    @pytest.mark.django_db
    def test_returns_htmx_partial(self, authenticated_client, saved_search):
        """Test that view returns HTMX partial template."""
        # Arrange
        url = reverse('scanner:edit_search_notes', kwargs={'pk': saved_search.pk})

        # Act
        response = authenticated_client.post(url, {'notes': 'New notes'})

        # Assert
        assert response.status_code == 200
        # Check if template name contains the partial path
        template_names = [t.name for t in response.templates if t.name]
        assert any('search_notes' in name for name in template_names)

    @pytest.mark.django_db
    def test_context_includes_search_and_status(self, authenticated_client, saved_search):
        """Test that context includes search object and success status."""
        # Arrange
        url = reverse('scanner:edit_search_notes', kwargs={'pk': saved_search.pk})

        # Act
        response = authenticated_client.post(url, {'notes': 'New notes'})

        # Assert
        assert response.status_code == 200
        assert 'search' in response.context
        assert 'status' in response.context
        assert response.context['status'] == 'success'

    @pytest.mark.django_db
    def test_returns_404_for_nonexistent_search(self, authenticated_client):
        """Test that 404 is returned for non-existent search."""
        # Arrange
        url = reverse('scanner:edit_search_notes', kwargs={'pk': 99999})

        # Act
        response = authenticated_client.post(url, {'notes': 'Notes'})

        # Assert
        assert response.status_code == 404

    @pytest.mark.django_db
    def test_user_isolation(self, authenticated_client, another_user):
        """Test that user cannot edit another user's notes."""
        # Arrange
        other_search = SavedSearch.objects.create(
            user=another_user,
            ticker='AAPL',
            option_type='put'
        )
        url = reverse('scanner:edit_search_notes', kwargs={'pk': other_search.pk})

        # Act
        response = authenticated_client.post(url, {'notes': 'Hacked notes'})

        # Assert
        assert response.status_code == 404
        other_search.refresh_from_db()
        assert other_search.notes != 'Hacked notes'
