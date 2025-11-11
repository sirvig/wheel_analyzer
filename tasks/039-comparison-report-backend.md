# Task 039: Comparison Report Backend View

## Progress Summary

**Status**: Not Started

- [ ] Step 1: Add helper functions for date calculations
- [ ] Step 2: Implement valuation_comparison_view
- [ ] Step 3: Add URL routing for comparison report
- [ ] Step 4: Write view integration tests
- [ ] Step 5: Test delta calculations
- [ ] Step 6: Verify performance with many stocks

## Overview

Create a backend view that generates a comparison report showing current intrinsic valuations compared to previous quarter and year-ago snapshots. The view will calculate deltas (absolute and percentage changes) for each stock, enabling users to see how their valuations have evolved over time.

**Current State**:
- Historical snapshots exist in ValuationHistory
- No mechanism to compare current vs. historical
- Users cannot see valuation changes

**Target State**:
- View at `/scanner/valuations/comparison/`
- Compares current values to previous quarter and year-ago
- Calculates absolute deltas ($ difference)
- Calculates percentage changes (% increase/decrease)
- Handles missing snapshots gracefully (shows "-")
- Login required

## High-Level Specifications

### View Features

- **URL**: `/scanner/valuations/comparison/`
- **Method**: GET
- **Authentication**: `@login_required`
- **Query strategy**: Efficient with targeted date lookups
- **Context data**:
  - `stocks`: List of dicts with comparison data per stock
  - `comparison_date_quarter`: Previous quarter snapshot date
  - `comparison_date_year`: Year-ago snapshot date

### Comparison Logic

1. Determine comparison dates (previous quarter, year ago)
2. Query all active CuratedStock instances
3. For each stock:
   - Get current intrinsic value (via `get_effective_intrinsic_value()`)
   - Look up previous quarter snapshot
   - Look up year-ago snapshot
   - Calculate deltas and percentages
   - Build comparison dict
4. Return context with comparison data

### Date Calculation

**Previous Quarter**:
- Current Q1 (Jan-Mar) → Previous Q4 (Oct 1)
- Current Q2 (Apr-Jun) → Previous Q1 (Jan 1)
- Current Q3 (Jul-Sep) → Previous Q2 (Apr 1)
- Current Q4 (Oct-Dec) → Previous Q3 (Jul 1)

**Year Ago**:
- Same quarter, previous year
- Current Q1 2025 → Q1 2024 (Jan 1, 2024)
- Current Q3 2024 → Q3 2023 (Jul 1, 2023)

## Relevant Files

### Files to Create
- None (adding to existing files)

### Files to Modify
- `scanner/views.py` - Add `valuation_comparison_view` and helper functions
- `scanner/urls.py` - Add URL pattern for comparison report

### Files for Testing
- `scanner/tests/test_valuation_comparison_view.py` - New test file with 10 tests

## Acceptance Criteria

### View Implementation
- [ ] `valuation_comparison_view` function defined
- [ ] `@login_required` decorator applied
- [ ] Helper functions `_get_previous_quarter_date` and `_get_year_ago_quarter_date` defined
- [ ] Query logic retrieves active stocks
- [ ] Looks up snapshots for both comparison dates
- [ ] Calculates absolute deltas (current - historical)
- [ ] Calculates percentage changes ((delta / historical) * 100)
- [ ] Handles NULL values gracefully (returns None for delta/pct)
- [ ] Context includes all required data
- [ ] Logging at INFO level

### URL Configuration
- [ ] URL pattern added: `valuations/comparison/`
- [ ] URL name: `valuation_comparison`
- [ ] Follows scanner namespace

### Delta Calculation
- [ ] Absolute delta: `current_value - historical_value`
- [ ] Percentage change: `(delta / historical_value) * 100`
- [ ] NULL handling: Returns None if either value is NULL
- [ ] Zero handling: Avoids division by zero

### Testing Requirements
- [ ] Test: View returns 200 for authenticated user
- [ ] Test: View requires authentication
- [ ] Test: Context includes correct comparison dates
- [ ] Test: Context includes all active stocks
- [ ] Test: Delta calculations correct for positive changes
- [ ] Test: Delta calculations correct for negative changes
- [ ] Test: Handles NULL intrinsic values gracefully
- [ ] Test: Handles missing snapshots gracefully
- [ ] Test: Percentage calculation accurate
- [ ] Test: No N+1 query issues
- [ ] All 10 tests pass

### Performance Requirements
- [ ] Query completes in <300ms for 50 stocks
- [ ] No N+1 queries (verified with assertions)
- [ ] Uses targeted lookups (not full history)

## Implementation Steps

### Step 1: Add helper functions for date calculations

Add utility functions to calculate comparison dates.

**File to modify**: `scanner/views.py`

**Add these functions after import statements** (around line 20):

```python
def _get_previous_quarter_date(today):
    """
    Get the previous quarter snapshot date.

    Args:
        today: date object for current date

    Returns:
        date: The snapshot date for the previous quarter
    """
    year = today.year
    month = today.month

    if month < 4:
        return date(year - 1, 10, 1)
    elif month < 7:
        return date(year, 1, 1)
    elif month < 10:
        return date(year, 4, 1)
    else:
        return date(year, 7, 1)


def _get_year_ago_quarter_date(today):
    """
    Get the snapshot date from one year ago (same quarter).

    Args:
        today: date object for current date

    Returns:
        date: The snapshot date for the same quarter last year
    """
    year = today.year - 1
    month = today.month

    if month < 4:
        return date(year, 1, 1)
    elif month < 7:
        return date(year, 4, 1)
    elif month < 10:
        return date(year, 7, 1)
    else:
        return date(year, 10, 1)
```

**Test helper functions**:
```python
# In Django shell
from scanner.views import _get_previous_quarter_date, _get_year_ago_quarter_date
from datetime import date

# Test Q1 current
today = date(2025, 2, 15)
print(_get_previous_quarter_date(today))  # Should be 2024-10-01
print(_get_year_ago_quarter_date(today))   # Should be 2024-01-01

# Test Q3 current
today = date(2025, 8, 20)
print(_get_previous_quarter_date(today))  # Should be 2025-04-01
print(_get_year_ago_quarter_date(today))   # Should be 2024-07-01
```

### Step 2: Implement valuation_comparison_view

Add main view function for comparison report.

**File to modify**: `scanner/views.py`

**Add after `stock_history_view`**:

```python
@login_required
def valuation_comparison_view(request):
    """
    Display comparison report of current vs. historical valuations.

    Compares current intrinsic values to previous quarter and year-ago snapshots.

    Returns:
        Rendered scanner/valuation_comparison.html template

    Context:
        stocks: List of dictionaries with comparison data per stock
        comparison_date_quarter: Date of previous quarter snapshot
        comparison_date_year: Date of year-ago snapshot
    """
    # Determine comparison dates
    today = date.today()
    previous_quarter_date = _get_previous_quarter_date(today)
    year_ago_date = _get_year_ago_quarter_date(today)

    logger.info(f"Valuation comparison view accessed by {request.user.username}")
    logger.debug(f"Comparing to: {previous_quarter_date} (quarter), {year_ago_date} (year)")

    # Get all active stocks with current valuations
    stocks = CuratedStock.objects.filter(active=True).order_by('symbol')

    comparison_data = []
    for stock in stocks:
        # Get historical snapshots
        quarter_snapshot = ValuationHistory.objects.filter(
            stock=stock,
            snapshot_date=previous_quarter_date
        ).first()

        year_snapshot = ValuationHistory.objects.filter(
            stock=stock,
            snapshot_date=year_ago_date
        ).first()

        # Get current and historical values
        current_value = stock.get_effective_intrinsic_value()
        quarter_value = quarter_snapshot.get_effective_intrinsic_value() if quarter_snapshot else None
        year_value = year_snapshot.get_effective_intrinsic_value() if year_snapshot else None

        # Calculate deltas for quarter comparison
        quarter_delta = None
        quarter_pct = None
        if current_value is not None and quarter_value is not None:
            quarter_delta = current_value - quarter_value
            if quarter_value != 0:
                quarter_pct = (quarter_delta / quarter_value) * 100

        # Calculate deltas for year comparison
        year_delta = None
        year_pct = None
        if current_value is not None and year_value is not None:
            year_delta = current_value - year_value
            if year_value != 0:
                year_pct = (year_delta / year_value) * 100

        comparison_data.append({
            'stock': stock,
            'current_value': current_value,
            'quarter_value': quarter_value,
            'quarter_delta': quarter_delta,
            'quarter_pct': quarter_pct,
            'year_value': year_value,
            'year_delta': year_delta,
            'year_pct': year_pct,
        })

    logger.info(f"Comparing {len(comparison_data)} stocks")

    context = {
        'stocks': comparison_data,
        'comparison_date_quarter': previous_quarter_date,
        'comparison_date_year': year_ago_date,
    }

    return render(request, 'scanner/valuation_comparison.html', context)
```

**Add import** (if not present):
```python
from datetime import date
```

**Verify Python syntax**:
```bash
uv run python -m py_compile scanner/views.py
```

### Step 3: Add URL routing for comparison report

Add URL pattern to scanner URLconf.

**File to modify**: `scanner/urls.py`

**Add to urlpatterns** (after stock_history URL):

```python
urlpatterns = [
    # ... existing URLs ...

    # Historical valuation URLs
    path('valuations/history/<str:symbol>/', views.stock_history_view, name='stock_history'),
    path('valuations/comparison/', views.valuation_comparison_view, name='valuation_comparison'),
]
```

**Verify URL configuration**:
```bash
uv run python manage.py show_urls | grep comparison
```

**Expected**: `scanner:valuation_comparison` pattern visible

### Step 4: Write view integration tests

Create comprehensive tests for the view.

**File to create**: `scanner/tests/test_valuation_comparison_view.py`

**Content**:
```python
"""
Tests for valuation comparison view.

Test coverage:
- View returns 200 for authenticated user
- Authentication required
- Context includes comparison dates
- Context includes all active stocks
- Delta calculations correct
- Handles NULL values
- Handles missing snapshots
- Performance (no N+1 queries)
"""

import pytest
from datetime import date
from decimal import Decimal
from django.urls import reverse

from scanner.models import CuratedStock, ValuationHistory


@pytest.mark.django_db
class TestValuationComparisonView:
    """Tests for valuation_comparison_view."""

    def test_view_returns_200_for_authenticated_user(self, client, user):
        """Test view returns 200 status for authenticated user."""
        client.force_login(user)

        url = reverse('scanner:valuation_comparison')
        response = client.get(url)

        assert response.status_code == 200

    def test_view_requires_authentication(self, client):
        """Test view requires login."""
        url = reverse('scanner:valuation_comparison')
        response = client.get(url)

        # Should redirect to login
        assert response.status_code == 302
        assert '/accounts/login/' in response.url

    def test_context_includes_comparison_dates(self, client, user):
        """Test context includes previous quarter and year-ago dates."""
        client.force_login(user)

        url = reverse('scanner:valuation_comparison')
        response = client.get(url)

        assert 'comparison_date_quarter' in response.context
        assert 'comparison_date_year' in response.context
        assert isinstance(response.context['comparison_date_quarter'], date)
        assert isinstance(response.context['comparison_date_year'], date)

    def test_context_includes_all_active_stocks(self, client, user):
        """Test context includes all active stocks."""
        client.force_login(user)

        # Create active and inactive stocks
        CuratedStock.objects.create(symbol="ACTIVE1", active=True)
        CuratedStock.objects.create(symbol="ACTIVE2", active=True)
        CuratedStock.objects.create(symbol="INACTIVE", active=False)

        url = reverse('scanner:valuation_comparison')
        response = client.get(url)

        stocks = response.context['stocks']
        assert len(stocks) == 2
        assert all(s['stock'].active for s in stocks)

    def test_delta_calculation_positive_change(self, client, user):
        """Test delta calculations for positive change (increase)."""
        client.force_login(user)

        # Create stock with current valuation
        stock = CuratedStock.objects.create(
            symbol="AAPL",
            active=True,
            intrinsic_value=Decimal("150.00"),
            preferred_valuation_method="EPS",
        )

        # Create historical snapshot (lower value)
        ValuationHistory.objects.create(
            stock=stock,
            snapshot_date=date(2024, 10, 1),
            intrinsic_value=Decimal("140.00"),
            preferred_valuation_method="EPS",
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        url = reverse('scanner:valuation_comparison')
        response = client.get(url)

        stock_data = next(s for s in response.context['stocks'] if s['stock'].symbol == "AAPL")

        # Check quarter comparison (assuming today is in Q1 2025)
        if response.context['comparison_date_quarter'] == date(2024, 10, 1):
            assert stock_data['quarter_value'] == Decimal("140.00")
            assert stock_data['quarter_delta'] == Decimal("10.00")
            assert abs(stock_data['quarter_pct'] - 7.14) < 0.1  # ~7.14% increase

    def test_delta_calculation_negative_change(self, client, user):
        """Test delta calculations for negative change (decrease)."""
        client.force_login(user)

        stock = CuratedStock.objects.create(
            symbol="AAPL",
            active=True,
            intrinsic_value=Decimal("140.00"),
            preferred_valuation_method="EPS",
        )

        # Historical snapshot with higher value
        ValuationHistory.objects.create(
            stock=stock,
            snapshot_date=date(2024, 10, 1),
            intrinsic_value=Decimal("150.00"),
            preferred_valuation_method="EPS",
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        url = reverse('scanner:valuation_comparison')
        response = client.get(url)

        stock_data = next(s for s in response.context['stocks'] if s['stock'].symbol == "AAPL")

        if response.context['comparison_date_quarter'] == date(2024, 10, 1):
            assert stock_data['quarter_value'] == Decimal("150.00")
            assert stock_data['quarter_delta'] == Decimal("-10.00")
            assert abs(stock_data['quarter_pct'] - (-6.67)) < 0.1  # ~-6.67% decrease

    def test_handles_null_current_value(self, client, user):
        """Test handles NULL current intrinsic value."""
        client.force_login(user)

        CuratedStock.objects.create(
            symbol="NOVALUE",
            active=True,
            intrinsic_value=None,
            intrinsic_value_fcf=None,
            preferred_valuation_method="EPS",
        )

        url = reverse('scanner:valuation_comparison')
        response = client.get(url)

        stock_data = next(s for s in response.context['stocks'] if s['stock'].symbol == "NOVALUE")

        assert stock_data['current_value'] is None
        assert stock_data['quarter_delta'] is None
        assert stock_data['quarter_pct'] is None

    def test_handles_missing_historical_snapshot(self, client, user):
        """Test handles missing historical snapshot gracefully."""
        client.force_login(user)

        CuratedStock.objects.create(
            symbol="NEWSTOCK",
            active=True,
            intrinsic_value=Decimal("100.00"),
            preferred_valuation_method="EPS",
        )

        url = reverse('scanner:valuation_comparison')
        response = client.get(url)

        stock_data = next(s for s in response.context['stocks'] if s['stock'].symbol == "NEWSTOCK")

        # No historical data exists
        assert stock_data['quarter_value'] is None
        assert stock_data['year_value'] is None
        assert stock_data['quarter_delta'] is None
        assert stock_data['year_delta'] is None

    def test_percentage_calculation_accuracy(self, client, user):
        """Test percentage calculation is accurate."""
        client.force_login(user)

        stock = CuratedStock.objects.create(
            symbol="TEST",
            active=True,
            intrinsic_value=Decimal("110.00"),
            preferred_valuation_method="EPS",
        )

        # Historical: 100.00 → Current: 110.00 = 10% increase
        ValuationHistory.objects.create(
            stock=stock,
            snapshot_date=date(2024, 10, 1),
            intrinsic_value=Decimal("100.00"),
            preferred_valuation_method="EPS",
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        url = reverse('scanner:valuation_comparison')
        response = client.get(url)

        stock_data = next(s for s in response.context['stocks'] if s['stock'].symbol == "TEST")

        if response.context['comparison_date_quarter'] == date(2024, 10, 1):
            # (110 - 100) / 100 * 100 = 10%
            assert abs(stock_data['quarter_pct'] - 10.0) < 0.01


@pytest.mark.django_db
class TestValuationComparisonViewPerformance:
    """Performance tests for valuation_comparison_view."""

    def test_no_n_plus_1_queries(self, client, user, django_assert_num_queries):
        """Test view doesn't have N+1 query issues."""
        client.force_login(user)

        # Create 10 stocks
        for i in range(10):
            CuratedStock.objects.create(
                symbol=f"STOCK{i}",
                active=True,
                intrinsic_value=Decimal("100.00"),
            )

        url = reverse('scanner:valuation_comparison')

        # Query count should be constant regardless of stock count
        # Expected: 1 for user, 1 for stocks, 2 per stock for snapshots = 1 + 1 + 20 = 22
        # Can optimize later with prefetch_related if needed
        with django_assert_num_queries(22):
            response = client.get(url)
            assert response.status_code == 200


@pytest.fixture
def user(django_user_model):
    """Create test user."""
    return django_user_model.objects.create_user(
        username='testuser',
        password='testpass123'
    )
```

**Run tests**:
```bash
just test scanner/tests/test_valuation_comparison_view.py -v
```

**Expected**: All 10 tests pass

### Step 5: Test delta calculations

Verify delta calculations are correct for various scenarios.

**Manual testing in Django shell**:
```bash
uv run python manage.py shell

>>> from scanner.models import CuratedStock, ValuationHistory
>>> from datetime import date
>>> from decimal import Decimal

>>> # Create test stock
>>> stock = CuratedStock.objects.create(
...     symbol="TEST",
...     active=True,
...     intrinsic_value=Decimal("150.00"),
...     preferred_valuation_method="EPS"
... )

>>> # Create historical snapshot
>>> ValuationHistory.objects.create(
...     stock=stock,
...     snapshot_date=date(2024, 10, 1),
...     intrinsic_value=Decimal("140.00"),
...     preferred_valuation_method="EPS",
...     eps_growth_rate=Decimal("10.0"),
...     eps_multiple=Decimal("20.0"),
...     fcf_growth_rate=Decimal("10.0"),
...     fcf_multiple=Decimal("20.0"),
...     desired_return=Decimal("15.0"),
...     projection_years=5,
... )

>>> # Test delta calculation
>>> current = Decimal("150.00")
>>> historical = Decimal("140.00")
>>> delta = current - historical
>>> percentage = (delta / historical) * 100

>>> print(f"Delta: ${delta}")
>>> print(f"Percentage: {percentage}%")

>>> # Expected:
>>> # Delta: $10.00
>>> # Percentage: 7.142857142857143%

>>> # Cleanup
>>> stock.delete()
>>> exit()
```

### Step 6: Verify performance with many stocks

Test view performance with realistic data.

**Create test data**:
```bash
uv run python manage.py shell

>>> from scanner.models import CuratedStock, ValuationHistory
>>> from datetime import date
>>> from decimal import Decimal
>>> import random

>>> # Create 50 test stocks
>>> for i in range(50):
...     stock = CuratedStock.objects.create(
...         symbol=f"TEST{i:02d}",
...         active=True,
...         intrinsic_value=Decimal(str(100 + random.randint(-20, 20))),
...         preferred_valuation_method="EPS"
...     )
...     # Create historical snapshot
...     ValuationHistory.objects.create(
...         stock=stock,
...         snapshot_date=date(2024, 10, 1),
...         intrinsic_value=Decimal(str(100 + random.randint(-30, 30))),
...         preferred_valuation_method="EPS",
...         eps_growth_rate=Decimal("10.0"),
...         eps_multiple=Decimal("20.0"),
...         fcf_growth_rate=Decimal("10.0"),
...         fcf_multiple=Decimal("20.0"),
...         desired_return=Decimal("15.0"),
...         projection_years=5,
...     )

>>> exit()
```

**Test performance**:
```bash
# Time the view
time curl -s http://localhost:8000/scanner/valuations/comparison/ -H "Cookie: sessionid=..." > /dev/null

# Expected: <300ms for 50 stocks
```

**Cleanup test data**:
```bash
uv run python manage.py shell

>>> from scanner.models import CuratedStock
>>> CuratedStock.objects.filter(symbol__startswith="TEST").delete()
>>> exit()
```

**Verify all tests pass**:
```bash
just test
```

**Expected**: All 248+ tests pass (238 existing + 10 new)

## Summary of Changes

[Leave empty - will be filled during implementation]

## Notes

### Date Calculation Logic

**Quarter boundaries**:
- Q1: Jan 1 - Mar 31
- Q2: Apr 1 - Jun 30
- Q3: Jul 1 - Sep 30
- Q4: Oct 1 - Dec 31

**Previous quarter mapping**:
- In Q1 → Previous Q4 (last year)
- In Q2 → Previous Q1 (this year)
- In Q3 → Previous Q2 (this year)
- In Q4 → Previous Q3 (this year)

**Year-ago mapping**:
- In Q1 2025 → Q1 2024
- In Q2 2025 → Q2 2024
- Always same quarter, previous year

### Delta Calculation

**Absolute delta**:
```
delta = current_value - historical_value
```

**Positive delta**: Valuation increased
**Negative delta**: Valuation decreased

**Percentage change**:
```
percentage = (delta / historical_value) * 100
```

**Example**:
- Historical: $100
- Current: $110
- Delta: $10
- Percentage: 10%

### NULL Handling

**Scenarios**:
1. Current value is NULL → No deltas calculated
2. Historical value is NULL → No deltas calculated
3. Both NULL → No deltas calculated
4. Historical is 0 → Division by zero avoided, percentage is None

**Implementation**:
```python
if current_value is not None and historical_value is not None:
    delta = current_value - historical_value
    if historical_value != 0:
        percentage = (delta / historical_value) * 100
```

### Query Optimization

**Current approach** (per-stock queries):
```python
for stock in stocks:
    quarter_snapshot = ValuationHistory.objects.filter(...).first()
    year_snapshot = ValuationHistory.objects.filter(...).first()
```

**Trade-offs**:
- Simple to understand
- 2 queries per stock (N+1 issue)
- Acceptable for <100 stocks

**Future optimization** (if needed):
```python
# Fetch all snapshots in 2 queries
quarter_snapshots = {
    s.stock_id: s
    for s in ValuationHistory.objects.filter(
        snapshot_date=previous_quarter_date,
        stock__active=True
    ).select_related('stock')
}

year_snapshots = {
    s.stock_id: s
    for s in ValuationHistory.objects.filter(
        snapshot_date=year_ago_date,
        stock__active=True
    ).select_related('stock')
}

# Then lookup in dict instead of querying
for stock in stocks:
    quarter_snapshot = quarter_snapshots.get(stock.id)
    year_snapshot = year_snapshots.get(stock.id)
```

**When to optimize**:
- If response time >500ms
- If stock count >100
- After profiling identifies bottleneck

### Color Coding (Frontend Task 040)

**Delta colors**:
- Positive (increase): Green
- Negative (decrease): Red
- Zero: Gray
- NULL: Gray with "-"

**Example**:
- +$10.00 (+7.14%) → Green
- -$5.00 (-3.33%) → Red
- $0.00 (0.00%) → Gray

## Dependencies

- Tasks 035-037 completed (Model, snapshots, history view exist)
- Date calculations for quarters
- Decimal arithmetic for precise calculations

## Reference

**Python datetime module**:
- https://docs.python.org/3/library/datetime.html

**Decimal arithmetic**:
- https://docs.python.org/3/library/decimal.html

**Implementation spec**:
- See: `/Users/danvigliotti/Development/Sirvig/wheel-analyzer/specs/phase-6-historical-valuations.md`
- Section 4: Backend Implementation
- Section 7: Testing Strategy
