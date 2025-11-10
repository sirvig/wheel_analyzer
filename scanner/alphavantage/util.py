"""
Alpha Vantage API utility functions with Django cache integration.

All API calls are cached for 7 days to reduce API consumption and improve performance.
Uses standardized cache key format: alphavantage:{function}:{symbol}:{params}
"""

import logging
import os
from urllib.parse import parse_qs

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


def get_api_key():
    """Get Alpha Vantage API key from environment."""
    API_KEY = os.environ.get("AV_API_KEY")
    return API_KEY


def get_base_url():
    """Get Alpha Vantage base URL from environment."""
    URL_BASE = os.environ.get("AV_URL_BASE")
    return URL_BASE


def _parse_function_from_url(url):
    """
    Parse the Alpha Vantage function name from URL query string.

    Args:
        url: Query string like "function=EARNINGS&symbol=AAPL"

    Returns:
        Tuple of (function_name, symbol, additional_params_dict)

    Example:
        >>> _parse_function_from_url("function=EARNINGS&symbol=AAPL")
        ('EARNINGS', 'AAPL', {})
        >>> _parse_function_from_url(
        ...     "function=SMA&symbol=AAPL&interval=daily&time_period=200"
        ... )
        ('SMA', 'AAPL', {'interval': 'daily', 'time_period': '200'})
    """
    params = parse_qs(url)

    function_name = params.get("function", ["unknown"])[0]
    symbol = params.get("symbol", ["unknown"])[0]

    # Collect additional parameters (exclude function, symbol, and apikey)
    additional_params = {}
    for key, values in params.items():
        if key not in ("function", "symbol", "apikey") and values:
            additional_params[key] = values[0]

    return function_name, symbol, additional_params


def _build_cache_key(function_name, symbol, additional_params=None):
    """
    Build standardized cache key for Alpha Vantage API responses.

    Format: alphavantage:{function}:{symbol}[:{param_key}_{param_value}]

    Args:
        function_name: Alpha Vantage function (EARNINGS, OVERVIEW, CASH_FLOW, SMA, etc.)
        symbol: Stock ticker symbol
        additional_params: Dictionary of additional parameters (for SMA, etc.)

    Returns:
        Cache key string

    Examples:
        >>> _build_cache_key("EARNINGS", "AAPL")
        'alphavantage:earnings:AAPL'
        >>> _build_cache_key("SMA", "AAPL", {"time_period": "200"})
        'alphavantage:sma:AAPL:time_period_200'
    """
    # Normalize function name to lowercase for consistency
    function_lower = function_name.lower()

    # Base key with prefix from settings
    key_parts = [settings.CACHE_KEY_PREFIX_ALPHAVANTAGE, function_lower, symbol.upper()]

    # Add additional parameters in sorted order for consistency
    if additional_params:
        for param_key in sorted(additional_params.keys()):
            param_value = additional_params[param_key]
            key_parts.append(f"{param_key}_{param_value}")

    cache_key = ":".join(key_parts)

    return cache_key


def get_market_data(url):
    """
    Fetch data from Alpha Vantage API with Django cache.

    Results are cached for 7 days (CACHE_TTL_ALPHAVANTAGE) to reduce API consumption.

    Cache key format: alphavantage:{function}:{symbol}[:{params}]

    Args:
        url: Query string for Alpha Vantage API (without base URL and API key)
             Example: "function=EARNINGS&symbol=AAPL"

    Returns:
        Dictionary with API response data

    Examples:
        >>> get_market_data("function=EARNINGS&symbol=AAPL")
        {'symbol': 'AAPL', 'quarterlyEarnings': [...]}

        >>> get_market_data("function=OVERVIEW&symbol=MSFT")
        {'Symbol': 'MSFT', 'Name': 'Microsoft Corp', ...}
    """
    # Parse function and symbol from URL for cache key
    function_name, symbol, additional_params = _parse_function_from_url(url)

    # Build cache key using standardized format
    cache_key = _build_cache_key(function_name, symbol, additional_params)

    # Try cache first
    try:
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            logger.info(f"Alpha Vantage cache hit: {function_name} for {symbol}")
            return cached_data
    except Exception as e:
        logger.warning(
            f"Cache get failed for {cache_key}: {e}. Continuing to API call."
        )
        # Continue to API call if cache fails

    # Cache miss - fetch from API
    logger.info(
        f"Alpha Vantage cache miss: {function_name} for {symbol}, fetching from API"
    )

    data = {}
    base_url = get_base_url()
    api_key = get_api_key()
    request_url = f"{base_url}?{url}&apikey={api_key}"

    try:
        response = requests.get(request_url, timeout=30)

        # Check if request was successful
        if response.status_code in (200, 203):
            # Parse JSON response
            data = response.json()

            # Cache the successful response for 7 days
            try:
                cache.set(cache_key, data, timeout=settings.CACHE_TTL_ALPHAVANTAGE)
                logger.info(
                    f"Cached Alpha Vantage response for {symbol} "
                    f"(function={function_name}, TTL={settings.CACHE_TTL_ALPHAVANTAGE}s)"
                )
            except Exception as e:
                logger.warning(
                    f"Failed to cache Alpha Vantage response for {cache_key}: {e}"
                )
                # Continue - we have the data even if caching failed
        else:
            logger.error(
                f"Failed to retrieve data from Alpha Vantage: "
                f"status={response.status_code}, url={request_url}"
            )

    except requests.RequestException as e:
        logger.error(f"Alpha Vantage API request failed: {e}")
        # Return empty dict on error

    return data
