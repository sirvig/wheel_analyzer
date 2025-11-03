"""Tests for scanner core functions."""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from scanner.factories import CuratedStockFactory
from scanner.scanner import perform_scan


@pytest.mark.django_db
class TestPerformScan:
    """Tests for the perform_scan function."""

    @patch("scanner.scanner.redis.Redis.from_url")
    @patch("scanner.scanner.is_market_open")
    @patch("scanner.scanner.find_options")
    def test_perform_scan_success(
        self, mock_find_options, mock_market_open, mock_redis_from_url, clean_curated_stocks
    ):
        """Test successful scan execution."""
        # Use factory-generated unique symbols
        CuratedStockFactory(active=True)
        CuratedStockFactory(active=True)
        CuratedStockFactory(active=False)  # Inactive, should be skipped

        # Mock Redis
        mock_redis = MagicMock()
        mock_redis_from_url.return_value = mock_redis

        # Mock market open
        mock_market_open.return_value = True

        # Mock options data
        mock_find_options.return_value = [
            {
                "date": "2024-12-20",
                "strike": 180.0,
                "price": 2.50,
                "delta": -0.15,
                "annualized": 35.5,
            }
        ]

        # Execute scan
        result = perform_scan(debug=False)

        # Verify result
        assert result["success"] is True
        assert result["scanned_count"] == 2  # Only active stocks
        assert "timestamp" in result
        assert "message" in result

        # Verify Redis calls
        assert mock_redis.set.called
        assert mock_redis.hset.called
        assert mock_redis.expire.called

        # Verify find_options was called for active stocks
        assert mock_find_options.call_count == 2

    @patch("scanner.scanner.redis.Redis.from_url")
    @patch("scanner.scanner.is_market_open")
    def test_perform_scan_market_closed(self, mock_market_open, mock_redis_from_url, clean_curated_stocks):
        """Test scan behavior when market is closed."""
        # Create test stock
        CuratedStockFactory(active=True)

        # Mock Redis
        mock_redis = MagicMock()
        mock_redis_from_url.return_value = mock_redis

        # Mock market closed
        mock_market_open.return_value = False

        # Execute scan
        result = perform_scan(debug=False)

        # Verify result
        assert result["success"] is False
        assert "Market is closed" in result["message"]
        assert result["scanned_count"] == 0

    @patch("scanner.scanner.redis.Redis.from_url")
    @patch("scanner.scanner.is_market_open")
    @patch("scanner.scanner.find_options")
    def test_perform_scan_with_debug_flag(
        self, mock_find_options, mock_market_open, mock_redis_from_url, clean_curated_stocks
    ):
        """Test scan with debug flag bypasses market hours check."""
        # Create test stock
        CuratedStockFactory(active=True)

        # Mock Redis
        mock_redis = MagicMock()
        mock_redis_from_url.return_value = mock_redis

        # Mock market closed
        mock_market_open.return_value = False

        # Mock options data
        mock_find_options.return_value = []

        # Execute scan with debug=True
        result = perform_scan(debug=True)

        # Verify scan proceeded despite market being closed
        assert result["success"] is True
        assert mock_find_options.called

    @patch("scanner.scanner.redis.Redis.from_url")
    @patch("scanner.scanner.is_market_open")
    @patch("scanner.scanner.find_options")
    def test_perform_scan_handles_errors(
        self, mock_find_options, mock_market_open, mock_redis_from_url, clean_curated_stocks
    ):
        """Test scan handles errors gracefully."""
        # Create test stock
        CuratedStockFactory(active=True)

        # Mock Redis
        mock_redis = MagicMock()
        mock_redis_from_url.return_value = mock_redis

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

    @patch("scanner.scanner.redis.Redis.from_url")
    @patch("scanner.scanner.is_market_open")
    @patch("scanner.scanner.find_options")
    def test_perform_scan_updates_redis_progress(
        self, mock_find_options, mock_market_open, mock_redis_from_url
    ):
        """Test that scan updates progress in Redis."""
        # Use existing stocks from migration (no clean_curated_stocks fixture)
        # Mock Redis
        mock_redis = MagicMock()
        mock_redis_from_url.return_value = mock_redis

        # Mock market open
        mock_market_open.return_value = True

        # Mock options data
        mock_find_options.return_value = []

        # Execute scan
        result = perform_scan(debug=False)

        # Verify Redis set was called for progress updates
        # Should be called multiple times: for progress updates + final timestamp
        assert mock_redis.set.call_count >= 5

        # Verify at least one call contains progress percentage
        progress_calls = [
            call for call in mock_redis.set.call_args_list if "%" in str(call)
        ]
        assert len(progress_calls) > 0

    @patch("scanner.scanner.redis.Redis.from_url")
    @patch("scanner.scanner.is_market_open")
    @patch("scanner.scanner.find_options")
    def test_perform_scan_only_scans_active_stocks(
        self, mock_find_options, mock_market_open, mock_redis_from_url, clean_curated_stocks
    ):
        """Test that scan only processes active stocks."""
        # Create mix of active and inactive stocks
        CuratedStockFactory(active=True)
        CuratedStockFactory(active=True)
        CuratedStockFactory(active=False)
        CuratedStockFactory(active=False)

        # Mock Redis
        mock_redis = MagicMock()
        mock_redis_from_url.return_value = mock_redis

        # Mock market open
        mock_market_open.return_value = True

        # Mock options data
        mock_find_options.return_value = []

        # Execute scan
        result = perform_scan(debug=False)

        # Verify only 2 active stocks were scanned
        assert result["scanned_count"] == 2
        assert mock_find_options.call_count == 2

    @patch("scanner.scanner.redis.Redis.from_url")
    @patch("scanner.scanner.is_market_open")
    @patch("scanner.scanner.find_options")
    def test_perform_scan_sets_ttl_on_redis_keys(
        self, mock_find_options, mock_market_open, mock_redis_from_url, clean_curated_stocks
    ):
        """Test that scan sets TTL on Redis keys."""
        # Create test stock
        CuratedStockFactory(active=True)

        # Mock Redis
        mock_redis = MagicMock()
        mock_redis_from_url.return_value = mock_redis

        # Mock market open
        mock_market_open.return_value = True

        # Mock options data
        mock_find_options.return_value = []

        # Execute scan
        result = perform_scan(debug=False)

        # Verify expire was called with correct TTL (30 minutes = 1800 seconds)
        mock_redis.expire.assert_called()
        # Get the actual call arguments
        expire_calls = mock_redis.expire.call_args_list
        assert len(expire_calls) == 1
        # Check that TTL is 30 minutes (1800 seconds)
        assert expire_calls[0][0][1] == 1800

    @patch("scanner.scanner.redis.Redis.from_url")
    @patch("scanner.scanner.is_market_open")
    @patch("scanner.scanner.find_options")
    def test_perform_scan_stores_options_as_json(
        self, mock_find_options, mock_market_open, mock_redis_from_url, clean_curated_stocks
    ):
        """Test that options data is stored as JSON in Redis."""
        # Create test stock
        CuratedStockFactory(active=True)

        # Mock Redis
        mock_redis = MagicMock()
        mock_redis_from_url.return_value = mock_redis

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

        # Verify hset was called with JSON-encoded options
        hset_calls = mock_redis.hset.call_args_list
        # Should be called twice per ticker: once for options, once for last_scan
        assert len(hset_calls) == 2

        # Find the options hset call
        options_call = [call for call in hset_calls if call[0][1] == "options"][0]

        # Verify the data is JSON-encoded
        stored_data = options_call[0][2]
        assert isinstance(stored_data, str)
        # Verify it can be decoded back to the original data
        decoded_data = json.loads(stored_data)
        assert decoded_data == options_data

    @patch("scanner.scanner.redis.Redis.from_url")
    @patch("scanner.scanner.is_market_open")
    @patch("scanner.scanner.find_options")
    def test_perform_scan_stores_last_scan_timestamp(
        self, mock_find_options, mock_market_open, mock_redis_from_url, clean_curated_stocks
    ):
        """Test that scan stores last_scan timestamp."""
        # Create test stock
        CuratedStockFactory(active=True)

        # Mock Redis
        mock_redis = MagicMock()
        mock_redis_from_url.return_value = mock_redis

        # Mock market open
        mock_market_open.return_value = True

        # Mock options data
        mock_find_options.return_value = []

        # Execute scan
        result = perform_scan(debug=False)

        # Verify hset was called with last_scan timestamp
        hset_calls = mock_redis.hset.call_args_list

        # Find the last_scan hset call
        last_scan_call = [call for call in hset_calls if call[0][1] == "last_scan"][0]

        # Verify timestamp format (YYYY-MM-DD HH:MM)
        timestamp = last_scan_call[0][2]
        # Should match format
        datetime.strptime(timestamp, "%Y-%m-%d %H:%M")
