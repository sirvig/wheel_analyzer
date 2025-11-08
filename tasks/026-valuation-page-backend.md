# Task 026: Create Curated Stock Valuation Page - Backend

## Progress Summary

**Status**: Completed

- [x] Step 1: Create valuation_list_view in scanner/views.py
- [x] Step 2: Add URL route for valuations page
- [x] Step 3: Test view returns correct data (integration tests added)
- [x] Step 4: Verify authentication requirement (integration tests added)

## Overview

Create the backend view and URL routing for a new page that displays all curated stocks with their valuation data. This page provides users with a comprehensive overview of intrinsic values across the entire portfolio.

The implementation adds:
- Django view function to query and display all active curated stocks
- URL route accessible at `/scanner/valuations/`
- Authentication requirement to protect valuation data
- Queryset ordered alphabetically by ticker symbol

## Current State Analysis

### Current Scanner URLs

The `scanner/urls.py` currently has:
- `''` - Main scanner page (index)
- `'options/'` - Options list page
- `'scan/'` - Manual scan trigger (HTMX endpoint)
- `'scan/status/'` - Scan status polling (HTMX endpoint)

**Missing**: Route for valuation page

### Current Scanner Views

The `scanner/views.py` has:
- `index` - Main scanner page
- `options_list` - Shows cached options results
- `scan_view` - Triggers manual scan in background thread
- `scan_status` - Polls for scan progress/results

**Missing**: View for valuation list page

### Current CuratedStock Model

All fields needed for display already exist:
- Basic info: `symbol`, `name`, `is_active`
- EPS valuation: `intrinsic_value`, `current_eps`, `eps_growth_rate`, `eps_multiple`
- FCF valuation: `intrinsic_value_fcf`, `current_fcf_per_share`, `fcf_growth_rate`, `fcf_multiple`
- Shared: `preferred_valuation_method`, `desired_return`, `projection_years`, `last_calculation_date`

## Target State

### New View Function

```python
@login_required
def valuation_list_view(request):
    """
    Display all active curated stocks with their valuation data.
    
    Shows intrinsic values (EPS and FCF methods), calculation assumptions,
    and last calculation dates for all active stocks in the curated list.
    
    Template: scanner/valuations.html
    Context:
        - stocks: QuerySet of CuratedStock objects (active only, ordered by symbol)
    """
    stocks = CuratedStock.objects.filter(is_active=True).order_by('symbol')
    
    context = {
        'stocks': stocks,
    }
    
    return render(request, 'scanner/valuations.html', context)
```

### New URL Pattern

```python
path('valuations/', views.valuation_list_view, name='valuations'),
```

### URL Structure

Full path: `/scanner/valuations/`
- App namespace: `scanner`
- View name: `valuation_list_view`
- URL name: `valuations`
- Template: `scanner/valuations.html`

**URL reverse**:
```python
{% url 'scanner:valuations' %}
```

## Implementation Steps

### Step 1: Create valuation_list_view in scanner/views.py

Add the new view function to display curated stock valuations.

**File to modify**: `scanner/views.py`

**Add imports** (at top of file, if not already present):
```python
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import CuratedStock
```

**Add view function** (at end of file, after existing views):

```python
@login_required
def valuation_list_view(request):
    """
    Display all active curated stocks with their valuation data.
    
    Shows intrinsic values (EPS and FCF methods), calculation assumptions,
    and last calculation dates for all active stocks in the curated list.
    
    This page provides a comprehensive overview of the portfolio's intrinsic
    value calculations, allowing users to review valuation metrics across
    all monitored stocks.
    
    Template: scanner/valuations.html
    
    Context:
        stocks (QuerySet): All active CuratedStock instances ordered by symbol
    
    Example:
        Access via: /scanner/valuations/
        Template receives list of stocks with all valuation fields
    """
    # Query all active curated stocks, ordered alphabetically
    stocks = CuratedStock.objects.filter(is_active=True).order_by('symbol')
    
    logger.info(f"Valuation list view accessed by {request.user.username}")
    logger.debug(f"Displaying {stocks.count()} active curated stocks")
    
    context = {
        'stocks': stocks,
    }
    
    return render(request, 'scanner/valuations.html', context)
```

**Location**: Add after the `scan_status` view function.

### Step 2: Add URL route for valuations page

Register the new view in the scanner URL configuration.

**File to modify**: `scanner/urls.py`

**Current URL patterns**:
```python
urlpatterns = [
    path("", views.index, name="index"),
    path("options/", views.options_list, name="options_list"),
    path("scan/", views.scan_view, name="scan"),
    path("scan/status/", views.scan_status, name="scan_status"),
]
```

**Add new URL pattern**:
```python
urlpatterns = [
    path("", views.index, name="index"),
    path("options/", views.options_list, name="options_list"),
    path("valuations/", views.valuation_list_view, name="valuations"),  # NEW
    path("scan/", views.scan_view, name="scan"),
    path("scan/status/", views.scan_status, name="scan_status"),
]
```

**Location**: Add after `options_list` and before `scan` for logical grouping.

### Step 3: Test view returns correct data

Verify the view queries and returns the correct stocks.

**Test with Django shell**:

```bash
just exec python manage.py shell
```

```python
from scanner.models import CuratedStock
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from scanner.views import valuation_list_view

# Create a test request
factory = RequestFactory()
User = get_user_model()
user = User.objects.first()

# Create GET request
request = factory.get('/scanner/valuations/')
request.user = user

# Call the view
response = valuation_list_view(request)

# Check response
print(f"Status code: {response.status_code}")
print(f"Template: {response.template_name}")

# Check context
stocks = response.context_data['stocks']
print(f"Number of stocks: {stocks.count()}")
print(f"First stock: {stocks.first().symbol if stocks.exists() else 'None'}")
print(f"Last stock: {stocks.last().symbol if stocks.exists() else 'None'}")

# Verify ordering
symbols = list(stocks.values_list('symbol', flat=True))
print(f"Symbols (should be alphabetical): {symbols}")

# Verify all are active
inactive_count = stocks.filter(is_active=False).count()
print(f"Inactive stocks (should be 0): {inactive_count}")
```

**Test manually via browser** (after Task 027 completes template):

1. Ensure you're logged in
2. Navigate to: `http://localhost:8000/scanner/valuations/`
3. Should see the valuations page (will be unstyled until Task 027)

**Test authentication requirement**:

```python
# In Django shell
from django.test import Client

client = Client()

# Try without login (should redirect)
response = client.get('/scanner/valuations/')
print(f"Unauthenticated status: {response.status_code}")  # Should be 302 (redirect)
print(f"Redirect to: {response.url}")  # Should be login page

# Try with login (should work)
from django.contrib.auth import get_user_model
User = get_user_model()
user = User.objects.first()
client.force_login(user)

response = client.get('/scanner/valuations/')
print(f"Authenticated status: {response.status_code}")  # Should be 200
```

### Step 4: Verify authentication requirement

Ensure unauthenticated users cannot access the page.

**Manual testing**:

1. **Logout** from the application
2. Try to access: `http://localhost:8000/scanner/valuations/`
3. Should redirect to login page
4. Login and access again - should work

**Automated test** (add to `scanner/tests/test_scanner_views.py`):

```python
def test_valuation_list_requires_authentication(self):
    """Valuation list view requires user to be logged in."""
    # Try without authentication
    response = self.client.get('/scanner/valuations/')
    
    # Should redirect to login
    self.assertEqual(response.status_code, 302)
    self.assertIn('/account/login/', response.url)

def test_valuation_list_authenticated(self, user):
    """Authenticated user can access valuation list."""
    self.client.force_login(user)
    
    response = self.client.get('/scanner/valuations/')
    
    # Should succeed
    self.assertEqual(response.status_code, 200)
    self.assertTemplateUsed(response, 'scanner/valuations.html')

def test_valuation_list_shows_active_stocks_only(self, user):
    """Valuation list shows only active curated stocks."""
    from scanner.factories import CuratedStockFactory
    
    # Create active and inactive stocks
    active1 = CuratedStockFactory(symbol='AAPL', is_active=True)
    active2 = CuratedStockFactory(symbol='MSFT', is_active=True)
    inactive = CuratedStockFactory(symbol='INACTIVE', is_active=False)
    
    self.client.force_login(user)
    response = self.client.get('/scanner/valuations/')
    
    stocks = response.context['stocks']
    
    # Should include active stocks
    self.assertIn(active1, stocks)
    self.assertIn(active2, stocks)
    
    # Should NOT include inactive stock
    self.assertNotIn(inactive, stocks)

def test_valuation_list_ordered_by_symbol(self, user):
    """Valuation list is ordered alphabetically by symbol."""
    from scanner.factories import CuratedStockFactory
    
    # Create stocks in non-alphabetical order
    CuratedStockFactory(symbol='TSLA', is_active=True)
    CuratedStockFactory(symbol='AAPL', is_active=True)
    CuratedStockFactory(symbol='MSFT', is_active=True)
    
    self.client.force_login(user)
    response = self.client.get('/scanner/valuations/')
    
    stocks = response.context['stocks']
    symbols = [stock.symbol for stock in stocks]
    
    # Should be in alphabetical order
    self.assertEqual(symbols, sorted(symbols))
    self.assertEqual(symbols, ['AAPL', 'MSFT', 'TSLA'])
```

**Run tests**:
```bash
just test scanner/tests/test_scanner_views.py::test_valuation_list_requires_authentication
just test scanner/tests/test_scanner_views.py::test_valuation_list_authenticated
just test scanner/tests/test_scanner_views.py::test_valuation_list_shows_active_stocks_only
just test scanner/tests/test_scanner_views.py::test_valuation_list_ordered_by_symbol
```

## Acceptance Criteria

### View Function Requirements

- [ ] `valuation_list_view` function created in `scanner/views.py`
- [ ] View requires authentication with `@login_required` decorator
- [ ] View queries only active curated stocks (`is_active=True`)
- [ ] QuerySet ordered alphabetically by `symbol`
- [ ] Context includes `stocks` variable
- [ ] View renders `scanner/valuations.html` template
- [ ] View has comprehensive docstring

### URL Routing Requirements

- [ ] URL pattern added to `scanner/urls.py`
- [ ] Route path is `valuations/`
- [ ] URL name is `valuations`
- [ ] Full path is `/scanner/valuations/`
- [ ] URL reverse works: `{% url 'scanner:valuations' %}`

### Authentication Requirements

- [ ] Unauthenticated users redirected to login page
- [ ] Authenticated users can access the page
- [ ] Login redirect preserves next parameter
- [ ] Authentication test passes

### Data Requirements

- [ ] Only active stocks returned in queryset
- [ ] Inactive stocks excluded from results
- [ ] Stocks ordered alphabetically (A-Z)
- [ ] Empty queryset handled gracefully (no stocks)
- [ ] QuerySet includes all valuation fields

### Testing Requirements

- [ ] View accessible via browser when logged in
- [ ] View redirects when not logged in
- [ ] Context contains correct data
- [ ] Automated tests pass
- [ ] Logger statements work correctly

## Files Involved

### Modified Files

- `scanner/views.py`
  - Add imports (if needed)
  - Add `valuation_list_view` function

- `scanner/urls.py`
  - Add URL pattern for valuations page

### New Test Cases

- `scanner/tests/test_scanner_views.py`
  - `test_valuation_list_requires_authentication`
  - `test_valuation_list_authenticated`
  - `test_valuation_list_shows_active_stocks_only`
  - `test_valuation_list_ordered_by_symbol`

### Template File (Created in Task 027)

- `templates/scanner/valuations.html` - Will be created in next task

## Notes

### Queryset Efficiency

**Single query**:
- Using `filter().order_by()` executes single SQL query
- No N+1 problems
- All fields loaded in one trip to database

**Typical performance**:
- 50 curated stocks = ~10ms query time
- Template rendering = ~20ms
- Total page load = ~50ms

### Future Enhancements (Not in This Task)

**Possible additions** (can be done later):
- Pagination for large stock lists (>100 stocks)
- Search/filter by symbol or name
- Sort by different columns (IV, last calc date)
- Export to CSV functionality
- Filter by preferred valuation method

**Current scope**: Simple list view, no filtering/sorting

### Edge Cases

**No active stocks**:
- QuerySet will be empty
- Template should handle gracefully
- Display message: "No active curated stocks found"

**Stock with NULL intrinsic values**:
- Stock still returned in queryset
- Template will display "-" or "Not calculated"
- Task 027 handles NULL value display

### Logging

**Info level**:
- User accessing the page
- Number of stocks displayed

**Debug level**:
- Detailed queryset information
- Performance metrics (if needed)

**Example log output**:
```
INFO: Valuation list view accessed by dan.vigliotti
DEBUG: Displaying 26 active curated stocks
```

## Dependencies

- Requires `CuratedStock` model from Task 001
- Uses Django's `@login_required` decorator
- Depends on authentication system (django-allauth)
- Template will be created in Task 027

## Reference

**Django Class-Based vs Function-Based Views**:
- We use function-based view for simplicity
- https://docs.djangoproject.com/en/5.1/topics/class-based-views/

**Django QuerySet API**:
- `filter()`: https://docs.djangoproject.com/en/5.1/ref/models/querysets/#filter
- `order_by()`: https://docs.djangoproject.com/en/5.1/ref/models/querysets/#order-by

**Django Authentication**:
- `@login_required`: https://docs.djangoproject.com/en/5.1/topics/auth/default/#the-login-required-decorator

**Django URL Dispatcher**:
- https://docs.djangoproject.com/en/5.1/topics/http/urls/
