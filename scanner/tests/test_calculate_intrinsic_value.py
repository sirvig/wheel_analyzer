import pytest
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.utils import timezone

from scanner.factories import CuratedStockFactory


@pytest.mark.django_db(transaction=True)
class TestCalculateIntrinsicValueCommand:
    """Integration tests for calculate_intrinsic_value management command."""

    @pytest.fixture
    def mock_alpha_vantage(self):
        """Mock Alpha Vantage API responses."""
        with patch(
            "scanner.management.commands.calculate_intrinsic_value.get_market_data"
        ) as mock:
            # Default successful response for all endpoints
            def side_effect(url):
                if "EARNINGS" in url:
                    return {
                        "quarterlyEarnings": [
                            {"fiscalDateEnding": "2024-09-30", "reportedEPS": "1.64"},
                            {"fiscalDateEnding": "2024-06-30", "reportedEPS": "1.40"},
                            {"fiscalDateEnding": "2024-03-31", "reportedEPS": "1.53"},
                            {"fiscalDateEnding": "2023-12-31", "reportedEPS": "1.85"},
                        ]
                    }
                elif "OVERVIEW" in url:
                    # Still needed for FCF (SharesOutstanding)
                    return {
                        "Symbol": "AAPL",
                        "SharesOutstanding": "15000000000",
                    }
                elif "CASH_FLOW" in url:
                    # For FCF calculation
                    return {
                        "quarterlyReports": [
                            {
                                "operatingCashflow": "30000000000",
                                "capitalExpenditures": "-2500000000",
                            },
                            {
                                "operatingCashflow": "31000000000",
                                "capitalExpenditures": "-2600000000",
                            },
                            {
                                "operatingCashflow": "29500000000",
                                "capitalExpenditures": "-2400000000",
                            },
                            {
                                "operatingCashflow": "32000000000",
                                "capitalExpenditures": "-2700000000",
                            },
                        ]
                    }
                return {}
            
            mock.side_effect = side_effect
            yield mock

    @pytest.fixture
    def mock_sleep(self):
        """Mock time.sleep to speed up tests."""
        with patch(
            "scanner.management.commands.calculate_intrinsic_value.time.sleep"
        ) as mock:
            yield mock

    def test_command_processes_active_stocks(
        self, mock_alpha_vantage, mock_sleep, clean_curated_stocks
    ):
        """Test that command processes all active stocks."""
        # Create test stocks
        stock1 = CuratedStockFactory(symbol="AAPL", active=True)
        stock2 = CuratedStockFactory(symbol="MSFT", active=True)
        stock3 = CuratedStockFactory(symbol="TSLA", active=False)  # Inactive

        # Run command
        out = StringIO()
        call_command("calculate_intrinsic_value", stdout=out)

        # Verify only active stocks were processed (3 API calls per stock: EARNINGS, OVERVIEW, CASH_FLOW)
        assert mock_alpha_vantage.call_count == 6  # 2 stocks * 3 calls each
        calls = [call.args[0] for call in mock_alpha_vantage.call_args_list]
        # Check for EARNINGS calls (primary endpoint for EPS)
        assert any("function=EARNINGS&symbol=AAPL" in call for call in calls)
        assert any("function=EARNINGS&symbol=MSFT" in call for call in calls)

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

        # Verify only specified stock was processed (3 API calls: EARNINGS, OVERVIEW, CASH_FLOW)
        assert mock_alpha_vantage.call_count == 3
        calls = [call.args[0] for call in mock_alpha_vantage.call_args_list]
        assert any("AAPL" in call for call in calls)

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
        """Test that current_eps is saved from API (sum of 4 quarters)."""
        stock = CuratedStockFactory(symbol="AAPL", active=True, current_eps=None)
        call_command("calculate_intrinsic_value")

        stock.refresh_from_db()
        # EPS TTM = 1.64 + 1.40 + 1.53 + 1.85 = 6.42
        assert stock.current_eps == Decimal("6.42")

    def test_command_skips_stock_with_missing_eps(self, mock_alpha_vantage, mock_sleep):
        """Test that stocks with missing EPS data are skipped."""
        # Override mock to return no quarterly earnings
        def side_effect(url):
            if "EARNINGS" in url:
                return {}  # No quarterlyEarnings field
            elif "OVERVIEW" in url:
                return {}  # No EPS field
            return {}
        
        mock_alpha_vantage.side_effect = side_effect

        stock = CuratedStockFactory(symbol="AAPL", active=True)
        call_command("calculate_intrinsic_value")

        stock.refresh_from_db()
        assert stock.intrinsic_value is None

    def test_command_skips_stock_with_negative_eps(
        self, mock_alpha_vantage, mock_sleep
    ):
        """Test that stocks with negative EPS are skipped."""
        # Override mock to return negative EPS
        def side_effect(url):
            if "EARNINGS" in url:
                return {
                    "quarterlyEarnings": [
                        {"fiscalDateEnding": "2024-09-30", "reportedEPS": "-0.50"},
                        {"fiscalDateEnding": "2024-06-30", "reportedEPS": "-0.60"},
                        {"fiscalDateEnding": "2024-03-31", "reportedEPS": "-0.70"},
                        {"fiscalDateEnding": "2023-12-31", "reportedEPS": "-0.70"},
                    ]
                }
            return {}
        
        mock_alpha_vantage.side_effect = side_effect

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
        def side_effect(url):
            return {"Error Message": "Invalid API call"}
        
        mock_alpha_vantage.side_effect = side_effect

        stock = CuratedStockFactory(symbol="AAPL", active=True)
        call_command("calculate_intrinsic_value")

        stock.refresh_from_db()
        assert stock.intrinsic_value is None

    def test_command_handles_api_rate_limit(self, mock_alpha_vantage, mock_sleep):
        """Test handling of API rate limit messages."""
        def side_effect(url):
            return {
                "Note": "Thank you for using Alpha Vantage! Our standard API call frequency is 5 calls per minute."
            }
        
        mock_alpha_vantage.side_effect = side_effect

        stock = CuratedStockFactory(symbol="AAPL", active=True)
        call_command("calculate_intrinsic_value")

        stock.refresh_from_db()
        assert stock.intrinsic_value is None

    @patch("scanner.management.commands.calculate_intrinsic_value.cache")
    def test_command_uses_cache(self, mock_cache, mock_alpha_vantage, mock_sleep):
        """Test that API responses are cached."""
        mock_cache.get.return_value = None  # Cache miss

        CuratedStockFactory(symbol="AAPL", active=True)
        call_command("calculate_intrinsic_value")

        # Verify cache was checked and set for all 3 endpoints
        cache_get_calls = [call[0][0] for call in mock_cache.get.call_args_list]
        assert "av_earnings_AAPL" in cache_get_calls
        assert "av_overview_AAPL" in cache_get_calls
        assert "av_cashflow_AAPL" in cache_get_calls
        
        # Verify cache.set was called (for all 3 endpoints)
        assert mock_cache.set.call_count >= 3
        
        # Verify cache TTL is 7 days
        cache_ttl = mock_cache.set.call_args[0][2]
        assert cache_ttl == 60 * 60 * 24 * 7

    @patch("scanner.management.commands.calculate_intrinsic_value.cache")
    def test_command_force_refresh(self, mock_cache, mock_alpha_vantage, mock_sleep):
        """Test --force-refresh bypasses cache for primary data."""
        # Set up mock to return None for cache misses
        mock_cache.get.return_value = None

        CuratedStockFactory(symbol="AAPL", active=True)
        call_command("calculate_intrinsic_value", force_refresh=True)

        # Verify fresh data was fetched from API (not from cache)
        assert mock_alpha_vantage.called
        # Verify data was cached after fetching
        assert mock_cache.set.called

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

        # Should process exactly 2 stocks (3 API calls each = 6 total)
        assert mock_alpha_vantage.call_count == 6

    def test_command_recalculation_updates_values(self, mock_alpha_vantage, mock_sleep):
        """Test that running command again updates existing values."""
        stock = CuratedStockFactory(
            symbol="AAPL",
            active=True,
            current_eps=Decimal("4.00"),  # Old value
            intrinsic_value=Decimal("80.00"),  # Old value
            last_calculation_date=timezone.now() - timezone.timedelta(days=7),
        )

        old_date = stock.last_calculation_date

        # Run command (will use default mock which returns EPS TTM = 6.42)
        call_command("calculate_intrinsic_value")

        stock.refresh_from_db()

        # Verify values were updated
        assert stock.current_eps == Decimal("6.42")  # New value from mock
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
            # Return normal data for AAPL and MSFT
            if "EARNINGS" in url:
                return {
                    "quarterlyEarnings": [
                        {"fiscalDateEnding": "2024-09-30", "reportedEPS": "1.75"},
                        {"fiscalDateEnding": "2024-06-30", "reportedEPS": "1.75"},
                        {"fiscalDateEnding": "2024-03-31", "reportedEPS": "1.75"},
                        {"fiscalDateEnding": "2023-12-31", "reportedEPS": "1.75"},
                    ]
                }
            elif "OVERVIEW" in url:
                return {"SharesOutstanding": "15000000000"}
            elif "CASH_FLOW" in url:
                return {
                    "quarterlyReports": [
                        {"operatingCashflow": "30000000000", "capitalExpenditures": "-2500000000"},
                        {"operatingCashflow": "31000000000", "capitalExpenditures": "-2600000000"},
                        {"operatingCashflow": "29500000000", "capitalExpenditures": "-2400000000"},
                        {"operatingCashflow": "32000000000", "capitalExpenditures": "-2700000000"},
                    ]
                }
            return {}

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

        # Verify cache delete was called for each stock (3 cache keys per stock)
        # 2 stocks * 3 cache keys = 6 delete calls
        assert mock_cache.delete.call_count >= 6

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

        # With EPS TTM=6.42 (from mock), growth=10%, multiple=20, return=15%, years=5
        # Expected intrinsic value should be around $130-140
        assert Decimal("120.00") < stock.intrinsic_value < Decimal("145.00")


@pytest.mark.django_db(transaction=True)
class TestEndToEndValuationFlow:
    """Test complete end-to-end valuation workflow."""

    @pytest.fixture
    def mock_alpha_vantage(self):
        """Mock Alpha Vantage API responses."""
        with patch(
            "scanner.management.commands.calculate_intrinsic_value.get_market_data"
        ) as mock:
            def side_effect(url):
                if "EARNINGS" in url:
                    return {
                        "quarterlyEarnings": [
                            {"fiscalDateEnding": "2024-09-30", "reportedEPS": "1.64"},
                            {"fiscalDateEnding": "2024-06-30", "reportedEPS": "1.40"},
                            {"fiscalDateEnding": "2024-03-31", "reportedEPS": "1.53"},
                            {"fiscalDateEnding": "2023-12-31", "reportedEPS": "1.85"},
                        ]
                    }
                elif "OVERVIEW" in url:
                    return {"SharesOutstanding": "15000000000"}
                elif "CASH_FLOW" in url:
                    return {
                        "quarterlyReports": [
                            {"operatingCashflow": "30000000000", "capitalExpenditures": "-2500000000"},
                            {"operatingCashflow": "31000000000", "capitalExpenditures": "-2600000000"},
                            {"operatingCashflow": "29500000000", "capitalExpenditures": "-2400000000"},
                            {"operatingCashflow": "32000000000", "capitalExpenditures": "-2700000000"},
                        ]
                    }
                return {}
            
            mock.side_effect = side_effect
            yield mock

    @pytest.fixture
    def mock_sleep(self):
        """Mock time.sleep to speed up tests."""
        with patch(
            "scanner.management.commands.calculate_intrinsic_value.time.sleep"
        ) as mock:
            yield mock

    def test_complete_workflow_single_stock(self, mock_alpha_vantage, mock_sleep):
        """Test complete workflow from API fetch to database save."""
        stock = CuratedStockFactory(
            symbol="TEST1",
            active=True,
            current_eps=None,
            intrinsic_value=None,
            last_calculation_date=None,
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        # Execute
        call_command("calculate_intrinsic_value")

        # Verify
        stock.refresh_from_db()

        # API data saved
        assert stock.current_eps == Decimal("6.42")

        # Calculation performed
        assert stock.intrinsic_value is not None
        assert stock.intrinsic_value > Decimal("0")

        # Timestamp updated
        assert stock.last_calculation_date is not None

        # Verify calculation is correct (manual calculation)
        # With EPS=6.42, growth=10%, multiple=20, return=15%, years=5
        # Expected intrinsic value should be around $130-140
        assert Decimal("120.00") < stock.intrinsic_value < Decimal("150.00")

    def test_multiple_stocks_sequential_processing(self, mock_sleep):
        """Test processing multiple stocks in sequence."""
        # Create 3 stocks
        stocks = [
            CuratedStockFactory(symbol="TEST2A", active=True),
            CuratedStockFactory(symbol="TEST2B", active=True),
            CuratedStockFactory(symbol="TEST2C", active=True),
        ]

        # Mock different EPS for each stock
        with patch(
            "scanner.management.commands.calculate_intrinsic_value.get_market_data"
        ) as mock:
            call_counter = {"count": 0}
            
            def side_effect(url):
                # Return different EPS based on which stock is being processed
                if "EARNINGS" in url:
                    if "TEST2A" in url:
                        eps_values = ["1.50", "1.50", "1.50", "1.50"]  # EPS TTM = 6.00
                    elif "TEST2B" in url:
                        eps_values = ["2.50", "2.50", "2.50", "2.50"]  # EPS TTM = 10.00
                    else:  # TEST2C
                        eps_values = ["1.25", "1.25", "1.25", "1.25"]  # EPS TTM = 5.00
                    
                    return {
                        "quarterlyEarnings": [
                            {"fiscalDateEnding": "2024-09-30", "reportedEPS": eps_values[0]},
                            {"fiscalDateEnding": "2024-06-30", "reportedEPS": eps_values[1]},
                            {"fiscalDateEnding": "2024-03-31", "reportedEPS": eps_values[2]},
                            {"fiscalDateEnding": "2023-12-31", "reportedEPS": eps_values[3]},
                        ]
                    }
                elif "OVERVIEW" in url:
                    return {"SharesOutstanding": "15000000000"}
                elif "CASH_FLOW" in url:
                    return {
                        "quarterlyReports": [
                            {"operatingCashflow": "30000000000", "capitalExpenditures": "-2500000000"},
                            {"operatingCashflow": "31000000000", "capitalExpenditures": "-2600000000"},
                            {"operatingCashflow": "29500000000", "capitalExpenditures": "-2400000000"},
                            {"operatingCashflow": "32000000000", "capitalExpenditures": "-2700000000"},
                        ]
                    }
                return {}
            
            mock.side_effect = side_effect

            call_command("calculate_intrinsic_value")

        # Verify all were processed
        for stock in stocks:
            stock.refresh_from_db()
            assert stock.intrinsic_value is not None
            assert stock.current_eps is not None

    def test_partial_failure_continues_processing(self, mock_sleep):
        """Test that failure on one stock doesn't stop others."""
        stock1 = CuratedStockFactory(symbol="TEST3A", active=True)
        stock2 = CuratedStockFactory(symbol="TEST3B", active=True)
        stock3 = CuratedStockFactory(symbol="TEST3C", active=True)

        # Mock: TEST3A succeeds, TEST3B fails, TEST3C succeeds
        def side_effect(url):
            if "TEST3B" in url:
                raise Exception("API Error")
            # Return normal data for TEST3A and TEST3C
            if "EARNINGS" in url:
                return {
                    "quarterlyEarnings": [
                        {"fiscalDateEnding": "2024-09-30", "reportedEPS": "1.75"},
                        {"fiscalDateEnding": "2024-06-30", "reportedEPS": "1.75"},
                        {"fiscalDateEnding": "2024-03-31", "reportedEPS": "1.75"},
                        {"fiscalDateEnding": "2023-12-31", "reportedEPS": "1.75"},
                    ]
                }
            elif "OVERVIEW" in url:
                return {"SharesOutstanding": "15000000000"}
            elif "CASH_FLOW" in url:
                return {
                    "quarterlyReports": [
                        {"operatingCashflow": "30000000000", "capitalExpenditures": "-2500000000"},
                        {"operatingCashflow": "31000000000", "capitalExpenditures": "-2600000000"},
                        {"operatingCashflow": "29500000000", "capitalExpenditures": "-2400000000"},
                        {"operatingCashflow": "32000000000", "capitalExpenditures": "-2700000000"},
                    ]
                }
            return {}

        with patch(
            "scanner.management.commands.calculate_intrinsic_value.get_market_data"
        ) as mock:
            mock.side_effect = side_effect

            call_command("calculate_intrinsic_value")

        # Verify TEST3A and TEST3C succeeded, TEST3B did not
        stock1.refresh_from_db()
        stock2.refresh_from_db()
        stock3.refresh_from_db()

        assert stock1.intrinsic_value is not None
        assert stock2.intrinsic_value is None  # Failed
        assert stock3.intrinsic_value is not None

    def test_recalculation_updates_existing_values(self, mock_sleep):
        """Test that running command again updates existing values."""
        with patch(
            "scanner.management.commands.calculate_intrinsic_value.get_market_data"
        ) as mock:
            def side_effect(url):
                if "EARNINGS" in url:
                    return {
                        "quarterlyEarnings": [
                            {"fiscalDateEnding": "2024-09-30", "reportedEPS": "1.25"},
                            {"fiscalDateEnding": "2024-06-30", "reportedEPS": "1.25"},
                            {"fiscalDateEnding": "2024-03-31", "reportedEPS": "1.25"},
                            {"fiscalDateEnding": "2023-12-31", "reportedEPS": "1.25"},
                        ]
                    }
                elif "OVERVIEW" in url:
                    return {"SharesOutstanding": "15000000000"}
                elif "CASH_FLOW" in url:
                    return {
                        "quarterlyReports": [
                            {"operatingCashflow": "30000000000", "capitalExpenditures": "-2500000000"},
                            {"operatingCashflow": "31000000000", "capitalExpenditures": "-2600000000"},
                            {"operatingCashflow": "29500000000", "capitalExpenditures": "-2400000000"},
                            {"operatingCashflow": "32000000000", "capitalExpenditures": "-2700000000"},
                        ]
                    }
                return {}
            
            mock.side_effect = side_effect

            stock = CuratedStockFactory(
                symbol="TEST4",
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
            assert stock.current_eps == Decimal("5.00")  # New value (1.25 * 4)
            assert stock.intrinsic_value != Decimal("80.00")  # Recalculated
            assert stock.last_calculation_date > old_date  # Updated


@pytest.mark.django_db(transaction=True)
class TestCachingBehavior:
    """Test Redis caching functionality."""

    @pytest.fixture
    def mock_sleep(self):
        """Mock time.sleep to speed up tests."""
        with patch(
            "scanner.management.commands.calculate_intrinsic_value.time.sleep"
        ) as mock:
            yield mock

    @patch("scanner.management.commands.calculate_intrinsic_value.cache")
    def test_cache_miss_then_hit(self, mock_cache, mock_sleep):
        """Test cache miss followed by cache hit."""
        CuratedStockFactory(symbol="TEST5", active=True)

        # First call: cache miss
        mock_cache.get.return_value = None

        with patch(
            "scanner.management.commands.calculate_intrinsic_value.get_market_data"
        ) as mock_api:
            def side_effect(url):
                if "EARNINGS" in url:
                    return {
                        "quarterlyEarnings": [
                            {"fiscalDateEnding": "2024-09-30", "reportedEPS": "1.64"},
                            {"fiscalDateEnding": "2024-06-30", "reportedEPS": "1.40"},
                            {"fiscalDateEnding": "2024-03-31", "reportedEPS": "1.53"},
                            {"fiscalDateEnding": "2023-12-31", "reportedEPS": "1.85"},
                        ]
                    }
                elif "OVERVIEW" in url:
                    return {"SharesOutstanding": "15000000000"}
                elif "CASH_FLOW" in url:
                    return {
                        "quarterlyReports": [
                            {"operatingCashflow": "30000000000", "capitalExpenditures": "-2500000000"},
                            {"operatingCashflow": "31000000000", "capitalExpenditures": "-2600000000"},
                            {"operatingCashflow": "29500000000", "capitalExpenditures": "-2400000000"},
                            {"operatingCashflow": "32000000000", "capitalExpenditures": "-2700000000"},
                        ]
                    }
                return {}
            
            mock_api.side_effect = side_effect
            call_command("calculate_intrinsic_value", symbols=["TEST5"])

        assert mock_cache.set.called
        cache_keys = [call[0][0] for call in mock_cache.set.call_args_list]
        assert "av_earnings_TEST5" in cache_keys

        # Second call: cache hit
        mock_cache.reset_mock()
        cached_earnings = {
            "quarterlyEarnings": [
                {"fiscalDateEnding": "2024-09-30", "reportedEPS": "1.64"},
                {"fiscalDateEnding": "2024-06-30", "reportedEPS": "1.40"},
                {"fiscalDateEnding": "2024-03-31", "reportedEPS": "1.53"},
                {"fiscalDateEnding": "2023-12-31", "reportedEPS": "1.85"},
            ]
        }
        mock_cache.get.return_value = cached_earnings

        call_command("calculate_intrinsic_value", symbols=["TEST5"])

        # Verify cache was used (no additional API call made via get)
        mock_cache.get.assert_called()

    @patch("scanner.management.commands.calculate_intrinsic_value.cache")
    def test_cache_ttl_is_7_days(self, mock_cache, mock_sleep):
        """Test that cache TTL is set to 7 days."""
        CuratedStockFactory(symbol="TEST6", active=True)

        mock_cache.get.return_value = None

        with patch(
            "scanner.management.commands.calculate_intrinsic_value.get_market_data"
        ) as mock_api:
            def side_effect(url):
                if "EARNINGS" in url:
                    return {
                        "quarterlyEarnings": [
                            {"fiscalDateEnding": "2024-09-30", "reportedEPS": "1.50"},
                            {"fiscalDateEnding": "2024-06-30", "reportedEPS": "1.50"},
                            {"fiscalDateEnding": "2024-03-31", "reportedEPS": "1.50"},
                            {"fiscalDateEnding": "2023-12-31", "reportedEPS": "1.50"},
                        ]
                    }
                elif "OVERVIEW" in url:
                    return {"SharesOutstanding": "15000000000"}
                elif "CASH_FLOW" in url:
                    return {
                        "quarterlyReports": [
                            {"operatingCashflow": "30000000000", "capitalExpenditures": "-2500000000"},
                            {"operatingCashflow": "31000000000", "capitalExpenditures": "-2600000000"},
                            {"operatingCashflow": "29500000000", "capitalExpenditures": "-2400000000"},
                            {"operatingCashflow": "32000000000", "capitalExpenditures": "-2700000000"},
                        ]
                    }
                return {}
            
            mock_api.side_effect = side_effect
            call_command("calculate_intrinsic_value")

        # Verify TTL was set to 7 days (604800 seconds)
        cache_ttl = mock_cache.set.call_args[0][2]
        assert cache_ttl == 60 * 60 * 24 * 7


@pytest.mark.django_db(transaction=True)
class TestCommandArguments:
    """Test command-line arguments."""

    @pytest.fixture
    def mock_sleep(self):
        """Mock time.sleep to speed up tests."""
        with patch(
            "scanner.management.commands.calculate_intrinsic_value.time.sleep"
        ) as mock:
            yield mock

    def test_invalid_symbol_raises_error(self, mock_sleep):
        """Test that invalid symbol raises CommandError."""
        out = StringIO()
        err = StringIO()

        # This should handle the error gracefully
        call_command(
            "calculate_intrinsic_value", symbols=["INVALID"], stdout=out, stderr=err
        )

        output = out.getvalue() + err.getvalue()
        assert "No stocks found" in output

    def test_multiple_symbols_argument(self, mock_sleep):
        """Test --symbols with multiple values."""
        CuratedStockFactory(symbol="TEST7A", active=True)
        CuratedStockFactory(symbol="TEST7B", active=True)
        CuratedStockFactory(symbol="TEST7C", active=True)

        with patch(
            "scanner.management.commands.calculate_intrinsic_value.get_market_data"
        ) as mock_api:
            def side_effect(url):
                if "EARNINGS" in url:
                    return {
                        "quarterlyEarnings": [
                            {"fiscalDateEnding": "2024-09-30", "reportedEPS": "1.50"},
                            {"fiscalDateEnding": "2024-06-30", "reportedEPS": "1.50"},
                            {"fiscalDateEnding": "2024-03-31", "reportedEPS": "1.50"},
                            {"fiscalDateEnding": "2023-12-31", "reportedEPS": "1.50"},
                        ]
                    }
                elif "OVERVIEW" in url:
                    return {"SharesOutstanding": "15000000000"}
                elif "CASH_FLOW" in url:
                    return {
                        "quarterlyReports": [
                            {"operatingCashflow": "30000000000", "capitalExpenditures": "-2500000000"},
                            {"operatingCashflow": "31000000000", "capitalExpenditures": "-2600000000"},
                            {"operatingCashflow": "29500000000", "capitalExpenditures": "-2400000000"},
                            {"operatingCashflow": "32000000000", "capitalExpenditures": "-2700000000"},
                        ]
                    }
                return {}
            
            mock_api.side_effect = side_effect

            call_command("calculate_intrinsic_value", symbols=["TEST7A", "TEST7B"])

            # Should process exactly 2 stocks (3 API calls each = 6 total)
            assert mock_api.call_count == 6


@pytest.mark.django_db(transaction=True)
class TestCalculateIntrinsicValueFCFIntegration:
    """Integration tests for FCF calculations in management command."""

    @pytest.fixture
    def mock_alpha_vantage_dual(self):
        """Mock both EARNINGS, OVERVIEW and CASH_FLOW API responses."""
        with patch(
            "scanner.management.commands.calculate_intrinsic_value.get_market_data"
        ) as mock:

            def side_effect(url):
                if "EARNINGS" in url:
                    return {
                        "quarterlyEarnings": [
                            {"fiscalDateEnding": "2024-09-30", "reportedEPS": "1.64"},
                            {"fiscalDateEnding": "2024-06-30", "reportedEPS": "1.40"},
                            {"fiscalDateEnding": "2024-03-31", "reportedEPS": "1.53"},
                            {"fiscalDateEnding": "2023-12-31", "reportedEPS": "1.85"},
                        ]
                    }
                elif "OVERVIEW" in url:
                    return {
                        "Symbol": "AAPL",
                        "SharesOutstanding": "15000000000",
                    }
                elif "CASH_FLOW" in url:
                    return {
                        "quarterlyReports": [
                            {
                                "operatingCashflow": "30000000000",
                                "capitalExpenditures": "-2500000000",
                            },
                            {
                                "operatingCashflow": "31000000000",
                                "capitalExpenditures": "-2600000000",
                            },
                            {
                                "operatingCashflow": "29500000000",
                                "capitalExpenditures": "-2400000000",
                            },
                            {
                                "operatingCashflow": "32000000000",
                                "capitalExpenditures": "-2700000000",
                            },
                        ]
                    }
                return {}

            mock.side_effect = side_effect
            yield mock

    @pytest.fixture
    def mock_sleep(self):
        """Mock time.sleep to speed up tests."""
        with patch(
            "scanner.management.commands.calculate_intrinsic_value.time.sleep"
        ) as mock:
            yield mock

    def test_command_calculates_both_eps_and_fcf(
        self, mock_alpha_vantage_dual, mock_sleep
    ):
        """Test that command calculates both EPS and FCF intrinsic values."""
        stock = CuratedStockFactory(symbol="FCFTEST1", active=True)

        call_command("calculate_intrinsic_value")

        stock.refresh_from_db()

        # Both values should be calculated
        assert stock.intrinsic_value is not None
        assert stock.intrinsic_value_fcf is not None
        assert stock.current_eps is not None
        assert stock.current_fcf_per_share is not None

    def test_command_fcf_skipped_with_insufficient_quarters(self, mock_sleep):
        """Test that FCF is skipped when fewer than 4 quarters available."""
        with patch(
            "scanner.management.commands.calculate_intrinsic_value.get_market_data"
        ) as mock:

            def side_effect(url):
                if "EARNINGS" in url:
                    return {
                        "quarterlyEarnings": [
                            {"fiscalDateEnding": "2024-09-30", "reportedEPS": "1.64"},
                            {"fiscalDateEnding": "2024-06-30", "reportedEPS": "1.40"},
                            {"fiscalDateEnding": "2024-03-31", "reportedEPS": "1.53"},
                            {"fiscalDateEnding": "2023-12-31", "reportedEPS": "1.85"},
                        ]
                    }
                elif "OVERVIEW" in url:
                    return {
                        "Symbol": "FCFTEST2",
                        "SharesOutstanding": "15000000000",
                    }
                elif "CASH_FLOW" in url:
                    return {
                        "quarterlyReports": [
                            {
                                "operatingCashflow": "30000000000",
                                "capitalExpenditures": "-2500000000",
                            },
                            {
                                "operatingCashflow": "31000000000",
                                "capitalExpenditures": "-2600000000",
                            },
                        ]
                    }
                return {}

            mock.side_effect = side_effect

            stock = CuratedStockFactory(symbol="FCFTEST2", active=True)
            call_command("calculate_intrinsic_value")

            stock.refresh_from_db()

            # EPS should succeed
            assert stock.intrinsic_value is not None
            # FCF should be skipped
            assert stock.intrinsic_value_fcf is None

    def test_command_fcf_skipped_with_negative_fcf(self, mock_sleep):
        """Test that FCF is skipped when FCF per share is negative."""
        with patch(
            "scanner.management.commands.calculate_intrinsic_value.get_market_data"
        ) as mock:

            def side_effect(url):
                if "EARNINGS" in url:
                    return {
                        "quarterlyEarnings": [
                            {"fiscalDateEnding": "2024-09-30", "reportedEPS": "0.875"},
                            {"fiscalDateEnding": "2024-06-30", "reportedEPS": "0.875"},
                            {"fiscalDateEnding": "2024-03-31", "reportedEPS": "0.875"},
                            {"fiscalDateEnding": "2023-12-31", "reportedEPS": "0.875"},
                        ]
                    }
                elif "OVERVIEW" in url:
                    return {
                        "Symbol": "FCFTEST3",
                        "SharesOutstanding": "3000000000",
                    }
                elif "CASH_FLOW" in url:
                    # Negative FCF scenario
                    return {
                        "quarterlyReports": [
                            {
                                "operatingCashflow": "1000000000",
                                "capitalExpenditures": "5000000000",
                            },
                            {
                                "operatingCashflow": "1100000000",
                                "capitalExpenditures": "5100000000",
                            },
                            {
                                "operatingCashflow": "1050000000",
                                "capitalExpenditures": "4900000000",
                            },
                            {
                                "operatingCashflow": "1200000000",
                                "capitalExpenditures": "5200000000",
                            },
                        ]
                    }
                return {}

            mock.side_effect = side_effect

            stock = CuratedStockFactory(symbol="FCFTEST3", active=True)
            call_command("calculate_intrinsic_value")

            stock.refresh_from_db()

            # EPS should succeed
            assert stock.intrinsic_value is not None
            # FCF should be skipped (negative)
            assert stock.intrinsic_value_fcf is None
            # But FCF per share should still be calculated (for reference)
            assert stock.current_fcf_per_share is not None
            assert stock.current_fcf_per_share < Decimal("0")

    @patch("scanner.management.commands.calculate_intrinsic_value.cache")
    def test_command_caches_cash_flow_data(
        self, mock_cache, mock_alpha_vantage_dual, mock_sleep
    ):
        """Test that all 3 API responses are cached."""
        mock_cache.get.return_value = None  # Cache miss

        stock = CuratedStockFactory(symbol="FCFTEST4", active=True)
        call_command("calculate_intrinsic_value")

        # Verify cache was checked and set for all 3 endpoints
        cache_calls = [call[0][0] for call in mock_cache.get.call_args_list]
        assert "av_earnings_FCFTEST4" in cache_calls
        assert "av_overview_FCFTEST4" in cache_calls
        assert "av_cashflow_FCFTEST4" in cache_calls

        # Verify cache was set (should be called 3 times for all 3 APIs)
        assert mock_cache.set.call_count >= 3

    def test_command_summary_shows_both_methods(
        self, mock_alpha_vantage_dual, mock_sleep
    ):
        """Test that command summary shows statistics for both methods."""
        CuratedStockFactory(symbol="FCFTEST5A", active=True)
        CuratedStockFactory(symbol="FCFTEST5B", active=True)

        out = StringIO()
        call_command("calculate_intrinsic_value", stdout=out)

        output = out.getvalue()

        # Verify summary includes both methods
        assert "EPS Method:" in output
        assert "FCF Method:" in output
        assert "Successful:" in output

    def test_command_updates_last_calculation_date_for_both(
        self, mock_alpha_vantage_dual, mock_sleep
    ):
        """Test that last_calculation_date is updated when either method runs."""
        stock = CuratedStockFactory(symbol="FCFTEST6", active=True)

        before_time = timezone.now()
        call_command("calculate_intrinsic_value")
        after_time = timezone.now()

        stock.refresh_from_db()

        # Date should be updated
        assert stock.last_calculation_date is not None
        assert before_time <= stock.last_calculation_date <= after_time

    def test_command_preferred_valuation_method_persists(
        self, mock_alpha_vantage_dual, mock_sleep
    ):
        """Test that preferred_valuation_method setting is preserved."""
        stock = CuratedStockFactory(
            symbol="FCFTEST7", active=True, preferred_valuation_method="FCF"
        )

        call_command("calculate_intrinsic_value")

        stock.refresh_from_db()

        # Preference should be unchanged
        assert stock.preferred_valuation_method == "FCF"

    def test_fcf_calculation_with_active_stocks_only(
        self, mock_alpha_vantage_dual, mock_sleep
    ):
        """Test that only active stocks get FCF calculations."""
        active_stock = CuratedStockFactory(symbol="FCFTEST8A", active=True)
        inactive_stock = CuratedStockFactory(symbol="FCFTEST8B", active=False)

        call_command("calculate_intrinsic_value")

        active_stock.refresh_from_db()
        inactive_stock.refresh_from_db()

        # Active stock should have both values
        assert active_stock.intrinsic_value is not None
        assert active_stock.intrinsic_value_fcf is not None

        # Inactive stock should have neither
        assert inactive_stock.intrinsic_value is None
        assert inactive_stock.intrinsic_value_fcf is None
