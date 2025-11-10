"""Tests for scanner core functions.

Updated for Task 033: perform_scan() no longer writes to Redis/cache directly.
Instead, it returns scan_results dict that the caller caches using Django cache.

The caching is done by:
- run_scan_in_background() in views.py (for manual/UI scans)
- cron_scanner command (for scheduled scans)
"""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from scanner.factories import CuratedStockFactory
from scanner.scanner import perform_scan


@pytest.mark.django_db
class TestPerformScan:
    """Tests for the perform_scan function.

    Note: perform_scan() no longer writes to Redis/cache directly.
    It returns scan_results for the caller to cache.
    """

    @patch("scanner.scanner.is_market_open")
    @patch("scanner.scanner.find_options")
    def test_perform_scan_success(
        self, mock_find_options, mock_market_open, clean_curated_stocks
    ):
        """Test successful scan execution and returns scan_results."""
        # Use factory-generated unique symbols
        stock1 = CuratedStockFactory(active=True)
        stock2 = CuratedStockFactory(active=True)
        CuratedStockFactory(active=False)  # Inactive, should be skipped

        # Mock market open
        mock_market_open.return_value = True

        # Mock options data
        mock_options = [
            {
                "date": "2024-12-20",
                "strike": 180.0,
                "price": 2.50,
                "delta": -0.15,
                "annualized": 35.5,
            }
        ]
        mock_find_options.return_value = mock_options

        # Execute scan
        result = perform_scan(debug=False)

        # Verify result structure
        assert result["success"] is True
        assert result["scanned_count"] == 2  # Only active stocks
        assert "timestamp" in result
        assert "message" in result
        assert "scan_results" in result

        # Verify scan_results contains options for both active tickers
        scan_results = result["scan_results"]
        assert isinstance(scan_results, dict)
        assert len(scan_results) == 2
        assert stock1.symbol in scan_results
        assert stock2.symbol in scan_results
        assert scan_results[stock1.symbol] == mock_options
        assert scan_results[stock2.symbol] == mock_options

        # Verify find_options was called for active stocks
        assert mock_find_options.call_count == 2

    @patch("scanner.scanner.is_market_open")
    def test_perform_scan_market_closed(self, mock_market_open, clean_curated_stocks):
        """Test scan behavior when market is closed."""
        # Create test stock
        CuratedStockFactory(active=True)

        # Mock market closed
        mock_market_open.return_value = False

        # Execute scan
        result = perform_scan(debug=False)

        # Verify result
        assert result["success"] is False
        assert "Market is closed" in result["message"]
        assert result["scanned_count"] == 0
        assert result["scan_results"] == {}

    @patch("scanner.scanner.is_market_open")
    @patch("scanner.scanner.find_options")
    def test_perform_scan_with_debug_flag(
        self, mock_find_options, mock_market_open, clean_curated_stocks
    ):
        """Test scan with debug flag bypasses market hours check."""
        # Create test stock
        stock = CuratedStockFactory(active=True)

        # Mock market closed
        mock_market_open.return_value = False

        # Mock options data
        mock_options = [{"strike": 150.0, "price": 1.50}]
        mock_find_options.return_value = mock_options

        # Execute scan with debug=True
        result = perform_scan(debug=True)

        # Verify scan proceeded despite market being closed
        assert result["success"] is True
        assert mock_find_options.called
        assert stock.symbol in result["scan_results"]

    @patch("scanner.scanner.is_market_open")
    @patch("scanner.scanner.find_options")
    def test_perform_scan_handles_errors(
        self,
        mock_find_options,
        mock_market_open,
        clean_curated_stocks,
    ):
        """Test scan handles errors gracefully."""
        # Create test stock
        CuratedStockFactory(active=True)

        # Mock market open
        mock_market_open.return_value = True

        # Mock error during options fetch
        mock_find_options.side_effect = Exception("API connection error")

        # Execute scan
        result = perform_scan(debug=False)

        # Verify error handling
        assert result["success"] is False
        assert "error occurred" in result["message"]
        assert "error" in result
        assert "API connection error" in result["error"]
        assert result["scan_results"] == {}

    @patch("scanner.scanner.is_market_open")
    @patch("scanner.scanner.find_options")
    def test_perform_scan_only_scans_active_stocks(
        self,
        mock_find_options,
        mock_market_open,
        clean_curated_stocks,
    ):
        """Test that scan only processes active stocks."""
        # Create mix of active and inactive stocks
        stock1 = CuratedStockFactory(active=True)
        stock2 = CuratedStockFactory(active=True)
        CuratedStockFactory(active=False)
        CuratedStockFactory(active=False)

        # Mock market open
        mock_market_open.return_value = True

        # Mock options data
        mock_options = [{"strike": 100.0}]
        mock_find_options.return_value = mock_options

        # Execute scan
        result = perform_scan(debug=False)

        # Verify only 2 active stocks were scanned
        assert result["scanned_count"] == 2
        assert mock_find_options.call_count == 2

        # Verify scan_results only contains active stocks
        assert len(result["scan_results"]) == 2
        assert stock1.symbol in result["scan_results"]
        assert stock2.symbol in result["scan_results"]

    @patch("scanner.scanner.is_market_open")
    @patch("scanner.scanner.find_options")
    def test_perform_scan_returns_structured_data(
        self,
        mock_find_options,
        mock_market_open,
        clean_curated_stocks,
    ):
        """Test that scan returns properly structured data for caching."""
        # Create test stock
        stock = CuratedStockFactory(active=True, symbol="AAPL")

        # Mock market open
        mock_market_open.return_value = True

        # Mock options data
        options_data = [
            {
                "date": "2024-12-20",
                "strike": 180.0,
                "price": 2.50,
                "delta": -0.15,
                "annualized": 35.5,
            }
        ]
        mock_find_options.return_value = options_data

        # Execute scan
        result = perform_scan(debug=False)

        # Verify structure
        assert isinstance(result, dict)
        assert "success" in result
        assert "message" in result
        assert "scanned_count" in result
        assert "timestamp" in result
        assert "scan_results" in result

        # Verify scan_results structure
        scan_results = result["scan_results"]
        assert isinstance(scan_results, dict)
        assert "AAPL" in scan_results
        assert scan_results["AAPL"] == options_data

    @patch("scanner.scanner.is_market_open")
    @patch("scanner.scanner.find_options")
    def test_perform_scan_omits_empty_results(
        self,
        mock_find_options,
        mock_market_open,
        clean_curated_stocks,
    ):
        """Test that scan omits tickers with no options from scan_results."""
        # Create two stocks
        stock1 = CuratedStockFactory(active=True, symbol="AAPL")
        stock2 = CuratedStockFactory(active=True, symbol="MSFT")

        # Mock market open
        mock_market_open.return_value = True

        # Mock options data - AAPL has options, MSFT has none
        def find_options_side_effect(ticker, contract_type):
            if ticker == "AAPL":
                return [{"strike": 150.0, "price": 2.0}]
            else:
                return []  # Empty list for MSFT

        mock_find_options.side_effect = find_options_side_effect

        # Execute scan
        result = perform_scan(debug=False)

        # Verify scan_results only contains tickers with options
        scan_results = result["scan_results"]
        assert "AAPL" in scan_results  # Has options, included
        assert "MSFT" not in scan_results  # No options, excluded
        assert len(scan_results) == 1

    @patch("scanner.scanner.is_market_open")
    @patch("scanner.scanner.find_options")
    def test_perform_scan_timestamp_format(
        self,
        mock_find_options,
        mock_market_open,
        clean_curated_stocks,
    ):
        """Test that scan returns timestamp in correct format."""
        # Create test stock
        CuratedStockFactory(active=True)

        # Mock market open
        mock_market_open.return_value = True

        # Mock options data
        mock_find_options.return_value = []

        # Execute scan
        result = perform_scan(debug=False)

        # Verify timestamp format (YYYY-MM-DD HH:MM)
        timestamp = result["timestamp"]
        # Should be parseable
        datetime.strptime(timestamp, "%Y-%m-%d %H:%M")
