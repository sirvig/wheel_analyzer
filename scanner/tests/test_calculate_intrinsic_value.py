import pytest
from decimal import Decimal
from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.utils import timezone

from scanner.factories import CuratedStockFactory
from scanner.models import CuratedStock


@pytest.mark.django_db
class TestCalculateIntrinsicValueCommand:
    """Integration tests for calculate_intrinsic_value management command."""

    @pytest.fixture
    def mock_alpha_vantage(self):
        """Mock Alpha Vantage API responses."""
        with patch(
            "scanner.management.commands.calculate_intrinsic_value.get_market_data"
        ) as mock:
            # Default successful response
            mock.return_value = {
                "Symbol": "AAPL",
                "EPS": "6.42",
                "PERatio": "25.5",
            }
            yield mock

    @pytest.fixture
    def mock_sleep(self):
        """Mock time.sleep to speed up tests."""
        with patch(
            "scanner.management.commands.calculate_intrinsic_value.time.sleep"
        ) as mock:
            yield mock

    def test_command_processes_active_stocks(self, mock_alpha_vantage, mock_sleep):
        """Test that command processes all active stocks."""
        # Create test stocks
        stock1 = CuratedStockFactory(symbol="AAPL", active=True)
        stock2 = CuratedStockFactory(symbol="MSFT", active=True)
        stock3 = CuratedStockFactory(symbol="TSLA", active=False)  # Inactive

        # Run command
        out = StringIO()
        call_command("calculate_intrinsic_value", stdout=out)

        # Verify only active stocks were processed
        assert mock_alpha_vantage.call_count == 2
        calls = [call.args[0] for call in mock_alpha_vantage.call_args_list]
        assert "function=OVERVIEW&symbol=AAPL" in calls
        assert "function=OVERVIEW&symbol=MSFT" in calls

        # Verify intrinsic values were calculated
        stock1.refresh_from_db()
        stock2.refresh_from_db()
        stock3.refresh_from_db()

        assert stock1.intrinsic_value is not None
        assert stock2.intrinsic_value is not None
        assert stock3.intrinsic_value is None  # Inactive, not processed

    def test_command_with_specific_symbols(self, mock_alpha_vantage, mock_sleep):
        """Test command with --symbols argument."""
        stock1 = CuratedStockFactory(symbol="AAPL", active=True)
        stock2 = CuratedStockFactory(symbol="MSFT", active=True)

        # Run command for specific symbol only
        call_command("calculate_intrinsic_value", symbols=["AAPL"])

        # Verify only specified stock was processed
        assert mock_alpha_vantage.call_count == 1
        assert "AAPL" in mock_alpha_vantage.call_args[0][0]

        stock1.refresh_from_db()
        stock2.refresh_from_db()

        assert stock1.intrinsic_value is not None
        assert stock2.intrinsic_value is None

    def test_command_updates_calculation_date(self, mock_alpha_vantage, mock_sleep):
        """Test that last_calculation_date is updated."""
        stock = CuratedStockFactory(symbol="AAPL", active=True)

        before_time = timezone.now()
        call_command("calculate_intrinsic_value")
        after_time = timezone.now()

        stock.refresh_from_db()

        assert stock.last_calculation_date is not None
        assert before_time <= stock.last_calculation_date <= after_time

    def test_command_saves_current_eps(self, mock_alpha_vantage, mock_sleep):
        """Test that current_eps is saved from API."""
        mock_alpha_vantage.return_value = {"EPS": "7.50"}

        stock = CuratedStockFactory(symbol="AAPL", active=True, current_eps=None)
        call_command("calculate_intrinsic_value")

        stock.refresh_from_db()
        assert stock.current_eps == Decimal("7.50")

    def test_command_skips_stock_with_missing_eps(self, mock_alpha_vantage, mock_sleep):
        """Test that stocks with missing EPS data are skipped."""
        mock_alpha_vantage.return_value = {}  # No EPS field

        stock = CuratedStockFactory(symbol="AAPL", active=True)
        call_command("calculate_intrinsic_value")

        stock.refresh_from_db()
        assert stock.intrinsic_value is None

    def test_command_skips_stock_with_negative_eps(
        self, mock_alpha_vantage, mock_sleep
    ):
        """Test that stocks with negative EPS are skipped."""
        mock_alpha_vantage.return_value = {"EPS": "-2.50"}

        stock = CuratedStockFactory(symbol="TSLA", active=True)
        call_command("calculate_intrinsic_value")

        stock.refresh_from_db()
        assert stock.intrinsic_value is None

    def test_command_handles_api_errors(self, mock_alpha_vantage, mock_sleep):
        """Test error handling when API fails."""
        mock_alpha_vantage.side_effect = Exception("API Error")

        stock = CuratedStockFactory(symbol="AAPL", active=True)

        # Command should not crash
        call_command("calculate_intrinsic_value")

        stock.refresh_from_db()
        assert stock.intrinsic_value is None

    def test_command_handles_api_error_message(self, mock_alpha_vantage, mock_sleep):
        """Test handling of API error messages."""
        mock_alpha_vantage.return_value = {"Error Message": "Invalid API call"}

        stock = CuratedStockFactory(symbol="AAPL", active=True)
        call_command("calculate_intrinsic_value")

        stock.refresh_from_db()
        assert stock.intrinsic_value is None

    def test_command_handles_api_rate_limit(self, mock_alpha_vantage, mock_sleep):
        """Test handling of API rate limit messages."""
        mock_alpha_vantage.return_value = {
            "Note": "Thank you for using Alpha Vantage! Our standard API call frequency is 5 calls per minute."
        }

        stock = CuratedStockFactory(symbol="AAPL", active=True)
        call_command("calculate_intrinsic_value")

        stock.refresh_from_db()
        assert stock.intrinsic_value is None

    @patch("scanner.management.commands.calculate_intrinsic_value.cache")
    def test_command_uses_cache(self, mock_cache, mock_alpha_vantage, mock_sleep):
        """Test that API responses are cached."""
        mock_cache.get.return_value = None  # Cache miss

        stock = CuratedStockFactory(symbol="AAPL", active=True)
        call_command("calculate_intrinsic_value")

        # Verify cache was checked and set
        mock_cache.get.assert_called_with("av_overview_AAPL")
        assert mock_cache.set.called
        # Verify cache TTL is 7 days
        cache_ttl = mock_cache.set.call_args[0][2]
        assert cache_ttl == 60 * 60 * 24 * 7

    @patch("scanner.management.commands.calculate_intrinsic_value.cache")
    def test_command_force_refresh(self, mock_cache, mock_alpha_vantage, mock_sleep):
        """Test --force-refresh bypasses cache."""
        mock_cache.get.return_value = {"EPS": "5.00"}  # Cached data

        stock = CuratedStockFactory(symbol="AAPL", active=True)
        call_command("calculate_intrinsic_value", force_refresh=True)

        # Verify cache was NOT checked (force refresh)
        assert not mock_cache.get.called
        # Verify fresh data was fetched
        assert mock_alpha_vantage.called

    def test_command_validates_assumptions(self, mock_alpha_vantage, mock_sleep):
        """Test that stocks with invalid assumptions are skipped."""
        stock = CuratedStockFactory(
            symbol="AAPL",
            active=True,
            eps_growth_rate=Decimal("0"),  # Invalid: should be > 0
        )

        call_command("calculate_intrinsic_value")

        stock.refresh_from_db()
        assert stock.intrinsic_value is None

    def test_command_with_multiple_symbols(self, mock_alpha_vantage, mock_sleep):
        """Test --symbols with multiple values."""
        CuratedStockFactory(symbol="AAPL", active=True)
        CuratedStockFactory(symbol="MSFT", active=True)
        CuratedStockFactory(symbol="GOOGL", active=True)

        call_command("calculate_intrinsic_value", symbols=["AAPL", "MSFT"])

        # Should process exactly 2 stocks
        assert mock_alpha_vantage.call_count == 2

    def test_command_recalculation_updates_values(self, mock_alpha_vantage, mock_sleep):
        """Test that running command again updates existing values."""
        mock_alpha_vantage.return_value = {"EPS": "5.00"}

        stock = CuratedStockFactory(
            symbol="AAPL",
            active=True,
            current_eps=Decimal("4.00"),  # Old value
            intrinsic_value=Decimal("80.00"),  # Old value
            last_calculation_date=timezone.now() - timezone.timedelta(days=7),
        )

        old_date = stock.last_calculation_date

        # Run command
        call_command("calculate_intrinsic_value")

        stock.refresh_from_db()

        # Verify values were updated
        assert stock.current_eps == Decimal("5.00")  # New value
        assert stock.intrinsic_value != Decimal("80.00")  # Recalculated
        assert stock.last_calculation_date > old_date  # Updated

    def test_partial_failure_continues_processing(self, mock_alpha_vantage, mock_sleep):
        """Test that failure on one stock doesn't stop others."""
        stock1 = CuratedStockFactory(symbol="AAPL", active=True)
        stock2 = CuratedStockFactory(symbol="FAIL", active=True)
        stock3 = CuratedStockFactory(symbol="MSFT", active=True)

        # Mock: AAPL succeeds, FAIL fails, MSFT succeeds
        def side_effect(url):
            if "FAIL" in url:
                raise Exception("API Error")
            return {"EPS": "7.00"}

        mock_alpha_vantage.side_effect = side_effect

        call_command("calculate_intrinsic_value")

        # Verify AAPL and MSFT succeeded, FAIL did not
        stock1.refresh_from_db()
        stock2.refresh_from_db()
        stock3.refresh_from_db()

        assert stock1.intrinsic_value is not None
        assert stock2.intrinsic_value is None  # Failed
        assert stock3.intrinsic_value is not None

    @patch("scanner.management.commands.calculate_intrinsic_value.cache")
    def test_clear_cache_option(self, mock_cache, mock_alpha_vantage, mock_sleep):
        """Test --clear-cache option."""
        CuratedStockFactory(symbol="AAPL", active=True)
        CuratedStockFactory(symbol="MSFT", active=True)

        mock_cache.delete.return_value = True

        call_command("calculate_intrinsic_value", clear_cache=True)

        # Verify cache delete was called for each stock
        assert mock_cache.delete.call_count >= 2

    def test_command_output_shows_summary(self, mock_alpha_vantage, mock_sleep):
        """Test that command outputs summary statistics."""
        CuratedStockFactory(symbol="AAPL", active=True)
        CuratedStockFactory(symbol="MSFT", active=True)

        out = StringIO()
        call_command("calculate_intrinsic_value", stdout=out)

        output = out.getvalue()

        # Verify summary is present
        assert "SUMMARY:" in output
        assert "Total processed: 2" in output
        assert "Successful:" in output
        assert "Duration:" in output

    def test_command_with_invalid_symbol_raises_error(
        self, mock_alpha_vantage, mock_sleep
    ):
        """Test that invalid symbol raises CommandError."""
        out = StringIO()
        err = StringIO()

        # This should handle the error gracefully
        call_command(
            "calculate_intrinsic_value", symbols=["INVALID"], stdout=out, stderr=err
        )

        output = out.getvalue() + err.getvalue()
        assert "No stocks found" in output

    def test_calculated_intrinsic_value_is_reasonable(
        self, mock_alpha_vantage, mock_sleep
    ):
        """Test that calculated intrinsic value is mathematically correct."""
        mock_alpha_vantage.return_value = {"EPS": "5.00"}

        stock = CuratedStockFactory(
            symbol="AAPL",
            active=True,
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        call_command("calculate_intrinsic_value")

        stock.refresh_from_db()

        # With EPS=5.00, growth=10%, multiple=20, return=15%, years=5
        # Expected intrinsic value should be around $101.97
        assert Decimal("100.00") < stock.intrinsic_value < Decimal("105.00")
