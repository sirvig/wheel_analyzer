"""
Tests for Phase 8: Stock Price Integration - End-to-End Integration Tests.

This module tests complete workflows from API fetch to view rendering:
- Command → Model → View → Template rendering
- Multiple tier scenarios
- Graceful degradation with missing data
- Error handling across the stack
"""

import pytest
from decimal import Decimal
from datetime import timedelta
from io import StringIO
from unittest.mock import patch
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from scanner.factories import CuratedStockFactory
from tracker.factories import UserFactory


# ===== End-to-End Workflow Tests =====

@pytest.mark.django_db
class TestStockPriceEndToEndWorkflow:
    """Test complete workflow from command → model → view → template."""

    @patch('scanner.management.commands.fetch_stock_prices.get_stock_quote')
    @patch('scanner.management.commands.fetch_stock_prices.timezone.localtime')
    def test_complete_workflow_fetch_to_display(self, mock_localtime, mock_get_quote, client):
        """Test complete workflow: fetch price → update model → display in view."""
        # Arrange
        # Mock localtime to return a real datetime with hour=18 for market hours check
        now = timezone.now()
        mock_time = now.replace(hour=18, minute=0, second=0, microsecond=0)
        mock_localtime.return_value = mock_time

        user = UserFactory()
        client.force_login(user)

        stock = CuratedStockFactory(
            symbol='AAPL',
            active=True,
            intrinsic_value=Decimal('150.00'),
            current_price=None,  # No price initially
            price_updated_at=None,
            preferred_valuation_method='EPS'
        )

        mock_get_quote.return_value = {
            'symbol': 'AAPL',
            'price': Decimal('100.00'),  # Undervalued price
            'updated': 1763144253
        }

        # Act 1: Fetch prices via command
        out = StringIO()
        call_command('fetch_stock_prices', stdout=out)

        # Act 2: View valuations page
        url = reverse('scanner:valuations')
        response = client.get(url)

        # Assert
        # Model updated correctly
        stock.refresh_from_db()
        assert stock.current_price == Decimal('100.00')
        assert stock.price_updated_at is not None

        # Model methods work correctly
        assert stock.is_undervalued() is True
        assert stock.get_discount_percentage() == Decimal('33.3')
        assert stock.get_undervaluation_tier() == 'green'

        # View context includes correct data
        stocks = response.context['stocks_with_discount']
        assert len(stocks) == 1
        assert stocks[0]['discount_pct'] == Decimal('33.3')
        assert stocks[0]['tier'] == 'green'
        assert stocks[0]['is_stale'] is False

    @patch('scanner.management.commands.fetch_stock_prices.get_stock_quote')
    @patch('scanner.management.commands.fetch_stock_prices.timezone.localtime')
    def test_complete_workflow_multiple_stocks_different_tiers(
        self, mock_localtime, mock_get_quote, client
    ):
        """Test workflow with multiple stocks in different undervaluation tiers."""
        # Arrange
        # Mock localtime to return a real datetime with hour=18 for market hours check
        now = timezone.now()
        mock_time = now.replace(hour=18, minute=0, second=0, microsecond=0)
        mock_localtime.return_value = mock_time
        user = UserFactory()
        client.force_login(user)

        # Create stocks for each tier
        green_stock = CuratedStockFactory(
            symbol='GREEN',
            active=True,
            intrinsic_value=Decimal('100.00'),
            preferred_valuation_method='EPS'
        )
        orange_stock = CuratedStockFactory(
            symbol='ORANGE',
            active=True,
            intrinsic_value=Decimal('100.00'),
            preferred_valuation_method='EPS'
        )
        yellow_stock = CuratedStockFactory(
            symbol='YELLOW',
            active=True,
            intrinsic_value=Decimal('100.00'),
            preferred_valuation_method='EPS'
        )
        slate_stock = CuratedStockFactory(
            symbol='SLATE',
            active=True,
            intrinsic_value=Decimal('100.00'),
            preferred_valuation_method='EPS'
        )
        overvalued_stock = CuratedStockFactory(
            symbol='OVER',
            active=True,
            intrinsic_value=Decimal('100.00'),
            preferred_valuation_method='EPS'
        )

        # Mock API responses for each tier
        def get_quote_side_effect(symbol):
            prices = {
                'GREEN': Decimal('65.00'),   # 35% discount
                'ORANGE': Decimal('75.00'),  # 25% discount
                'YELLOW': Decimal('85.00'),  # 15% discount
                'SLATE': Decimal('95.00'),   # 5% discount
                'OVER': Decimal('120.00'),   # -20% discount (overvalued)
            }
            return {
                'symbol': symbol,
                'price': prices[symbol],
                'updated': 1763144253
            }

        mock_get_quote.side_effect = get_quote_side_effect

        # Act 1: Fetch all prices
        out = StringIO()
        call_command('fetch_stock_prices', stdout=out)

        # Act 2: View valuations page
        url = reverse('scanner:valuations')
        response = client.get(url)

        # Assert
        stocks = response.context['stocks_with_discount']

        # Should be sorted by discount (highest first)
        assert stocks[0]['stock'] == green_stock
        assert stocks[0]['tier'] == 'green'
        assert stocks[0]['discount_pct'] == Decimal('35.0')

        assert stocks[1]['stock'] == orange_stock
        assert stocks[1]['tier'] == 'orange'
        assert stocks[1]['discount_pct'] == Decimal('25.0')

        assert stocks[2]['stock'] == yellow_stock
        assert stocks[2]['tier'] == 'yellow'
        assert stocks[2]['discount_pct'] == Decimal('15.0')

        assert stocks[3]['stock'] == slate_stock
        assert stocks[3]['tier'] == 'slate'
        assert stocks[3]['discount_pct'] == Decimal('5.0')

        assert stocks[4]['stock'] == overvalued_stock
        assert stocks[4]['tier'] == 'overvalued'
        assert stocks[4]['discount_pct'] == Decimal('-20.0')


# ===== Graceful Degradation Tests =====

@pytest.mark.django_db
class TestStockPriceGracefulDegradation:
    """Test graceful handling of missing or invalid data."""

    def test_graceful_degradation_missing_current_price(self, client):
        """Test view handles stocks with no current price."""
        # Arrange
        user = UserFactory()
        client.force_login(user)

        stock = CuratedStockFactory(
            symbol='NOPRICE',
            active=True,
            intrinsic_value=Decimal('150.00'),
            current_price=None,  # Missing
            price_updated_at=None,
            preferred_valuation_method='EPS'
        )

        # Act
        url = reverse('scanner:valuations')
        response = client.get(url)

        # Assert
        stocks = response.context['stocks_with_discount']
        assert len(stocks) == 1
        assert stocks[0]['discount_pct'] is None
        assert stocks[0]['tier'] is None
        assert stocks[0]['is_stale'] is True

        # Model methods return safe defaults
        assert stock.is_undervalued() is False
        assert stock.get_discount_percentage() is None
        assert stock.get_undervaluation_tier() is None
        assert stock.is_price_stale() is True

    def test_graceful_degradation_missing_intrinsic_value(self, client):
        """Test view handles stocks with no intrinsic value."""
        # Arrange
        user = UserFactory()
        client.force_login(user)

        now = timezone.now()
        stock = CuratedStockFactory(
            symbol='NOIV',
            active=True,
            intrinsic_value=None,  # Missing
            current_price=Decimal('100.00'),
            price_updated_at=now - timedelta(hours=1),
            preferred_valuation_method='EPS'
        )

        # Act
        url = reverse('scanner:valuations')
        response = client.get(url)

        # Assert
        stocks = response.context['stocks_with_discount']
        assert len(stocks) == 1
        assert stocks[0]['discount_pct'] is None
        assert stocks[0]['tier'] is None
        assert stocks[0]['is_stale'] is False

        # Model methods return safe defaults
        assert stock.is_undervalued() is False
        assert stock.get_discount_percentage() is None
        assert stock.get_undervaluation_tier() is None

    def test_graceful_degradation_mixed_data_quality(self, client):
        """Test view handles mix of complete and incomplete data."""
        # Arrange
        user = UserFactory()
        client.force_login(user)

        now = timezone.now()

        # Complete data
        complete = CuratedStockFactory(
            symbol='COMPLETE',
            active=True,
            intrinsic_value=Decimal('150.00'),
            current_price=Decimal('120.00'),
            price_updated_at=now - timedelta(hours=1),
            preferred_valuation_method='EPS'
        )

        # Missing price
        no_price = CuratedStockFactory(
            symbol='NOPRICE',
            active=True,
            intrinsic_value=Decimal('150.00'),
            current_price=None,
            price_updated_at=None,
            preferred_valuation_method='EPS'
        )

        # Missing IV
        no_iv = CuratedStockFactory(
            symbol='NOIV',
            active=True,
            intrinsic_value=None,
            current_price=Decimal('100.00'),
            price_updated_at=now - timedelta(hours=1),
            preferred_valuation_method='EPS'
        )

        # Stale price
        stale = CuratedStockFactory(
            symbol='STALE',
            active=True,
            intrinsic_value=Decimal('150.00'),
            current_price=Decimal('100.00'),
            price_updated_at=now - timedelta(hours=30),  # Stale
            preferred_valuation_method='EPS'
        )

        # Act
        url = reverse('scanner:valuations')
        response = client.get(url)

        # Assert - all stocks displayed with appropriate data
        stocks_dict = {
            s['stock'].symbol: s for s in response.context['stocks_with_discount']
        }

        # Complete stock has all data
        assert stocks_dict['COMPLETE']['discount_pct'] == Decimal('20.0')
        assert stocks_dict['COMPLETE']['tier'] == 'orange'  # 20% is orange tier (20-29%)
        assert stocks_dict['COMPLETE']['is_stale'] is False

        # Incomplete stocks have None where appropriate
        assert stocks_dict['NOPRICE']['discount_pct'] is None
        assert stocks_dict['NOPRICE']['tier'] is None
        assert stocks_dict['NOPRICE']['is_stale'] is True

        assert stocks_dict['NOIV']['discount_pct'] is None
        assert stocks_dict['NOIV']['tier'] is None
        assert stocks_dict['NOIV']['is_stale'] is False

        assert stocks_dict['STALE']['discount_pct'] == Decimal('33.3')
        assert stocks_dict['STALE']['tier'] == 'green'
        assert stocks_dict['STALE']['is_stale'] is True


# ===== Error Handling Tests =====

@pytest.mark.django_db
class TestStockPriceErrorHandling:
    """Test error handling across the stack."""

    @patch('scanner.management.commands.fetch_stock_prices.get_stock_quote')
    @patch('scanner.management.commands.fetch_stock_prices.timezone.localtime')
    def test_partial_api_failure_still_displays_successful_data(
        self, mock_localtime, mock_get_quote, client
    ):
        """Test that partial API failures don't break view rendering."""
        # Arrange
        # Mock localtime to return a real datetime with hour=18 for market hours check
        now = timezone.now()
        mock_time = now.replace(hour=18, minute=0, second=0, microsecond=0)
        mock_localtime.return_value = mock_time
        user = UserFactory()
        client.force_login(user)

        success_stock = CuratedStockFactory(
            symbol='AAPL',  # Comes first alphabetically
            active=True,
            intrinsic_value=Decimal('150.00'),
            preferred_valuation_method='EPS'
        )
        failure_stock = CuratedStockFactory(
            symbol='MSFT',  # Comes second alphabetically
            active=True,
            intrinsic_value=Decimal('150.00'),
            preferred_valuation_method='EPS'
        )

        # Mock: first call succeeds (AAPL), second fails (MSFT)
        mock_get_quote.side_effect = [
            {'symbol': 'AAPL', 'price': Decimal('120.00'), 'updated': 1763144253},
            None  # API failure for MSFT
        ]

        # Act
        out = StringIO()
        call_command('fetch_stock_prices', stdout=out)

        url = reverse('scanner:valuations')
        response = client.get(url)

        # Assert
        # Command completes with partial success
        output = out.getvalue()
        assert 'Updated: 1/2' in output
        assert 'AAPL:' in output  # Success
        assert 'MSFT: Failed' in output  # Failure

        # View still renders successfully
        assert response.status_code == 200

        stocks_dict = {
            s['stock'].symbol: s for s in response.context['stocks_with_discount']
        }

        # Successful stock has data
        success_stock.refresh_from_db()
        assert success_stock.current_price == Decimal('120.00')
        assert stocks_dict['AAPL']['discount_pct'] == Decimal('20.0')
        assert stocks_dict['AAPL']['tier'] == 'orange'  # 20% is orange tier (20-29%)

        # Failed stock has no price data
        failure_stock.refresh_from_db()
        assert failure_stock.current_price is None
        assert stocks_dict['MSFT']['discount_pct'] is None
        assert stocks_dict['MSFT']['tier'] is None

    @patch('scanner.management.commands.fetch_stock_prices.get_stock_quote')
    @patch('scanner.management.commands.fetch_stock_prices.timezone.localtime')
    def test_api_timeout_does_not_crash_command(self, mock_localtime, mock_get_quote):
        """Test that API timeout is handled gracefully."""
        # Arrange
        # Mock localtime to return a real datetime with hour=18 for market hours check
        now = timezone.now()
        mock_time = now.replace(hour=18, minute=0, second=0, microsecond=0)
        mock_localtime.return_value = mock_time
        CuratedStockFactory(symbol='AAPL', active=True)

        # Mock get_stock_quote to return None (simulating API timeout handled internally)
        mock_get_quote.return_value = None

        # Act
        out = StringIO()
        call_command('fetch_stock_prices', stdout=out)

        # Assert - command completes without crashing
        output = out.getvalue()
        assert 'Updated: 0/1' in output
        assert 'Failed: AAPL' in output

    def test_view_renders_with_no_stocks(self, client):
        """Test valuations view renders when no stocks exist."""
        # Arrange
        user = UserFactory()
        client.force_login(user)

        # Act
        url = reverse('scanner:valuations')
        response = client.get(url)

        # Assert
        assert response.status_code == 200
        assert response.context['stocks_with_discount'] == []
        assert response.context['latest_price_update'] is None


# ===== FCF Method Preference Tests =====

@pytest.mark.django_db
class TestStockPriceFCFMethodPreference:
    """Test that FCF preferred method is respected throughout the stack."""

    @patch('scanner.management.commands.fetch_stock_prices.get_stock_quote')
    @patch('scanner.management.commands.fetch_stock_prices.timezone.localtime')
    def test_fcf_preference_end_to_end(self, mock_localtime, mock_get_quote, client):
        """Test FCF preference from command through to view."""
        # Arrange
        # Mock localtime to return a real datetime with hour=18 for market hours check
        now = timezone.now()
        mock_time = now.replace(hour=18, minute=0, second=0, microsecond=0)
        mock_localtime.return_value = mock_time
        user = UserFactory()
        client.force_login(user)

        stock = CuratedStockFactory(
            symbol='FCFPREF',
            active=True,
            intrinsic_value=Decimal('100.00'),  # EPS method
            intrinsic_value_fcf=Decimal('200.00'),  # FCF method
            current_price=None,
            preferred_valuation_method='FCF'  # Prefer FCF
        )

        mock_get_quote.return_value = {
            'symbol': 'FCFPREF',
            'price': Decimal('150.00'),
            'updated': 1763144253
        }

        # Act
        out = StringIO()
        call_command('fetch_stock_prices', stdout=out)

        url = reverse('scanner:valuations')
        response = client.get(url)

        # Assert
        stock.refresh_from_db()

        # Model uses FCF value
        assert stock.get_effective_intrinsic_value() == Decimal('200.00')
        assert stock.is_undervalued() is True  # 150 < 200 (FCF)
        assert stock.get_discount_percentage() == Decimal('25.0')  # (200-150)/200
        assert stock.get_undervaluation_tier() == 'orange'

        # View context uses FCF calculations
        stocks = response.context['stocks_with_discount']
        assert stocks[0]['discount_pct'] == Decimal('25.0')
        assert stocks[0]['tier'] == 'orange'

    @patch('scanner.views.get_scan_results')
    def test_fcf_preference_in_undervalued_widget(self, mock_get_results, client):
        """Test FCF preference in index page undervalued widget."""
        # Arrange
        mock_get_results.return_value = {
            'ticker_options': {},
            'ticker_scan': {},
            'last_scan': 'Never',
            'curated_stocks': {},
            'is_local_environment': False,
        }

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
            preferred_valuation_method='FCF'
        )

        # Act
        url = reverse('scanner:index')
        response = client.get(url)

        # Assert - widget shows stock because FCF method shows it's undervalued
        undervalued = response.context['undervalued_stocks']
        assert len(undervalued) == 1
        assert undervalued[0]['stock'] == stock
        assert undervalued[0]['discount_pct'] == Decimal('25.0')  # FCF-based


# ===== Staleness Filtering Tests =====

@pytest.mark.django_db
class TestStockPriceStalenessFiltering:
    """Test staleness filtering in undervalued widget."""

    @patch('scanner.views.get_scan_results')
    def test_undervalued_widget_excludes_24_hour_boundary(self, mock_get_results, client):
        """Test widget excludes stocks at exactly 24 hour boundary."""
        # Arrange
        mock_get_results.return_value = {
            'ticker_options': {},
            'ticker_scan': {},
            'last_scan': 'Never',
            'curated_stocks': {},
            'is_local_environment': False,
        }

        user = UserFactory()
        client.force_login(user)

        now = timezone.now()

        # Fresh price (23 hours)
        fresh = CuratedStockFactory(
            symbol='FRESH',
            active=True,
            intrinsic_value=Decimal('150.00'),
            current_price=Decimal('100.00'),
            price_updated_at=now - timedelta(hours=23),
            preferred_valuation_method='EPS'
        )

        # Stale price (25 hours)
        stale = CuratedStockFactory(
            symbol='STALE',
            active=True,
            intrinsic_value=Decimal('150.00'),
            current_price=Decimal('100.00'),
            price_updated_at=now - timedelta(hours=25),
            preferred_valuation_method='EPS'
        )

        # Act
        url = reverse('scanner:index')
        response = client.get(url)

        # Assert
        undervalued = response.context['undervalued_stocks']
        assert len(undervalued) == 1
        assert undervalued[0]['stock'] == fresh  # Only fresh included


# ===== Performance Tests =====

@pytest.mark.django_db
class TestStockPricePerformance:
    """Test performance with large datasets."""

    @patch('scanner.views.get_scan_results')
    def test_undervalued_widget_with_100_stocks(self, mock_get_results, client):
        """Test widget performance with 100 stocks."""
        # Arrange
        mock_get_results.return_value = {
            'ticker_options': {},
            'ticker_scan': {},
            'last_scan': 'Never',
            'curated_stocks': {},
            'is_local_environment': False,
        }

        user = UserFactory()
        client.force_login(user)

        now = timezone.now()

        # Create 100 undervalued stocks
        for i in range(100):
            CuratedStockFactory(
                symbol=f'STOCK{i:03d}',
                active=True,
                intrinsic_value=Decimal('100.00'),
                current_price=Decimal(f'{90 - (i * 0.1):.2f}'),  # Varying discounts
                price_updated_at=now - timedelta(hours=1),
                preferred_valuation_method='EPS'
            )

        # Act
        url = reverse('scanner:index')
        response = client.get(url)

        # Assert - widget limits to 10 and query completes
        undervalued = response.context['undervalued_stocks']
        assert len(undervalued) == 10
        assert response.status_code == 200

    def test_valuations_page_with_100_stocks(self, client):
        """Test valuations page performance with 100 stocks."""
        # Arrange
        user = UserFactory()
        client.force_login(user)

        now = timezone.now()

        # Create 100 stocks
        for i in range(100):
            CuratedStockFactory(
                symbol=f'STOCK{i:03d}',
                active=True,
                intrinsic_value=Decimal('100.00'),
                current_price=Decimal(f'{90 - (i * 0.1):.2f}'),
                price_updated_at=now - timedelta(hours=1),
                preferred_valuation_method='EPS'
            )

        # Act
        url = reverse('scanner:valuations')
        response = client.get(url)

        # Assert - all stocks displayed, sorted correctly
        stocks = response.context['stocks_with_discount']
        assert len(stocks) == 100
        assert response.status_code == 200

        # Verify sorting (best discount first)
        discounts = [s['discount_pct'] for s in stocks if s['discount_pct'] is not None]
        assert discounts == sorted(discounts, reverse=True)
