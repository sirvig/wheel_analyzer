# Task 023: API Call Tracking and Enhanced Reporting

## Progress Summary

**Status**: ✅ Completed

- [x] Step 1: Add API call tracking instance variables
- [x] Step 2: Update fetch methods to track calls and cache hits
- [x] Step 3: Enhance per-stock output with before/after values
- [x] Step 4: Update post-execution summary with API stats
- [x] Step 5: Update module docstring
- [x] Step 6: Test with various scenarios

### Summary of Changes

Enhanced the `calculate_intrinsic_value` management command with comprehensive API call tracking and detailed reporting:
- Added `api_calls_made` and `cache_hits` instance variables
- Updated all three fetch methods (`_fetch_earnings_data`, `_fetch_eps_data`, `_fetch_cash_flow_data`) to track API calls vs cache hits
- Enhanced per-stock output to show previous values with calculation dates
- Display delta and percentage change for both EPS and FCF intrinsic values
- Show "(new)" label for first-time calculations
- Added API usage section to summary with cache hit rate
- Added remaining work section showing stocks never calculated and total active
- Updated module docstring to reflect daily rolling update strategy with 20-second rate limiting (3 calls/minute, conservative approach)

## Overview

Enhance the `calculate_intrinsic_value` management command with comprehensive API call tracking and very detailed reporting. This task adds:

- API call counters (actual API calls made vs cached responses)
- Cache hit rate calculation and reporting
- Before/after intrinsic values for each stock (both EPS and FCF methods)
- Delta calculations showing value changes and percentages
- Enhanced summaries showing remaining stocks to calculate
- Updated documentation reflecting the new daily rolling update strategy

## Current State Analysis

### Current Reporting

The command currently provides:
- Basic per-stock output: "✓ EPS intrinsic value: $150.25"
- Summary statistics: Success/Skipped/Error counts
- Duration in seconds

**Missing information**:
- How many actual API calls were made
- How many responses came from cache
- Previous intrinsic values (can't see what changed)
- Delta/percentage change in valuations
- Remaining stocks needing calculation

### Current Fetch Methods

The three fetch methods (`_fetch_earnings_data`, `_fetch_eps_data`, `_fetch_cash_flow_data`) return data but don't track whether the response came from cache or API.

**Current pattern**:
```python
def _fetch_earnings_data(self, symbol, force_refresh=False):
    cache_key = f"av_earnings_{symbol}"
    
    if not force_refresh:
        cached_data = cache.get(cache_key)
        if cached_data:
            self.stdout.write(self.style.SUCCESS("  Using cached earnings data"))
            return cached_data
    
    self.stdout.write("  Fetching earnings from Alpha Vantage API...")
    earnings_data = get_market_data(url)
    
    if earnings_data:
        cache.set(cache_key, earnings_data, CACHE_TTL)
    
    return earnings_data
```

**No tracking**: We print messages but don't count API calls vs cache hits.

## Target State

### Enhanced Per-Stock Output

```
[1/7] Processing AAPL...
  Previous values (Last calc: 2025-10-15 14:30:00):
    EPS intrinsic value: $150.25
    FCF intrinsic value: $148.50
  
  Fetching earnings from Alpha Vantage API...
  Using cached overview data
  Using cached cash flow data
  
  ✓ EPS intrinsic value: $152.75 (+$2.50, +1.66%)
  ✓ FCF intrinsic value: $151.20 (+$2.70, +1.82%)
```

**For never-calculated stocks**:
```
[2/7] Processing ABNB...
  Previous values: Never calculated
  
  Fetching earnings from Alpha Vantage API...
  Fetching overview from Alpha Vantage API...
  Fetching cash flow from Alpha Vantage API...
  
  ✓ EPS intrinsic value: $95.50 (new)
  ✓ FCF intrinsic value: $92.30 (new)
```

**For skipped calculations**:
```
[3/7] Processing TSLA...
  Previous values (Last calc: 2025-10-10 09:15:00):
    EPS intrinsic value: $180.00
    FCF intrinsic value: None
  
  Using cached earnings data
  Using cached overview data
  Using cached cash flow data
  
  ✓ EPS intrinsic value: $185.25 (+$5.25, +2.92%)
  ⊘ FCF skipped: Non-positive FCF/share: -$2.15
```

### Enhanced Post-Execution Summary

```
=================================================================
SUMMARY:
  Total processed: 7
  
  EPS Method:
    Successful: 7
    Skipped: 0
    Errors: 0
  
  FCF Method:
    Successful: 6
    Skipped: 1
    Errors: 0
  
  API USAGE:
    API calls made: 14
    Cache hits: 7
    Cache hit rate: 33.33%
  
  REMAINING WORK:
    Stocks never calculated: 5
    Stocks previously calculated: 38
    Total active stocks: 43
    
  Duration: 145.50 seconds
=================================================================
```

### Updated Module Docstring

```python
"""
Django management command to calculate intrinsic value for curated stocks.

This command fetches EPS TTM and FCF data from Alpha Vantage and calculates
the intrinsic value (fair value) for stocks in the curated list using both
EPS-based and FCF-based DCF models.

The command implements a smart selection strategy to respect AlphaVantage's
25 API calls/day limit on the free tier, processing 7 stocks per run (21 API
calls) by default, prioritizing never-calculated and oldest-calculated stocks
for a rolling update approach.

...

Usage:
    # Default: smart select 7 stocks (21 API calls)
    python manage.py calculate_intrinsic_value
    
    # Custom limit: process 10 stocks
    python manage.py calculate_intrinsic_value --limit 10
    
    # Force all: process all active stocks (shows warning if >25 calls)
    python manage.py calculate_intrinsic_value --force-all
    
    # Specific symbols (bypasses smart selection)
    python manage.py calculate_intrinsic_value --symbols AAPL MSFT
    
    # Force refresh API data
    python manage.py calculate_intrinsic_value --force-refresh
    
    # Clear cache before processing
    python manage.py calculate_intrinsic_value --clear-cache

Schedule:
    Run daily at 8 PM via cron for rolling updates:
    0 20 * * * cd /path/to/project && python manage.py calculate_intrinsic_value
"""
```

## Implementation Steps

### Step 1: Add API call tracking instance variables

Add instance variables to track API calls and cache hits.

**File to modify**: `scanner/management/commands/calculate_intrinsic_value.py`

**Changes to `handle()` method** (add near the start):

```python
def handle(self, *args, **options):
    """Main command execution."""
    # Log command start
    logger.info("=" * 60)
    logger.info("Starting intrinsic value calculation command")
    logger.info(f"Options: {options}")
    logger.info("=" * 60)
    
    start_time = timezone.now()
    
    # Initialize API tracking counters
    self.api_calls_made = 0
    self.cache_hits = 0
    
    # ... rest of existing code ...
```

### Step 2: Update fetch methods to track calls and cache hits

Modify all three fetch methods to increment counters.

**File to modify**: `scanner/management/commands/calculate_intrinsic_value.py`

**Pattern to apply to all fetch methods**:

```python
def _fetch_earnings_data(self, symbol, force_refresh=False):
    """
    Fetch quarterly earnings data from Alpha Vantage EARNINGS endpoint with Redis caching.
    
    Tracks API calls and cache hits for reporting.
    
    ...
    """
    cache_key = f"av_earnings_{symbol}"
    
    # Try to get from cache (unless force refresh)
    if not force_refresh:
        cached_data = cache.get(cache_key)
        if cached_data:
            self.cache_hits += 1  # Track cache hit
            self.stdout.write(self.style.SUCCESS("  Using cached earnings data"))
            logger.debug(f"Earnings cache hit for {symbol}")
            return cached_data
    
    # Fetch from API
    self.api_calls_made += 1  # Track API call
    self.stdout.write("  Fetching earnings from Alpha Vantage API...")
    logger.debug(f"Earnings cache miss for {symbol}, fetching from API")
    
    url = f"function=EARNINGS&symbol={symbol}"
    earnings_data = get_market_data(url)
    
    # Cache the response
    if earnings_data:
        cache.set(cache_key, earnings_data, CACHE_TTL)
        logger.debug(f"Cached earnings data for {symbol} (TTL: {CACHE_TTL}s)")
    
    return earnings_data
```

**Apply the same pattern to**:
- `_fetch_eps_data()` - Add `self.cache_hits += 1` and `self.api_calls_made += 1`
- `_fetch_cash_flow_data()` - Add `self.cache_hits += 1` and `self.api_calls_made += 1`

### Step 3: Enhance per-stock output with before/after values

Update the per-stock processing to show before/after values.

**File to modify**: `scanner/management/commands/calculate_intrinsic_value.py`

**Changes to `handle()` method** (inside the main loop):

```python
for index, stock in enumerate(stocks, start=1):
    self.stdout.write(
        f"\n[{index}/{total_stocks}] Processing {stock.symbol}..."
    )
    
    # Store previous values for comparison
    prev_eps_value = stock.intrinsic_value
    prev_fcf_value = stock.intrinsic_value_fcf
    prev_calc_date = stock.last_calculation_date
    
    # Show previous values
    if prev_calc_date:
        self.stdout.write(
            f"  Previous values (Last calc: {prev_calc_date.strftime('%Y-%m-%d %H:%M:%S')}):"
        )
        if prev_eps_value:
            self.stdout.write(f"    EPS intrinsic value: ${prev_eps_value}")
        else:
            self.stdout.write(f"    EPS intrinsic value: None")
        
        if prev_fcf_value:
            self.stdout.write(f"    FCF intrinsic value: ${prev_fcf_value}")
        else:
            self.stdout.write(f"    FCF intrinsic value: None")
    else:
        self.stdout.write("  Previous values: Never calculated")
    
    self.stdout.write("")  # Blank line
    
    # Process EPS (existing logic)
    try:
        eps_result = self._process_stock(
            stock, force_refresh=options.get("force_refresh", False)
        )
        
        if eps_result["status"] == "success":
            eps_success += 1
            new_value = eps_result['intrinsic_value']
            
            # Calculate delta
            if prev_eps_value:
                delta = new_value - prev_eps_value
                pct_change = (delta / prev_eps_value) * 100
                delta_str = f"(+${delta:.2f}, +{pct_change:.2f}%)" if delta >= 0 else f"(-${abs(delta):.2f}, {pct_change:.2f}%)"
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  ✓ EPS intrinsic value: ${new_value} {delta_str}"
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  ✓ EPS intrinsic value: ${new_value} (new)"
                    )
                )
        elif eps_result["status"] == "skipped":
            eps_skipped += 1
            self.stdout.write(
                self.style.WARNING(f"  ⊘ EPS skipped: {eps_result['reason']}")
            )
    except Exception as e:
        eps_error += 1
        logger.error(
            f"EPS processing error for {stock.symbol}: {e}", exc_info=True
        )
        self.stdout.write(self.style.ERROR(f"  ✗ EPS error: {str(e)}"))
    
    # Process FCF (existing logic with similar delta calculation)
    try:
        overview_data = self._fetch_eps_data(
            stock.symbol, force_refresh=False
        )
        
        if overview_data and "SharesOutstanding" in overview_data:
            fcf_result = self._process_stock_fcf(
                stock,
                overview_data,
                force_refresh=options.get("force_refresh", False),
            )
            
            if fcf_result["status"] == "success":
                fcf_success += 1
                new_fcf_value = fcf_result['intrinsic_value_fcf']
                
                # Calculate delta
                if prev_fcf_value:
                    delta = new_fcf_value - prev_fcf_value
                    pct_change = (delta / prev_fcf_value) * 100
                    delta_str = f"(+${delta:.2f}, +{pct_change:.2f}%)" if delta >= 0 else f"(-${abs(delta):.2f}, {pct_change:.2f}%)"
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  ✓ FCF intrinsic value: ${new_fcf_value} {delta_str}"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  ✓ FCF intrinsic value: ${new_fcf_value} (new)"
                        )
                    )
            elif fcf_result["status"] == "skipped":
                fcf_skipped += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"  ⊘ FCF skipped: {fcf_result['reason']}"
                    )
                )
        else:
            fcf_skipped += 1
            self.stdout.write(
                self.style.WARNING(
                    "  ⊘ FCF skipped: OVERVIEW data not available"
                )
            )
    except Exception as e:
        fcf_error += 1
        logger.error(
            f"FCF processing error for {stock.symbol}: {e}", exc_info=True
        )
        self.stdout.write(self.style.ERROR(f"  ✗ FCF error: {str(e)}"))
    
    # Rate limiting: wait between API calls
    if index < total_stocks:
        self._rate_limit_delay()
```

### Step 4: Update post-execution summary with API stats

Enhance the summary section to include API usage and remaining work.

**File to modify**: `scanner/management/commands/calculate_intrinsic_value.py`

**Changes to `handle()` method** (summary section):

```python
# Summary
end_time = timezone.now()
duration = (end_time - start_time).total_seconds()

# Get remaining work stats
remaining_stats = self._get_calculation_stats()

self.stdout.write(self.style.SUCCESS(f"\n{'=' * 65}"))
self.stdout.write(self.style.SUCCESS("SUMMARY:"))
self.stdout.write(self.style.SUCCESS(f"  Total processed: {total_stocks}"))
self.stdout.write(self.style.SUCCESS("\n  EPS Method:"))
self.stdout.write(self.style.SUCCESS(f"    Successful: {eps_success}"))
self.stdout.write(self.style.WARNING(f"    Skipped: {eps_skipped}"))
self.stdout.write(self.style.ERROR(f"    Errors: {eps_error}"))
self.stdout.write(self.style.SUCCESS("\n  FCF Method:"))
self.stdout.write(self.style.SUCCESS(f"    Successful: {fcf_success}"))
self.stdout.write(self.style.WARNING(f"    Skipped: {fcf_skipped}"))
self.stdout.write(self.style.ERROR(f"    Errors: {fcf_error}"))

# API usage statistics
self.stdout.write(self.style.SUCCESS("\n  API USAGE:"))
self.stdout.write(f"    API calls made: {self.api_calls_made}")
self.stdout.write(f"    Cache hits: {self.cache_hits}")
total_requests = self.api_calls_made + self.cache_hits
if total_requests > 0:
    cache_hit_rate = (self.cache_hits / total_requests) * 100
    self.stdout.write(f"    Cache hit rate: {cache_hit_rate:.2f}%")

# Remaining work
self.stdout.write(self.style.SUCCESS("\n  REMAINING WORK:"))
self.stdout.write(f"    Stocks never calculated: {remaining_stats['never_calculated']}")
self.stdout.write(f"    Stocks previously calculated: {remaining_stats['previously_calculated']}")
self.stdout.write(f"    Total active stocks: {remaining_stats['total']}")

self.stdout.write(self.style.SUCCESS(f"\n  Duration: {duration:.2f} seconds"))
self.stdout.write(self.style.SUCCESS(f"{'=' * 65}\n"))

# Log command completion
logger.info("=" * 60)
logger.info(f"Command completed in {duration:.2f} seconds")
logger.info(
    f"EPS - Success: {eps_success}, Skipped: {eps_skipped}, Errors: {eps_error}"
)
logger.info(
    f"FCF - Success: {fcf_success}, Skipped: {fcf_skipped}, Errors: {fcf_error}"
)
logger.info(f"API - Calls: {self.api_calls_made}, Cache hits: {self.cache_hits}")
logger.info("=" * 60)
```

### Step 5: Update module docstring

Update the docstring at the top of the file to reflect new functionality.

**File to modify**: `scanner/management/commands/calculate_intrinsic_value.py`

**Replace existing docstring** (lines 1-25) with enhanced version:

```python
"""
Django management command to calculate intrinsic value for curated stocks.

This command fetches EPS TTM and FCF data from Alpha Vantage and calculates
the intrinsic value (fair value) for stocks in the curated list using both
EPS-based and FCF-based DCF models.

The command implements a smart selection strategy to respect AlphaVantage's
25 API calls/day limit on the free tier. By default, it processes 7 stocks
per run (21 API calls), prioritizing never-calculated stocks and then
selecting the oldest-calculated stocks for a rolling update approach.

EPS is calculated as Trailing Twelve Months (TTM) by summing the 4 most recent
quarterly reportedEPS values from the EARNINGS endpoint.

The command makes 3 API calls per stock:
- EARNINGS: to calculate EPS TTM from quarterly data
- OVERVIEW: to fetch SharesOutstanding (needed for FCF calculation)
- CASH_FLOW: to calculate FCF TTM from quarterly data

All API responses are cached in Redis for 7 days to minimize API usage.

Usage:
    # Default: smart select 7 stocks (21 API calls)
    python manage.py calculate_intrinsic_value
    
    # Custom limit: process 10 stocks
    python manage.py calculate_intrinsic_value --limit 10
    
    # Force all: process all active stocks (shows warning if >25 calls)
    python manage.py calculate_intrinsic_value --force-all
    
    # Specific symbols (bypasses smart selection)
    python manage.py calculate_intrinsic_value --symbols AAPL MSFT
    
    # Force refresh API data (bypass cache)
    python manage.py calculate_intrinsic_value --force-refresh
    
    # Clear cache before processing
    python manage.py calculate_intrinsic_value --clear-cache

Schedule:
    Run daily at 8 PM via cron for rolling updates:
    0 20 * * * cd /path/to/project && python manage.py calculate_intrinsic_value
    
    With 7 stocks/day, all stocks refresh within ~7 days (for 50 stocks).

Smart Selection Logic:
    1. Prioritize stocks with NULL last_calculation_date (never calculated)
    2. Then select stocks with oldest last_calculation_date (stale valuations)
    3. Limit to N stocks (default: 7) to respect API quotas
    
API Rate Limiting:
    - AlphaVantage free tier: 25 calls/day
    - Default: 7 stocks × 3 calls = 21 API calls (conservative)
    - Cache: 7-day TTL reduces actual API calls significantly
    - Use --force-all carefully to avoid rate limits

Reporting:
    - Detailed per-stock output with before/after values
    - Delta and percentage change calculations
    - API call tracking (actual calls vs cache hits)
    - Cache hit rate statistics
    - Remaining stocks to calculate
"""
```

### Step 6: Test with various scenarios

Test the enhanced reporting with different data states.

**Test scenarios**:

1. **Fresh calculations** (no previous values):
   - Set all `last_calculation_date` to NULL
   - Set all intrinsic values to NULL
   - Run command
   - Verify: "Never calculated" and "(new)" labels appear

2. **Updates with changes**:
   - Set some stocks with previous values and dates
   - Manually change a stock's assumptions (growth rate)
   - Run command
   - Verify: Delta and percentage change displayed correctly

3. **Cache hits**:
   - Run command twice without clearing cache
   - Verify: Second run shows "Using cached..." messages
   - Verify: API stats show cache hits

4. **Mixed success/failure**:
   - Have some stocks with complete data, some missing
   - Run command
   - Verify: Both successful calculations and skipped stocks shown properly

5. **API call tracking**:
   - Clear cache, run with `--limit 3`
   - Verify: API calls = 9 (3 stocks × 3 calls)
   - Run again without clearing
   - Verify: Cache hits > 0, API calls < 9

**Test commands**:

```bash
# Fresh run with cleared cache
just exec python manage.py calculate_intrinsic_value --limit 3 --clear-cache

# Second run to test cache
just exec python manage.py calculate_intrinsic_value --limit 3

# Large batch to test summary stats
just exec python manage.py calculate_intrinsic_value --limit 10

# Single stock for focused testing
just exec python manage.py calculate_intrinsic_value --symbols AAPL
```

## Acceptance Criteria

### API Tracking Requirements

- [x] API call counter increments on actual API requests
- [x] Cache hit counter increments on cached responses
- [x] Counters accurate across all three fetch methods
- [x] Cache hit rate calculation is correct
- [x] Summary displays API usage statistics

### Per-Stock Output Requirements

- [x] Previous values displayed before processing
- [x] Previous calculation date shown (if exists)
- [x] "Never calculated" shown for NULL dates
- [x] Before/after values shown for both EPS and FCF
- [x] Delta calculated correctly (new - old)
- [x] Percentage change calculated correctly
- [x] "(new)" label for first-time calculations
- [x] Positive changes show "+" prefix
- [x] Negative changes show "-" prefix (automatic with format)

### Summary Requirements

- [x] Remaining stocks statistics accurate
- [x] API usage section displays all metrics
- [x] Cache hit rate percentage formatted correctly
- [x] Duration displayed in seconds
- [x] Both EPS and FCF statistics shown

### Documentation Requirements

- [x] Module docstring updated with new usage patterns
- [x] All command options documented
- [x] Smart selection logic explained
- [x] Cron schedule updated (daily, not weekly)
- [x] API rate limiting explained (20 seconds, 3 calls/minute)

### Technical Requirements

- [x] No breaking changes to existing functionality
- [x] Counters initialized properly in handle()
- [x] All three fetch methods track correctly
- [x] Decimal precision maintained in delta calculations
- [x] No performance degradation

## Files Involved

### Modified Files

- `scanner/management/commands/calculate_intrinsic_value.py`
  - Module docstring (lines 1-70) - Complete rewrite
  - `handle()` - Add counters, per-stock deltas, enhanced summary
  - `_fetch_earnings_data()` - Add tracking
  - `_fetch_eps_data()` - Add tracking
  - `_fetch_cash_flow_data()` - Add tracking

## Notes

### Delta Calculation Logic

**Formula**:
- Delta = New Value - Previous Value
- Percentage = (Delta / Previous Value) × 100

**Special cases**:
- Previous = NULL → Show "(new)" instead of delta
- Previous = 0 → Skip percentage (avoid division by zero)
- Delta = 0 → Show "$0.00, 0.00%"

**Formatting**:
- Positive delta: `+$2.50, +1.66%`
- Negative delta: `-$2.50, -1.66%`
- Zero delta: `$0.00, 0.00%`
- New value: `(new)`

### API Tracking Accuracy

**Per-stock API calls** (worst case, no cache):
- EARNINGS: 1 call
- OVERVIEW: 1 call  
- CASH_FLOW: 1 call
- Total: 3 calls

**Cache scenarios**:
- All cached: 0 API calls, 3 cache hits
- None cached: 3 API calls, 0 cache hits
- Mixed: varies (e.g., 1 API call, 2 cache hits)

**Tracking verification**:
```python
# After processing N stocks
assert self.api_calls_made + self.cache_hits == N * 3
```

### Cache Hit Rate Interpretation

**High cache hit rate** (>70%):
- Data recently fetched
- Cache working effectively
- Very few actual API calls
- Good for frequent runs

**Low cache hit rate** (<30%):
- Cache cleared or expired
- First run after 7 days
- Using --force-refresh
- High API usage

**Example calculation**:
- 7 stocks processed
- 14 API calls made
- 7 cache hits
- Total: 21 requests
- Cache hit rate: 7/21 = 33.33%

### Remaining Work Statistics

**Purpose**:
- Track overall progress toward full portfolio valuation
- Estimate time to complete all stocks
- Identify if new stocks added need calculation

**Example interpretation**:
```
Remaining work:
  Never calculated: 5
  Previously calculated: 38
  Total active: 43

Interpretation:
- 5 stocks need initial valuation (high priority)
- 38 stocks have valuations (may need refresh based on age)
- Processing complete when never_calculated = 0
```

### Performance Considerations

**Additional processing per stock**:
- Store 2 previous values (trivial memory)
- Calculate 2 deltas (simple arithmetic)
- Format output strings (negligible CPU)

**Overall impact**: <1% increase in execution time

**Benefits outweigh costs**:
- Much better visibility into changes
- Easier debugging of valuation shifts
- More confidence in calculations

## Dependencies

- Requires Task 022 (smart stock selection) for remaining work statistics
- Uses `_get_calculation_stats()` helper from Task 022
- All dependencies from previous Phase 4 tasks

## Reference

**Python String Formatting**:
- f-strings: https://docs.python.org/3/tutorial/inputoutput.html#formatted-string-literals
- Decimal formatting: https://docs.python.org/3/library/decimal.html

**Django Command Output**:
- Styling: https://docs.djangoproject.com/en/5.1/howto/custom-management-commands/#django.core.management.BaseCommand.style

**Logging**:
- Python logging: https://docs.python.org/3/library/logging.html
- Django logging: https://docs.djangoproject.com/en/5.1/topics/logging/
