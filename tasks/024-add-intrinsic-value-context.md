# Task 024: Add Intrinsic Value Context to Scanner View

## Progress Summary

**Status**: Not Started

- [ ] Step 1: Add helper method to CuratedStock model
- [ ] Step 2: Update scan_view to include intrinsic value context
- [ ] Step 3: Update scan_status polling view with intrinsic value context
- [ ] Step 4: Test context data flow with various stock states

## Overview

Modify the scanner view to include intrinsic value data for each stock when rendering options results. This provides the foundation for displaying visual indicators comparing option strike prices to intrinsic values.

The implementation adds:
- Helper method on `CuratedStock` model to get the effective intrinsic value based on preferred valuation method
- Dictionary mapping ticker symbols to `CuratedStock` instances in template context
- Same intrinsic value context in both initial scan view and polling status endpoint

## Current State Analysis

### Current Scanner View Behavior

The `scan_view` in `scanner/views.py` currently:
- Executes the scan in a background thread
- Stores results in Redis with key `options_scan_results`
- Returns polling template that fetches results every 15 seconds
- Results structure: `{symbol: [option_dict, ...]}`

### Current Template Context

The `scan_status` polling view provides:
```python
context = {
    'options': results,  # Dict of {symbol: [options]}
    'scan_complete': complete,
    'scan_error': error_msg,
}
```

**Missing**: No `CuratedStock` model data in context

### Current Models

`CuratedStock` has intrinsic value fields:
- `intrinsic_value` (EPS-based DCF result)
- `intrinsic_value_fcf` (FCF-based DCF result)
- `preferred_valuation_method` (choices: 'eps' or 'fcf')
- `last_calculation_date` (when last calculated)

**Missing**: No method to get the "effective" intrinsic value based on preference

## Target State

### New Helper Method

Add to `scanner/models.py`:
```python
def get_effective_intrinsic_value(self):
    """
    Get the intrinsic value based on the preferred valuation method.
    
    Returns:
        Decimal or None: The intrinsic value for the preferred method,
                         or None if not calculated.
    """
    if self.preferred_valuation_method == 'fcf':
        return self.intrinsic_value_fcf
    else:
        return self.intrinsic_value
```

### Enhanced Template Context

Both `scan_view` and `scan_status` will provide:
```python
context = {
    'options': results,  # {symbol: [options]}
    'curated_stocks': curated_stocks_dict,  # {symbol: CuratedStock instance}
    'scan_complete': complete,
    'scan_error': error_msg,
}
```

### Context Building Logic

```python
# In scan_view and scan_status
results = cache.get('options_scan_results') or {}

# Get all symbols from results
symbols = list(results.keys())

# Fetch CuratedStock instances for these symbols
curated_stocks = CuratedStock.objects.filter(
    symbol__in=symbols,
    is_active=True
)

# Create dictionary for template access
curated_stocks_dict = {stock.symbol: stock for stock in curated_stocks}

context = {
    'options': results,
    'curated_stocks': curated_stocks_dict,
    # ... other context
}
```

## Implementation Steps

### Step 1: Add helper method to CuratedStock model

Add the `get_effective_intrinsic_value()` method to the `CuratedStock` model.

**File to modify**: `scanner/models.py`

**Add method to CuratedStock class**:

```python
def get_effective_intrinsic_value(self):
    """
    Get the intrinsic value based on the preferred valuation method.
    
    Returns:
        Decimal or None: The intrinsic value for the preferred method,
                         or None if not calculated.
    
    Example:
        >>> stock = CuratedStock.objects.get(symbol='AAPL')
        >>> stock.preferred_valuation_method = 'eps'
        >>> stock.get_effective_intrinsic_value()
        Decimal('150.25')
    """
    if self.preferred_valuation_method == 'fcf':
        return self.intrinsic_value_fcf
    else:  # Default to EPS
        return self.intrinsic_value
```

**Location**: Add after the `__str__` method, before the `Meta` class.

### Step 2: Update scan_view to include intrinsic value context

Modify the `scan_view` to fetch `CuratedStock` instances and add to context.

**File to modify**: `scanner/views.py`

**Changes to `scan_view` function** (after scan completes, before rendering):

Find the section that prepares the initial response:
```python
# Return polling template
return render(
    request,
    "scanner/partials/scan_polling.html",
    context,
)
```

**Add before the render call**:
```python
# Prepare context for initial polling template
# Get any existing results to show stock info
results = cache.get("options_scan_results") or {}

# Fetch CuratedStock instances for all symbols in results
if results:
    symbols = list(results.keys())
    curated_stocks = CuratedStock.objects.filter(
        symbol__in=symbols, is_active=True
    )
    curated_stocks_dict = {stock.symbol: stock for stock in curated_stocks}
else:
    curated_stocks_dict = {}

context = {
    "scan_in_progress": True,
    "curated_stocks": curated_stocks_dict,
}

# Return polling template
return render(
    request,
    "scanner/partials/scan_polling.html",
    context,
)
```

### Step 3: Update scan_status polling view with intrinsic value context

Modify the `scan_status` view to include the same intrinsic value context.

**File to modify**: `scanner/views.py`

**Changes to `scan_status` function** (update the context preparation):

Find the existing context building:
```python
context = {
    "options": results,
    "scan_complete": complete,
    "scan_error": error_msg,
}
```

**Replace with**:
```python
# Fetch CuratedStock instances for all symbols in results
if results:
    symbols = list(results.keys())
    curated_stocks = CuratedStock.objects.filter(
        symbol__in=symbols, is_active=True
    )
    curated_stocks_dict = {stock.symbol: stock for stock in curated_stocks}
else:
    curated_stocks_dict = {}

context = {
    "options": results,
    "curated_stocks": curated_stocks_dict,
    "scan_complete": complete,
    "scan_error": error_msg,
}
```

### Step 4: Test context data flow with various stock states

Test that the context includes correct intrinsic value data in different scenarios.

**Test scenarios**:

1. **Stocks with EPS intrinsic values**:
   - Set `preferred_valuation_method='eps'`
   - Set `intrinsic_value` to non-NULL
   - Run scan
   - Verify: `curated_stocks_dict[symbol].get_effective_intrinsic_value()` returns EPS value

2. **Stocks with FCF intrinsic values**:
   - Set `preferred_valuation_method='fcf'`
   - Set `intrinsic_value_fcf` to non-NULL
   - Run scan
   - Verify: `curated_stocks_dict[symbol].get_effective_intrinsic_value()` returns FCF value

3. **Stocks with NULL intrinsic values**:
   - Set both `intrinsic_value` and `intrinsic_value_fcf` to NULL
   - Run scan
   - Verify: `curated_stocks_dict[symbol].get_effective_intrinsic_value()` returns None

4. **Mixed scenario**:
   - Have multiple stocks with different valuation states
   - Run scan
   - Verify: Context includes all stocks, each with correct intrinsic value

**Test with Django shell**:

```bash
just exec python manage.py shell
```

```python
from scanner.models import CuratedStock

# Test the helper method
stock = CuratedStock.objects.filter(is_active=True).first()

print(f"Symbol: {stock.symbol}")
print(f"Preferred method: {stock.preferred_valuation_method}")
print(f"EPS IV: {stock.intrinsic_value}")
print(f"FCF IV: {stock.intrinsic_value_fcf}")
print(f"Effective IV: {stock.get_effective_intrinsic_value()}")

# Change preference and test again
stock.preferred_valuation_method = 'fcf'
print(f"\nAfter changing to FCF:")
print(f"Effective IV: {stock.get_effective_intrinsic_value()}")
```

**Manual testing via UI**:

1. Navigate to scanner page
2. Click "Scan for Options"
3. Use browser dev tools to inspect the polling responses
4. Verify context includes `curated_stocks` dictionary
5. Check that intrinsic values are present in context

**Debugging tips**:
- Add `print()` statements in views to inspect `curated_stocks_dict`
- Use Django Debug Toolbar to see template context variables
- Check browser Network tab for HTMX polling requests

## Acceptance Criteria

### Model Method Requirements

- [ ] `get_effective_intrinsic_value()` method added to CuratedStock
- [ ] Method returns `intrinsic_value_fcf` when preferred method is 'fcf'
- [ ] Method returns `intrinsic_value` when preferred method is 'eps'
- [ ] Method returns `None` when intrinsic value not calculated
- [ ] Method has proper docstring with example

### View Context Requirements

- [ ] `scan_view` includes `curated_stocks` dictionary in context
- [ ] `scan_status` includes `curated_stocks` dictionary in context
- [ ] Dictionary keys are stock symbols (strings)
- [ ] Dictionary values are `CuratedStock` model instances
- [ ] Only active curated stocks are included
- [ ] Empty dict when no results yet

### Data Integrity Requirements

- [ ] No duplicate database queries (use single `filter()` call)
- [ ] No N+1 query problems
- [ ] Context includes stocks only for symbols in scan results
- [ ] Missing stocks handled gracefully (not in curated list)

### Testing Requirements

- [ ] Helper method tested with EPS preference
- [ ] Helper method tested with FCF preference
- [ ] Helper method tested with NULL values
- [ ] Context verified in both scan_view and scan_status
- [ ] Mixed scenario tested (multiple stocks with different states)

## Files Involved

### Modified Files

- `scanner/models.py`
  - Add `get_effective_intrinsic_value()` method to `CuratedStock` class
  
- `scanner/views.py`
  - Update `scan_view` to fetch curated stocks and add to context
  - Update `scan_status` to fetch curated stocks and add to context

### Template Files (Not Modified Yet)

- `templates/scanner/partials/scan_polling.html` - Will use context in Task 025
- `templates/scanner/partials/options_results.html` - Will use context in Task 025

## Notes

### Performance Considerations

**Single query per request**:
- Using `filter(symbol__in=symbols)` fetches all stocks in one query
- Dictionary comprehension is O(n) for building lookup dict
- Template lookups are O(1) with dictionary

**Typical performance**:
- Scan finds 5-10 stocks with matching options
- Single DB query fetches 5-10 CuratedStock instances
- Negligible overhead (<10ms)

### Edge Cases

**Stock not in curated list**:
- If scanner finds options for a non-curated stock (shouldn't happen)
- `curated_stocks_dict.get(symbol)` returns `None` in template
- Template should handle gracefully

**NULL intrinsic values**:
- Common for newly added stocks
- `get_effective_intrinsic_value()` returns `None`
- Next task will display warning indicator

**Both intrinsic values NULL**:
- Stock never calculated
- Method still returns `None` (correct behavior)
- Warning indicator should be shown

### Debugging

**Check context in template**:
```django
{# Temporary debug output in template #}
<pre>
Curated stocks: {{ curated_stocks|length }}
{% for symbol, stock in curated_stocks.items %}
  {{ symbol }}: IV={{ stock.get_effective_intrinsic_value }}
{% endfor %}
</pre>
```

**Check context in view**:
```python
# Add temporary debugging
logger.info(f"Curated stocks in context: {curated_stocks_dict.keys()}")
for symbol, stock in curated_stocks_dict.items():
    logger.info(f"  {symbol}: IV={stock.get_effective_intrinsic_value()}")
```

## Dependencies

- Requires Phase 4 completion (intrinsic value fields exist)
- Uses `CuratedStock` model from Task 001
- Builds on scanner views from Phase 2 and Phase 3

## Reference

**Django QuerySet API**:
- `filter()`: https://docs.djangoproject.com/en/5.1/ref/models/querysets/#filter
- `in` lookup: https://docs.djangoproject.com/en/5.1/ref/models/querysets/#in

**Python Dictionary Comprehension**:
- https://docs.python.org/3/tutorial/datastructures.html#dictionaries

**Django Template Context**:
- https://docs.djangoproject.com/en/5.1/ref/templates/api/#django.template.Context
