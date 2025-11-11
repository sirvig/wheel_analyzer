# Task 037: Per-Stock History Backend View

## Progress Summary

**Status**: Not Started

- [ ] Step 1: Add stock_history_view to scanner/views.py
- [ ] Step 2: Add URL routing for stock history
- [ ] Step 3: Write view integration tests
- [ ] Step 4: Test query performance
- [ ] Step 5: Verify error handling

## Overview

Implement a Django view that displays the complete valuation history for a single stock. The view will show all quarterly snapshots in reverse chronological order (newest first), enabling users to see how intrinsic valuations and DCF assumptions have changed over time.

**Current State**:
- ValuationHistory model populated with snapshots
- No view to display historical data
- Users cannot see valuation trends

**Target State**:
- View accessible at `/scanner/valuations/history/<symbol>/`
- Shows all snapshots for the stock ordered by date descending
- Includes current valuation summary for comparison
- Login required for access
- 404 error for non-existent or inactive stocks
- Efficient queries with select_related

## High-Level Specifications

### View Features

- **URL pattern**: `/scanner/valuations/history/<symbol>/`
- **Authentication**: `@login_required` decorator
- **Query optimization**: Use `select_related('stock')` for foreign key
- **Error handling**: 404 for invalid symbols or inactive stocks
- **Context data**:
  - `stock`: CuratedStock instance
  - `history`: QuerySet of ValuationHistory ordered by `-snapshot_date`
  - `has_history`: Boolean flag for empty state
- **Template**: `scanner/stock_history.html` (created in Task 038)

### Query Pattern

```python
# Efficient query with foreign key optimization
history = ValuationHistory.objects.filter(
    stock=stock
).order_by('-snapshot_date')
```

### Error Cases

- Symbol not found → 404
- Stock is inactive → 404
- No history exists → Render with `has_history=False`

## Relevant Files

### Files to Create
- None (adding to existing files)

### Files to Modify
- `scanner/views.py` - Add `stock_history_view` function
- `scanner/urls.py` - Add URL pattern for history view

### Files for Testing
- `scanner/tests/test_valuation_history_views.py` - New test file with 8 tests

## Acceptance Criteria

### View Implementation
- [ ] `stock_history_view` function defined in `scanner/views.py`
- [ ] Function has `@login_required` decorator
- [ ] Takes `request` and `symbol` parameters
- [ ] Uses `get_object_or_404` for stock lookup
- [ ] Filters by `active=True` for stock
- [ ] Queries history with `order_by('-snapshot_date')`
- [ ] Context includes `stock`, `history`, `has_history`
- [ ] Returns rendered `scanner/stock_history.html` template
- [ ] Logging statements at INFO level

### URL Configuration
- [ ] URL pattern added to `scanner/urls.py`
- [ ] Pattern: `valuations/history/<str:symbol>/`
- [ ] Name: `stock_history`
- [ ] Follows existing URL namespace conventions

### Testing Requirements
- [ ] Test: View returns 200 for valid stock with history
- [ ] Test: View returns 404 for nonexistent stock
- [ ] Test: View returns 404 for inactive stock
- [ ] Test: View requires authentication (redirects to login)
- [ ] Test: Context includes correct stock instance
- [ ] Test: Context includes history ordered by date descending
- [ ] Test: `has_history` is True when snapshots exist
- [ ] Test: `has_history` is False when no snapshots
- [ ] All 8 tests pass

### Query Performance
- [ ] No N+1 query issues (verified with assertions)
- [ ] History query completes in <50ms for 20 snapshots
- [ ] select_related used for foreign keys if needed

### Error Handling
- [ ] 404 response for invalid symbol
- [ ] 404 response for inactive stock
- [ ] Graceful handling of no history (empty state)

## Implementation Steps

### Step 1: Add stock_history_view to scanner/views.py

Add the new view function to display stock history.

**File to modify**: `scanner/views.py`

**Add after valuation_list_view** (around line 400):

```python
@login_required
def stock_history_view(request, symbol):
    """
    Display valuation history for a single stock.

    Shows quarterly snapshots with trend visualization and assumption tracking.

    Args:
        symbol: Stock ticker symbol

    Returns:
        Rendered scanner/stock_history.html template

    Context:
        stock: CuratedStock instance
        history: QuerySet of ValuationHistory ordered by date descending
        has_history: Boolean indicating if any snapshots exist
    """
    # Get stock (404 if not found or inactive)
    stock = get_object_or_404(CuratedStock, symbol=symbol.upper(), active=True)

    # Get history ordered by date (newest first)
    history = ValuationHistory.objects.filter(stock=stock).order_by('-snapshot_date')

    logger.info(f"Stock history view accessed by {request.user.username} for {symbol}")
    logger.debug(f"Found {history.count()} historical snapshots for {symbol}")

    context = {
        'stock': stock,
        'history': history,
        'has_history': history.exists(),
    }

    return render(request, 'scanner/stock_history.html', context)
```

**Add import at top** (if not present):
```python
from scanner.models import ValuationHistory
```

**Verify Python syntax**:
```bash
uv run python -m py_compile scanner/views.py
```

### Step 2: Add URL routing for stock history

Add URL pattern to scanner URLconf.

**File to modify**: `scanner/urls.py`

**Add to urlpatterns** (after valuations URLs):
```python
urlpatterns = [
    # ... existing URLs ...

    # Valuation URLs
    path('valuations/', views.valuation_list_view, name='valuations'),

    # Historical valuation URLs (add these)
    path('valuations/history/<str:symbol>/', views.stock_history_view, name='stock_history'),
]
```

**Verify URL configuration**:
```bash
# Show all URLs
uv run python manage.py show_urls | grep history

# Expected: scanner:stock_history pattern with symbol parameter
```

### Step 3: Write view integration tests

Create comprehensive integration tests for the view.

**File to create**: `scanner/tests/test_valuation_history_views.py`

**Content**:
```python
"""
Tests for valuation history views.

Test coverage:
- stock_history_view returns 200 for valid stock
- 404 for nonexistent stock
- 404 for inactive stock
- Authentication required
- Context data correct
- History ordering
- Empty state handling
"""

import pytest
from datetime import date
from decimal import Decimal
from django.urls import reverse

from scanner.models import CuratedStock, ValuationHistory


@pytest.mark.django_db
class TestStockHistoryView:
    """Tests for stock_history_view."""

    def test_view_returns_200_for_valid_stock(self, client, user):
        """Test view returns 200 status for valid stock with history."""
        # Login
        client.force_login(user)

        # Create stock with history
        stock = CuratedStock.objects.create(
            symbol="AAPL",
            name="Apple Inc.",
            active=True,
            intrinsic_value=Decimal("150.00"),
        )

        ValuationHistory.objects.create(
            stock=stock,
            snapshot_date=date(2025, 1, 1),
            intrinsic_value=Decimal("150.00"),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        # Request view
        url = reverse('scanner:stock_history', kwargs={'symbol': 'AAPL'})
        response = client.get(url)

        assert response.status_code == 200

    def test_view_returns_404_for_nonexistent_stock(self, client, user):
        """Test view returns 404 for nonexistent stock."""
        client.force_login(user)

        url = reverse('scanner:stock_history', kwargs={'symbol': 'NONEXISTENT'})
        response = client.get(url)

        assert response.status_code == 404

    def test_view_returns_404_for_inactive_stock(self, client, user):
        """Test view returns 404 for inactive stock."""
        client.force_login(user)

        # Create inactive stock
        CuratedStock.objects.create(
            symbol="INACTIVE",
            active=False,
        )

        url = reverse('scanner:stock_history', kwargs={'symbol': 'INACTIVE'})
        response = client.get(url)

        assert response.status_code == 404

    def test_view_requires_authentication(self, client):
        """Test view requires login."""
        # Create stock
        CuratedStock.objects.create(
            symbol="AAPL",
            active=True,
        )

        # Request without login
        url = reverse('scanner:stock_history', kwargs={'symbol': 'AAPL'})
        response = client.get(url)

        # Should redirect to login
        assert response.status_code == 302
        assert '/accounts/login/' in response.url

    def test_context_includes_stock(self, client, user):
        """Test context includes correct stock instance."""
        client.force_login(user)

        stock = CuratedStock.objects.create(
            symbol="AAPL",
            name="Apple Inc.",
            active=True,
        )

        url = reverse('scanner:stock_history', kwargs={'symbol': 'AAPL'})
        response = client.get(url)

        assert response.context['stock'] == stock
        assert response.context['stock'].symbol == "AAPL"

    def test_context_includes_history_ordered_descending(self, client, user):
        """Test context includes history ordered by date descending."""
        client.force_login(user)

        stock = CuratedStock.objects.create(
            symbol="AAPL",
            active=True,
        )

        # Create snapshots in random order
        snapshot1 = ValuationHistory.objects.create(
            stock=stock,
            snapshot_date=date(2024, 1, 1),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        snapshot2 = ValuationHistory.objects.create(
            stock=stock,
            snapshot_date=date(2025, 1, 1),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        snapshot3 = ValuationHistory.objects.create(
            stock=stock,
            snapshot_date=date(2024, 7, 1),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        url = reverse('scanner:stock_history', kwargs={'symbol': 'AAPL'})
        response = client.get(url)

        history = list(response.context['history'])

        # Should be ordered newest first
        assert history[0] == snapshot2  # 2025-01-01
        assert history[1] == snapshot3  # 2024-07-01
        assert history[2] == snapshot1  # 2024-01-01

    def test_has_history_true_when_snapshots_exist(self, client, user):
        """Test has_history flag is True when snapshots exist."""
        client.force_login(user)

        stock = CuratedStock.objects.create(
            symbol="AAPL",
            active=True,
        )

        ValuationHistory.objects.create(
            stock=stock,
            snapshot_date=date(2025, 1, 1),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        url = reverse('scanner:stock_history', kwargs={'symbol': 'AAPL'})
        response = client.get(url)

        assert response.context['has_history'] is True

    def test_has_history_false_when_no_snapshots(self, client, user):
        """Test has_history flag is False when no snapshots exist."""
        client.force_login(user)

        CuratedStock.objects.create(
            symbol="AAPL",
            active=True,
        )

        url = reverse('scanner:stock_history', kwargs={'symbol': 'AAPL'})
        response = client.get(url)

        assert response.context['has_history'] is False


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
just test scanner/tests/test_valuation_history_views.py -v
```

**Expected**: All 8 tests pass

### Step 4: Test query performance

Verify no N+1 query issues and reasonable performance.

**Create performance test**:

Add to `test_valuation_history_views.py`:
```python
@pytest.mark.django_db
class TestStockHistoryViewPerformance:
    """Performance tests for stock_history_view."""

    def test_no_n_plus_1_queries(self, client, user, django_assert_num_queries):
        """Test view doesn't have N+1 query issues."""
        client.force_login(user)

        stock = CuratedStock.objects.create(
            symbol="AAPL",
            active=True,
        )

        # Create 10 snapshots
        for i in range(10):
            ValuationHistory.objects.create(
                stock=stock,
                snapshot_date=date(2020 + i, 1, 1),
                eps_growth_rate=Decimal("10.0"),
                eps_multiple=Decimal("20.0"),
                fcf_growth_rate=Decimal("10.0"),
                fcf_multiple=Decimal("20.0"),
                desired_return=Decimal("15.0"),
                projection_years=5,
            )

        url = reverse('scanner:stock_history', kwargs={'symbol': 'AAPL'})

        # Should use constant number of queries regardless of snapshot count
        # Expected: 1 for user, 1 for stock lookup, 1 for history
        with django_assert_num_queries(3):
            response = client.get(url)
            assert response.status_code == 200
```

**Run performance test**:
```bash
just test scanner/tests/test_valuation_history_views.py::TestStockHistoryViewPerformance -v
```

**Expected**: Test passes with 3 queries

### Step 5: Verify error handling

Test error cases and edge conditions.

**Manual testing**:
```bash
# Start server
just run

# Login at http://localhost:8000/accounts/login/

# Test valid stock (should work)
# http://localhost:8000/scanner/valuations/history/AAPL/

# Test invalid symbol (should 404)
# http://localhost:8000/scanner/valuations/history/INVALID/

# Test without login (should redirect)
# Logout and try accessing the URL

# Test lowercase symbol (should work - uppercase conversion)
# http://localhost:8000/scanner/valuations/history/aapl/
```

**Check logs**:
```bash
# In server output, verify INFO logs appear:
# "Stock history view accessed by testuser for AAPL"
# "Found X historical snapshots for AAPL"
```

**Verify all tests still pass**:
```bash
just test
```

**Expected**: All 238+ tests pass (230 existing + 8 new)

## Summary of Changes

[Leave empty - will be filled during implementation]

## Notes

### Query Optimization

**Current approach** (efficient):
```python
history = ValuationHistory.objects.filter(stock=stock).order_by('-snapshot_date')
```

**Why no select_related needed**:
- We already have the `stock` instance from `get_object_or_404`
- Template will access `stock.symbol` which is already loaded
- History → stock foreign key won't be traversed in template

**If we needed stock data**:
```python
history = ValuationHistory.objects.filter(
    stock=stock
).select_related('stock').order_by('-snapshot_date')
```

### URL Pattern Design

**Pattern**: `valuations/history/<str:symbol>/`

**Why this structure?**:
- Logical hierarchy: valuations → history → stock
- Consistent with existing `valuations/` URL
- Symbol as path parameter (RESTful design)
- Could add query params later for filtering (e.g., `?start_date=2024-01-01`)

**Alternative patterns considered**:
- `/history/<symbol>/` - Too generic, not clear it's for valuations
- `/stocks/<symbol>/history/` - Inconsistent with existing URLs
- `/valuations/<symbol>/history/` - More verbose but acceptable

### Empty State Handling

**When no history exists**:
- View still renders successfully (200 status)
- `has_history` flag set to False
- Template shows informative message (Task 038)
- Not an error condition (new stocks won't have history yet)

### Symbol Case Sensitivity

**Implementation**: `symbol.upper()` in view

**Why?**:
- Stock symbols are conventionally uppercase
- Users might type lowercase (e.g., "aapl")
- Database comparison is case-sensitive in PostgreSQL
- Converting to uppercase ensures consistent lookups

**Example**:
- User visits: `/valuations/history/aapl/`
- View converts to: `AAPL`
- Lookup: `CuratedStock.objects.get(symbol='AAPL')`

### Logging Strategy

**INFO level**:
- User access tracking
- Snapshot count for monitoring

**DEBUG level**:
- Detailed query information
- Not shown in production by default

**Example logs**:
```
INFO: Stock history view accessed by john@example.com for AAPL
DEBUG: Found 8 historical snapshots for AAPL
```

## Dependencies

- Task 035 completed (ValuationHistory model exists)
- Task 036 completed (Snapshots can be created)
- Existing valuation_list_view as reference
- Login system configured

## Reference

**Django views documentation**:
- https://docs.djangoproject.com/en/5.1/topics/http/views/
- https://docs.djangoproject.com/en/5.1/topics/http/shortcuts/#get-object-or-404

**Django URL dispatcher**:
- https://docs.djangoproject.com/en/5.1/topics/http/urls/

**Implementation spec**:
- See: `/Users/danvigliotti/Development/Sirvig/wheel-analyzer/specs/phase-6-historical-valuations.md`
- Section 4: Backend Implementation
- Section 7: Testing Strategy
