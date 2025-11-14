"""
Tests for Phase 8: Stock Price Integration - fetch_stock_prices Management Command.

This module tests the fetch_stock_prices management command covering:
- Fetching all active stocks
- --symbols flag for specific stocks
- --force flag to override market hours
- --dry-run flag to preview without saving
- Market hours validation
- Success/failure counting
"""

import pytest
from io import StringIO
from decimal import Decimal
from unittest.mock import patch, Mock
from django.core.management import call_command
from django.utils import timezone

from scanner.factories import CuratedStockFactory


# ===== Basic Command Execution Tests =====

@pytest.mark.django_db
class TestFetchStockPricesBasic:
    """Tests for basic command execution."""

    @patch('scanner.management.commands.fetch_stock_prices.get_stock_quote')
    @patch('scanner.management.commands.fetch_stock_prices.timezone.localtime')
    def test_fetch_all_active_stocks(self, mock_localtime, mock_get_quote):
        """Test fetching prices for all active stocks."""
        # Arrange
        # Mock localtime to return a real datetime with hour=18
        from django.utils import timezone as tz
        now = tz.now()
        mock_time = now.replace(hour=18, minute=0, second=0, microsecond=0)
        mock_localtime.return_value = mock_time  # 6 PM (valid time)

        stock1 = CuratedStockFactory(symbol='AAPL', active=True)
        stock2 = CuratedStockFactory(symbol='MSFT', active=True)
        CuratedStockFactory(symbol='GOOGL', active=False)  # Inactive, should skip

        mock_get_quote.return_value = {
            'symbol': 'TEST',
            'price': Decimal('100.00'),
            'updated': 1763144253
        }

        out = StringIO()

        # Act
        call_command('fetch_stock_prices', stdout=out)

        # Assert
        assert mock_get_quote.call_count == 2  # Only active stocks
        output = out.getvalue()
        assert 'AAPL' in output
        assert 'MSFT' in output
        assert 'GOOGL' not in output
        assert 'Updated: 2/2' in output

    @patch('scanner.management.commands.fetch_stock_prices.get_stock_quote')
    @patch('scanner.management.commands.fetch_stock_prices.timezone.localtime')
    def test_fetch_updates_database(self, mock_localtime, mock_get_quote):
        """Test that successful fetch updates database fields."""
        # Arrange
        # Mock localtime to return a real datetime with hour=18
        from django.utils import timezone as tz
        now = tz.now()
        mock_time = now.replace(hour=18, minute=0, second=0, microsecond=0)
        mock_localtime.return_value = mock_time
        stock = CuratedStockFactory(
            symbol='AAPL',
            active=True,
            current_price=None,
            price_updated_at=None
        )

        mock_get_quote.return_value = {
            'symbol': 'AAPL',
            'price': Decimal('175.50'),
            'updated': 1763144253
        }

        out = StringIO()

        # Act
        call_command('fetch_stock_prices', stdout=out)

        # Assert
        stock.refresh_from_db()
        assert stock.current_price == Decimal('175.50')
        assert stock.price_updated_at is not None

    @patch('scanner.management.commands.fetch_stock_prices.get_stock_quote')
    @patch('scanner.management.commands.fetch_stock_prices.timezone.localtime')
    def test_fetch_only_updates_price_fields(self, mock_localtime, mock_get_quote):
        """Test that only current_price and price_updated_at are modified."""
        # Arrange
        # Mock localtime to return a real datetime with hour=18
        from django.utils import timezone as tz
        now = tz.now()
        mock_time = now.replace(hour=18, minute=0, second=0, microsecond=0)
        mock_localtime.return_value = mock_time
        original_notes = "Important stock"
        stock = CuratedStockFactory(
            symbol='MSFT',
            active=True,
            notes=original_notes,
            intrinsic_value=Decimal('200.00')
        )

        mock_get_quote.return_value = {
            'symbol': 'MSFT',
            'price': Decimal('150.00'),
            'updated': 1763144253
        }

        out = StringIO()

        # Act
        call_command('fetch_stock_prices', stdout=out)

        # Assert
        stock.refresh_from_db()
        assert stock.notes == original_notes  # Unchanged
        assert stock.intrinsic_value == Decimal('200.00')  # Unchanged
        assert stock.current_price == Decimal('150.00')  # Changed


# ===== --symbols Flag Tests =====

@pytest.mark.django_db
class TestFetchStockPricesSymbolsFlag:
    """Tests for --symbols command flag."""

    @patch('scanner.management.commands.fetch_stock_prices.get_stock_quote')
    @patch('scanner.management.commands.fetch_stock_prices.timezone.localtime')
    def test_symbols_flag_fetches_specific_stocks(self, mock_localtime, mock_get_quote):
        """Test --symbols flag fetches only specified stocks."""
        # Arrange
        # Mock localtime to return a real datetime with hour=18
        from django.utils import timezone as tz
        now = tz.now()
        mock_time = now.replace(hour=18, minute=0, second=0, microsecond=0)
        mock_localtime.return_value = mock_time

        CuratedStockFactory(symbol='AAPL', active=True)
        CuratedStockFactory(symbol='MSFT', active=True)
        CuratedStockFactory(symbol='GOOGL', active=True)

        mock_get_quote.return_value = {
            'symbol': 'TEST',
            'price': Decimal('100.00'),
            'updated': 1763144253
        }

        out = StringIO()

        # Act
        call_command('fetch_stock_prices', symbols=['AAPL', 'MSFT'], stdout=out)

        # Assert
        assert mock_get_quote.call_count == 2
        output = out.getvalue()
        assert 'AAPL' in output
        assert 'MSFT' in output
        assert 'GOOGL' not in output

    @patch('scanner.management.commands.fetch_stock_prices.get_stock_quote')
    @patch('scanner.management.commands.fetch_stock_prices.timezone.localtime')
    def test_symbols_flag_handles_case_insensitive(self, mock_localtime, mock_get_quote):
        """Test --symbols flag handles lowercase symbols."""
        # Arrange
        # Mock localtime to return a real datetime with hour=18
        from django.utils import timezone as tz
        now = tz.now()
        mock_time = now.replace(hour=18, minute=0, second=0, microsecond=0)
        mock_localtime.return_value = mock_time
        CuratedStockFactory(symbol='AAPL', active=True)

        mock_get_quote.return_value = {
            'symbol': 'AAPL',
            'price': Decimal('100.00'),
            'updated': 1763144253
        }

        out = StringIO()

        # Act
        call_command('fetch_stock_prices', symbols=['aapl'], stdout=out)  # lowercase

        # Assert
        assert mock_get_quote.call_count == 1
        output = out.getvalue()
        assert 'AAPL' in output

    @patch('scanner.management.commands.fetch_stock_prices.get_stock_quote')
    @patch('scanner.management.commands.fetch_stock_prices.timezone.localtime')
    def test_symbols_flag_with_nonexistent_symbol(self, mock_localtime, mock_get_quote):
        """Test --symbols flag with symbol not in database."""
        # Arrange
        # Mock localtime to return a real datetime with hour=18
        from django.utils import timezone as tz
        now = tz.now()
        mock_time = now.replace(hour=18, minute=0, second=0, microsecond=0)
        mock_localtime.return_value = mock_time
        CuratedStockFactory(symbol='AAPL', active=True)

        mock_get_quote.return_value = {
            'symbol': 'TEST',
            'price': Decimal('100.00'),
            'updated': 1763144253
        }

        out = StringIO()

        # Act
        call_command('fetch_stock_prices', symbols=['INVALID'], stdout=out)

        # Assert
        assert mock_get_quote.call_count == 0  # No stocks found to fetch
        output = out.getvalue()
        assert 'Fetching prices for 0 stocks' in output


# ===== --force Flag Tests =====

@pytest.mark.django_db
class TestFetchStockPricesForceFlag:
    """Tests for --force command flag to override market hours."""

    @patch('scanner.management.commands.fetch_stock_prices.get_stock_quote')
    @patch('scanner.management.commands.fetch_stock_prices.timezone.localtime')
    def test_force_flag_bypasses_market_hours_check(self, mock_localtime, mock_get_quote):
        """Test --force flag allows fetching outside normal hours."""
        # Arrange
        mock_localtime.return_value = Mock(hour=3)  # 3 AM (outside 5-8 PM)
        CuratedStockFactory(symbol='AAPL', active=True)

        mock_get_quote.return_value = {
            'symbol': 'AAPL',
            'price': Decimal('150.00'),
            'updated': 1763144253
        }

        out = StringIO()

        # Act
        call_command('fetch_stock_prices', force=True, stdout=out)

        # Assert
        assert mock_get_quote.call_count == 1
        output = out.getvalue()
        assert 'AAPL' in output

    @patch('scanner.management.commands.fetch_stock_prices.get_stock_quote')
    @patch('scanner.management.commands.fetch_stock_prices.timezone.localtime')
    def test_without_force_flag_blocks_outside_hours(self, mock_localtime, mock_get_quote):
        """Test command blocks execution outside normal hours without --force."""
        # Arrange
        mock_localtime.return_value = Mock(hour=3)  # 3 AM (outside 5-8 PM)
        CuratedStockFactory(symbol='AAPL', active=True)

        out = StringIO()

        # Act
        call_command('fetch_stock_prices', stdout=out)

        # Assert
        assert mock_get_quote.call_count == 0  # Should not fetch
        output = out.getvalue()
        assert 'Outside normal update window' in output
        assert 'Use --force to override' in output

    @patch('scanner.management.commands.fetch_stock_prices.get_stock_quote')
    @patch('scanner.management.commands.fetch_stock_prices.timezone.localtime')
    def test_normal_hours_allows_execution(self, mock_localtime, mock_get_quote):
        """Test command executes normally during 5-8 PM ET."""
        # Arrange
        # Mock localtime to return a real datetime with hour=18
        from django.utils import timezone as tz
        now = tz.now()
        mock_time = now.replace(hour=18, minute=0, second=0, microsecond=0)
        mock_localtime.return_value = mock_time  # 6 PM
        CuratedStockFactory(symbol='AAPL', active=True)

        mock_get_quote.return_value = {
            'symbol': 'AAPL',
            'price': Decimal('150.00'),
            'updated': 1763144253
        }

        out = StringIO()

        # Act
        call_command('fetch_stock_prices', stdout=out)

        # Assert
        assert mock_get_quote.call_count == 1

    @patch('scanner.management.commands.fetch_stock_prices.get_stock_quote')
    @patch('scanner.management.commands.fetch_stock_prices.timezone.localtime')
    def test_market_hours_boundary_5pm(self, mock_localtime, mock_get_quote):
        """Test market hours at 5 PM boundary."""
        # Arrange
        mock_localtime.return_value = Mock(hour=17)  # 5 PM (start of window)
        CuratedStockFactory(symbol='AAPL', active=True)

        mock_get_quote.return_value = {
            'symbol': 'AAPL',
            'price': Decimal('150.00'),
            'updated': 1763144253
        }

        out = StringIO()

        # Act
        call_command('fetch_stock_prices', stdout=out)

        # Assert
        assert mock_get_quote.call_count == 1  # Should execute

    @patch('scanner.management.commands.fetch_stock_prices.get_stock_quote')
    @patch('scanner.management.commands.fetch_stock_prices.timezone.localtime')
    def test_market_hours_boundary_8pm(self, mock_localtime, mock_get_quote):
        """Test market hours at 8 PM boundary."""
        # Arrange
        mock_localtime.return_value = Mock(hour=20)  # 8 PM (end of window)
        CuratedStockFactory(symbol='AAPL', active=True)

        mock_get_quote.return_value = {
            'symbol': 'AAPL',
            'price': Decimal('150.00'),
            'updated': 1763144253
        }

        out = StringIO()

        # Act
        call_command('fetch_stock_prices', stdout=out)

        # Assert
        assert mock_get_quote.call_count == 1  # Should execute


# ===== --dry-run Flag Tests =====

@pytest.mark.django_db
class TestFetchStockPricesDryRunFlag:
    """Tests for --dry-run command flag."""

    @patch('scanner.management.commands.fetch_stock_prices.get_stock_quote')
    @patch('scanner.management.commands.fetch_stock_prices.timezone.localtime')
    def test_dry_run_flag_does_not_save_to_database(self, mock_localtime, mock_get_quote):
        """Test --dry-run flag fetches but doesn't save to database."""
        # Arrange
        # Mock localtime to return a real datetime with hour=18
        from django.utils import timezone as tz
        now = tz.now()
        mock_time = now.replace(hour=18, minute=0, second=0, microsecond=0)
        mock_localtime.return_value = mock_time
        stock = CuratedStockFactory(
            symbol='AAPL',
            active=True,
            current_price=None,
            price_updated_at=None
        )

        mock_get_quote.return_value = {
            'symbol': 'AAPL',
            'price': Decimal('175.50'),
            'updated': 1763144253
        }

        out = StringIO()

        # Act
        call_command('fetch_stock_prices', dry_run=True, stdout=out)

        # Assert
        stock.refresh_from_db()
        assert stock.current_price is None  # Should not be updated
        assert stock.price_updated_at is None  # Should not be updated

    @patch('scanner.management.commands.fetch_stock_prices.get_stock_quote')
    @patch('scanner.management.commands.fetch_stock_prices.timezone.localtime')
    def test_dry_run_flag_displays_would_update_message(self, mock_localtime, mock_get_quote):
        """Test --dry-run flag displays preview message."""
        # Arrange
        # Mock localtime to return a real datetime with hour=18
        from django.utils import timezone as tz
        now = tz.now()
        mock_time = now.replace(hour=18, minute=0, second=0, microsecond=0)
        mock_localtime.return_value = mock_time
        CuratedStockFactory(symbol='AAPL', active=True)

        mock_get_quote.return_value = {
            'symbol': 'AAPL',
            'price': Decimal('175.50'),
            'updated': 1763144253
        }

        out = StringIO()

        # Act
        call_command('fetch_stock_prices', dry_run=True, stdout=out)

        # Assert
        output = out.getvalue()
        assert '[DRY RUN]' in output
        assert 'Would update AAPL' in output
        assert '175.50' in output
        assert 'No changes saved' in output

    @patch('scanner.management.commands.fetch_stock_prices.get_stock_quote')
    @patch('scanner.management.commands.fetch_stock_prices.timezone.localtime')
    def test_dry_run_flag_still_calls_api(self, mock_localtime, mock_get_quote):
        """Test --dry-run still makes API calls (to verify connectivity)."""
        # Arrange
        # Mock localtime to return a real datetime with hour=18
        from django.utils import timezone as tz
        now = tz.now()
        mock_time = now.replace(hour=18, minute=0, second=0, microsecond=0)
        mock_localtime.return_value = mock_time
        CuratedStockFactory(symbol='AAPL', active=True)
        CuratedStockFactory(symbol='MSFT', active=True)

        mock_get_quote.return_value = {
            'symbol': 'TEST',
            'price': Decimal('100.00'),
            'updated': 1763144253
        }

        out = StringIO()

        # Act
        call_command('fetch_stock_prices', dry_run=True, stdout=out)

        # Assert
        assert mock_get_quote.call_count == 2  # API calls still made


# ===== Error Handling Tests =====

@pytest.mark.django_db
class TestFetchStockPricesErrorHandling:
    """Tests for error handling and failure scenarios."""

    @patch('scanner.management.commands.fetch_stock_prices.get_stock_quote')
    @patch('scanner.management.commands.fetch_stock_prices.timezone.localtime')
    def test_failed_api_call_increments_failed_count(self, mock_localtime, mock_get_quote):
        """Test that failed API calls are counted correctly."""
        # Arrange
        # Mock localtime to return a real datetime with hour=18
        from django.utils import timezone as tz
        now = tz.now()
        mock_time = now.replace(hour=18, minute=0, second=0, microsecond=0)
        mock_localtime.return_value = mock_time
        CuratedStockFactory(symbol='AAPL', active=True)
        CuratedStockFactory(symbol='MSFT', active=True)

        # First call succeeds, second fails
        mock_get_quote.side_effect = [
            {'symbol': 'AAPL', 'price': Decimal('100.00'), 'updated': 1763144253},
            None  # API failure
        ]

        out = StringIO()

        # Act
        call_command('fetch_stock_prices', stdout=out)

        # Assert
        output = out.getvalue()
        assert 'Updated: 1/2' in output
        assert 'Failed: MSFT' in output

    @patch('scanner.management.commands.fetch_stock_prices.get_stock_quote')
    @patch('scanner.management.commands.fetch_stock_prices.timezone.localtime')
    def test_failed_api_call_does_not_update_database(self, mock_localtime, mock_get_quote):
        """Test that failed fetch doesn't modify database."""
        # Arrange
        # Mock localtime to return a real datetime with hour=18
        from django.utils import timezone as tz
        now = tz.now()
        mock_time = now.replace(hour=18, minute=0, second=0, microsecond=0)
        mock_localtime.return_value = mock_time
        stock = CuratedStockFactory(
            symbol='AAPL',
            active=True,
            current_price=Decimal('150.00'),
            price_updated_at=timezone.now()
        )
        original_price = stock.current_price
        original_timestamp = stock.price_updated_at

        mock_get_quote.return_value = None  # API failure

        out = StringIO()

        # Act
        call_command('fetch_stock_prices', stdout=out)

        # Assert
        stock.refresh_from_db()
        assert stock.current_price == original_price  # Unchanged
        assert stock.price_updated_at == original_timestamp  # Unchanged

    @patch('scanner.management.commands.fetch_stock_prices.get_stock_quote')
    @patch('scanner.management.commands.fetch_stock_prices.timezone.localtime')
    def test_all_failures_shows_error_summary(self, mock_localtime, mock_get_quote):
        """Test summary when all API calls fail."""
        # Arrange
        # Mock localtime to return a real datetime with hour=18
        from django.utils import timezone as tz
        now = tz.now()
        mock_time = now.replace(hour=18, minute=0, second=0, microsecond=0)
        mock_localtime.return_value = mock_time
        CuratedStockFactory(symbol='AAPL', active=True)
        CuratedStockFactory(symbol='MSFT', active=True)

        mock_get_quote.return_value = None  # All calls fail

        out = StringIO()

        # Act
        call_command('fetch_stock_prices', stdout=out)

        # Assert
        output = out.getvalue()
        assert 'Updated: 0/2' in output
        assert 'Failed: AAPL, MSFT' in output


# ===== Summary Output Tests =====

@pytest.mark.django_db
class TestFetchStockPricesSummary:
    """Tests for command summary output."""

    @patch('scanner.management.commands.fetch_stock_prices.get_stock_quote')
    @patch('scanner.management.commands.fetch_stock_prices.timezone.localtime')
    def test_summary_shows_total_count(self, mock_localtime, mock_get_quote):
        """Test summary displays total stock count."""
        # Arrange
        # Mock localtime to return a real datetime with hour=18
        from django.utils import timezone as tz
        now = tz.now()
        mock_time = now.replace(hour=18, minute=0, second=0, microsecond=0)
        mock_localtime.return_value = mock_time
        CuratedStockFactory(symbol='AAPL', active=True)
        CuratedStockFactory(symbol='MSFT', active=True)
        CuratedStockFactory(symbol='GOOGL', active=True)

        mock_get_quote.return_value = {
            'symbol': 'TEST',
            'price': Decimal('100.00'),
            'updated': 1763144253
        }

        out = StringIO()

        # Act
        call_command('fetch_stock_prices', stdout=out)

        # Assert
        output = out.getvalue()
        assert 'Fetching prices for 3 stocks' in output

    @patch('scanner.management.commands.fetch_stock_prices.get_stock_quote')
    @patch('scanner.management.commands.fetch_stock_prices.timezone.localtime')
    def test_summary_shows_success_checkmark(self, mock_localtime, mock_get_quote):
        """Test successful update shows checkmark."""
        # Arrange
        # Mock localtime to return a real datetime with hour=18
        from django.utils import timezone as tz
        now = tz.now()
        mock_time = now.replace(hour=18, minute=0, second=0, microsecond=0)
        mock_localtime.return_value = mock_time
        CuratedStockFactory(symbol='AAPL', active=True)

        mock_get_quote.return_value = {
            'symbol': 'AAPL',
            'price': Decimal('175.50'),
            'updated': 1763144253
        }

        out = StringIO()

        # Act
        call_command('fetch_stock_prices', stdout=out)

        # Assert
        output = out.getvalue()
        assert '✓ AAPL' in output
        assert '$175.50' in output

    @patch('scanner.management.commands.fetch_stock_prices.get_stock_quote')
    @patch('scanner.management.commands.fetch_stock_prices.timezone.localtime')
    def test_summary_shows_failure_x_mark(self, mock_localtime, mock_get_quote):
        """Test failed update shows X mark."""
        # Arrange
        # Mock localtime to return a real datetime with hour=18
        from django.utils import timezone as tz
        now = tz.now()
        mock_time = now.replace(hour=18, minute=0, second=0, microsecond=0)
        mock_localtime.return_value = mock_time
        CuratedStockFactory(symbol='FAIL', active=True)

        mock_get_quote.return_value = None

        out = StringIO()

        # Act
        call_command('fetch_stock_prices', stdout=out)

        # Assert
        output = out.getvalue()
        assert '✗ FAIL' in output
        assert 'Failed to fetch' in output


# ===== Integration Tests =====

@pytest.mark.django_db
class TestFetchStockPricesIntegration:
    """Integration tests for complete command workflows."""

    @patch('scanner.management.commands.fetch_stock_prices.get_stock_quote')
    @patch('scanner.management.commands.fetch_stock_prices.timezone.localtime')
    def test_complete_workflow_all_flags_combined(self, mock_localtime, mock_get_quote):
        """Test command with multiple flags combined."""
        # Arrange
        mock_localtime.return_value = Mock(hour=3)  # Outside normal hours
        stock = CuratedStockFactory(
            symbol='AAPL',
            active=True,
            current_price=None
        )

        mock_get_quote.return_value = {
            'symbol': 'AAPL',
            'price': Decimal('175.50'),
            'updated': 1763144253
        }

        out = StringIO()

        # Act
        call_command(
            'fetch_stock_prices',
            symbols=['AAPL'],
            force=True,
            dry_run=True,
            stdout=out
        )

        # Assert
        output = out.getvalue()
        assert '[DRY RUN]' in output
        assert 'AAPL' in output

        stock.refresh_from_db()
        assert stock.current_price is None  # Dry run didn't save

    @patch('scanner.management.commands.fetch_stock_prices.get_stock_quote')
    @patch('scanner.management.commands.fetch_stock_prices.timezone.localtime')
    def test_complete_workflow_mixed_success_failure(self, mock_localtime, mock_get_quote):
        """Test command with mix of successful and failed fetches."""
        # Arrange
        # Mock localtime to return a real datetime with hour=18
        from django.utils import timezone as tz
        now = tz.now()
        mock_time = now.replace(hour=18, minute=0, second=0, microsecond=0)
        mock_localtime.return_value = mock_time
        stock1 = CuratedStockFactory(symbol='AAPL', active=True)
        stock2 = CuratedStockFactory(symbol='MSFT', active=True)
        stock3 = CuratedStockFactory(symbol='GOOGL', active=True)

        # Mock responses in alphabetical order: AAPL, GOOGL, MSFT
        # AAPL success, GOOGL success, MSFT failure
        mock_get_quote.side_effect = [
            {'symbol': 'AAPL', 'price': Decimal('150.00'), 'updated': 1763144253},
            {'symbol': 'GOOGL', 'price': Decimal('140.00'), 'updated': 1763144253},
            None  # MSFT fails
        ]

        out = StringIO()

        # Act
        call_command('fetch_stock_prices', stdout=out)

        # Assert
        output = out.getvalue()
        assert 'Updated: 2/3' in output
        assert '✓ AAPL' in output
        assert '✗ MSFT' in output
        assert '✓ GOOGL' in output

        stock1.refresh_from_db()
        stock2.refresh_from_db()
        stock3.refresh_from_db()

        assert stock1.current_price == Decimal('150.00')  # AAPL success
        assert stock2.current_price is None  # MSFT failed
        assert stock3.current_price == Decimal('140.00')  # GOOGL success
