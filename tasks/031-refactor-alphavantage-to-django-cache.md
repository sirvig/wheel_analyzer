# Task 031: Refactor Alpha Vantage Module to Use Django Cache

## Progress Summary

**Status**: ✅ COMPLETED (Session: 2025-11-10)

- [x] Step 1: Write failing tests for Alpha Vantage cache integration
- [x] Step 2: Refactor technical_analysis.py to use Django cache
- [x] Step 3: Refactor util.py to use Django cache (if exists)
- [x] Step 4: Update calculate_intrinsic_value management command
- [x] Step 5: Run tests until all pass
- [x] Step 6: Manual testing of intrinsic value calculations

**Completion Notes**:
- Refactored `scanner/alphavantage/util.py` to use Django cache with standardized key format
- Added cache key parsing and building functions: `_parse_function_from_url()` and `_build_cache_key()`
- Cache keys now follow format: `alphavantage:{function}:{symbol}[:{params}]`
- All API calls automatically cached for 7 days (CACHE_TTL_ALPHAVANTAGE)
- Updated `calculate_intrinsic_value` management command to use new cache keys
- Removed duplicate caching logic from command (now handled by util.py)
- Created comprehensive test file `scanner/tests/test_alphavantage_cache.py` with 18 tests
- All 31 cache tests passing (13 Django cache + 18 Alpha Vantage cache)
- Cache hit/miss logging implemented with proper error handling
- Graceful degradation: API calls succeed even if cache fails
- Branch remains `refactor/scanner-django-cache`

## Overview

Refactor the Alpha Vantage module to use Django cache backend instead of direct cache calls. This ensures API responses are properly cached with a 7-day TTL, reducing API consumption and following Django best practices.

**Current State**:
- Alpha Vantage module may have cache calls or may not cache at all
- Bug report indicates API responses are NOT being cached
- Direct code inspection needed

**Target State**:
- All Alpha Vantage API calls wrapped with Django cache
- 7-day TTL applied to all fundamental data
- Cache keys use consistent naming: `alphavantage:earnings:{ticker}`
- Tests validate cache hit/miss behavior

## Current State Analysis

### Alpha Vantage Module Structure

**Files in `scanner/alphavantage/`**:
- `__init__.py` - Module initialization
- `technical_analysis.py` - SMA calculations and API calls
- `util.py` - Utility functions (may contain API helpers)

**Key Functions to Review**:
1. Functions that call Alpha Vantage API
2. Functions that fetch earnings data (EPS)
3. Functions that fetch cash flow data (FCF)
4. Functions that fetch company overview data
5. Any existing cache logic

### API Endpoints Used

Alpha Vantage endpoints likely called:
- `EARNINGS` - Quarterly and annual EPS data
- `CASH_FLOW` - Annual cash flow statements
- `OVERVIEW` - Company overview with growth rates
- `SMA` - Simple moving average (technical)

### Current Bug

From BUGS.md:
> "The calculate_intrinsic_value command does not actually cache the API return into redis. It looks like we are using Django cache but are not actually defining the Redis cache in settings."

**Implies**:
- Code may already have `cache.set()` calls
- But cache backend wasn't configured (Task 030 fixed this)
- Need to verify cache calls exist and work correctly

## Target State

### Cache Strategy

**Cache key format**:
```python
f"{settings.CACHE_KEY_PREFIX_ALPHAVANTAGE}:earnings:{ticker}"
f"{settings.CACHE_KEY_PREFIX_ALPHAVANTAGE}:cashflow:{ticker}"
f"{settings.CACHE_KEY_PREFIX_ALPHAVANTAGE}:overview:{ticker}"
f"{settings.CACHE_KEY_PREFIX_ALPHAVANTAGE}:sma:{ticker}:{period}"
```

**Cache TTL**: 7 days (604,800 seconds) via `settings.CACHE_TTL_ALPHAVANTAGE`

**Cache flow**:
```python
from django.core.cache import cache
from django.conf import settings

def get_earnings_data(ticker):
    """Fetch earnings data with 7-day cache."""
    cache_key = f"{settings.CACHE_KEY_PREFIX_ALPHAVANTAGE}:earnings:{ticker}"
    
    # Try cache first
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        logger.info(f"Cache hit for earnings: {ticker}")
        return cached_data
    
    # Cache miss - fetch from API
    logger.info(f"Cache miss for earnings: {ticker}, fetching from API")
    data = fetch_from_api(ticker)  # Make API call
    
    # Cache for 7 days
    cache.set(cache_key, data, timeout=settings.CACHE_TTL_ALPHAVANTAGE)
    
    return data
```

## Implementation Steps

### Step 1: Write failing tests for Alpha Vantage cache integration

Create tests first (TDD approach) to define expected behavior.

**File to create**: `scanner/tests/test_alphavantage_cache.py`

**Content**:

```python
"""
Unit tests for Alpha Vantage module cache integration.

Tests verify that Alpha Vantage API calls are properly cached using
Django cache backend with 7-day TTL.
"""

import pytest
from unittest.mock import patch, MagicMock
from django.core.cache import cache
from django.conf import settings


@pytest.mark.django_db
class TestAlphaVantageEarningsCache:
    """Tests for earnings data caching."""

    def setup_method(self):
        """Clear cache before each test."""
        cache.clear()

    @patch('scanner.alphavantage.technical_analysis.requests.get')
    def test_earnings_cached_on_first_call(self, mock_requests):
        """First call to get earnings data caches the result."""
        from scanner.alphavantage.technical_analysis import get_earnings_data
        
        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'symbol': 'AAPL',
            'quarterlyEarnings': [
                {'fiscalDateEnding': '2024-12-31', 'reportedEPS': '2.50'}
            ]
        }
        mock_requests.return_value = mock_response
        
        ticker = 'AAPL'
        cache_key = f"{settings.CACHE_KEY_PREFIX_ALPHAVANTAGE}:earnings:{ticker}"
        
        # Verify cache is empty
        assert cache.get(cache_key) is None
        
        # Call function
        result = get_earnings_data(ticker)
        
        # Verify API was called
        assert mock_requests.called
        
        # Verify result is cached
        cached_result = cache.get(cache_key)
        assert cached_result is not None
        assert cached_result == result

    @patch('scanner.alphavantage.technical_analysis.requests.get')
    def test_earnings_cache_hit_skips_api_call(self, mock_requests):
        """Second call uses cache and doesn't hit API."""
        from scanner.alphavantage.technical_analysis import get_earnings_data
        
        ticker = 'AAPL'
        cache_key = f"{settings.CACHE_KEY_PREFIX_ALPHAVANTAGE}:earnings:{ticker}"
        
        # Pre-populate cache
        cached_data = {
            'symbol': 'AAPL',
            'quarterlyEarnings': [
                {'fiscalDateEnding': '2024-12-31', 'reportedEPS': '2.50'}
            ]
        }
        cache.set(cache_key, cached_data, timeout=settings.CACHE_TTL_ALPHAVANTAGE)
        
        # Call function
        result = get_earnings_data(ticker)
        
        # Verify API was NOT called (cache hit)
        assert not mock_requests.called
        
        # Verify result matches cached data
        assert result == cached_data

    @patch('scanner.alphavantage.technical_analysis.requests.get')
    def test_earnings_cache_uses_7_day_ttl(self, mock_requests):
        """Earnings data cached with 7-day TTL."""
        from scanner.alphavantage.technical_analysis import get_earnings_data
        
        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = {'symbol': 'AAPL'}
        mock_requests.return_value = mock_response
        
        ticker = 'AAPL'
        cache_key = f"{settings.CACHE_KEY_PREFIX_ALPHAVANTAGE}:earnings:{ticker}"
        
        # Call function
        with patch.object(cache, 'set', wraps=cache.set) as mock_cache_set:
            get_earnings_data(ticker)
            
            # Verify cache.set was called with 7-day timeout
            mock_cache_set.assert_called_once()
            args, kwargs = mock_cache_set.call_args
            assert kwargs.get('timeout') == settings.CACHE_TTL_ALPHAVANTAGE


@pytest.mark.django_db
class TestAlphaVantageCashFlowCache:
    """Tests for cash flow data caching."""

    def setup_method(self):
        """Clear cache before each test."""
        cache.clear()

    @patch('scanner.alphavantage.technical_analysis.requests.get')
    def test_cashflow_cached_on_first_call(self, mock_requests):
        """First call to get cash flow data caches the result."""
        from scanner.alphavantage.technical_analysis import get_cashflow_data
        
        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'symbol': 'AAPL',
            'annualReports': [
                {'fiscalDateEnding': '2024-12-31', 'operatingCashflow': '100000000'}
            ]
        }
        mock_requests.return_value = mock_response
        
        ticker = 'AAPL'
        cache_key = f"{settings.CACHE_KEY_PREFIX_ALPHAVANTAGE}:cashflow:{ticker}"
        
        # Call function
        result = get_cashflow_data(ticker)
        
        # Verify result is cached
        cached_result = cache.get(cache_key)
        assert cached_result is not None
        assert cached_result == result

    @patch('scanner.alphavantage.technical_analysis.requests.get')
    def test_cashflow_cache_hit_skips_api_call(self, mock_requests):
        """Second call uses cache and doesn't hit API."""
        from scanner.alphavantage.technical_analysis import get_cashflow_data
        
        ticker = 'AAPL'
        cache_key = f"{settings.CACHE_KEY_PREFIX_ALPHAVANTAGE}:cashflow:{ticker}"
        
        # Pre-populate cache
        cached_data = {
            'symbol': 'AAPL',
            'annualReports': [
                {'fiscalDateEnding': '2024-12-31', 'operatingCashflow': '100000000'}
            ]
        }
        cache.set(cache_key, cached_data, timeout=settings.CACHE_TTL_ALPHAVANTAGE)
        
        # Call function
        result = get_cashflow_data(ticker)
        
        # Verify API was NOT called
        assert not mock_requests.called
        assert result == cached_data


@pytest.mark.django_db
class TestAlphaVantageOverviewCache:
    """Tests for company overview data caching."""

    def setup_method(self):
        """Clear cache before each test."""
        cache.clear()

    @patch('scanner.alphavantage.technical_analysis.requests.get')
    def test_overview_cached_on_first_call(self, mock_requests):
        """First call to get overview data caches the result."""
        from scanner.alphavantage.technical_analysis import get_company_overview
        
        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'Symbol': 'AAPL',
            'Name': 'Apple Inc',
            'MarketCapitalization': '3000000000000'
        }
        mock_requests.return_value = mock_response
        
        ticker = 'AAPL'
        cache_key = f"{settings.CACHE_KEY_PREFIX_ALPHAVANTAGE}:overview:{ticker}"
        
        # Call function
        result = get_company_overview(ticker)
        
        # Verify result is cached
        cached_result = cache.get(cache_key)
        assert cached_result is not None


@pytest.mark.django_db
class TestAlphaVantageSMACache:
    """Tests for SMA data caching."""

    def setup_method(self):
        """Clear cache before each test."""
        cache.clear()

    @patch('scanner.alphavantage.technical_analysis.requests.get')
    def test_sma_cached_with_period_in_key(self, mock_requests):
        """SMA cache key includes period parameter."""
        from scanner.alphavantage.technical_analysis import get_sma_data
        
        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'Meta Data': {'1: Symbol': 'AAPL'},
            'Technical Analysis: SMA': {
                '2024-11-10': {'SMA': '150.25'}
            }
        }
        mock_requests.return_value = mock_response
        
        ticker = 'AAPL'
        period = 200
        cache_key = f"{settings.CACHE_KEY_PREFIX_ALPHAVANTAGE}:sma:{ticker}:{period}"
        
        # Call function
        result = get_sma_data(ticker, period)
        
        # Verify result is cached with period in key
        cached_result = cache.get(cache_key)
        assert cached_result is not None


@pytest.mark.django_db
class TestCacheErrorHandling:
    """Tests for cache error handling in Alpha Vantage module."""

    def setup_method(self):
        """Clear cache before each test."""
        cache.clear()

    @patch('scanner.alphavantage.technical_analysis.requests.get')
    @patch('django.core.cache.cache.set')
    def test_api_call_succeeds_even_if_cache_set_fails(
        self, mock_cache_set, mock_requests
    ):
        """API call completes successfully even if caching fails."""
        from scanner.alphavantage.technical_analysis import get_earnings_data
        
        # Mock cache.set to raise exception
        mock_cache_set.side_effect = Exception("Cache unavailable")
        
        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = {'symbol': 'AAPL'}
        mock_requests.return_value = mock_response
        
        # Call should succeed despite cache failure
        result = get_earnings_data('AAPL')
        
        # Verify we got API data
        assert result is not None
        assert result['symbol'] == 'AAPL'

    @patch('scanner.alphavantage.technical_analysis.requests.get')
    @patch('django.core.cache.cache.get')
    def test_api_call_if_cache_get_fails(self, mock_cache_get, mock_requests):
        """API call made if cache.get() fails."""
        from scanner.alphavantage.technical_analysis import get_earnings_data
        
        # Mock cache.get to raise exception
        mock_cache_get.side_effect = Exception("Cache unavailable")
        
        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = {'symbol': 'AAPL'}
        mock_requests.return_value = mock_response
        
        # Should fall back to API call
        result = get_earnings_data('AAPL')
        
        # Verify API was called
        assert mock_requests.called
        assert result is not None


@pytest.mark.django_db
class TestCacheIntrinsicValueCommand:
    """Tests for cache integration in calculate_intrinsic_value command."""

    def setup_method(self):
        """Clear cache before each test."""
        cache.clear()

    @patch('scanner.alphavantage.technical_analysis.get_earnings_data')
    @patch('scanner.alphavantage.technical_analysis.get_cashflow_data')
    def test_command_uses_cached_data(
        self, mock_get_cashflow, mock_get_earnings
    ):
        """calculate_intrinsic_value command uses cached Alpha Vantage data."""
        from scanner.factories import CuratedStockFactory
        from django.core.management import call_command
        
        # Create test stock
        stock = CuratedStockFactory(symbol='AAPL', active=True)
        
        # Pre-populate cache
        earnings_data = {'symbol': 'AAPL', 'quarterlyEarnings': []}
        cashflow_data = {'symbol': 'AAPL', 'annualReports': []}
        
        mock_get_earnings.return_value = earnings_data
        mock_get_cashflow.return_value = cashflow_data
        
        # Run command
        call_command('calculate_intrinsic_value')
        
        # Verify cached data was used (functions called)
        assert mock_get_earnings.called
        assert mock_get_cashflow.called
```

**Run tests (they should FAIL initially)**:
```bash
just test scanner/tests/test_alphavantage_cache.py -v
```

**Expected**: Tests fail because functions don't exist or don't use cache yet.

### Step 2: Refactor technical_analysis.py to use Django cache

Update Alpha Vantage API functions to use Django cache.

**File to modify**: `scanner/alphavantage/technical_analysis.py`

**First, read the file to understand current implementation**:
```bash
# Read file to see current structure
uv run python -c "print(open('scanner/alphavantage/technical_analysis.py').read())"
```

**Expected changes** (exact implementation depends on current code):

```python
"""
Alpha Vantage API integration with Django cache.

All API calls are cached for 7 days to reduce API consumption and improve performance.
"""

import logging
import requests
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


def get_earnings_data(ticker):
    """
    Fetch quarterly and annual earnings data from Alpha Vantage.
    
    Results are cached for 7 days.
    
    Args:
        ticker (str): Stock ticker symbol
    
    Returns:
        dict: Earnings data from Alpha Vantage API
    """
    cache_key = f"{settings.CACHE_KEY_PREFIX_ALPHAVANTAGE}:earnings:{ticker}"
    
    # Try cache first
    try:
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            logger.info(f"Cache hit for earnings: {ticker}")
            return cached_data
    except Exception as e:
        logger.warning(f"Cache get failed for earnings:{ticker}: {e}")
        # Continue to API call
    
    # Cache miss - fetch from API
    logger.info(f"Cache miss for earnings: {ticker}, fetching from API")
    
    try:
        url = f"https://www.alphavantage.co/query"
        params = {
            'function': 'EARNINGS',
            'symbol': ticker,
            'apikey': settings.ALPHA_VANTAGE_API_KEY,
        }
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Cache the result for 7 days
        try:
            cache.set(cache_key, data, timeout=settings.CACHE_TTL_ALPHAVANTAGE)
            logger.info(f"Cached earnings data for {ticker}")
        except Exception as e:
            logger.warning(f"Failed to cache earnings for {ticker}: {e}")
            # Continue even if caching fails
        
        return data
        
    except requests.RequestException as e:
        logger.error(f"API request failed for earnings:{ticker}: {e}")
        raise


def get_cashflow_data(ticker):
    """
    Fetch cash flow data from Alpha Vantage.
    
    Results are cached for 7 days.
    
    Args:
        ticker (str): Stock ticker symbol
    
    Returns:
        dict: Cash flow data from Alpha Vantage API
    """
    cache_key = f"{settings.CACHE_KEY_PREFIX_ALPHAVANTAGE}:cashflow:{ticker}"
    
    # Try cache first
    try:
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            logger.info(f"Cache hit for cashflow: {ticker}")
            return cached_data
    except Exception as e:
        logger.warning(f"Cache get failed for cashflow:{ticker}: {e}")
    
    # Cache miss - fetch from API
    logger.info(f"Cache miss for cashflow: {ticker}, fetching from API")
    
    try:
        url = f"https://www.alphavantage.co/query"
        params = {
            'function': 'CASH_FLOW',
            'symbol': ticker,
            'apikey': settings.ALPHA_VANTAGE_API_KEY,
        }
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Cache for 7 days
        try:
            cache.set(cache_key, data, timeout=settings.CACHE_TTL_ALPHAVANTAGE)
            logger.info(f"Cached cashflow data for {ticker}")
        except Exception as e:
            logger.warning(f"Failed to cache cashflow for {ticker}: {e}")
        
        return data
        
    except requests.RequestException as e:
        logger.error(f"API request failed for cashflow:{ticker}: {e}")
        raise


def get_company_overview(ticker):
    """
    Fetch company overview from Alpha Vantage.
    
    Results are cached for 7 days.
    
    Args:
        ticker (str): Stock ticker symbol
    
    Returns:
        dict: Company overview data
    """
    cache_key = f"{settings.CACHE_KEY_PREFIX_ALPHAVANTAGE}:overview:{ticker}"
    
    # Try cache first
    try:
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            logger.info(f"Cache hit for overview: {ticker}")
            return cached_data
    except Exception as e:
        logger.warning(f"Cache get failed for overview:{ticker}: {e}")
    
    # Cache miss - fetch from API
    logger.info(f"Cache miss for overview: {ticker}, fetching from API")
    
    try:
        url = f"https://www.alphavantage.co/query"
        params = {
            'function': 'OVERVIEW',
            'symbol': ticker,
            'apikey': settings.ALPHA_VANTAGE_API_KEY,
        }
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Cache for 7 days
        try:
            cache.set(cache_key, data, timeout=settings.CACHE_TTL_ALPHAVANTAGE)
        except Exception as e:
            logger.warning(f"Failed to cache overview for {ticker}: {e}")
        
        return data
        
    except requests.RequestException as e:
        logger.error(f"API request failed for overview:{ticker}: {e}")
        raise


def get_sma_data(ticker, period=200):
    """
    Fetch SMA (Simple Moving Average) data from Alpha Vantage.
    
    Results are cached for 7 days.
    
    Args:
        ticker (str): Stock ticker symbol
        period (int): SMA period (default 200)
    
    Returns:
        dict: SMA data from Alpha Vantage API
    """
    cache_key = f"{settings.CACHE_KEY_PREFIX_ALPHAVANTAGE}:sma:{ticker}:{period}"
    
    # Try cache first
    try:
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            logger.info(f"Cache hit for SMA: {ticker} (period={period})")
            return cached_data
    except Exception as e:
        logger.warning(f"Cache get failed for sma:{ticker}:{period}: {e}")
    
    # Cache miss - fetch from API
    logger.info(f"Cache miss for SMA: {ticker} (period={period}), fetching from API")
    
    try:
        url = f"https://www.alphavantage.co/query"
        params = {
            'function': 'SMA',
            'symbol': ticker,
            'interval': 'daily',
            'time_period': period,
            'series_type': 'close',
            'apikey': settings.ALPHA_VANTAGE_API_KEY,
        }
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Cache for 7 days
        try:
            cache.set(cache_key, data, timeout=settings.CACHE_TTL_ALPHAVANTAGE)
        except Exception as e:
            logger.warning(f"Failed to cache SMA for {ticker}: {e}")
        
        return data
        
    except requests.RequestException as e:
        logger.error(f"API request failed for SMA:{ticker}: {e}")
        raise
```

**Note**: The exact implementation will depend on what currently exists in the file. The key pattern is:
1. Check cache first with `cache.get()`
2. If miss, call API
3. Cache result with `cache.set()` and 7-day TTL
4. Wrap cache operations in try/except (don't fail if cache unavailable)

### Step 3: Refactor util.py to use Django cache (if exists)

Check if `util.py` has API-related functions that need caching.

**File to check**: `scanner/alphavantage/util.py`

**Read file first**:
```bash
# Check if file exists and has content
[ -f scanner/alphavantage/util.py ] && cat scanner/alphavantage/util.py || echo "File does not exist"
```

**If file has API functions**:
- Apply same caching pattern as Step 2
- Use appropriate cache keys
- Use 7-day TTL

**If file is empty or doesn't exist**:
- Skip this step

### Step 4: Update calculate_intrinsic_value management command

Verify command uses the cached Alpha Vantage functions.

**File to check**: `scanner/management/commands/calculate_intrinsic_value.py`

**Verify** that command calls the refactored functions:
- `get_earnings_data(ticker)`
- `get_cashflow_data(ticker)`
- `get_company_overview(ticker)`

**Expected**: Command should "just work" since it calls the refactored functions. No code changes needed unless command was directly accessing cache.

**If command has direct cache access**: Remove it in favor of the function-level caching.

### Step 5: Run tests until all pass

Iteratively fix issues until all tests pass.

**Run Alpha Vantage cache tests**:
```bash
just test scanner/tests/test_alphavantage_cache.py -v
```

**Fix any failures**:
1. Ensure functions exist with correct names
2. Ensure cache keys match test expectations
3. Ensure TTL is settings.CACHE_TTL_ALPHAVANTAGE
4. Ensure error handling works

**Run full test suite**:
```bash
just test
```

**Expected**: All 180+ tests pass (including new ones).

### Step 6: Manual testing of intrinsic value calculations

Test that caching works in real usage.

**Clear cache first**:
```bash
uv run python manage.py shell

>>> from django.core.cache import cache
>>> cache.clear()
>>> exit()
```

**Run command (first time - should hit API)**:
```bash
# Run for one stock to test
uv run python manage.py calculate_intrinsic_value --limit 1

# Check logs - should see "Cache miss" messages
# Should see API calls being made
```

**Run command again (second time - should use cache)**:
```bash
uv run python manage.py calculate_intrinsic_value --limit 1

# Check logs - should see "Cache hit" messages
# Should NOT see API calls
# Should complete much faster
```

**Verify in Redis**:
```bash
just redis-cli

127.0.0.1:6379> KEYS *alphavantage*
# Should see keys like:
# wheel_analyzer:1:alphavantage:earnings:AAPL
# wheel_analyzer:1:alphavantage:cashflow:AAPL

127.0.0.1:6379> TTL wheel_analyzer:1:alphavantage:earnings:AAPL
# Should show ~604800 seconds (7 days)

127.0.0.1:6379> exit
```

**Expected outcome**:
- First run hits API (cache miss)
- Second run uses cache (cache hit)
- Cache keys visible in Redis
- TTL is 7 days
- Intrinsic values calculated correctly

## Acceptance Criteria

### Code Requirements

- [ ] All Alpha Vantage API functions use Django cache
- [ ] Cache keys follow format: `alphavantage:{function}:{ticker}`
- [ ] All cached data uses 7-day TTL (CACHE_TTL_ALPHAVANTAGE)
- [ ] Cache operations wrapped in try/except (graceful degradation)
- [ ] Logging added for cache hits and misses
- [ ] Error handling prevents cache failures from breaking API calls

### Testing Requirements

- [ ] Tests verify cache set on first call
- [ ] Tests verify cache hit on second call
- [ ] Tests verify 7-day TTL is used
- [ ] Tests verify cache miss triggers API call
- [ ] Tests verify cache errors don't break functionality
- [ ] All existing tests still pass (180+)
- [ ] New cache tests pass (10-15 new tests)

### Manual Testing Requirements

- [ ] `calculate_intrinsic_value` command works correctly
- [ ] First run logs "Cache miss" and hits API
- [ ] Second run logs "Cache hit" and skips API
- [ ] Cache keys visible in Redis with correct format
- [ ] TTL is 604,800 seconds (7 days)
- [ ] Intrinsic values calculated correctly

### Performance Requirements

- [ ] Second run significantly faster than first run
- [ ] API rate limits respected (reduced API calls)
- [ ] No performance degradation on cache hits

## Files Involved

### Modified Files

- `scanner/alphavantage/technical_analysis.py` (~100-150 lines changed)
  - Add cache.get() checks before API calls
  - Add cache.set() after API calls
  - Add error handling for cache operations
  - Add logging for cache hits/misses

- `scanner/alphavantage/util.py` (~50 lines changed, if applicable)
  - Same caching pattern as above

### Created Files

- `scanner/tests/test_alphavantage_cache.py` (~300 lines)
  - Tests for earnings cache
  - Tests for cashflow cache
  - Tests for overview cache
  - Tests for SMA cache
  - Tests for error handling

### Total Changes

- **Modified**: 2 files
- **Created**: 1 file
- **Lines changed**: ~450 lines

## Notes

### Cache Hit Rate

**Expected cache behavior**:
- **First command run**: 0% cache hit rate (all API calls)
- **Subsequent runs within 7 days**: 100% cache hit rate (no API calls)
- **After 7 days**: Cache expired, back to API calls

**Benefits**:
- Reduced API consumption (Alpha Vantage has rate limits)
- Faster response times (cache lookup vs network request)
- Lower costs (if using paid Alpha Vantage tier)

### Error Handling Philosophy

**Principle**: Cache should enhance performance, not cause failures.

**Implementation**:
```python
# Cache read failure - fall back to API
try:
    cached = cache.get(key)
except Exception:
    cached = None  # Continue to API call

# Cache write failure - log but continue
try:
    cache.set(key, data, timeout=TTL)
except Exception as e:
    logger.warning(f"Cache set failed: {e}")
    # Data already fetched, return it anyway
```

**Why**:
- API call success is more important than caching
- Cache unavailability shouldn't break core functionality
- Temporary cache issues shouldn't require code changes

### API Rate Limits

Alpha Vantage free tier:
- 5 API calls per minute
- 500 API calls per day

**Without caching**:
- Running `calculate_intrinsic_value` for 100 stocks = 200-300 API calls
- Exceeds daily limit quickly

**With 7-day caching**:
- First run: 200-300 API calls (within limit if spaced out)
- Subsequent runs within 7 days: 0 API calls
- Weekly runs sustainable

### Cache Invalidation

**When to invalidate cache**:
- Company releases new earnings report (quarterly)
- Cash flow statements updated (annually)
- Manual refresh needed

**How to invalidate**:
```python
# Clear specific stock
from django.core.cache import cache
cache.delete('alphavantage:earnings:AAPL')
cache.delete('alphavantage:cashflow:AAPL')

# Clear all Alpha Vantage cache
cache.delete_pattern('*alphavantage*')
```

**Future enhancement**: Add management command to clear specific cache types.

## Dependencies

- Django cache configured (Task 030)
- `requests` library for API calls
- Alpha Vantage API key in settings
- Redis running on port 36379

## Reference

**Alpha Vantage API documentation**:
- https://www.alphavantage.co/documentation/

**Django cache documentation**:
- https://docs.djangoproject.com/en/5.1/topics/cache/

**Cache patterns**:
- Cache-aside pattern (read-through cache)
- Lazy loading (populate on first access)
- TTL-based expiration
