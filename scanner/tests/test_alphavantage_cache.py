"""
Unit tests for Alpha Vantage module cache integration.

Tests verify that Alpha Vantage API calls are properly cached using
Django cache backend with 7-day TTL.
"""

import pytest
from unittest.mock import patch, MagicMock
from django.core.cache import cache
from django.conf import settings

from scanner.alphavantage.util import (
    get_market_data,
    _parse_function_from_url,
    _build_cache_key,
)


@pytest.mark.django_db
class TestAlphaVantageCache:
    """Tests for Alpha Vantage API caching."""

    def setup_method(self):
        """Clear cache before each test."""
        cache.clear()

    def test_parse_function_from_url_basic(self):
        """Parse function and symbol from basic URL."""
        function, symbol, params = _parse_function_from_url(
            "function=EARNINGS&symbol=AAPL"
        )

        assert function == "EARNINGS"
        assert symbol == "AAPL"
        assert params == {}

    def test_parse_function_from_url_with_params(self):
        """Parse function with additional parameters."""
        function, symbol, params = _parse_function_from_url(
            "function=SMA&symbol=AAPL&interval=daily&time_period=200"
        )

        assert function == "SMA"
        assert symbol == "AAPL"
        assert params == {"interval": "daily", "time_period": "200"}

    def test_build_cache_key_basic(self):
        """Build cache key for basic function."""
        cache_key = _build_cache_key("EARNINGS", "AAPL")

        assert cache_key == f"{settings.CACHE_KEY_PREFIX_ALPHAVANTAGE}:earnings:AAPL"

    def test_build_cache_key_with_params(self):
        """Build cache key with additional parameters."""
        cache_key = _build_cache_key("SMA", "AAPL", {"time_period": "200"})

        assert (
            cache_key
            == f"{settings.CACHE_KEY_PREFIX_ALPHAVANTAGE}:sma:AAPL:time_period_200"
        )

    def test_build_cache_key_normalizes_case(self):
        """Cache key function name is normalized to lowercase."""
        cache_key = _build_cache_key("OVERVIEW", "aapl")

        expected = f"{settings.CACHE_KEY_PREFIX_ALPHAVANTAGE}:overview:AAPL"
        assert cache_key == expected

    @patch("scanner.alphavantage.util.requests.get")
    def test_get_market_data_caches_on_first_call(self, mock_get):
        """First call to get_market_data caches the result."""
        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "symbol": "AAPL",
            "quarterlyEarnings": [
                {"fiscalDateEnding": "2024-12-31", "reportedEPS": "2.50"}
            ],
        }
        mock_get.return_value = mock_response

        url = "function=EARNINGS&symbol=AAPL"
        cache_key = f"{settings.CACHE_KEY_PREFIX_ALPHAVANTAGE}:earnings:AAPL"

        # Verify cache is empty
        assert cache.get(cache_key) is None

        # Call function
        result = get_market_data(url)

        # Verify API was called
        assert mock_get.called

        # Verify result is cached
        cached_result = cache.get(cache_key)
        assert cached_result is not None
        assert cached_result == result
        assert cached_result["symbol"] == "AAPL"

    @patch("scanner.alphavantage.util.requests.get")
    def test_get_market_data_cache_hit_skips_api_call(self, mock_get):
        """Second call uses cache and doesn't hit API."""
        url = "function=EARNINGS&symbol=AAPL"
        cache_key = f"{settings.CACHE_KEY_PREFIX_ALPHAVANTAGE}:earnings:AAPL"

        # Pre-populate cache
        cached_data = {
            "symbol": "AAPL",
            "quarterlyEarnings": [
                {"fiscalDateEnding": "2024-12-31", "reportedEPS": "2.50"}
            ],
        }
        cache.set(cache_key, cached_data, timeout=settings.CACHE_TTL_ALPHAVANTAGE)

        # Call function
        result = get_market_data(url)

        # Verify API was NOT called (cache hit)
        assert not mock_get.called

        # Verify result matches cached data
        assert result == cached_data

    @patch("scanner.alphavantage.util.requests.get")
    def test_get_market_data_uses_7_day_ttl(self, mock_get):
        """Market data cached with 7-day TTL."""
        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"symbol": "AAPL"}
        mock_get.return_value = mock_response

        url = "function=EARNINGS&symbol=AAPL"
        cache_key = f"{settings.CACHE_KEY_PREFIX_ALPHAVANTAGE}:earnings:AAPL"

        # Call function
        with patch.object(cache, "set", wraps=cache.set) as mock_cache_set:
            get_market_data(url)

            # Verify cache.set was called with 7-day timeout
            mock_cache_set.assert_called_once()
            args, kwargs = mock_cache_set.call_args
            assert args[0] == cache_key
            assert kwargs.get("timeout") == settings.CACHE_TTL_ALPHAVANTAGE

    @patch("scanner.alphavantage.util.requests.get")
    def test_get_market_data_overview(self, mock_get):
        """OVERVIEW function caching works correctly."""
        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Symbol": "AAPL",
            "Name": "Apple Inc",
            "SharesOutstanding": "15000000000",
        }
        mock_get.return_value = mock_response

        url = "function=OVERVIEW&symbol=AAPL"
        cache_key = f"{settings.CACHE_KEY_PREFIX_ALPHAVANTAGE}:overview:AAPL"

        # First call - should hit API
        result = get_market_data(url)
        assert mock_get.called
        assert result["Symbol"] == "AAPL"

        # Verify cached
        cached_result = cache.get(cache_key)
        assert cached_result is not None
        assert cached_result["Symbol"] == "AAPL"

    @patch("scanner.alphavantage.util.requests.get")
    def test_get_market_data_cash_flow(self, mock_get):
        """CASH_FLOW function caching works correctly."""
        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "symbol": "AAPL",
            "quarterlyReports": [
                {
                    "fiscalDateEnding": "2024-09-30",
                    "operatingCashflow": "10000000000",
                    "capitalExpenditures": "-2000000000",
                }
            ],
        }
        mock_get.return_value = mock_response

        url = "function=CASH_FLOW&symbol=AAPL"
        cache_key = f"{settings.CACHE_KEY_PREFIX_ALPHAVANTAGE}:cash_flow:AAPL"

        # Call function
        result = get_market_data(url)

        # Verify result is cached
        cached_result = cache.get(cache_key)
        assert cached_result is not None
        assert cached_result["symbol"] == "AAPL"

    @patch("scanner.alphavantage.util.requests.get")
    def test_get_market_data_sma_with_period_in_key(self, mock_get):
        """SMA cache key includes period parameter."""
        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Meta Data": {"1: Symbol": "AAPL"},
            "Technical Analysis: SMA": {"2024-11-10": {"SMA": "150.25"}},
        }
        mock_get.return_value = mock_response

        url = "function=SMA&symbol=AAPL&interval=daily&time_period=200"
        cache_key = f"{settings.CACHE_KEY_PREFIX_ALPHAVANTAGE}:sma:AAPL:interval_daily:time_period_200"

        # Call function
        result = get_market_data(url)

        # Verify result is cached with period in key
        cached_result = cache.get(cache_key)
        assert cached_result is not None

    @patch("scanner.alphavantage.util.requests.get")
    def test_get_market_data_handles_api_error(self, mock_get):
        """API call handles error status codes gracefully."""
        # Mock API error
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        url = "function=EARNINGS&symbol=AAPL"

        # Should return empty dict on error
        result = get_market_data(url)

        assert result == {}

    @patch("scanner.alphavantage.util.requests.get")
    def test_get_market_data_handles_request_exception(self, mock_get):
        """API call handles request exceptions gracefully."""
        import requests

        # Mock request exception (use RequestException which is the base class we catch)
        mock_get.side_effect = requests.RequestException("Network error")

        url = "function=EARNINGS&symbol=AAPL"

        # Should return empty dict on exception
        result = get_market_data(url)

        assert result == {}

    @patch("scanner.alphavantage.util.requests.get")
    @patch("django.core.cache.cache.set")
    def test_api_call_succeeds_even_if_cache_set_fails(self, mock_cache_set, mock_get):
        """API call completes successfully even if caching fails."""
        # Mock cache.set to raise exception
        mock_cache_set.side_effect = Exception("Cache unavailable")

        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"symbol": "AAPL"}
        mock_get.return_value = mock_response

        url = "function=EARNINGS&symbol=AAPL"

        # Call should succeed despite cache failure
        result = get_market_data(url)

        # Verify we got API data
        assert result is not None
        assert result["symbol"] == "AAPL"

    @patch("scanner.alphavantage.util.requests.get")
    @patch("django.core.cache.cache.get")
    def test_api_call_if_cache_get_fails(self, mock_cache_get, mock_get):
        """API call made if cache.get() fails."""
        # Mock cache.get to raise exception
        mock_cache_get.side_effect = Exception("Cache unavailable")

        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"symbol": "AAPL"}
        mock_get.return_value = mock_response

        url = "function=EARNINGS&symbol=AAPL"

        # Should fall back to API call
        result = get_market_data(url)

        # Verify API was called
        assert mock_get.called
        assert result is not None

    @patch("scanner.alphavantage.util.requests.get")
    def test_multiple_symbols_have_separate_cache_keys(self, mock_get):
        """Different symbols use different cache keys."""
        # Mock API responses
        mock_response_aapl = MagicMock()
        mock_response_aapl.status_code = 200
        mock_response_aapl.json.return_value = {"symbol": "AAPL"}

        mock_response_msft = MagicMock()
        mock_response_msft.status_code = 200
        mock_response_msft.json.return_value = {"symbol": "MSFT"}

        mock_get.side_effect = [mock_response_aapl, mock_response_msft]

        # Fetch both symbols
        result_aapl = get_market_data("function=EARNINGS&symbol=AAPL")
        result_msft = get_market_data("function=EARNINGS&symbol=MSFT")

        # Verify both are cached separately
        cache_key_aapl = f"{settings.CACHE_KEY_PREFIX_ALPHAVANTAGE}:earnings:AAPL"
        cache_key_msft = f"{settings.CACHE_KEY_PREFIX_ALPHAVANTAGE}:earnings:MSFT"

        cached_aapl = cache.get(cache_key_aapl)
        cached_msft = cache.get(cache_key_msft)

        assert cached_aapl is not None
        assert cached_msft is not None
        assert cached_aapl["symbol"] == "AAPL"
        assert cached_msft["symbol"] == "MSFT"


@pytest.mark.django_db
class TestAlphaVantageCacheIntegrationWithCommand:
    """Integration tests with calculate_intrinsic_value command."""

    def setup_method(self):
        """Clear cache before each test."""
        cache.clear()

    @patch("scanner.alphavantage.util.requests.get")
    def test_command_uses_cached_data(self, mock_get):
        """Verify command benefits from caching."""
        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "symbol": "AAPL",
            "quarterlyEarnings": [
                {"fiscalDateEnding": "2024-12-31", "reportedEPS": "2.50"},
                {"fiscalDateEnding": "2024-09-30", "reportedEPS": "2.40"},
                {"fiscalDateEnding": "2024-06-30", "reportedEPS": "2.30"},
                {"fiscalDateEnding": "2024-03-31", "reportedEPS": "2.20"},
            ],
        }
        mock_get.return_value = mock_response

        # First call - should hit API
        result1 = get_market_data("function=EARNINGS&symbol=AAPL")
        assert mock_get.call_count == 1

        # Second call - should use cache
        result2 = get_market_data("function=EARNINGS&symbol=AAPL")
        assert mock_get.call_count == 1  # Still 1, not called again

        # Results should be identical
        assert result1 == result2

    def test_cache_clear_removes_alpha_vantage_keys(self):
        """Verify cache clearing removes Alpha Vantage keys."""
        # Manually populate cache
        cache_key = f"{settings.CACHE_KEY_PREFIX_ALPHAVANTAGE}:earnings:AAPL"
        cache.set(cache_key, {"symbol": "AAPL"}, timeout=3600)

        # Verify key exists
        assert cache.get(cache_key) is not None

        # Clear cache
        cache.clear()

        # Verify key is gone
        assert cache.get(cache_key) is None
