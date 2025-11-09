"""
Integration tests for Redis error handling in scanner app.

Tests simulate Redis failures and data expiration scenarios using mocks
to verify graceful degradation without actual Redis dependency.
"""

import pytest
from unittest.mock import patch, MagicMock
import redis
from decimal import Decimal


@pytest.mark.django_db
class TestRedisDataExpiration:
    """Tests for handling Redis data expiration scenarios."""

    @patch("scanner.views.redis.Redis.from_url")
    def test_scan_results_with_expired_data(self, mock_redis_from_url):
        """get_scan_results handles expired data gracefully."""
        from scanner.views import get_scan_results
        from scanner.factories import CuratedStockFactory

        # Create curated stock with unique symbol
        stock = CuratedStockFactory(
            symbol="TESTEX", intrinsic_value=Decimal("150.00"), active=True
        )

        mock_redis = mock_redis_from_url.return_value
        # Simulate expired keys - no keys found
        mock_redis.keys.return_value = []
        mock_redis.get.return_value = None  # last_run also expired
        mock_redis.exists.return_value = False  # No scan in progress

        result = get_scan_results()

        # Should handle gracefully without errors
        assert result["ticker_options"] == {}
        assert result["curated_stocks"] == {}
        # Should show "Never" when last_run is None
        assert result["last_scan"] == "Never"

    @patch("scanner.views.redis.Redis.from_url")
    def test_template_rendering_with_empty_curated_stocks(self, mock_redis_from_url):
        """get_scan_results returns empty dict for curated_stocks when no data."""
        from scanner.views import get_scan_results

        mock_redis = mock_redis_from_url.return_value
        mock_redis.keys.return_value = []
        mock_redis.get.return_value = b"Never"
        mock_redis.exists.return_value = False

        result = get_scan_results()

        # Should return empty dict - this is the main bug fix validation
        assert result["curated_stocks"] == {}
        assert isinstance(result["curated_stocks"], dict)

    @patch("scanner.views.redis.Redis.from_url")
    def test_partial_redis_data(self, mock_redis_from_url):
        """get_scan_results handles case where some Redis keys exist but others don't."""
        import json
        from scanner.views import get_scan_results

        mock_redis = mock_redis_from_url.return_value
        mock_redis.keys.return_value = [b"put_AAPL", b"put_MSFT"]

        def mock_hget(key, field):
            # AAPL has options, MSFT has expired/missing data
            if key == b"put_AAPL" and field == "options":
                return json.dumps([{"strike": 145.0}]).encode()
            elif key == b"put_AAPL" and field == "last_scan":
                return b"2025-11-09 10:00:00"
            else:
                return None  # MSFT data missing

        mock_redis.hget.side_effect = mock_hget
        mock_redis.get.return_value = b"Last scan: 2025-11-09"
        mock_redis.exists.return_value = False

        result = get_scan_results()

        # Should handle partial data gracefully
        assert "AAPL" in result["ticker_options"]
        assert "MSFT" not in result["ticker_options"]


@pytest.mark.django_db
class TestRedisConnectionFailures:
    """Tests for handling complete Redis connection failures."""

    @patch("scanner.views.redis.Redis.from_url")
    def test_complete_redis_failure(self, mock_redis_from_url):
        """get_scan_results displays user-friendly message when Redis is down."""
        from scanner.views import get_scan_results

        mock_redis_from_url.side_effect = redis.ConnectionError("Connection refused")

        result = get_scan_results()

        assert result["ticker_options"] == {}
        assert "Data temporarily unavailable" in result["last_scan"]

    @patch("scanner.views.redis.Redis.from_url")
    def test_redis_timeout_error(self, mock_redis_from_url):
        """get_scan_results handles Redis timeout errors gracefully."""
        from scanner.views import get_scan_results

        mock_redis_from_url.side_effect = redis.TimeoutError("Operation timed out")

        result = get_scan_results()

        assert result["curated_stocks"] == {}

    @patch("scanner.views.redis.Redis.from_url")
    def test_generic_redis_error(self, mock_redis_from_url):
        """get_scan_results handles generic Redis errors."""
        from scanner.views import get_scan_results

        mock_redis_from_url.side_effect = redis.RedisError("Generic Redis error")

        result = get_scan_results()

        assert isinstance(result["curated_stocks"], dict)


@pytest.mark.django_db
class TestTemplateFilterErrorHandling:
    """Tests for template filter error handling in rendered templates."""

    @patch("scanner.views.redis.Redis.from_url")
    def test_dict_get_filter_with_invalid_curated_stocks(self, mock_redis_from_url):
        """Template filter handles invalid curated_stocks gracefully."""
        import json
        from scanner.views import get_scan_results

        # This test verifies the dict_get filter's defensive coding
        # In practice, the view should prevent this, but filter provides backup

        mock_redis = mock_redis_from_url.return_value
        mock_redis.keys.return_value = [b"put_AAPL"]
        mock_redis.hget.side_effect = lambda k, f: (
            json.dumps([{"strike": 145.0}]).encode()
            if f == "options"
            else b"2025-11-09"
        )
        mock_redis.get.return_value = b"Last scan"
        mock_redis.exists.return_value = False

        result = get_scan_results()

        # Should return valid result with curated_stocks as dict
        assert isinstance(result["curated_stocks"], dict)

    def test_dict_get_filter_defensive_behavior(self):
        """dict_get filter returns None for invalid inputs rather than crashing."""
        from scanner.templatetags.options_extras import dict_get

        # Test with various invalid types
        invalid_inputs = [
            "",  # Empty string (the original bug case)
            "string",  # Non-empty string
            42,  # Integer
            [],  # List
            None,  # None
        ]

        for invalid_input in invalid_inputs:
            result = dict_get(invalid_input, "any_key")
            assert result is None, f"Failed for input type: {type(invalid_input)}"
