"""Integration tests for SavedSearch feature (Phase 7.1).

This module tests complete workflows across multiple components:
- Full user journey: search → save → quick scan → edit notes → delete
- HTMX integration and partial rendering
- Cache interaction with quick scan
- Multi-user isolation in concurrent scenarios
"""

import pytest
from unittest.mock import Mock, patch
from django.urls import reverse

from scanner.models import SavedSearch
from tracker.factories import UserFactory


@pytest.fixture
def user():
    """Create test user."""
    return UserFactory()


@pytest.fixture
def authenticated_client(client, user):
    """Client authenticated with test user."""
    client.force_login(user)
    return client


class TestSavedSearchFullWorkflow:
    """Tests for complete user workflow."""

    @pytest.mark.django_db
    @patch('scanner.views.threading.Thread')
    @patch('scanner.views.cache')
    def test_complete_workflow_save_scan_edit_delete(
        self,
        mock_cache,
        mock_thread,
        authenticated_client,
        user
    ):
        """
        Test complete workflow:
        1. Save a search from individual scan results
        2. View saved searches list
        3. Quick scan from saved search
        4. Edit notes
        5. Delete search
        """
        # Step 1: Save a search
        save_url = reverse('scanner:save_search')
        save_response = authenticated_client.post(
            save_url,
            {'ticker': 'AAPL', 'option_type': 'put'}
        )
        assert save_response.status_code == 200
        assert SavedSearch.objects.filter(user=user, ticker='AAPL').exists()

        saved_search = SavedSearch.objects.get(user=user, ticker='AAPL')

        # Step 2: View saved searches list
        list_url = reverse('scanner:saved_searches')
        list_response = authenticated_client.get(list_url)
        assert list_response.status_code == 200
        assert saved_search in list_response.context['searches']

        # Step 3: Quick scan
        mock_cache.get.return_value = None
        mock_cache.set.return_value = True
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance

        scan_url = reverse('scanner:quick_scan', kwargs={'pk': saved_search.pk})
        scan_response = authenticated_client.post(scan_url)
        assert scan_response.status_code == 200

        saved_search.refresh_from_db()
        assert saved_search.scan_count > 0
        assert saved_search.last_scanned_at is not None

        # Step 4: Edit notes
        edit_url = reverse('scanner:edit_search_notes', kwargs={'pk': saved_search.pk})
        edit_response = authenticated_client.post(
            edit_url,
            {'notes': 'Earnings play - high volatility'}
        )
        assert edit_response.status_code == 200

        saved_search.refresh_from_db()
        assert saved_search.notes == 'Earnings play - high volatility'

        # Step 5: Delete search
        delete_url = reverse('scanner:delete_search', kwargs={'pk': saved_search.pk})
        delete_response = authenticated_client.post(delete_url)
        assert delete_response.status_code == 302

        saved_search.refresh_from_db()
        assert saved_search.is_deleted is True

        # Verify search no longer appears in list
        list_response_after = authenticated_client.get(list_url)
        assert saved_search not in list_response_after.context['searches']

    @pytest.mark.django_db
    def test_save_same_ticker_different_option_types(self, authenticated_client, user):
        """Test saving same ticker with both put and call options."""
        # Arrange
        save_url = reverse('scanner:save_search')

        # Act - Save put option
        put_response = authenticated_client.post(
            save_url,
            {'ticker': 'AAPL', 'option_type': 'put'}
        )

        # Act - Save call option
        call_response = authenticated_client.post(
            save_url,
            {'ticker': 'AAPL', 'option_type': 'call'}
        )

        # Assert
        assert put_response.status_code == 200
        assert call_response.status_code == 200

        put_search = SavedSearch.objects.get(
            user=user,
            ticker='AAPL',
            option_type='put'
        )
        call_search = SavedSearch.objects.get(
            user=user,
            ticker='AAPL',
            option_type='call'
        )

        assert put_search.ticker == call_search.ticker
        assert put_search.option_type != call_search.option_type

    @pytest.mark.django_db
    def test_delete_and_recreate_search(self, authenticated_client, user):
        """Test that deleted search can be recreated."""
        # Arrange - Create and delete search
        save_url = reverse('scanner:save_search')
        authenticated_client.post(
            save_url,
            {'ticker': 'AAPL', 'option_type': 'put'}
        )

        search = SavedSearch.objects.get(user=user, ticker='AAPL')
        delete_url = reverse('scanner:delete_search', kwargs={'pk': search.pk})
        authenticated_client.post(delete_url)

        search.refresh_from_db()
        assert search.is_deleted is True

        # Act - Save same search again
        recreate_response = authenticated_client.post(
            save_url,
            {'ticker': 'AAPL', 'option_type': 'put'}
        )

        # Assert
        assert recreate_response.status_code == 200
        active_searches = SavedSearch.objects.filter(
            user=user,
            ticker='AAPL',
            option_type='put',
            is_deleted=False
        )
        assert active_searches.count() == 1


class TestMultiUserIsolation:
    """Tests for multi-user isolation scenarios."""

    @pytest.mark.django_db
    def test_two_users_save_same_ticker(self, client):
        """Test that two users can save the same ticker independently."""
        # Arrange
        user1 = UserFactory()
        user2 = UserFactory()
        save_url = reverse('scanner:save_search')

        # Act - User 1 saves AAPL
        client.force_login(user1)
        response1 = client.post(
            save_url,
            {'ticker': 'AAPL', 'option_type': 'put'}
        )

        # Act - User 2 saves AAPL
        client.force_login(user2)
        response2 = client.post(
            save_url,
            {'ticker': 'AAPL', 'option_type': 'put'}
        )

        # Assert
        assert response1.status_code == 200
        assert response2.status_code == 200

        user1_searches = SavedSearch.objects.filter(user=user1, ticker='AAPL')
        user2_searches = SavedSearch.objects.filter(user=user2, ticker='AAPL')

        assert user1_searches.count() == 1
        assert user2_searches.count() == 1
        assert user1_searches.first() != user2_searches.first()

    @pytest.mark.django_db
    def test_user_cannot_access_other_users_searches(self, client):
        """Test that user cannot view or modify another user's searches."""
        # Arrange
        user1 = UserFactory()
        user2 = UserFactory()

        user2_search = SavedSearch.objects.create(
            user=user2,
            ticker='AAPL',
            option_type='put'
        )

        client.force_login(user1)

        # Act - Try to delete user2's search
        delete_url = reverse('scanner:delete_search', kwargs={'pk': user2_search.pk})
        delete_response = client.post(delete_url)

        # Assert
        assert delete_response.status_code == 404

        user2_search.refresh_from_db()
        assert user2_search.is_deleted is False

        # Act - Try to edit user2's notes
        edit_url = reverse('scanner:edit_search_notes', kwargs={'pk': user2_search.pk})
        edit_response = client.post(edit_url, {'notes': 'Hacked'})

        # Assert
        assert edit_response.status_code == 404

        user2_search.refresh_from_db()
        assert user2_search.notes != 'Hacked'

    @pytest.mark.django_db
    @patch('scanner.views.threading.Thread')
    @patch('scanner.views.cache')
    def test_concurrent_quick_scans_different_users(
        self,
        mock_cache,
        mock_thread,
        client
    ):
        """Test that concurrent quick scans work for different users."""
        # Arrange
        user1 = UserFactory()
        user2 = UserFactory()

        search1 = SavedSearch.objects.create(
            user=user1,
            ticker='AAPL',
            option_type='put'
        )
        search2 = SavedSearch.objects.create(
            user=user2,
            ticker='MSFT',
            option_type='call'
        )

        mock_cache.get.return_value = None
        mock_cache.set.return_value = True
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance

        # Act - User 1 quick scans
        client.force_login(user1)
        scan_url1 = reverse('scanner:quick_scan', kwargs={'pk': search1.pk})
        response1 = client.post(scan_url1)

        # Act - User 2 quick scans
        client.force_login(user2)
        scan_url2 = reverse('scanner:quick_scan', kwargs={'pk': search2.pk})
        response2 = client.post(scan_url2)

        # Assert
        assert response1.status_code == 200
        assert response2.status_code == 200

        search1.refresh_from_db()
        search2.refresh_from_db()

        assert search1.scan_count == 1
        assert search2.scan_count == 1


class TestHTMXIntegration:
    """Tests for HTMX-specific functionality."""

    @pytest.mark.django_db
    def test_save_search_returns_partial_template(self, authenticated_client, user):
        """Test that save_search returns HTMX partial."""
        # Arrange
        url = reverse('scanner:save_search')

        # Act
        response = authenticated_client.post(
            url,
            {'ticker': 'AAPL', 'option_type': 'put'},
            HTTP_HX_REQUEST='true'  # Simulate HTMX request
        )

        # Assert
        assert response.status_code == 200
        assert 'scanner/partials/save_search_message.html' in [
            t.name for t in response.templates
        ]

    @pytest.mark.django_db
    def test_edit_notes_returns_partial_template(self, authenticated_client, user):
        """Test that edit_search_notes returns HTMX partial."""
        # Arrange
        search = SavedSearch.objects.create(
            user=user,
            ticker='AAPL',
            option_type='put'
        )
        url = reverse('scanner:edit_search_notes', kwargs={'pk': search.pk})

        # Act
        response = authenticated_client.post(
            url,
            {'notes': 'Updated notes'},
            HTTP_HX_REQUEST='true'
        )

        # Assert
        assert response.status_code == 200
        assert 'scanner/partials/search_notes_display.html' in [
            t.name for t in response.templates
        ]

    @pytest.mark.django_db
    @patch('scanner.views.cache')
    def test_quick_scan_returns_polling_partial(self, mock_cache, authenticated_client, user):
        """Test that quick_scan returns polling partial for HTMX."""
        # Arrange
        search = SavedSearch.objects.create(
            user=user,
            ticker='AAPL',
            option_type='put'
        )
        mock_cache.get.return_value = None
        mock_cache.set.return_value = True
        url = reverse('scanner:quick_scan', kwargs={'pk': search.pk})

        # Act
        response = authenticated_client.post(
            url,
            HTTP_HX_REQUEST='true'
        )

        # Assert
        assert response.status_code == 200
        assert 'scanner/partials/search_polling.html' in [
            t.name for t in response.templates
        ]


class TestCacheInteraction:
    """Tests for cache interaction with quick scan."""

    @pytest.mark.django_db
    @patch('scanner.views.threading.Thread')
    @patch('scanner.views.cache')
    def test_quick_scan_sets_cache_lock(self, mock_cache, mock_thread, authenticated_client, user):
        """Test that quick scan sets user-specific cache lock."""
        # Arrange
        search = SavedSearch.objects.create(
            user=user,
            ticker='AAPL',
            option_type='put'
        )
        mock_cache.get.return_value = None
        url = reverse('scanner:quick_scan', kwargs={'pk': search.pk})

        # Act
        authenticated_client.post(url)

        # Assert - Verify cache.set was called with lock key
        cache_calls = [call[0] for call in mock_cache.set.call_args_list]
        lock_key = f"scanner:individual_scan_lock:{user.id}"
        assert any(lock_key in str(call) for call in cache_calls)

    @pytest.mark.django_db
    @patch('scanner.views.cache')
    def test_concurrent_quick_scan_respects_lock(self, mock_cache, authenticated_client, user):
        """Test that concurrent quick scan respects existing lock."""
        # Arrange
        search = SavedSearch.objects.create(
            user=user,
            ticker='AAPL',
            option_type='put'
        )
        # Mock: Return True only for lock key, default/None for others
        def cache_get_side_effect(key, default=None):
            if 'individual_scan_lock' in key:
                return True
            return default
        mock_cache.get.side_effect = cache_get_side_effect
        url = reverse('scanner:quick_scan', kwargs={'pk': search.pk})

        # Act
        response = authenticated_client.post(url)

        # Assert
        assert response.status_code == 200
        # Should return polling partial without starting new thread
        assert 'scanner/partials/search_polling.html' in [
            t.name for t in response.templates
        ]


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.django_db
    def test_save_search_with_special_characters_in_notes(self, authenticated_client, user):
        """Test saving search with special characters in notes."""
        # Arrange
        url = reverse('scanner:save_search')

        # Act
        response = authenticated_client.post(
            url,
            {
                'ticker': 'AAPL',
                'option_type': 'put',
            }
        )

        search = SavedSearch.objects.get(user=user, ticker='AAPL')
        edit_url = reverse('scanner:edit_search_notes', kwargs={'pk': search.pk})

        edit_response = authenticated_client.post(
            edit_url,
            {'notes': 'Test <script>alert("XSS")</script> & symbols'}
        )

        # Assert
        assert edit_response.status_code == 200
        search.refresh_from_db()
        assert 'script' in search.notes  # Notes are stored as-is
        # Template should escape HTML (Django auto-escapes)

    @pytest.mark.django_db
    @patch('scanner.views.threading.Thread')
    @patch('scanner.views.cache')
    def test_quick_scan_multiple_times(self, mock_cache, mock_thread, authenticated_client, user):
        """Test quick scanning same search multiple times."""
        # Arrange
        search = SavedSearch.objects.create(
            user=user,
            ticker='AAPL',
            option_type='put'
        )
        mock_cache.get.return_value = None
        mock_cache.set.return_value = True
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance
        url = reverse('scanner:quick_scan', kwargs={'pk': search.pk})

        # Act - Scan 3 times
        authenticated_client.post(url)
        authenticated_client.post(url)
        authenticated_client.post(url)

        # Assert
        search.refresh_from_db()
        assert search.scan_count == 3

    @pytest.mark.django_db
    def test_sorting_with_null_last_scanned_at(self, authenticated_client, user):
        """Test sorting by recent works with NULL last_scanned_at values."""
        # Arrange
        from django.utils import timezone

        search_never_scanned = SavedSearch.objects.create(
            user=user,
            ticker='NEVER',
            option_type='put',
            last_scanned_at=None
        )
        search_scanned = SavedSearch.objects.create(
            user=user,
            ticker='SCANNED',
            option_type='call',
            last_scanned_at=timezone.now()
        )
        url = reverse('scanner:saved_searches')

        # Act
        response = authenticated_client.get(url, {'sort': 'recent'})

        # Assert
        assert response.status_code == 200
        searches = list(response.context['searches'])
        assert searches[0] == search_scanned  # Scanned first
        assert searches[1] == search_never_scanned  # NULL last
