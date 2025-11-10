# Task 032: Refactor Scanner Views to Use Django Cache

## Progress Summary

**Status**: Not Started

- [ ] Step 1: Write failing tests for scanner view cache integration
- [ ] Step 2: Refactor get_scan_results() to use Django cache
- [ ] Step 3: Refactor scan_view() to use Django cache
- [ ] Step 4: Refactor run_scan_in_background() to use Django cache
- [ ] Step 5: Update index() view cache usage
- [ ] Step 6: Update scan_status() view cache usage
- [ ] Step 7: Remove all direct Redis client instantiation
- [ ] Step 8: Run tests until all pass
- [ ] Step 9: Manual testing of scanner functionality

## Overview

Refactor all scanner views to use Django cache backend instead of direct Redis client connections. This migrates options scan data storage to use the same Django cache framework as Alpha Vantage data.

**Current State**:
- Scanner views use `redis.Redis.from_url()` directly
- Options data stored with manual JSON encoding/decoding
- Cache keys: `put_{ticker}`, `last_run`
- Task 029 added error handling for Redis failures

**Target State**:
- All views use `from django.core.cache import cache`
- Django cache handles serialization automatically
- Cache keys use consistent prefix: `scanner:put_{ticker}`
- 45-minute TTL applied to all options scan data
- No direct Redis client usage remaining

## Current State Analysis

### Current Redis Usage in Views

**Files using direct Redis**:
- `scanner/views.py`:
  - `index()` - Fetches cached results
  - `get_scan_results()` - Helper to fetch cached results
  - `scan_view()` - Triggers scan and stores results
  - `run_scan_in_background()` - Performs scan and caches results
  - `scan_status()` - Checks scan status

**Current pattern** (from Task 029):
```python
import redis
import os
import json

def get_scan_results():
    try:
        r = redis.Redis.from_url(os.environ.get("REDIS_URL"))
        keys = r.keys("put_*")
        
        for hash_key in keys:
            ticker = hash_key.decode("utf-8").split("_")[1]
            options_data = r.hget(hash_key, "options")
            if options_data:
                options = json.loads(options_data.decode("utf-8"))
                # ... process ...
        
        last_run_data = r.get("last_run")
        # ...
    except redis.RedisError as e:
        # Error handling from Task 029
        logger.warning(...)
        return safe_defaults
```

### Cache Keys Used

**Current keys**:
- `put_{ticker}` - Hash with fields: `options`, `last_scan`
- `last_run` - String with last scan timestamp
- `scan_in_progress` - Flag indicating scan is running

### Data Structures

**Options data**:
```python
# Stored per ticker as hash
{
    "options": json_string,  # List of option dicts
    "last_scan": timestamp_string
}
```

**Challenges**:
- Currently uses Redis hashes (`hset`, `hget`)
- Django cache doesn't support hash data structures
- Need to refactor to use simple key-value pairs

## Target State

### Django Cache Pattern

**New pattern**:
```python
from django.core.cache import cache
from django.conf import settings

def get_scan_results():
    """Fetch cached scan results using Django cache."""
    try:
        # Get all ticker options from cache
        ticker_options = cache.get(
            f"{settings.CACHE_KEY_PREFIX_SCANNER}:ticker_options",
            default={}
        )
        
        # Get scan metadata
        last_run = cache.get(
            f"{settings.CACHE_KEY_PREFIX_SCANNER}:last_run",
            default="Never"
        )
        
        # ... process ...
        
    except Exception as e:
        logger.warning(f"Cache error in get_scan_results: {e}")
        return safe_defaults
```

### Cache Keys Refactored

**New key structure**:
- `scanner:ticker_options` - Dict with all ticker options data
- `scanner:ticker_scan_times` - Dict with scan timestamps per ticker
- `scanner:last_run` - Last scan timestamp
- `scanner:scan_in_progress` - Boolean flag

**Benefit**: Simpler structure, fewer cache operations, automatic serialization.

### Data Structure Refactor

**Old structure** (Redis hashes):
```
put_AAPL (hash)
  ├─ options: "[{...}, {...}]"
  └─ last_scan: "2025-11-10 14:30:00"

put_MSFT (hash)
  ├─ options: "[{...}, {...}]"
  └─ last_scan: "2025-11-10 14:30:00"

last_run: "Scan completed at 2025-11-10 14:30:00"
```

**New structure** (Django cache):
```
scanner:ticker_options (dict):
{
    "AAPL": [{strike: 145, ...}, {strike: 150, ...}],
    "MSFT": [{strike: 340, ...}, {strike: 345, ...}]
}

scanner:ticker_scan_times (dict):
{
    "AAPL": "2025-11-10 14:30:00",
    "MSFT": "2025-11-10 14:30:00"
}

scanner:last_run (str): "Scan completed at 2025-11-10 14:30:00"
scanner:scan_in_progress (bool): False
```

**Benefit**: Single cache.get() fetches all ticker options instead of looping through keys.

## Implementation Steps

### Step 1: Write failing tests for scanner view cache integration

Create tests to define expected Django cache behavior.

**File to modify**: `scanner/tests/test_scanner_views.py`

**Add test class**:

```python
@pytest.mark.django_db
class TestScannerDjangoCacheIntegration:
    """Tests for scanner views using Django cache backend."""

    def setup_method(self):
        """Clear cache before each test."""
        from django.core.cache import cache
        cache.clear()

    def test_scan_stores_results_in_django_cache(self, client, user):
        """Scan view stores results using Django cache."""
        from django.core.cache import cache
        from django.conf import settings
        
        client.force_login(user)
        
        # Trigger scan (mocked to complete immediately)
        with patch('scanner.views.run_scan_in_background'):
            response = client.post('/scanner/scan/')
        
        # Verify cache keys exist
        ticker_options = cache.get(
            f"{settings.CACHE_KEY_PREFIX_SCANNER}:ticker_options"
        )
        last_run = cache.get(
            f"{settings.CACHE_KEY_PREFIX_SCANNER}:last_run"
        )
        
        assert ticker_options is not None
        assert last_run is not None

    def test_get_scan_results_uses_django_cache(self):
        """get_scan_results() fetches from Django cache."""
        from django.core.cache import cache
        from django.conf import settings
        from scanner.views import get_scan_results
        
        # Pre-populate cache
        cache.set(
            f"{settings.CACHE_KEY_PREFIX_SCANNER}:ticker_options",
            {"AAPL": [{"strike": 145.0, "premium": 2.5}]},
            timeout=settings.CACHE_TTL_OPTIONS
        )
        cache.set(
            f"{settings.CACHE_KEY_PREFIX_SCANNER}:last_run",
            "Test scan",
            timeout=settings.CACHE_TTL_OPTIONS
        )
        
        # Call function
        result = get_scan_results()
        
        # Verify it used cache
        assert result["ticker_options"]["AAPL"][0]["strike"] == 145.0
        assert result["last_scan"] == "Test scan"

    def test_scan_results_cached_with_45_min_ttl(self):
        """Scan results cached with 45-minute TTL."""
        from django.core.cache import cache
        from django.conf import settings
        
        # Mock the cache.set to verify timeout
        with patch.object(cache, 'set', wraps=cache.set) as mock_cache_set:
            # Run scan (mocked)
            from scanner.views import run_scan_in_background
            with patch('scanner.scanner.scan_options') as mock_scan:
                mock_scan.return_value = {"AAPL": [{"strike": 145}]}
                run_scan_in_background()
            
            # Verify cache.set called with correct timeout
            for call_args in mock_cache_set.call_args_list:
                args, kwargs = call_args
                if 'scanner:ticker_options' in args[0]:
                    assert kwargs['timeout'] == settings.CACHE_TTL_OPTIONS

    def test_no_direct_redis_usage_in_views(self):
        """Verify views don't use redis.Redis.from_url()."""
        import inspect
        from scanner import views
        
        # Get source code of views module
        source = inspect.getsource(views)
        
        # Should NOT contain direct Redis client usage
        assert 'redis.Redis.from_url' not in source
        assert 'Redis.from_url' not in source
        
        # Should use Django cache
        assert 'from django.core.cache import cache' in source

    def test_cache_error_handling_preserved(self, client, user):
        """Cache error handling from Task 029 still works."""
        from django.core.cache import cache
        
        # Mock cache.get to raise exception
        with patch.object(cache, 'get', side_effect=Exception("Cache error")):
            client.force_login(user)
            response = client.get('/scanner/scan/status/')
            
            # Should return safe defaults, not crash
            assert response.status_code == 200
            assert response.context["ticker_options"] == {}
```

**Run tests (should FAIL)**:
```bash
just test scanner/tests/test_scanner_views.py::TestScannerDjangoCacheIntegration -v
```

### Step 2: Refactor get_scan_results() to use Django cache

Convert helper function from Redis client to Django cache.

**File to modify**: `scanner/views.py`

**Replace get_scan_results() function**:

```python
def get_scan_results():
    """
    Helper function to fetch current scan results from Django cache.
    
    Returns:
        dict: Context with ticker_options, ticker_scan, last_scan, and curated_stocks
        
    Note:
        Returns safe defaults (empty dicts) if cache is unavailable.
        Uses Django cache backend instead of direct Redis client.
    """
    try:
        # Fetch all ticker options in single cache hit
        ticker_options = cache.get(
            f"{settings.CACHE_KEY_PREFIX_SCANNER}:ticker_options",
            default={}
        )
        
        # Fetch scan timestamps
        ticker_scan = cache.get(
            f"{settings.CACHE_KEY_PREFIX_SCANNER}:ticker_scan_times",
            default={}
        )
        
        # Fetch last run status
        last_scan = cache.get(
            f"{settings.CACHE_KEY_PREFIX_SCANNER}:last_run",
            default="Never"
        )
        
        # Sort ticker options by ticker symbol
        sorted_ticker_options = {k: ticker_options[k] for k in sorted(ticker_options)}
        
        # Fetch CuratedStock instances for all symbols in results
        if sorted_ticker_options:
            symbols = list(sorted_ticker_options.keys())
            curated_stocks = CuratedStock.objects.filter(symbol__in=symbols, active=True)
            curated_stocks_dict = {stock.symbol: stock for stock in curated_stocks}
        else:
            curated_stocks_dict = {}
        
        # Defensive: ensure curated_stocks_dict is actually a dict
        if not isinstance(curated_stocks_dict, dict):
            logger.warning(
                f"curated_stocks_dict is not a dict: {type(curated_stocks_dict).__name__}. "
                f"Resetting to empty dict."
            )
            curated_stocks_dict = {}
        
        return {
            "ticker_options": sorted_ticker_options,
            "ticker_scan": ticker_scan,
            "last_scan": last_scan,
            "curated_stocks": curated_stocks_dict,
            "is_local_environment": settings.ENVIRONMENT == "LOCAL",
        }
    
    except Exception as e:
        # Catch any cache errors (ConnectionError, TimeoutError, etc.)
        logger.warning(f"Cache error in get_scan_results: {e}", exc_info=True)
        return {
            "ticker_options": {},
            "ticker_scan": {},
            "last_scan": "Data temporarily unavailable. Please refresh the page.",
            "curated_stocks": {},  # ALWAYS dict, never None
            "is_local_environment": settings.ENVIRONMENT == "LOCAL",
        }
```

**Changes**:
- Removed `redis.Redis.from_url()`
- Removed `r.keys()` loop
- Removed `json.loads()` (Django cache handles serialization)
- Single cache.get() for all ticker options
- Simplified logic (no more hash operations)

### Step 3: Refactor scan_view() to use Django cache

Update scan trigger view to use Django cache.

**File to modify**: `scanner/views.py`

**Update scan_view() function**:

```python
@login_required
def scan_view(request):
    """
    Trigger options scan and return status.
    
    Initiates background scan and sets initial status in cache.
    """
    if request.method == "POST":
        try:
            # Set initial status
            cache.set(
                f"{settings.CACHE_KEY_PREFIX_SCANNER}:last_run",
                "Scanning in progress...",
                timeout=settings.CACHE_TTL_OPTIONS
            )
            
            # Set scan in progress flag
            cache.set(
                f"{settings.CACHE_KEY_PREFIX_SCANNER}:scan_in_progress",
                True,
                timeout=settings.CACHE_TTL_OPTIONS
            )
            
            # Run scan in background
            run_scan_in_background()
            
        except Exception as e:
            logger.error(f"Error initiating scan: {e}", exc_info=True)
            cache.set(
                f"{settings.CACHE_KEY_PREFIX_SCANNER}:last_run",
                f"Error initiating scan: {str(e)}",
                timeout=settings.CACHE_TTL_OPTIONS
            )
        
        # Return polling partial
        context = get_scan_results()
        return render(request, "scanner/partials/scan_polling.html", context)
    
    # GET request - show current status
    context = get_scan_results()
    return render(request, "scanner/index.html", context)
```

**Changes**:
- Use `cache.set()` instead of `r.set()`
- Use Django cache keys with prefix
- Add explicit timeout parameter

### Step 4: Refactor run_scan_in_background() to use Django cache

Update background scan function to store results in Django cache.

**File to modify**: `scanner/views.py`

**Replace run_scan_in_background() function**:

```python
def run_scan_in_background():
    """
    Execute options scan and store results in Django cache.
    
    Scans all active CuratedStock symbols for put options and caches
    results with 45-minute TTL.
    """
    try:
        from scanner.scanner import scan_options
        from datetime import datetime
        
        # Get active stocks to scan
        curated_stocks = CuratedStock.objects.filter(active=True)
        symbols = [stock.symbol for stock in curated_stocks]
        
        logger.info(f"Starting scan for {len(symbols)} symbols")
        
        # Run scan
        scan_results = scan_options(symbols)
        
        # Build results dictionaries
        ticker_options = {}
        ticker_scan_times = {}
        scan_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        for ticker, options in scan_results.items():
            if options:  # Only store if options found
                ticker_options[ticker] = options
                ticker_scan_times[ticker] = scan_time
        
        # Store in cache with 45-minute TTL
        cache.set(
            f"{settings.CACHE_KEY_PREFIX_SCANNER}:ticker_options",
            ticker_options,
            timeout=settings.CACHE_TTL_OPTIONS
        )
        
        cache.set(
            f"{settings.CACHE_KEY_PREFIX_SCANNER}:ticker_scan_times",
            ticker_scan_times,
            timeout=settings.CACHE_TTL_OPTIONS
        )
        
        # Update last run status
        completion_message = f"Scan completed successfully at {scan_time}"
        cache.set(
            f"{settings.CACHE_KEY_PREFIX_SCANNER}:last_run",
            completion_message,
            timeout=settings.CACHE_TTL_OPTIONS
        )
        
        # Clear scan in progress flag
        cache.delete(f"{settings.CACHE_KEY_PREFIX_SCANNER}:scan_in_progress")
        
        logger.info(f"Scan completed: {len(ticker_options)} tickers with options")
        
    except Exception as e:
        logger.error(f"Error during scan: {e}", exc_info=True)
        
        # Set error message in cache
        cache.set(
            f"{settings.CACHE_KEY_PREFIX_SCANNER}:last_run",
            f"Scan failed: {str(e)}",
            timeout=settings.CACHE_TTL_OPTIONS
        )
        
        # Clear scan in progress flag
        cache.delete(f"{settings.CACHE_KEY_PREFIX_SCANNER}:scan_in_progress")
```

**Changes**:
- Removed Redis client instantiation
- Build ticker_options and ticker_scan_times dicts in memory
- Single cache.set() call per data structure (not per ticker)
- Django cache handles serialization (no json.dumps needed)
- Explicit 45-minute TTL

### Step 5: Update index() view cache usage

Ensure index view uses get_scan_results() helper (should already be done from Task 029).

**File to check**: `scanner/views.py`

**Verify index() function**:

```python
@login_required
def index(request):
    """
    Display scanner index page with cached options results.
    
    Uses get_scan_results() helper which now uses Django cache.
    """
    context = get_scan_results()
    return render(request, "scanner/index.html", context)
```

**Expected**: No changes needed if Task 029 refactored this view to use `get_scan_results()`.

### Step 6: Update scan_status() view cache usage

Ensure scan_status view uses get_scan_results() helper.

**File to check**: `scanner/views.py`

**Verify scan_status() function**:

```python
@login_required
def scan_status(request):
    """
    Return current scan status as HTMX partial.
    
    Uses get_scan_results() helper which now uses Django cache.
    """
    context = get_scan_results()
    
    # Check if scan is still in progress
    scan_in_progress = cache.get(
        f"{settings.CACHE_KEY_PREFIX_SCANNER}:scan_in_progress",
        default=False
    )
    context["scan_in_progress"] = scan_in_progress
    
    return render(request, "scanner/partials/scan_polling.html", context)
```

**Change**: Add scan_in_progress check using Django cache.

### Step 7: Remove all direct Redis client instantiation

Search for and remove any remaining Redis client usage.

**Search for Redis imports**:
```bash
grep -n "import redis" scanner/views.py
grep -n "redis.Redis" scanner/views.py
grep -n "Redis.from_url" scanner/views.py
```

**Remove**:
- `import redis` statement
- Any `redis.Redis.from_url()` calls
- Any `json.loads()` or `json.dumps()` related to cache data

**Add if not present**:
```python
from django.core.cache import cache
from django.conf import settings
```

**Verify no Redis client in views**:
```bash
# Should return no results
grep -i "redis\.redis\|from_url" scanner/views.py
```

### Step 8: Run tests until all pass

Fix issues iteratively until all tests pass.

**Run scanner view tests**:
```bash
just test scanner/tests/test_scanner_views.py -v
```

**Run full test suite**:
```bash
just test
```

**Common issues to fix**:
1. Missing imports (`cache`, `settings`)
2. Cache key mismatch (test expects different key)
3. Serialization differences (Django cache handles differently than JSON)
4. Test mocks need updating (mock `cache` not `redis`)

**Expected**: All tests pass including existing + new cache integration tests.

### Step 9: Manual testing of scanner functionality

Test scanner works end-to-end with Django cache.

**Clear cache**:
```bash
uv run python manage.py shell

>>> from django.core.cache import cache
>>> cache.clear()
>>> exit()
```

**Test scan via UI**:
1. Start dev server: `just run`
2. Login at http://localhost:8000/accounts/login/
3. Navigate to http://localhost:8000/scanner/
4. Click "Scan for Options" button
5. Verify:
   - Status shows "Scanning in progress..."
   - After completion, shows "Scan completed successfully at [time]"
   - Options results display in accordion
   - Good/Bad pills show correctly

**Verify in cache**:
```bash
uv run python manage.py shell

>>> from django.core.cache import cache
>>> from django.conf import settings

>>> # Check ticker options
>>> ticker_options = cache.get(f"{settings.CACHE_KEY_PREFIX_SCANNER}:ticker_options")
>>> ticker_options
{'AAPL': [{...}], 'MSFT': [{...}], ...}

>>> # Check last run
>>> cache.get(f"{settings.CACHE_KEY_PREFIX_SCANNER}:last_run")
'Scan completed successfully at 2025-11-10 15:30:00'

>>> exit()
```

**Verify in Redis CLI**:
```bash
just redis-cli

127.0.0.1:6379> KEYS *scanner*
# Should see:
# wheel_analyzer:1:scanner:ticker_options
# wheel_analyzer:1:scanner:ticker_scan_times
# wheel_analyzer:1:scanner:last_run

127.0.0.1:6379> TTL wheel_analyzer:1:scanner:ticker_options
# Should show ~2700 seconds (45 minutes)

127.0.0.1:6379> exit
```

**Expected outcome**:
- Scanner works correctly
- Results cached in Django cache
- TTL is 45 minutes
- No direct Redis client usage
- Good/Bad pills display correctly

## Acceptance Criteria

### Code Requirements

- [ ] All scanner views use Django cache (not direct Redis client)
- [ ] Cache keys use `scanner:` prefix from settings
- [ ] All options data cached with 45-minute TTL
- [ ] Removed all `redis.Redis.from_url()` calls
- [ ] Removed all manual JSON serialization (json.loads/dumps)
- [ ] Error handling from Task 029 preserved
- [ ] Logging statements updated appropriately

### Testing Requirements

- [ ] Tests verify Django cache usage (not Redis client)
- [ ] Tests verify 45-minute TTL
- [ ] Tests verify cache keys use correct prefix
- [ ] Tests verify no direct Redis usage in code
- [ ] Tests verify error handling still works
- [ ] All existing tests still pass
- [ ] New cache integration tests pass

### Manual Testing Requirements

- [ ] Scanner UI works correctly
- [ ] Scan button triggers scan
- [ ] Status updates during scan
- [ ] Results display after scan
- [ ] Good/Bad pills show correctly
- [ ] Cache keys visible in Redis with correct prefix
- [ ] TTL is 2,700 seconds (45 minutes)

### Performance Requirements

- [ ] Scan performance unchanged or improved
- [ ] Cache lookups fast (single cache.get() vs multiple hget calls)
- [ ] No performance degradation

## Files Involved

### Modified Files

- `scanner/views.py` (~200 lines changed)
  - `get_scan_results()` - Complete refactor to Django cache
  - `scan_view()` - Update to Django cache
  - `run_scan_in_background()` - Complete refactor to Django cache
  - `scan_status()` - Add scan_in_progress check
  - Remove Redis imports
  - Add Django cache imports

- `scanner/tests/test_scanner_views.py` (~100 lines added)
  - Add `TestScannerDjangoCacheIntegration` class
  - Update existing test mocks to use Django cache

### Total Changes

- **Modified**: 2 files
- **Lines changed**: ~300 lines

## Notes

### Data Structure Migration

**Old: Redis hash per ticker**
```
Pros: Atomic operations per ticker
Cons: Multiple cache calls (r.keys, r.hget for each ticker)
```

**New: Single dict with all tickers**
```
Pros: Single cache.get() fetches all data, automatic serialization
Cons: Need to update entire dict to change one ticker (acceptable trade-off)
```

**Why this is better**:
- Fewer cache round trips (1 vs N)
- Simpler code (no loops over keys)
- Django cache handles serialization
- Still cached, so updates infrequent (45 min TTL)

### Cache Key Strategy

**Consolidated keys**:
- `scanner:ticker_options` - All ticker options in single dict
- `scanner:ticker_scan_times` - All scan timestamps in single dict
- `scanner:last_run` - Last scan status message
- `scanner:scan_in_progress` - Boolean flag

**Alternative considered**: Keep per-ticker keys like `scanner:put_AAPL`
**Rejected because**: More complex, more cache calls, harder to test

### Error Handling

**Preserved from Task 029**:
- Cache errors return safe defaults
- Warning-level logging (not error)
- App remains functional if cache unavailable
- Template handles empty dicts gracefully

**New considerations**:
- Django cache may raise different exceptions than Redis client
- Catch generic `Exception` instead of specific `redis.RedisError`
- Same principle: don't break app if cache fails

### TTL Considerations

**45-minute TTL reasoning**:
- Options data changes throughout trading day
- Manual scan trigger (user controls refresh)
- Balance between API load and data freshness
- Reasonable time for user to review results before re-scan

**Alternative**: 1-hour TTL for less frequent scans
**Chosen**: 45 minutes as middle ground

## Dependencies

- Django cache configured (Task 030)
- `scanner.scanner.scan_options()` function exists
- CuratedStock model with active field
- Templates expect ticker_options dict structure

## Reference

**Django cache documentation**:
- https://docs.djangoproject.com/en/5.1/topics/cache/
- https://docs.djangoproject.com/en/5.1/ref/settings/#std-setting-CACHES

**Cache-aside pattern**:
- Check cache first
- On miss, fetch data and populate cache
- Return data

**Serialization**:
- Django cache automatically pickles Python objects
- No need for manual JSON encoding
- Complex types (Decimal) may need special handling
