"""
Tests for Phase 8: Stock Price Integration - View Functions.

This module tests view functions enhanced with stock price features:
- valuation_list_view(): Sorting, discount calculation, latest price timestamp
- index(): Undervalued widget, top 10 filtering, stale exclusion
"""

import pytest
from decimal import Decimal
from datetime import timedelta
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch

from scanner.factories import CuratedStockFactory
from tracker.factories import UserFactory


# ===== valuation_list_view() Tests =====

@pytest.mark.django_db
class TestValuationListView:
    """Tests for valuation_list_view() with Phase 8 enhancements."""

    def test_valuation_list_view_requires_authentication(self, client):
        """Test that valuation list requires login."""
        # Arrange
        url = reverse('scanner:valuations')

        # Act
        response = client.get(url)

        # Assert
        assert response.status_code == 302  # Redirect to login
        assert '/accounts/login/' in response.url

    def test_valuation_list_view_displays_active_stocks(self, client):
        """Test view displays only active stocks."""
        # Arrange
        user = UserFactory()
        client.force_login(user)

        CuratedStockFactory(symbol='ACTIVE1', active=True)
        CuratedStockFactory(symbol='ACTIVE2', active=True)
        CuratedStockFactory(symbol='INACTIVE', active=False)

        url = reverse('scanner:valuations')

        # Act
        response = client.get(url)

        # Assert
        assert response.status_code == 200
        assert len(response.context['stocks_with_discount']) == 2

    def test_valuation_list_view_calculates_discount_percentage(self, client):
        """Test view calculates discount percentage for each stock."""
        # Arrange
        user = UserFactory()
        client.force_login(user)

        stock = CuratedStockFactory(
            symbol='AAPL',
            active=True,
            intrinsic_value=Decimal('150.00'),
            current_price=Decimal('120.00'),
            preferred_valuation_method='EPS'
        )

        url = reverse('scanner:valuations')

        # Act
        response = client.get(url)

        # Assert
        stocks = response.context['stocks_with_discount']
        assert len(stocks) == 1
        assert stocks[0]['stock'] == stock
        assert stocks[0]['discount_pct'] == Decimal('20.0')

    def test_valuation_list_view_sorts_by_discount_descending(self, client):
        """Test view sorts stocks by discount percentage (best deals first)."""
        # Arrange
        user = UserFactory()
        client.force_login(user)

        # Create stocks with different discount percentages
        stock1 = CuratedStockFactory(
            symbol='STOCK1',
            active=True,
            intrinsic_value=Decimal('100.00'),
            current_price=Decimal('90.00'),  # 10% discount
            preferred_valuation_method='EPS'
        )
        stock2 = CuratedStockFactory(
            symbol='STOCK2',
            active=True,
            intrinsic_value=Decimal('100.00'),
            current_price=Decimal('70.00'),  # 30% discount
            preferred_valuation_method='EPS'
        )
        stock3 = CuratedStockFactory(
            symbol='STOCK3',
            active=True,
            intrinsic_value=Decimal('100.00'),
            current_price=Decimal('80.00'),  # 20% discount
            preferred_valuation_method='EPS'
        )

        url = reverse('scanner:valuations')

        # Act
        response = client.get(url)

        # Assert
        stocks = response.context['stocks_with_discount']
        assert stocks[0]['stock'] == stock2  # 30% first
        assert stocks[1]['stock'] == stock3  # 20% second
        assert stocks[2]['stock'] == stock1  # 10% third

    def test_valuation_list_view_includes_undervaluation_tier(self, client):
        """Test view includes tier for each stock."""
        # Arrange
        user = UserFactory()
        client.force_login(user)

        stock = CuratedStockFactory(
            symbol='AAPL',
            active=True,
            intrinsic_value=Decimal('100.00'),
            current_price=Decimal('70.00'),  # 30% discount (green tier)
            preferred_valuation_method='EPS'
        )

        url = reverse('scanner:valuations')

        # Act
        response = client.get(url)

        # Assert
        stocks = response.context['stocks_with_discount']
        assert stocks[0]['tier'] == 'green'

    def test_valuation_list_view_marks_stale_prices(self, client):
        """Test view marks stocks with stale prices."""
        # Arrange
        user = UserFactory()
        client.force_login(user)

        now = timezone.now()
        stock = CuratedStockFactory(
            symbol='AAPL',
            active=True,
            current_price=Decimal('150.00'),
            price_updated_at=now - timedelta(hours=25)  # Stale
        )

        url = reverse('scanner:valuations')

        # Act
        response = client.get(url)

        # Assert
        stocks = response.context['stocks_with_discount']
        assert stocks[0]['is_stale'] is True

    def test_valuation_list_view_handles_missing_prices(self, client):
        """Test view handles stocks without current prices."""
        # Arrange
        user = UserFactory()
        client.force_login(user)

        stock = CuratedStockFactory(
            symbol='NOPRICE',
            active=True,
            intrinsic_value=Decimal('150.00'),
            current_price=None,  # No price
            preferred_valuation_method='EPS'
        )

        url = reverse('scanner:valuations')

        # Act
        response = client.get(url)

        # Assert
        stocks = response.context['stocks_with_discount']
        assert stocks[0]['discount_pct'] is None
        assert stocks[0]['tier'] is None

    def test_valuation_list_view_shows_latest_price_update_timestamp(self, client):
        """Test view shows most recent price update timestamp."""
        # Arrange
        user = UserFactory()
        client.force_login(user)

        now = timezone.now()
        old_timestamp = now - timedelta(hours=10)
        recent_timestamp = now - timedelta(hours=1)

        CuratedStockFactory(
            symbol='OLD',
            active=True,
            current_price=Decimal('100.00'),
            price_updated_at=old_timestamp
        )
        CuratedStockFactory(
            symbol='RECENT',
            active=True,
            current_price=Decimal('150.00'),
            price_updated_at=recent_timestamp
        )

        url = reverse('scanner:valuations')

        # Act
        response = client.get(url)

        # Assert
        latest_update = response.context['latest_price_update']
        assert latest_update == recent_timestamp

    def test_valuation_list_view_handles_no_price_updates(self, client):
        """Test view handles case when no stocks have price updates."""
        # Arrange
        user = UserFactory()
        client.force_login(user)

        CuratedStockFactory(
            symbol='NOUPDATE',
            active=True,
            current_price=None,
            price_updated_at=None
        )

        url = reverse('scanner:valuations')

        # Act
        response = client.get(url)

        # Assert
        assert response.context['latest_price_update'] is None

    def test_valuation_list_view_handles_overvalued_stocks_in_sorting(self, client):
        """Test view correctly sorts overvalued stocks (negative discounts)."""
        # Arrange
        user = UserFactory()
        client.force_login(user)

        undervalued = CuratedStockFactory(
            symbol='UNDER',
            active=True,
            intrinsic_value=Decimal('100.00'),
            current_price=Decimal('80.00'),  # +20% discount
            preferred_valuation_method='EPS'
        )
        overvalued = CuratedStockFactory(
            symbol='OVER',
            active=True,
            intrinsic_value=Decimal('100.00'),
            current_price=Decimal('120.00'),  # -20% discount
            preferred_valuation_method='EPS'
        )

        url = reverse('scanner:valuations')

        # Act
        response = client.get(url)

        # Assert
        stocks = response.context['stocks_with_discount']
        assert stocks[0]['stock'] == undervalued  # Positive discount first
        assert stocks[1]['stock'] == overvalued   # Negative discount last

    def test_valuation_list_view_sorts_none_discounts_to_end(self, client):
        """Test view sorts stocks with None discount to end of list."""
        # Arrange
        user = UserFactory()
        client.force_login(user)

        with_price = CuratedStockFactory(
            symbol='WITHPRICE',
            active=True,
            intrinsic_value=Decimal('100.00'),
            current_price=Decimal('90.00'),  # 10% discount
            preferred_valuation_method='EPS'
        )
        without_price = CuratedStockFactory(
            symbol='NOPRICE',
            active=True,
            intrinsic_value=Decimal('100.00'),
            current_price=None,  # None discount
            preferred_valuation_method='EPS'
        )

        url = reverse('scanner:valuations')

        # Act
        response = client.get(url)

        # Assert
        stocks = response.context['stocks_with_discount']
        assert stocks[0]['stock'] == with_price     # Real discount first
        assert stocks[1]['stock'] == without_price  # None discount last


# ===== index() View Tests =====

@pytest.mark.django_db
class TestIndexViewUndervaluedWidget:
    """Tests for index() view undervalued stocks widget (Phase 8)."""

    def test_index_view_includes_undervalued_stocks_context(self, client):
        """Test index view includes undervalued_stocks in context."""
        # Arrange
        user = UserFactory()
        client.force_login(user)

        url = reverse('scanner:index')

        # Act
        with patch('scanner.views.get_scan_results') as mock_get_results:
            mock_get_results.return_value = {
                'ticker_options': {},
                'ticker_scan': {},
                'last_scan': 'Never',
                'curated_stocks': {},
                'is_local_environment': False,
            }
            response = client.get(url)

        # Assert
        assert 'undervalued_stocks' in response.context

    def test_index_view_shows_undervalued_stocks_with_fresh_prices(self, client):
        """Test widget shows stocks with price < IV and fresh prices."""
        # Arrange
        user = UserFactory()
        client.force_login(user)

        now = timezone.now()
        undervalued = CuratedStockFactory(
            symbol='BARGAIN',
            active=True,
            intrinsic_value=Decimal('150.00'),
            current_price=Decimal('100.00'),  # Undervalued
            price_updated_at=now - timedelta(hours=1),  # Fresh
            preferred_valuation_method='EPS'
        )

        url = reverse('scanner:index')

        # Act
        with patch('scanner.views.get_scan_results') as mock_get_results:
            mock_get_results.return_value = {
                'ticker_options': {},
                'ticker_scan': {},
                'last_scan': 'Never',
                'curated_stocks': {},
                'is_local_environment': False,
            }
            response = client.get(url)

        # Assert
        undervalued_stocks = response.context['undervalued_stocks']
        assert len(undervalued_stocks) == 1
        assert undervalued_stocks[0]['stock'] == undervalued

    def test_index_view_excludes_overvalued_stocks(self, client):
        """Test widget excludes stocks with price > IV."""
        # Arrange
        user = UserFactory()
        client.force_login(user)

        now = timezone.now()
        overvalued = CuratedStockFactory(
            symbol='EXPENSIVE',
            active=True,
            intrinsic_value=Decimal('100.00'),
            current_price=Decimal('150.00'),  # Overvalued
            price_updated_at=now - timedelta(hours=1),
            preferred_valuation_method='EPS'
        )

        url = reverse('scanner:index')

        # Act
        with patch('scanner.views.get_scan_results') as mock_get_results:
            mock_get_results.return_value = {
                'ticker_options': {},
                'ticker_scan': {},
                'last_scan': 'Never',
                'curated_stocks': {},
                'is_local_environment': False,
            }
            response = client.get(url)

        # Assert
        undervalued_stocks = response.context['undervalued_stocks']
        assert len(undervalued_stocks) == 0

    def test_index_view_excludes_stale_prices(self, client):
        """Test widget excludes stocks with stale prices (>24 hours)."""
        # Arrange
        user = UserFactory()
        client.force_login(user)

        now = timezone.now()
        stale = CuratedStockFactory(
            symbol='STALE',
            active=True,
            intrinsic_value=Decimal('150.00'),
            current_price=Decimal('100.00'),  # Undervalued
            price_updated_at=now - timedelta(hours=25),  # Stale
            preferred_valuation_method='EPS'
        )

        url = reverse('scanner:index')

        # Act
        with patch('scanner.views.get_scan_results') as mock_get_results:
            mock_get_results.return_value = {
                'ticker_options': {},
                'ticker_scan': {},
                'last_scan': 'Never',
                'curated_stocks': {},
                'is_local_environment': False,
            }
            response = client.get(url)

        # Assert
        undervalued_stocks = response.context['undervalued_stocks']
        assert len(undervalued_stocks) == 0

    def test_index_view_shows_top_10_undervalued_stocks(self, client):
        """Test widget limits to top 10 stocks sorted by discount."""
        # Arrange
        user = UserFactory()
        client.force_login(user)

        now = timezone.now()

        # Create 15 undervalued stocks with different discounts
        for i in range(15):
            CuratedStockFactory(
                symbol=f'STOCK{i:02d}',
                active=True,
                intrinsic_value=Decimal('100.00'),
                current_price=Decimal(f'{90 - i}.00'),  # Increasing discount
                price_updated_at=now - timedelta(hours=1),
                preferred_valuation_method='EPS'
            )

        url = reverse('scanner:index')

        # Act
        with patch('scanner.views.get_scan_results') as mock_get_results:
            mock_get_results.return_value = {
                'ticker_options': {},
                'ticker_scan': {},
                'last_scan': 'Never',
                'curated_stocks': {},
                'is_local_environment': False,
            }
            response = client.get(url)

        # Assert
        undervalued_stocks = response.context['undervalued_stocks']
        assert len(undervalued_stocks) == 10  # Capped at 10

    def test_index_view_sorts_undervalued_by_discount_descending(self, client):
        """Test widget sorts undervalued stocks by discount (highest first)."""
        # Arrange
        user = UserFactory()
        client.force_login(user)

        now = timezone.now()

        stock1 = CuratedStockFactory(
            symbol='STOCK1',
            active=True,
            intrinsic_value=Decimal('100.00'),
            current_price=Decimal('90.00'),  # 10% discount
            price_updated_at=now - timedelta(hours=1),
            preferred_valuation_method='EPS'
        )
        stock2 = CuratedStockFactory(
            symbol='STOCK2',
            active=True,
            intrinsic_value=Decimal('100.00'),
            current_price=Decimal('70.00'),  # 30% discount
            price_updated_at=now - timedelta(hours=1),
            preferred_valuation_method='EPS'
        )
        stock3 = CuratedStockFactory(
            symbol='STOCK3',
            active=True,
            intrinsic_value=Decimal('100.00'),
            current_price=Decimal('80.00'),  # 20% discount
            price_updated_at=now - timedelta(hours=1),
            preferred_valuation_method='EPS'
        )

        url = reverse('scanner:index')

        # Act
        with patch('scanner.views.get_scan_results') as mock_get_results:
            mock_get_results.return_value = {
                'ticker_options': {},
                'ticker_scan': {},
                'last_scan': 'Never',
                'curated_stocks': {},
                'is_local_environment': False,
            }
            response = client.get(url)

        # Assert
        undervalued_stocks = response.context['undervalued_stocks']
        assert undervalued_stocks[0]['stock'] == stock2  # 30% first
        assert undervalued_stocks[1]['stock'] == stock3  # 20% second
        assert undervalued_stocks[2]['stock'] == stock1  # 10% third

    def test_index_view_includes_discount_pct_in_widget(self, client):
        """Test widget includes discount_pct for each stock."""
        # Arrange
        user = UserFactory()
        client.force_login(user)

        now = timezone.now()
        stock = CuratedStockFactory(
            symbol='AAPL',
            active=True,
            intrinsic_value=Decimal('150.00'),
            current_price=Decimal('120.00'),  # 20% discount
            price_updated_at=now - timedelta(hours=1),
            preferred_valuation_method='EPS'
        )

        url = reverse('scanner:index')

        # Act
        with patch('scanner.views.get_scan_results') as mock_get_results:
            mock_get_results.return_value = {
                'ticker_options': {},
                'ticker_scan': {},
                'last_scan': 'Never',
                'curated_stocks': {},
                'is_local_environment': False,
            }
            response = client.get(url)

        # Assert
        undervalued_stocks = response.context['undervalued_stocks']
        assert undervalued_stocks[0]['discount_pct'] == Decimal('20.0')

    def test_index_view_includes_tier_in_widget(self, client):
        """Test widget includes tier for badge color."""
        # Arrange
        user = UserFactory()
        client.force_login(user)

        now = timezone.now()
        stock = CuratedStockFactory(
            symbol='AAPL',
            active=True,
            intrinsic_value=Decimal('100.00'),
            current_price=Decimal('70.00'),  # 30% discount (green tier)
            price_updated_at=now - timedelta(hours=1),
            preferred_valuation_method='EPS'
        )

        url = reverse('scanner:index')

        # Act
        with patch('scanner.views.get_scan_results') as mock_get_results:
            mock_get_results.return_value = {
                'ticker_options': {},
                'ticker_scan': {},
                'last_scan': 'Never',
                'curated_stocks': {},
                'is_local_environment': False,
            }
            response = client.get(url)

        # Assert
        undervalued_stocks = response.context['undervalued_stocks']
        assert undervalued_stocks[0]['tier'] == 'green'

    def test_index_view_excludes_inactive_stocks(self, client):
        """Test widget excludes inactive stocks."""
        # Arrange
        user = UserFactory()
        client.force_login(user)

        now = timezone.now()
        inactive = CuratedStockFactory(
            symbol='INACTIVE',
            active=False,  # Inactive
            intrinsic_value=Decimal('150.00'),
            current_price=Decimal('100.00'),
            price_updated_at=now - timedelta(hours=1),
            preferred_valuation_method='EPS'
        )

        url = reverse('scanner:index')

        # Act
        with patch('scanner.views.get_scan_results') as mock_get_results:
            mock_get_results.return_value = {
                'ticker_options': {},
                'ticker_scan': {},
                'last_scan': 'Never',
                'curated_stocks': {},
                'is_local_environment': False,
            }
            response = client.get(url)

        # Assert
        undervalued_stocks = response.context['undervalued_stocks']
        assert len(undervalued_stocks) == 0

    def test_index_view_handles_no_undervalued_stocks(self, client):
        """Test widget handles case when no stocks are undervalued."""
        # Arrange
        user = UserFactory()
        client.force_login(user)

        now = timezone.now()
        overvalued = CuratedStockFactory(
            symbol='EXPENSIVE',
            active=True,
            intrinsic_value=Decimal('100.00'),
            current_price=Decimal('150.00'),  # Overvalued
            price_updated_at=now - timedelta(hours=1),
            preferred_valuation_method='EPS'
        )

        url = reverse('scanner:index')

        # Act
        with patch('scanner.views.get_scan_results') as mock_get_results:
            mock_get_results.return_value = {
                'ticker_options': {},
                'ticker_scan': {},
                'last_scan': 'Never',
                'curated_stocks': {},
                'is_local_environment': False,
            }
            response = client.get(url)

        # Assert
        undervalued_stocks = response.context['undervalued_stocks']
        assert undervalued_stocks == []

    def test_index_view_uses_fcf_method_when_preferred(self, client):
        """Test widget respects FCF preferred method for filtering."""
        # Arrange
        user = UserFactory()
        client.force_login(user)

        now = timezone.now()
        stock = CuratedStockFactory(
            symbol='FCFPREF',
            active=True,
            intrinsic_value=Decimal('100.00'),  # EPS - would be overvalued
            intrinsic_value_fcf=Decimal('200.00'),  # FCF - is undervalued
            current_price=Decimal('150.00'),
            price_updated_at=now - timedelta(hours=1),
            preferred_valuation_method='FCF'  # Prefer FCF
        )

        url = reverse('scanner:index')

        # Act
        with patch('scanner.views.get_scan_results') as mock_get_results:
            mock_get_results.return_value = {
                'ticker_options': {},
                'ticker_scan': {},
                'last_scan': 'Never',
                'curated_stocks': {},
                'is_local_environment': False,
            }
            response = client.get(url)

        # Assert
        undervalued_stocks = response.context['undervalued_stocks']
        assert len(undervalued_stocks) == 1  # Should show (150 < 200 FCF)
        assert undervalued_stocks[0]['stock'] == stock


# ===== Integration Tests =====

@pytest.mark.django_db
class TestStockPriceViewsIntegration:
    """Integration tests for stock price views."""

    def test_complete_workflow_undervalued_widget_to_valuations_page(self, client):
        """Test workflow from index widget to valuations page."""
        # Arrange
        user = UserFactory()
        client.force_login(user)

        now = timezone.now()
        stock = CuratedStockFactory(
            symbol='AAPL',
            active=True,
            intrinsic_value=Decimal('150.00'),
            current_price=Decimal('100.00'),
            price_updated_at=now - timedelta(hours=1),
            preferred_valuation_method='EPS'
        )

        # Act 1: Visit index
        with patch('scanner.views.get_scan_results') as mock_get_results:
            mock_get_results.return_value = {
                'ticker_options': {},
                'ticker_scan': {},
                'last_scan': 'Never',
                'curated_stocks': {},
                'is_local_environment': False,
            }
            index_response = client.get(reverse('scanner:index'))

        # Act 2: Visit valuations page
        valuations_response = client.get(reverse('scanner:valuations'))

        # Assert
        # Index page shows stock in widget
        index_stocks = index_response.context['undervalued_stocks']
        assert len(index_stocks) == 1
        assert index_stocks[0]['stock'] == stock
        assert index_stocks[0]['discount_pct'] == Decimal('33.3')

        # Valuations page shows stock with full details
        val_stocks = valuations_response.context['stocks_with_discount']
        assert len(val_stocks) == 1
        assert val_stocks[0]['stock'] == stock
        assert val_stocks[0]['discount_pct'] == Decimal('33.3')
        assert val_stocks[0]['tier'] == 'green'
