# Task 022: Smart Stock Selection for API Rate Limit Optimization

## Progress Summary

**Status**: ✅ Completed

- [x] Step 1: Add command-line arguments (--limit and --force-all)
- [x] Step 2: Implement smart stock selection logic
- [x] Step 3: Add pre-execution summary
- [x] Step 4: Test stock selection with various scenarios

### Summary of Changes

Implemented smart stock selection logic in the `calculate_intrinsic_value` management command with new `--limit` and `--force-all` flags. The command now:
- Processes 7 stocks by default (21 API calls, conservative limit respecting AlphaVantage's 25 calls/day)
- Prioritizes stocks with NULL `last_calculation_date` (never calculated)
- Then selects stocks with oldest calculation dates for rolling updates
- Shows detailed pre-execution summary with calculation statistics
- Warns when API call estimates exceed 25 calls/day
- Uses 20-second rate limiting (3 calls/minute) for conservative API usage

## Overview

Modify the `calculate_intrinsic_value` management command to intelligently select which stocks to process, respecting AlphaVantage's 25 API requests/day limit. The command currently processes all active stocks, making 3 API calls per stock (EARNINGS, OVERVIEW, CASH_FLOW). 

This task implements a rolling update strategy that:
- Processes 7 stocks per run by default (21 API calls, conservative limit)
- Prioritizes stocks never calculated (NULL `last_calculation_date`)
- Then selects stocks with oldest `last_calculation_date` (stale valuations)
- Allows override with `--limit N` or `--force-all` flags

## Current State Analysis

### Current Behavior

The `_get_stocks_to_process()` method in `calculate_intrinsic_value.py`:

```python
def _get_stocks_to_process(self, symbols=None):
    if symbols:
        # Process specific symbols
        stocks = CuratedStock.objects.filter(
            symbol__in=[s.upper() for s in symbols]
        )
        # ... validation ...
    else:
        # Process all active stocks
        stocks = CuratedStock.objects.filter(active=True)
    
    return stocks.order_by("symbol")
```

**Current limitations**:
- Processes ALL active stocks when no `--symbols` provided
- No respect for API rate limits
- No way to limit the number of stocks processed
- No prioritization strategy

### API Call Analysis

**Per-stock API calls** (3 total):
1. EARNINGS endpoint - for EPS TTM calculation
2. OVERVIEW endpoint - for shares outstanding (FCF calculation)
3. CASH_FLOW endpoint - for FCF TTM calculation

**Daily limit**: 25 API calls on AlphaVantage free tier
**Conservative processing**: 7 stocks × 3 calls = 21 API calls (4-call buffer)

## Target State

### New Command Arguments

```bash
# Default: process 7 stocks (21 API calls)
python manage.py calculate_intrinsic_value

# Custom limit: process 10 stocks (30 API calls - will show warning)
python manage.py calculate_intrinsic_value --limit 10

# Force all: process all active stocks (shows warning if >25 calls)
python manage.py calculate_intrinsic_value --force-all

# Existing functionality preserved
python manage.py calculate_intrinsic_value --symbols AAPL MSFT
```

### Smart Selection Logic

**Priority order**:
1. **Never calculated**: Active stocks where `last_calculation_date IS NULL`
2. **Oldest calculated**: Active stocks ordered by `last_calculation_date ASC`
3. **Combine**: Take first N stocks from combined QuerySet

**Example scenario** (15 active stocks, limit=7):
- 3 stocks with NULL calculation date → Selected (positions 1-3)
- 12 stocks with calculation dates → Select 4 oldest (positions 4-7)
- Result: 7 stocks prioritizing never-calculated, then stalest valuations

### Pre-Execution Summary

```
Starting intrinsic value calculation...
=================================================================
CALCULATION STATISTICS:
  Total active curated stocks: 50
  Never calculated: 12
  Previously calculated: 38
  Oldest calculation: 2024-10-01 (AAPL)
  
EXECUTION PLAN:
  Stocks to process this run: 7
  Estimated API calls: 21 (under 25/day limit ✓)
  
  Selected stocks (in processing order):
    1. ABNB (never calculated)
    2. CRWD (never calculated)
    3. DDOG (never calculated)
    4. AAPL (last calculated: 2024-10-01)
    5. MSFT (last calculated: 2024-10-08)
    6. GOOGL (last calculated: 2024-10-10)
    7. AMZN (last calculated: 2024-10-12)
=================================================================
Processing stocks...
```

**Warning for --force-all** (if API calls > 25):
```
⚠ WARNING: Processing 50 stocks will make ~150 API calls.
⚠ This exceeds the AlphaVantage free tier limit of 25 calls/day.
⚠ You may encounter rate limit errors.
Proceeding with processing...
```

## Implementation Steps

### Step 1: Add command-line arguments (--limit and --force-all)

Update the `add_arguments()` method to accept new flags.

**File to modify**: `scanner/management/commands/calculate_intrinsic_value.py`

**Changes**:

```python
def add_arguments(self, parser):
    parser.add_argument(
        "--symbols",
        nargs="+",
        type=str,
        help="Specific stock symbols to calculate (default: smart selection)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=7,
        help="Number of stocks to process (default: 7 for ~21 API calls)",
    )
    parser.add_argument(
        "--force-all",
        action="store_true",
        help="Process ALL active stocks (ignores --limit, may exceed API limits)",
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Force refresh of cached API data",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear all cached Alpha Vantage data before processing",
    )
```

**Validation**:
- `--force-all` and `--limit` are mutually exclusive (use `--force-all` behavior)
- `--force-all` and `--symbols` are mutually exclusive (use `--symbols` behavior)
- `--limit` must be positive integer
- `--symbols` takes precedence over both `--limit` and `--force-all`

### Step 2: Implement smart stock selection logic

Rewrite the `_get_stocks_to_process()` method with smart selection.

**File to modify**: `scanner/management/commands/calculate_intrinsic_value.py`

**New implementation**:

```python
def _get_stocks_to_process(self, symbols=None, limit=7, force_all=False):
    """
    Get list of CuratedStock objects to process with smart selection.
    
    Priority:
    1. If --symbols provided: process those specific symbols
    2. If --force-all: process all active stocks
    3. Otherwise: smart select `limit` stocks (default 7)
    
    Smart selection logic:
    - First priority: stocks with NULL last_calculation_date (never calculated)
    - Second priority: stocks with oldest last_calculation_date
    - Combine both lists and take first `limit` stocks
    
    Args:
        symbols: Optional list of specific symbols to process
        limit: Number of stocks to process (default: 7)
        force_all: Process all active stocks (default: False)
    
    Returns:
        QuerySet of CuratedStock objects
    """
    # Case 1: Specific symbols requested
    if symbols:
        stocks = CuratedStock.objects.filter(
            symbol__in=[s.upper() for s in symbols]
        )
        
        if not stocks.exists():
            raise CommandError(
                f"No stocks found with symbols: {', '.join(symbols)}"
            )
        
        # Warn about inactive stocks
        inactive = stocks.filter(active=False)
        if inactive.exists():
            self.stdout.write(
                self.style.WARNING(
                    f"Note: {inactive.count()} inactive stock(s) will be processed"
                )
            )
        
        return stocks.order_by("symbol")
    
    # Case 2: Force all active stocks
    if force_all:
        stocks = CuratedStock.objects.filter(active=True).order_by("symbol")
        
        # Show API limit warning if exceeding 25 calls
        estimated_calls = stocks.count() * 3
        if estimated_calls > 25:
            self.stdout.write(
                self.style.WARNING(
                    f"\n⚠ WARNING: Processing {stocks.count()} stocks will make "
                    f"~{estimated_calls} API calls."
                )
            )
            self.stdout.write(
                self.style.WARNING(
                    "⚠ This exceeds the AlphaVantage free tier limit of 25 calls/day."
                )
            )
            self.stdout.write(
                self.style.WARNING(
                    "⚠ You may encounter rate limit errors."
                )
            )
            self.stdout.write("")  # Blank line
        
        return stocks
    
    # Case 3: Smart selection with limit
    # Get stocks never calculated (NULL last_calculation_date)
    never_calculated = CuratedStock.objects.filter(
        active=True,
        last_calculation_date__isnull=True
    ).order_by('symbol')
    
    # Get stocks previously calculated, ordered by oldest first
    previously_calculated = CuratedStock.objects.filter(
        active=True,
        last_calculation_date__isnull=False
    ).order_by('last_calculation_date', 'symbol')
    
    # Combine: prioritize never_calculated, then oldest
    never_calc_list = list(never_calculated)
    prev_calc_list = list(previously_calculated)
    
    # Take up to `limit` stocks total
    combined = never_calc_list + prev_calc_list
    selected = combined[:limit]
    
    # Convert back to QuerySet for consistent return type
    if selected:
        selected_ids = [stock.id for stock in selected]
        # Preserve the order we selected
        stocks = CuratedStock.objects.filter(id__in=selected_ids)
        
        # Manually order to preserve priority: never calculated first, then by date
        stocks_dict = {stock.id: stock for stock in stocks}
        ordered_stocks = [stocks_dict[sid] for sid in selected_ids]
        
        # Return as list (handle() can iterate over it)
        return ordered_stocks
    
    return CuratedStock.objects.none()
```

### Step 3: Add pre-execution summary

Create a new helper method and integrate into `handle()`.

**File to modify**: `scanner/management/commands/calculate_intrinsic_value.py`

**New helper method**:

```python
def _get_calculation_stats(self):
    """
    Get statistics about calculation status across all active stocks.
    
    Returns:
        Dictionary with calculation statistics
    """
    total = CuratedStock.objects.filter(active=True).count()
    never_calculated = CuratedStock.objects.filter(
        active=True,
        last_calculation_date__isnull=True
    ).count()
    previously_calculated = total - never_calculated
    
    # Get oldest calculation date
    oldest = CuratedStock.objects.filter(
        active=True,
        last_calculation_date__isnull=False
    ).order_by('last_calculation_date').first()
    
    oldest_date = oldest.last_calculation_date if oldest else None
    oldest_symbol = oldest.symbol if oldest else None
    
    return {
        'total': total,
        'never_calculated': never_calculated,
        'previously_calculated': previously_calculated,
        'oldest_date': oldest_date,
        'oldest_symbol': oldest_symbol,
    }

def _print_pre_execution_summary(self, stocks, force_all=False, limit=7):
    """
    Print detailed pre-execution summary.
    
    Args:
        stocks: List/QuerySet of stocks to process
        force_all: Whether --force-all was used
        limit: The limit value used
    """
    stats = self._get_calculation_stats()
    stocks_to_process = len(stocks)
    estimated_calls = stocks_to_process * 3
    
    self.stdout.write("=" * 65)
    self.stdout.write(self.style.SUCCESS("CALCULATION STATISTICS:"))
    self.stdout.write(f"  Total active curated stocks: {stats['total']}")
    self.stdout.write(f"  Never calculated: {stats['never_calculated']}")
    self.stdout.write(f"  Previously calculated: {stats['previously_calculated']}")
    
    if stats['oldest_date']:
        self.stdout.write(
            f"  Oldest calculation: {stats['oldest_date'].strftime('%Y-%m-%d')} "
            f"({stats['oldest_symbol']})"
        )
    
    self.stdout.write("")
    self.stdout.write(self.style.SUCCESS("EXECUTION PLAN:"))
    self.stdout.write(f"  Stocks to process this run: {stocks_to_process}")
    self.stdout.write(f"  Estimated API calls: {estimated_calls}", ending="")
    
    if estimated_calls <= 25:
        self.stdout.write(self.style.SUCCESS(" (under 25/day limit ✓)"))
    else:
        self.stdout.write(self.style.WARNING(f" (EXCEEDS 25/day limit ⚠)"))
    
    # List selected stocks
    if stocks_to_process > 0 and stocks_to_process <= 20:
        self.stdout.write("")
        self.stdout.write("  Selected stocks (in processing order):")
        for i, stock in enumerate(stocks, start=1):
            if stock.last_calculation_date:
                date_str = stock.last_calculation_date.strftime('%Y-%m-%d')
                self.stdout.write(f"    {i}. {stock.symbol} (last calculated: {date_str})")
            else:
                self.stdout.write(f"    {i}. {stock.symbol} (never calculated)")
    
    self.stdout.write("=" * 65)
    self.stdout.write("")
```

**Update handle() method**:

```python
def handle(self, *args, **options):
    """Main command execution."""
    # ... existing logging ...
    
    # Clear cache if requested
    if options.get("clear_cache"):
        self._clear_alpha_vantage_cache()
    
    # Get stocks to process
    try:
        stocks = self._get_stocks_to_process(
            symbols=options.get("symbols"),
            limit=options.get("limit", 7),
            force_all=options.get("force_all", False)
        )
    except CommandError as e:
        self.stdout.write(self.style.ERROR(str(e)))
        return
    
    total_stocks = len(stocks)
    
    if total_stocks == 0:
        self.stdout.write(self.style.WARNING("No stocks to process"))
        return
    
    # Print pre-execution summary
    self._print_pre_execution_summary(
        stocks,
        force_all=options.get("force_all", False),
        limit=options.get("limit", 7)
    )
    
    # ... continue with existing processing logic ...
```

### Step 4: Test stock selection with various scenarios

Test the new selection logic with different data scenarios.

**Manual test cases**:

1. **All stocks never calculated**:
   - Set all `last_calculation_date` to NULL
   - Run command (should select first 7 alphabetically)

2. **Mix of calculated and never calculated**:
   - 5 stocks with NULL, 20 stocks with dates
   - Run command (should select 5 NULL + 2 oldest)

3. **All stocks previously calculated**:
   - All stocks have calculation dates
   - Run command (should select 7 oldest)

4. **Fewer than 7 stocks total**:
   - Only 3 active stocks
   - Run command (should process all 3)

5. **Force all with many stocks**:
   - 50 active stocks
   - Run with `--force-all` (should show warning, process all)

6. **Custom limit**:
   - Run with `--limit 3` (should process 3 stocks)

7. **Specific symbols**:
   - Run with `--symbols AAPL MSFT` (should ignore limit, process those 2)

**Test commands**:

```bash
# Test default (7 stocks)
just exec python manage.py calculate_intrinsic_value

# Test custom limit
just exec python manage.py calculate_intrinsic_value --limit 3

# Test force all
just exec python manage.py calculate_intrinsic_value --force-all

# Test specific symbols (existing functionality)
just exec python manage.py calculate_intrinsic_value --symbols AAPL MSFT

# Test with clear cache
just exec python manage.py calculate_intrinsic_value --limit 5 --clear-cache
```

## Acceptance Criteria

### Functional Requirements

- [x] `--limit N` flag sets custom stock limit
- [x] `--force-all` flag processes all active stocks
- [x] Smart selection prioritizes NULL last_calculation_date first
- [x] Smart selection then selects oldest calculated stocks
- [x] Specific `--symbols` takes precedence over limit/force-all
- [x] Pre-execution summary shows accurate statistics
- [x] Warning displayed when estimated API calls > 25
- [x] Default limit is 7 stocks (21 API calls)

### Selection Logic Requirements

- [x] Never-calculated stocks selected first
- [x] Previously-calculated stocks ordered by date (oldest first)
- [x] Combined selection respects the limit
- [x] Fewer stocks selected if total < limit
- [x] Empty list returned if no active stocks

### Output Requirements

- [x] Pre-execution summary shows total stocks, calculated/never counts
- [x] Summary shows oldest calculation date and symbol
- [x] Summary lists selected stocks with their calculation status
- [x] Summary shows estimated API calls with limit check
- [x] Force-all warning is clear and prominent

### Technical Requirements

- [x] No breaking changes to existing `--symbols` functionality
- [x] Efficient database queries (uses index on last_calculation_date)
- [x] QuerySet operations are optimized (no N+1 queries)
- [x] Command still works if no stocks in database

## Files Involved

### Modified Files

- `scanner/management/commands/calculate_intrinsic_value.py`
  - `add_arguments()` - Add --limit and --force-all flags
  - `_get_stocks_to_process()` - Complete rewrite with smart selection
  - `_get_calculation_stats()` - New helper method
  - `_print_pre_execution_summary()` - New helper method
  - `handle()` - Add pre-execution summary call

## Notes

### Selection Algorithm Details

**Why prioritize NULL dates**:
- These stocks have never been valued
- Most critical to get initial valuations
- Provides baseline data for decision-making

**Why then select oldest**:
- Keeps all stocks relatively up-to-date
- Rolling update strategy ensures freshness
- Prevents any stock from going too long without update

**Math examples**:

With 50 active stocks, limit=7:
- Day 1: 50 NULL → process 7 (43 NULL remain)
- Day 2: 43 NULL → process 7 (36 NULL remain)
- ...
- Day 8: 1 NULL, 43 calculated → process 1 NULL + 6 oldest (all initialized)
- Day 9+: 0 NULL, 50 calculated → process 7 oldest (rolling update)

**Full cycle time**: With 50 stocks and 7/day processing, full refresh every ~7 days

### API Rate Limiting Strategy

**Conservative approach**:
- Default limit: 7 stocks = 21 API calls
- Leaves 4-call buffer for margin of error
- Accounts for potential cache misses

**Caching reduces actual calls**:
- With 7-day cache TTL, many calls hit cache
- Real API calls often much lower than estimated
- Buffer ensures we stay under limit even without cache

**Force-all use cases**:
- Initial setup (first-time valuation of all stocks)
- After adding many new stocks
- When cache is cleared and fresh data needed
- Manual catch-up after extended downtime

### Command Examples

```bash
# Daily automated run (via cron)
0 20 * * * cd /path/to/project && python manage.py calculate_intrinsic_value

# Manual catch-up with larger batch
python manage.py calculate_intrinsic_value --limit 10

# Emergency full refresh (weekend/off-hours)
python manage.py calculate_intrinsic_value --force-all --force-refresh

# Test specific problem stocks
python manage.py calculate_intrinsic_value --symbols AAPL MSFT GOOGL

# Clear cache and update 5 stocks
python manage.py calculate_intrinsic_value --limit 5 --clear-cache
```

### Cron Schedule Recommendation

**Old schedule** (Phase 4):
```cron
# Weekly on Monday 8 PM
0 20 * * 1 cd /path/to/project && python manage.py calculate_intrinsic_value
```

**New schedule** (Phase 4.1):
```cron
# Daily at 8 PM Eastern
0 20 * * * cd /path/to/project && python manage.py calculate_intrinsic_value
```

**Rationale**:
- Daily execution with 7-stock limit respects API quotas
- All stocks refreshed within ~7 days
- More frequent updates than weekly batch
- Better data freshness for trading decisions

## Dependencies

- Requires Task 021 (database index) for optimal query performance
- Depends on existing `calculate_intrinsic_value` command infrastructure
- Required before Task 023 (API call tracking and enhanced reporting)

## Reference

**Django QuerySet Documentation**:
- Filtering: https://docs.djangoproject.com/en/5.1/topics/db/queries/#retrieving-specific-objects-with-filters
- Ordering: https://docs.djangoproject.com/en/5.1/ref/models/querysets/#order-by
- QuerySet union: https://docs.djangoproject.com/en/5.1/ref/models/querysets/#union

**Python itertools**:
- Chain: https://docs.python.org/3/library/itertools.html#itertools.chain
