# Task 033: Update Management Commands to Use Django Cache

## Progress Summary

**Status**: Not Started

- [ ] Step 1: Review all management commands for Redis usage
- [ ] Step 2: Update cron_scanner.py to use Django cache
- [ ] Step 3: Update cron_sma.py to use Django cache
- [ ] Step 4: Verify calculate_intrinsic_value uses cached Alpha Vantage data
- [ ] Step 5: Write tests for management command cache integration
- [ ] Step 6: Run tests until all pass
- [ ] Step 7: Manual testing of each command

## Overview

Update management commands in `scanner/management/commands/` to use Django cache backend instead of direct Redis clients. Ensures consistency across entire application.

**Current State**:
- `cron_scanner.py` - May use direct Redis to store scan results
- `cron_sma.py` - May use direct Redis to store SMA data  
- `calculate_intrinsic_value.py` - Uses Alpha Vantage module (already refactored in Task 031)
- Other commands - Need to check for Redis usage

**Target State**:
- All commands use Django cache
- No direct Redis client usage
- Consistent with views and Alpha Vantage module
- Tests verify cache integration

## Current State Analysis

### Management Commands Location

**Directory**: `scanner/management/commands/`

**Files to review**:
- `calculate_intrinsic_value.py` - DCF calculations
- `calculate_minimum_premium.py` - Premium calculations
- `cron_scanner.py` - Scheduled options scanning
- `cron_sma.py` - Scheduled SMA calculations
- `find_options.py` - Find options for trading
- `find_rolls.py` - Find roll opportunities
- `verify_curated_stocks.py` - Data validation

### Expected Redis Usage

**Likely candidates for Redis usage**:
1. `cron_scanner.py` - Stores scan results (similar to views)
2. `cron_sma.py` - Stores SMA data
3. Others - Unlikely but need to verify

**Commands unlikely to use Redis**:
- `calculate_intrinsic_value.py` - Uses Alpha Vantage functions (Task 031)
- `calculate_minimum_premium.py` - Calculation only
- `find_options.py` - Query only
- `find_rolls.py` - Query only
- `verify_curated_stocks.py` - Data validation only

## Implementation Steps

### Step 1: Review all management commands for Redis usage

Search for Redis usage across all commands.

**Search commands**:
```bash
# Search for redis imports
grep -r "import redis" scanner/management/commands/

# Search for Redis client usage  
grep -r "redis.Redis\|Redis.from_url" scanner/management/commands/

# Search for json.loads/dumps (indicator of manual serialization)
grep -r "json.loads\|json.dumps" scanner/management/commands/
```

**For each file with Redis usage**:
1. Note the file name
2. Identify what data is cached
3. Identify cache keys used
4. Plan migration to Django cache

**Document findings**:
```bash
# List files that need changes
# Create action plan for each file
```

### Step 2: Update cron_scanner.py to use Django cache

Migrate cron_scanner from Redis client to Django cache.

**File to modify**: `scanner/management/commands/cron_scanner.py`

**Read file first**:
```bash
cat scanner/management/commands/cron_scanner.py
```

**Expected pattern** (similar to run_scan_in_background):

**Before**:
```python
import redis
import os
import json

class Command(BaseCommand):
    def handle(self, *args, **options):
        # ... scan logic ...
        
        r = redis.Redis.from_url(os.environ.get("REDIS_URL"))
        
        for ticker, options in results.items():
            r.hset(f"put_{ticker}", "options", json.dumps(options))
            r.hset(f"put_{ticker}", "last_scan", scan_time)
        
        r.set("last_run", completion_message)
```

**After**:
```python
from django.core.cache import cache
from django.conf import settings

class Command(BaseCommand):
    def handle(self, *args, **options):
        # ... scan logic ...
        
        # Build results dictionaries
        ticker_options = {}
        ticker_scan_times = {}
        
        for ticker, options in results.items():
            if options:
                ticker_options[ticker] = options
                ticker_scan_times[ticker] = scan_time
        
        # Store in Django cache with 45-minute TTL
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
        
        cache.set(
            f"{settings.CACHE_KEY_PREFIX_SCANNER}:last_run",
            completion_message,
            timeout=settings.CACHE_TTL_OPTIONS
        )
```

**Changes**:
- Replace `redis.Redis.from_url()` with Django cache
- Remove JSON serialization (cache handles it)
- Use same cache keys as views (Task 032)
- Use 45-minute TTL from settings

### Step 3: Update cron_sma.py to use Django cache

Migrate cron_sma from Redis client to Django cache.

**File to modify**: `scanner/management/commands/cron_sma.py`

**Read file first**:
```bash
cat scanner/management/commands/cron_sma.py
```

**Expected pattern**:

**If storing SMA data**:
```python
from django.core.cache import cache
from django.conf import settings

class Command(BaseCommand):
    def handle(self, *args, **options):
        # ... fetch SMA data ...
        
        # Cache SMA data with 7-day TTL (technical data doesn't change frequently)
        for ticker, sma_data in sma_results.items():
            cache_key = f"{settings.CACHE_KEY_PREFIX_ALPHAVANTAGE}:sma:{ticker}:200"
            cache.set(
                cache_key,
                sma_data,
                timeout=settings.CACHE_TTL_ALPHAVANTAGE
            )
```

**Note**: SMA is technical data from Alpha Vantage, so use:
- `CACHE_KEY_PREFIX_ALPHAVANTAGE` prefix
- `CACHE_TTL_ALPHAVANTAGE` (7 days) TTL
- This matches the caching in `get_sma_data()` from Task 031

**If NO caching needed**:
- Command might just calculate and display SMA
- No changes needed

### Step 4: Verify calculate_intrinsic_value uses cached Alpha Vantage data

Check that command uses refactored Alpha Vantage functions from Task 031.

**File to check**: `scanner/management/commands/calculate_intrinsic_value.py`

**Read file**:
```bash
cat scanner/management/commands/calculate_intrinsic_value.py
```

**Verify**:
- Imports from `scanner.alphavantage.technical_analysis`
- Calls `get_earnings_data()`, `get_cashflow_data()`, etc.
- Does NOT have direct Redis client usage
- Does NOT cache data itself (functions handle caching)

**Expected**: No changes needed if using refactored functions.

**If command has direct Redis usage**:
- Remove it (duplicates function-level caching)
- Functions already cache for 7 days

### Step 5: Write tests for management command cache integration

Create tests to verify commands use Django cache correctly.

**File to create**: `scanner/tests/test_management_commands_cache.py`

**Content**:

```python
"""
Tests for management commands cache integration.

Verifies that management commands use Django cache backend
instead of direct Redis clients.
"""

import pytest
from unittest.mock import patch, MagicMock
from django.core.cache import cache
from django.core.management import call_command
from django.conf import settings
from io import StringIO


@pytest.mark.django_db
class TestCronScannerCache:
    """Tests for cron_scanner command cache integration."""

    def setup_method(self):
        """Clear cache before each test."""
        cache.clear()

    @patch('scanner.scanner.scan_options')
    def test_cron_scanner_stores_in_django_cache(self, mock_scan):
        """cron_scanner stores results in Django cache."""
        # Mock scan results
        mock_scan.return_value = {
            'AAPL': [{'strike': 145.0, 'premium': 2.5}],
            'MSFT': [{'strike': 340.0, 'premium': 3.0}],
        }
        
        # Run command
        out = StringIO()
        call_command('cron_scanner', stdout=out)
        
        # Verify cache keys exist
        ticker_options = cache.get(
            f"{settings.CACHE_KEY_PREFIX_SCANNER}:ticker_options"
        )
        
        assert ticker_options is not None
        assert 'AAPL' in ticker_options
        assert ticker_options['AAPL'][0]['strike'] == 145.0

    @patch('scanner.scanner.scan_options')
    def test_cron_scanner_uses_45_min_ttl(self, mock_scan):
        """cron_scanner caches with 45-minute TTL."""
        mock_scan.return_value = {'AAPL': [{'strike': 145.0}]}
        
        # Mock cache.set to verify TTL
        with patch.object(cache, 'set', wraps=cache.set) as mock_cache_set:
            out = StringIO()
            call_command('cron_scanner', stdout=out)
            
            # Find call with ticker_options
            for call_args in mock_cache_set.call_args_list:
                args, kwargs = call_args
                if 'ticker_options' in args[0]:
                    assert kwargs['timeout'] == settings.CACHE_TTL_OPTIONS
                    break
            else:
                pytest.fail("cache.set not called with ticker_options")

    def test_cron_scanner_no_direct_redis_usage(self):
        """cron_scanner doesn't use redis.Redis.from_url()."""
        import inspect
        from scanner.management.commands import cron_scanner
        
        # Get source code
        source = inspect.getsource(cron_scanner)
        
        # Should NOT contain direct Redis usage
        assert 'redis.Redis.from_url' not in source
        assert 'Redis.from_url' not in source


@pytest.mark.django_db  
class TestCronSMACache:
    """Tests for cron_sma command cache integration."""

    def setup_method(self):
        """Clear cache before each test."""
        cache.clear()

    @patch('scanner.alphavantage.technical_analysis.get_sma_data')
    def test_cron_sma_uses_django_cache(self, mock_get_sma):
        """cron_sma uses Django cache for SMA data."""
        # Pre-populate cache
        cache_key = f"{settings.CACHE_KEY_PREFIX_ALPHAVANTAGE}:sma:AAPL:200"
        cached_sma = {'Technical Analysis: SMA': {'2024-11-10': {'SMA': '150.25'}}}
        cache.set(cache_key, cached_sma, timeout=settings.CACHE_TTL_ALPHAVANTAGE)
        
        mock_get_sma.return_value = cached_sma
        
        # Run command
        out = StringIO()
        call_command('cron_sma', stdout=out)
        
        # Verify cached data was used
        # (Implementation depends on command structure)

    def test_cron_sma_no_direct_redis_usage(self):
        """cron_sma doesn't use redis.Redis.from_url()."""
        import inspect
        from scanner.management.commands import cron_sma
        
        # Get source code
        source = inspect.getsource(cron_sma)
        
        # Should NOT contain direct Redis usage
        assert 'redis.Redis.from_url' not in source


@pytest.mark.django_db
class TestCalculateIntrinsicValueCache:
    """Tests for calculate_intrinsic_value command cache integration."""

    def setup_method(self):
        """Clear cache before each test."""
        cache.clear()

    @patch('scanner.alphavantage.technical_analysis.get_earnings_data')
    @patch('scanner.alphavantage.technical_analysis.get_cashflow_data')
    def test_calculate_iv_uses_cached_alphavantage_data(
        self, mock_get_cashflow, mock_get_earnings
    ):
        """calculate_intrinsic_value uses cached Alpha Vantage data."""
        from scanner.factories import CuratedStockFactory
        
        # Create test stock
        stock = CuratedStockFactory(symbol='AAPL', active=True)
        
        # Mock Alpha Vantage responses
        mock_get_earnings.return_value = {
            'symbol': 'AAPL',
            'quarterlyEarnings': [
                {'fiscalDateEnding': '2024-09-30', 'reportedEPS': '1.50'},
                {'fiscalDateEnding': '2024-06-30', 'reportedEPS': '1.40'},
                {'fiscalDateEnding': '2024-03-31', 'reportedEPS': '1.55'},
                {'fiscalDateEnding': '2023-12-31', 'reportedEPS': '2.18'},
            ]
        }
        
        mock_get_cashflow.return_value = {
            'symbol': 'AAPL',
            'annualReports': [
                {'fiscalDateEnding': '2024-09-30', 'operatingCashflow': '110543000000'},
            ]
        }
        
        # Run command
        out = StringIO()
        call_command('calculate_intrinsic_value', '--limit', '1', stdout=out)
        
        # Verify Alpha Vantage functions were called (using cache)
        assert mock_get_earnings.called
        assert mock_get_cashflow.called

    def test_calculate_iv_no_direct_redis_usage(self):
        """calculate_intrinsic_value doesn't use redis.Redis.from_url()."""
        import inspect
        from scanner.management.commands import calculate_intrinsic_value
        
        # Get source code
        source = inspect.getsource(calculate_intrinsic_value)
        
        # Should NOT contain direct Redis usage
        assert 'redis.Redis.from_url' not in source
        assert 'Redis.from_url' not in source


@pytest.mark.django_db
class TestAllManagementCommandsNoDirect Redis:
    """Verify NO management commands use direct Redis client."""

    def test_no_management_commands_use_direct_redis(self):
        """All management commands use Django cache, not Redis client."""
        import os
        import glob
        
        commands_dir = 'scanner/management/commands/'
        command_files = glob.glob(f'{commands_dir}*.py')
        
        for filepath in command_files:
            if filepath.endswith('__init__.py'):
                continue
            
            with open(filepath, 'r') as f:
                source = f.read()
            
            # Check for direct Redis usage
            if 'redis.Redis.from_url' in source or 'Redis.from_url' in source:
                pytest.fail(
                    f"{filepath} still uses direct Redis client. "
                    f"Should use Django cache instead."
                )
```

**Run tests (should FAIL initially)**:
```bash
just test scanner/tests/test_management_commands_cache.py -v
```

### Step 6: Run tests until all pass

Fix issues in commands and tests until all pass.

**Iterative process**:
1. Run tests
2. Read error messages
3. Fix command code or test code
4. Repeat

**Common issues**:
- Command doesn't exist (need to implement)
- Command has different structure than expected
- Cache keys don't match
- TTL not set correctly
- Missing imports

**Run tests**:
```bash
just test scanner/tests/test_management_commands_cache.py -v
```

**Run full suite**:
```bash
just test
```

**Expected**: All tests pass.

### Step 7: Manual testing of each command

Test each command manually to verify cache integration.

**Test cron_scanner**:
```bash
# Clear cache
uv run python manage.py shell -c "from django.core.cache import cache; cache.clear()"

# Run command
uv run python manage.py cron_scanner

# Verify cache
uv run python manage.py shell

>>> from django.core.cache import cache
>>> from django.conf import settings
>>> ticker_options = cache.get(f"{settings.CACHE_KEY_PREFIX_SCANNER}:ticker_options")
>>> ticker_options
{'AAPL': [{...}], ...}
>>> exit()
```

**Test cron_sma**:
```bash
# Clear cache
uv run python manage.py shell -c "from django.core.cache import cache; cache.clear()"

# Run command
uv run python manage.py cron_sma

# Verify cache (if applicable)
uv run python manage.py shell

>>> from django.core.cache import cache
>>> from django.conf import settings
>>> # Check for SMA cache keys
>>> # (exact verification depends on command implementation)
>>> exit()
```

**Test calculate_intrinsic_value**:
```bash
# Clear cache
uv run python manage.py shell -c "from django.core.cache import cache; cache.clear()"

# First run (should hit API, cache miss)
uv run python manage.py calculate_intrinsic_value --limit 1
# Watch for "Cache miss" log messages

# Second run (should use cache, cache hit)
uv run python manage.py calculate_intrinsic_value --limit 1
# Watch for "Cache hit" log messages
# Should complete faster

# Verify cache
uv run python manage.py shell

>>> from django.core.cache import cache
>>> from django.conf import settings
>>> earnings = cache.get(f"{settings.CACHE_KEY_PREFIX_ALPHAVANTAGE}:earnings:AAPL")
>>> earnings
{...}  # Alpha Vantage earnings data
>>> exit()
```

**Expected outcomes**:
- All commands run successfully
- Data cached with correct keys
- TTLs set correctly
- No direct Redis client errors
- Cache reused on subsequent runs

## Acceptance Criteria

### Code Requirements

- [ ] All management commands use Django cache
- [ ] No `redis.Redis.from_url()` calls in any command
- [ ] No manual JSON serialization in commands
- [ ] Cache keys use appropriate prefixes (scanner: or alphavantage:)
- [ ] TTLs match data type (45 min for options, 7 days for fundamentals)
- [ ] Error handling for cache failures

### Testing Requirements

- [ ] Tests verify commands use Django cache
- [ ] Tests verify correct cache keys
- [ ] Tests verify correct TTLs
- [ ] Tests verify no direct Redis usage
- [ ] All existing tests still pass
- [ ] New command cache tests pass

### Manual Testing Requirements

- [ ] `cron_scanner` command works and caches results
- [ ] `cron_sma` command works (and caches if applicable)
- [ ] `calculate_intrinsic_value` uses cached Alpha Vantage data
- [ ] Cache hit/miss behavior works correctly
- [ ] Cache keys visible in Redis with correct format
- [ ] TTLs set correctly

### Documentation Requirements

- [ ] Command help text updated if needed
- [ ] Comments explain cache usage
- [ ] Logging statements informative

## Files Involved

### Modified Files

- `scanner/management/commands/cron_scanner.py` (~50 lines changed)
  - Replace Redis client with Django cache
  - Update cache keys
  - Add TTL

- `scanner/management/commands/cron_sma.py` (~30 lines changed)
  - Replace Redis client with Django cache (if applicable)
  - Update cache keys
  - Add TTL

- `scanner/management/commands/calculate_intrinsic_value.py` (~10 lines changed)
  - Verify uses cached functions
  - Remove any direct Redis usage

### Created Files

- `scanner/tests/test_management_commands_cache.py` (~200 lines)
  - Tests for cron_scanner cache integration
  - Tests for cron_sma cache integration  
  - Tests for calculate_intrinsic_value cache integration
  - Test for no direct Redis usage across all commands

### Total Changes

- **Modified**: 3 files
- **Created**: 1 file
- **Lines changed**: ~300 lines

## Notes

### Command vs View Caching

**Commands** (cron_scanner):
- Scheduled/manual execution
- Store data for views to consume
- Use same cache keys as views
- Populate cache for UI

**Views** (scan_view):
- User-triggered
- Read from cache OR populate cache
- Display cached data
- Provide UI interaction

**Key insight**: Commands and views share cache, same keys, same structure.

### SMA Caching Strategy

**Option 1**: Cache in command
- Command fetches SMA from API
- Command caches for 7 days
- Views/calculations use cached data

**Option 2**: Cache in function
- Command calls `get_sma_data()` (Task 031)
- Function handles caching
- Command just orchestrates

**Recommended**: Option 2 (function-level caching)
- Consistent with Alpha Vantage pattern
- Single source of truth
- Command doesn't duplicate caching logic

### Error Handling in Commands

**Commands should be robust**:
```python
try:
    # Cache operation
    cache.set(key, value, timeout=TTL)
except Exception as e:
    # Log but don't fail command
    self.stdout.write(
        self.style.WARNING(f"Cache set failed: {e}")
    )
    # Command completes successfully anyway
```

**Why**:
- Commands often run in cron
- Can't interact with user to fix
- Better to log and continue
- Data computed anyway, caching is optimization

### Cache Warm-up

**Purpose of cron commands**:
- Pre-populate cache before users access UI
- Reduce user wait time
- Stay within API rate limits

**Example flow**:
1. Cron runs `cron_scanner` at 9:00 AM
2. Command fetches options, caches for 45 minutes
3. User accesses scanner at 9:15 AM
4. View instantly returns cached results
5. Cache expires at 9:45 AM
6. User can trigger manual scan

## Dependencies

- Django cache configured (Task 030)
- Alpha Vantage functions refactored (Task 031)
- Scanner views refactored (Task 032)
- CuratedStock model with active field
- `scanner.scanner.scan_options()` function

## Reference

**Django management commands**:
- https://docs.djangoproject.com/en/5.1/howto/custom-management-commands/

**Django cache**:
- https://docs.djangoproject.com/en/5.1/topics/cache/

**Cron patterns**:
- Pre-populate cache during off-peak hours
- Respect API rate limits
- Log all operations for debugging
- Fail gracefully if cache unavailable
