# Task 019: Update Management Command for FCF Calculations

## Progress Summary

**Status**: ✅ Completed

- [x] Step 1: Add CASH_FLOW API integration
- [x] Step 2: Implement FCF stock processing method
- [x] Step 3: Update command to process both EPS and FCF
- [x] Step 4: Update command output and logging

### Summary of Changes

- Updated rate limiting to 15 seconds (4 calls/minute) for dual API calls
- Added `_fetch_cash_flow_data()` method to fetch and cache CASH_FLOW data
- Added `_process_stock_fcf()` method to calculate FCF-based intrinsic value
- Updated `handle()` method to track separate EPS and FCF statistics
- Modified processing loop to calculate both EPS and FCF per stock:
  - EPS processing first (fetches OVERVIEW with EPS + shares outstanding)
  - FCF processing second (uses cached OVERVIEW + fetches CASH_FLOW)
  - Independent success/failure tracking for each method
- Updated summary output to show both EPS and FCF statistics
- Updated `_clear_alpha_vantage_cache()` to clear both OVERVIEW and CASH_FLOW caches
- Added warning display for negative FCF (logged but FCF intrinsic value skipped)
- All Django system checks pass
- Code passes linter checks

## Overview

This task updates the `calculate_intrinsic_value` management command to support both EPS-based and FCF-based DCF calculations. The command will:

1. Fetch both OVERVIEW (for EPS and shares outstanding) and CASH_FLOW (for quarterly data) from Alpha Vantage
2. Calculate both EPS and FCF intrinsic values independently
3. Handle failures gracefully - each method succeeds or fails independently
4. Update rate limiting to 15 seconds (safer with 2 API calls per stock)
5. Display separate success/failure statistics for each method

## Implementation Steps

### Step 1: Add CASH_FLOW API integration

Add function to fetch cash flow data from Alpha Vantage:

**Files to modify:**
- `scanner/management/commands/calculate_intrinsic_value.py`

**New constant:**
```python
# Update rate limiting for dual API calls
ALPHA_VANTAGE_CALLS_PER_MINUTE = 4  # Conservative: 2 calls per stock
RATE_LIMIT_DELAY = 60 / ALPHA_VANTAGE_CALLS_PER_MINUTE  # 15 seconds
```

**New method to add to Command class:**
```python
def _fetch_cash_flow_data(self, symbol, force_refresh=False):
    """
    Fetch cash flow data from Alpha Vantage with Redis caching.
    
    Cache TTL: 7 days (same as OVERVIEW)
    Cache key format: av_cashflow_{symbol}
    
    Args:
        symbol: Stock ticker symbol
        force_refresh: Bypass cache and fetch fresh data
    
    Returns:
        Dictionary with cash flow data from Alpha Vantage
    """
    cache_key = f"av_cashflow_{symbol}"
    
    # Try to get from cache (unless force refresh)
    if not force_refresh:
        cached_data = cache.get(cache_key)
        if cached_data:
            self.stdout.write(
                self.style.SUCCESS("  Using cached cash flow data")
            )
            logger.debug(f"Cash flow cache hit for {symbol}")
            return cached_data
    
    # Fetch from API
    self.stdout.write("  Fetching cash flow from Alpha Vantage API...")
    logger.debug(f"Cash flow cache miss for {symbol}, fetching from API")
    
    url = f"function=CASH_FLOW&symbol={symbol}"
    cash_flow_data = get_market_data(url)
    
    # Cache the response
    if cash_flow_data:
        cache.set(cache_key, cash_flow_data, CACHE_TTL)
        logger.debug(f"Cached cash flow data for {symbol} (TTL: {CACHE_TTL}s)")
    
    return cash_flow_data
```

### Step 2: Implement FCF stock processing method

Add new method to process FCF calculations for a stock:

**New method to add to Command class:**
```python
def _process_stock_fcf(self, stock, overview_data, force_refresh=False):
    """
    Process FCF-based intrinsic value calculation for a single stock.
    
    Args:
        stock: CuratedStock instance
        overview_data: Already fetched OVERVIEW data (contains shares outstanding)
        force_refresh: Force refresh of cached API data
    
    Returns:
        Dictionary with status and result details
    """
    from scanner.valuation import (
        calculate_fcf_from_quarters,
        calculate_fcf_per_share,
        calculate_intrinsic_value_fcf,
    )
    
    # Validate FCF assumptions
    if stock.fcf_growth_rate is None or stock.fcf_growth_rate <= 0:
        return {
            "status": "skipped",
            "reason": "Invalid FCF growth rate"
        }
    
    if stock.fcf_multiple is None or stock.fcf_multiple <= 0:
        return {
            "status": "skipped",
            "reason": "Invalid FCF multiple"
        }
    
    # Fetch cash flow data
    try:
        cash_flow_data = self._fetch_cash_flow_data(
            stock.symbol,
            force_refresh=force_refresh
        )
        
        if not cash_flow_data:
            return {
                "status": "skipped",
                "reason": "Cash flow data not available from API"
            }
        
        # Check for API error messages
        if "Error Message" in cash_flow_data:
            return {
                "status": "skipped",
                "reason": f"API error: {cash_flow_data['Error Message']}"
            }
        
        if "Note" in cash_flow_data:
            return {
                "status": "skipped",
                "reason": f"API rate limit: {cash_flow_data['Note']}"
            }
        
        # Calculate TTM FCF
        ttm_fcf = calculate_fcf_from_quarters(cash_flow_data)
        
        # Get shares outstanding from overview data
        if "SharesOutstanding" not in overview_data:
            return {
                "status": "skipped",
                "reason": "Shares outstanding not available"
            }
        
        shares_outstanding = Decimal(overview_data["SharesOutstanding"])
        
        # Calculate FCF per share
        fcf_per_share = calculate_fcf_per_share(ttm_fcf, shares_outstanding)
        
        # Warn if FCF is negative but continue calculation
        if fcf_per_share < 0:
            logger.warning(
                f"{stock.symbol} has negative FCF/share: {fcf_per_share}"
            )
            self.stdout.write(
                self.style.WARNING(
                    f"  ⚠ Negative FCF/share: ${fcf_per_share}"
                )
            )
        
        # Update current FCF in database
        stock.current_fcf_per_share = fcf_per_share
        
    except ValueError as e:
        logger.warning(f"Invalid FCF data for {stock.symbol}: {e}")
        return {
            "status": "skipped",
            "reason": f"Invalid data: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Error fetching FCF data for {stock.symbol}: {e}")
        return {
            "status": "error",
            "reason": f"API error: {str(e)}"
        }
    
    # Calculate intrinsic value using FCF DCF model
    try:
        # Skip if FCF per share is negative or zero
        if fcf_per_share <= 0:
            return {
                "status": "skipped",
                "reason": f"Non-positive FCF/share: {fcf_per_share}"
            }
        
        fcf_result = calculate_intrinsic_value_fcf(
            current_fcf_per_share=fcf_per_share,
            fcf_growth_rate=stock.fcf_growth_rate,
            fcf_multiple=stock.fcf_multiple,
            desired_return=stock.desired_return,
            projection_years=stock.projection_years,
        )
        
        intrinsic_value_fcf = fcf_result["intrinsic_value"]
        
    except Exception as e:
        logger.error(
            f"Error calculating FCF intrinsic value for {stock.symbol}: {e}"
        )
        return {
            "status": "error",
            "reason": f"Calculation error: {str(e)}"
        }
    
    # Save results to database
    stock.intrinsic_value_fcf = intrinsic_value_fcf
    stock.save()
    
    logger.info(
        f"Updated {stock.symbol} FCF: FCF/share=${fcf_per_share}, "
        f"Intrinsic Value=${intrinsic_value_fcf}"
    )
    
    return {
        "status": "success",
        "intrinsic_value_fcf": intrinsic_value_fcf,
        "fcf_per_share": fcf_per_share,
        "fcf_details": fcf_result,
    }
```

### Step 3: Update command to process both EPS and FCF

Modify the main `handle()` method to track both EPS and FCF statistics:

**Updates to handle() method:**
```python
def handle(self, *args, **options):
    """Main command execution."""
    # ... existing setup code ...
    
    # Process each stock - track separate statistics
    eps_success = 0
    eps_skipped = 0
    eps_error = 0
    fcf_success = 0
    fcf_skipped = 0
    fcf_error = 0
    
    for index, stock in enumerate(stocks, start=1):
        self.stdout.write(f"\n[{index}/{total_stocks}] Processing {stock.symbol}...")
        
        # Process EPS (existing logic)
        try:
            eps_result = self._process_stock(
                stock,
                force_refresh=options.get("force_refresh", False)
            )
            
            if eps_result["status"] == "success":
                eps_success += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  ✓ EPS intrinsic value: ${eps_result['intrinsic_value']}"
                    )
                )
            elif eps_result["status"] == "skipped":
                eps_skipped += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"  ⊘ EPS skipped: {eps_result['reason']}"
                    )
                )
        except Exception as e:
            eps_error += 1
            logger.error(f"EPS processing error for {stock.symbol}: {e}", exc_info=True)
            self.stdout.write(
                self.style.ERROR(f"  ✗ EPS error: {str(e)}")
            )
        
        # Process FCF (new logic)
        # Only process FCF if we have overview_data from EPS processing
        if eps_result.get("status") == "success":
            # Get overview_data from the previous EPS call (need to store it)
            # For now, we'll fetch it again if needed or pass it through
            try:
                # Fetch overview again or reuse from _process_stock
                overview_data = self._fetch_eps_data(
                    stock.symbol,
                    force_refresh=False  # Use cache if available
                )
                
                fcf_result = self._process_stock_fcf(
                    stock,
                    overview_data,
                    force_refresh=options.get("force_refresh", False)
                )
                
                if fcf_result["status"] == "success":
                    fcf_success += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  ✓ FCF intrinsic value: ${fcf_result['intrinsic_value_fcf']}"
                        )
                    )
                elif fcf_result["status"] == "skipped":
                    fcf_skipped += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ⊘ FCF skipped: {fcf_result['reason']}"
                        )
                    )
            except Exception as e:
                fcf_error += 1
                logger.error(f"FCF processing error for {stock.symbol}: {e}", exc_info=True)
                self.stdout.write(
                    self.style.ERROR(f"  ✗ FCF error: {str(e)}")
                )
        else:
            # Skip FCF if EPS failed
            fcf_skipped += 1
            self.stdout.write(
                self.style.WARNING("  ⊘ FCF skipped: EPS processing failed")
            )
        
        # Rate limiting between stocks
        if index < total_stocks:
            self._rate_limit_delay()
    
    # Update summary to show both EPS and FCF statistics
    # ... (see Step 4) ...
```

### Step 4: Update command output and logging

Update the summary display to show statistics for both methods:

**Updated summary output:**
```python
# Summary
end_time = timezone.now()
duration = (end_time - start_time).total_seconds()

self.stdout.write(self.style.SUCCESS(f"\n{'=' * 60}"))
self.stdout.write(self.style.SUCCESS("SUMMARY:"))
self.stdout.write(self.style.SUCCESS(f"  Total processed: {total_stocks}"))
self.stdout.write(self.style.SUCCESS(f"\n  EPS Method:"))
self.stdout.write(self.style.SUCCESS(f"    Successful: {eps_success}"))
self.stdout.write(self.style.WARNING(f"    Skipped: {eps_skipped}"))
self.stdout.write(self.style.ERROR(f"    Errors: {eps_error}"))
self.stdout.write(self.style.SUCCESS(f"\n  FCF Method:"))
self.stdout.write(self.style.SUCCESS(f"    Successful: {fcf_success}"))
self.stdout.write(self.style.WARNING(f"    Skipped: {fcf_skipped}"))
self.stdout.write(self.style.ERROR(f"    Errors: {fcf_error}"))
self.stdout.write(self.style.SUCCESS(f"\n  Duration: {duration:.2f} seconds"))
self.stdout.write(self.style.SUCCESS(f"{'=' * 60}\n"))

# Log command completion
logger.info("=" * 60)
logger.info(f"Command completed in {duration:.2f} seconds")
logger.info(
    f"EPS - Success: {eps_success}, Skipped: {eps_skipped}, Errors: {eps_error}"
)
logger.info(
    f"FCF - Success: {fcf_success}, Skipped: {fcf_skipped}, Errors: {fcf_error}"
)
logger.info("=" * 60)
```

**Update cache clearing to include FCF:**
```python
def _clear_alpha_vantage_cache(self):
    """Clear all cached Alpha Vantage data (OVERVIEW and CASH_FLOW)."""
    symbols = CuratedStock.objects.values_list("symbol", flat=True)
    
    cleared = 0
    for symbol in symbols:
        # Clear OVERVIEW cache
        if cache.delete(f"av_overview_{symbol}"):
            cleared += 1
        # Clear CASH_FLOW cache
        if cache.delete(f"av_cashflow_{symbol}"):
            cleared += 1
    
    self.stdout.write(self.style.SUCCESS(f"Cleared {cleared} cached entries"))
    logger.info(f"Cleared {cleared} Alpha Vantage cache entries")
```

## Acceptance Criteria

### Command Functionality:
- [ ] Command processes both EPS and FCF for each stock
- [ ] Each method succeeds or fails independently
- [ ] CASH_FLOW API data is fetched and cached
- [ ] Rate limiting updated to 15 seconds between stocks
- [ ] Command options work for both methods (--symbols, --force-refresh, --clear-cache)

### Data Management:
- [ ] Saves both `intrinsic_value` (EPS) and `intrinsic_value_fcf` (FCF)
- [ ] Updates `current_fcf_per_share` from calculations
- [ ] Single `last_calculation_date` updated when either method runs
- [ ] Negative FCF is calculated but logged as warning

### Error Handling:
- [ ] Missing cash flow data skips FCF calculation
- [ ] Insufficient quarters (< 4) skips FCF calculation
- [ ] API errors logged and don't crash command
- [ ] EPS failure doesn't prevent FCF calculation attempt
- [ ] FCF failure doesn't affect EPS results

### Output:
- [ ] Summary shows separate statistics for EPS and FCF methods
- [ ] Format matches: "EPS - Successful: X, Skipped: Y, Errors: Z"
- [ ] Both intrinsic values displayed per stock (if calculated)
- [ ] Clear indication of which method succeeded/failed

### Performance:
- [ ] Cache works for both OVERVIEW and CASH_FLOW data
- [ ] 15-second rate limiting between stocks
- [ ] Reasonable execution time (~6-7 minutes for 26 stocks with delays)

## Files Involved

### Modified Files:
- `scanner/management/commands/calculate_intrinsic_value.py` - Add FCF support

### Files to Reference:
- `scanner/valuation.py` - FCF calculation functions (from Task 018)
- `scanner/models.py` - FCF fields (from Task 017)

## Notes

### Dual API Calls:

For each stock, the command now makes:
1. **OVERVIEW call** - Get EPS and shares outstanding (for both methods)
2. **CASH_FLOW call** - Get quarterly cash flow data (for FCF only)

**Rate limiting**: Increased to 15 seconds to be conservative with 2 API calls per stock.

### Processing Flow:

```
For each stock:
1. Process EPS:
   - Fetch OVERVIEW (EPS, shares outstanding)
   - Calculate EPS-based intrinsic value
   - Save intrinsic_value, current_eps
   
2. Process FCF:
   - Reuse OVERVIEW data (shares outstanding)
   - Fetch CASH_FLOW (quarterly data)
   - Calculate TTM FCF and FCF/share
   - Calculate FCF-based intrinsic value
   - Save intrinsic_value_fcf, current_fcf_per_share
   
3. Update last_calculation_date (once for both)
4. Rate limit delay (15 seconds)
```

### Independent Failures:

- If EPS fails, FCF still attempts (needs to fetch OVERVIEW separately)
- If FCF fails, EPS results are preserved
- Stocks can have only EPS value, only FCF value, both, or neither

### Example Output:

```
Starting intrinsic value calculation...
Processing 26 stock(s)...

[1/26] Processing AAPL...
  Fetching from Alpha Vantage API...
  ✓ EPS intrinsic value: $150.25
  Using cached data
  Fetching cash flow from Alpha Vantage API...
  ✓ FCF intrinsic value: $145.80
  Rate limiting: waiting 15 seconds...

[2/26] Processing TSLA...
  Using cached data
  ✓ EPS intrinsic value: $215.50
  Using cached cash flow data
  ⚠ Negative FCF/share: $-2.50
  ⊘ FCF skipped: Non-positive FCF/share: -2.50
  Rate limiting: waiting 15 seconds...

============================================================
SUMMARY:
  Total processed: 26
  
  EPS Method:
    Successful: 24
    Skipped: 1
    Errors: 1
  
  FCF Method:
    Successful: 20
    Skipped: 4
    Errors: 2
  
  Duration: 435.5 seconds
============================================================
```

## Testing Checklist

### Command Execution:
- [ ] Run command processes both methods
- [ ] --symbols option works
- [ ] --force-refresh bypasses both caches
- [ ] --clear-cache clears both OVERVIEW and CASH_FLOW

### Data Verification:
- [ ] Both intrinsic values saved to database
- [ ] current_fcf_per_share populated
- [ ] last_calculation_date updated
- [ ] Negative FCF logged but calculated

### Cache Testing:
- [ ] CASH_FLOW data cached with 7-day TTL
- [ ] Cache keys: av_cashflow_SYMBOL
- [ ] Force refresh fetches fresh cash flow data
- [ ] Cache clear removes both caches

### Error Scenarios:
- [ ] Missing cash flow data skips FCF gracefully
- [ ] Insufficient quarters handled
- [ ] EPS success + FCF failure = partial results saved
- [ ] Both failures = no values saved

### Performance:
- [ ] 15-second delays observed
- [ ] Command completes in reasonable time
- [ ] Cached runs faster than fresh fetches

## Reference

**Alpha Vantage API:**
- CASH_FLOW endpoint: https://www.alphavantage.co/documentation/#cash-flow
- Rate limits: https://www.alphavantage.co/support/#support

**Django Cache Framework:**
- Cache API: https://docs.djangoproject.com/en/5.1/topics/cache/
