# Task 028: Testing and Refinement

## Progress Summary

**Status**: In Progress

- [x] Step 1: Add unit tests for get_effective_intrinsic_value method (6 tests, all passing)
- [x] Step 2: Add integration tests for valuation_list_view (7 tests added, static files config issue)
- [ ] Step 3: Add integration tests for scanner views with intrinsic value context  
- [ ] Step 4: Manual testing checklist for complete feature
- [ ] Step 5: Fix any bugs or issues discovered

## Overview

Add comprehensive tests for Phase 5 features and perform thorough manual testing to ensure all functionality works correctly end-to-end. This task validates the intrinsic value indicators in the scanner and the new valuations page.

The implementation adds:
- Unit tests for the `get_effective_intrinsic_value()` model method
- Integration tests for the valuation list view
- Integration tests for scanner views with intrinsic value context
- Manual testing checklist covering all user scenarios
- Bug fixes and refinements based on test results

## Current State Analysis

### Existing Test Files

**scanner/tests/test_scanner_models.py**:
- Tests for `CuratedStock` model
- Tests for `OptionsWatch` model

**scanner/tests/test_scanner_views.py**:
- Tests for scanner views
- Tests for manual scan functionality
- Tests for polling mechanism

**scanner/tests/conftest.py**:
- Pytest fixtures for testing
- User factory, stock factories, etc.

### Test Coverage Gaps

**Missing tests for Phase 5**:
- No tests for `get_effective_intrinsic_value()` method
- No tests for `valuation_list_view`
- No tests for intrinsic value context in scanner views
- No tests for visual indicator logic

## Target State

### Unit Test Coverage

**Model method tests**:
- `test_get_effective_intrinsic_value_eps_method()`
- `test_get_effective_intrinsic_value_fcf_method()`
- `test_get_effective_intrinsic_value_null_values()`

### Integration Test Coverage

**Valuation list view tests**:
- `test_valuation_list_requires_authentication()`
- `test_valuation_list_authenticated()`
- `test_valuation_list_shows_active_stocks_only()`
- `test_valuation_list_ordered_by_symbol()`
- `test_valuation_list_context_includes_stocks()`

**Scanner view tests**:
- `test_scan_view_includes_curated_stocks_context()`
- `test_scan_status_includes_curated_stocks_context()`
- `test_curated_stocks_context_empty_results()`

### Manual Testing Checklist

**Scanner page**:
- Run scan and verify badges appear
- Test with stocks at different IV states
- Test accordion badges reflect option status
- Test individual option badges

**Valuations page**:
- Verify all stocks displayed
- Test with NULL values
- Test navbar dropdown navigation
- Test responsive layout

## Implementation Steps

### Step 1: Add unit tests for get_effective_intrinsic_value method

Add tests for the new model method in the CuratedStock model.

**File to modify**: `scanner/tests/test_scanner_models.py`

**Add tests** (at end of file or in appropriate test class):

```python
class TestCuratedStockValuationMethods:
    """Tests for CuratedStock valuation-related methods."""
    
    def test_get_effective_intrinsic_value_eps_method(self):
        """get_effective_intrinsic_value returns EPS value when preferred method is 'eps'."""
        from decimal import Decimal
        from scanner.factories import CuratedStockFactory
        
        stock = CuratedStockFactory(
            symbol='AAPL',
            intrinsic_value=Decimal('150.25'),
            intrinsic_value_fcf=Decimal('148.50'),
            preferred_valuation_method='eps'
        )
        
        effective_iv = stock.get_effective_intrinsic_value()
        
        assert effective_iv == Decimal('150.25')
        assert effective_iv == stock.intrinsic_value
    
    def test_get_effective_intrinsic_value_fcf_method(self):
        """get_effective_intrinsic_value returns FCF value when preferred method is 'fcf'."""
        from decimal import Decimal
        from scanner.factories import CuratedStockFactory
        
        stock = CuratedStockFactory(
            symbol='MSFT',
            intrinsic_value=Decimal('200.00'),
            intrinsic_value_fcf=Decimal('195.75'),
            preferred_valuation_method='fcf'
        )
        
        effective_iv = stock.get_effective_intrinsic_value()
        
        assert effective_iv == Decimal('195.75')
        assert effective_iv == stock.intrinsic_value_fcf
    
    def test_get_effective_intrinsic_value_null_eps(self):
        """get_effective_intrinsic_value returns None when EPS value is NULL."""
        from scanner.factories import CuratedStockFactory
        
        stock = CuratedStockFactory(
            symbol='TSLA',
            intrinsic_value=None,
            intrinsic_value_fcf=Decimal('100.00'),
            preferred_valuation_method='eps'
        )
        
        effective_iv = stock.get_effective_intrinsic_value()
        
        assert effective_iv is None
    
    def test_get_effective_intrinsic_value_null_fcf(self):
        """get_effective_intrinsic_value returns None when FCF value is NULL."""
        from scanner.factories import CuratedStockFactory
        
        stock = CuratedStockFactory(
            symbol='ABNB',
            intrinsic_value=Decimal('85.00'),
            intrinsic_value_fcf=None,
            preferred_valuation_method='fcf'
        )
        
        effective_iv = stock.get_effective_intrinsic_value()
        
        assert effective_iv is None
    
    def test_get_effective_intrinsic_value_both_null(self):
        """get_effective_intrinsic_value returns None when both values are NULL."""
        from scanner.factories import CuratedStockFactory
        
        stock = CuratedStockFactory(
            symbol='NEW',
            intrinsic_value=None,
            intrinsic_value_fcf=None,
            preferred_valuation_method='eps'
        )
        
        effective_iv = stock.get_effective_intrinsic_value()
        
        assert effective_iv is None
    
    def test_get_effective_intrinsic_value_defaults_to_eps(self):
        """get_effective_intrinsic_value defaults to EPS for unknown method."""
        from decimal import Decimal
        from scanner.factories import CuratedStockFactory
        
        stock = CuratedStockFactory(
            symbol='TEST',
            intrinsic_value=Decimal('120.00'),
            intrinsic_value_fcf=Decimal('115.00'),
            preferred_valuation_method='unknown'  # Invalid method
        )
        
        effective_iv = stock.get_effective_intrinsic_value()
        
        # Should default to EPS
        assert effective_iv == Decimal('120.00')
```

**Run tests**:
```bash
just test scanner/tests/test_scanner_models.py::TestCuratedStockValuationMethods
```

### Step 2: Add integration tests for valuation_list_view

Add comprehensive tests for the new valuation page view.

**File to modify**: `scanner/tests/test_scanner_views.py`

**Add tests** (at end of file or in appropriate test class):

```python
class TestValuationListView:
    """Tests for the valuation list view."""
    
    def test_valuation_list_requires_authentication(self, client):
        """Valuation list view requires user to be logged in."""
        response = client.get('/scanner/valuations/')
        
        # Should redirect to login
        assert response.status_code == 302
        assert '/account/login/' in response.url
    
    def test_valuation_list_authenticated(self, client, user):
        """Authenticated user can access valuation list."""
        client.force_login(user)
        
        response = client.get('/scanner/valuations/')
        
        # Should succeed
        assert response.status_code == 200
        assert 'scanner/valuations.html' in [t.name for t in response.templates]
    
    def test_valuation_list_shows_active_stocks_only(self, client, user):
        """Valuation list shows only active curated stocks."""
        from scanner.factories import CuratedStockFactory
        
        # Create active and inactive stocks
        active1 = CuratedStockFactory(symbol='AAPL', is_active=True)
        active2 = CuratedStockFactory(symbol='MSFT', is_active=True)
        inactive = CuratedStockFactory(symbol='INACTIVE', is_active=False)
        
        client.force_login(user)
        response = client.get('/scanner/valuations/')
        
        stocks = response.context['stocks']
        
        # Should include active stocks
        assert active1 in stocks
        assert active2 in stocks
        
        # Should NOT include inactive stock
        assert inactive not in stocks
    
    def test_valuation_list_ordered_by_symbol(self, client, user):
        """Valuation list is ordered alphabetically by symbol."""
        from scanner.factories import CuratedStockFactory
        
        # Create stocks in non-alphabetical order
        CuratedStockFactory(symbol='TSLA', is_active=True)
        CuratedStockFactory(symbol='AAPL', is_active=True)
        CuratedStockFactory(symbol='MSFT', is_active=True)
        
        client.force_login(user)
        response = client.get('/scanner/valuations/')
        
        stocks = response.context['stocks']
        symbols = [stock.symbol for stock in stocks]
        
        # Should be in alphabetical order
        assert symbols == sorted(symbols)
    
    def test_valuation_list_context_includes_stocks(self, client, user):
        """Valuation list context includes stocks queryset."""
        from scanner.factories import CuratedStockFactory
        
        stock = CuratedStockFactory(symbol='AAPL', is_active=True)
        
        client.force_login(user)
        response = client.get('/scanner/valuations/')
        
        # Should have stocks in context
        assert 'stocks' in response.context
        
        stocks = response.context['stocks']
        assert stocks.count() > 0
        assert stock in stocks
    
    def test_valuation_list_handles_no_stocks(self, client, user):
        """Valuation list handles case with no active stocks."""
        from scanner.models import CuratedStock
        
        # Deactivate all stocks
        CuratedStock.objects.update(is_active=False)
        
        client.force_login(user)
        response = client.get('/scanner/valuations/')
        
        # Should still succeed with empty queryset
        assert response.status_code == 200
        assert response.context['stocks'].count() == 0
    
    def test_valuation_list_displays_intrinsic_values(self, client, user):
        """Valuation list can display stocks with NULL intrinsic values."""
        from decimal import Decimal
        from scanner.factories import CuratedStockFactory
        
        # Stock with values
        stock_with_values = CuratedStockFactory(
            symbol='AAPL',
            intrinsic_value=Decimal('150.00'),
            intrinsic_value_fcf=Decimal('148.00'),
            is_active=True
        )
        
        # Stock with NULL values
        stock_without_values = CuratedStockFactory(
            symbol='NEW',
            intrinsic_value=None,
            intrinsic_value_fcf=None,
            is_active=True
        )
        
        client.force_login(user)
        response = client.get('/scanner/valuations/')
        
        # Should succeed without errors
        assert response.status_code == 200
        
        stocks = response.context['stocks']
        assert stock_with_values in stocks
        assert stock_without_values in stocks
```

**Run tests**:
```bash
just test scanner/tests/test_scanner_views.py::TestValuationListView
```

### Step 3: Add integration tests for scanner views with intrinsic value context

Test that scanner views include intrinsic value context correctly.

**File to modify**: `scanner/tests/test_scanner_views.py`

**Add tests** (in existing test class or new class):

```python
class TestScannerViewsIntrinsicValueContext:
    """Tests for intrinsic value context in scanner views."""
    
    def test_scan_status_includes_curated_stocks_context(self, client, user):
        """scan_status view includes curated_stocks in context."""
        from scanner.factories import CuratedStockFactory
        from django.core.cache import cache
        
        # Create curated stock
        stock = CuratedStockFactory(symbol='AAPL', is_active=True)
        
        # Set up scan results in cache
        cache.set('options_scan_results', {
            'AAPL': [
                {'strike': 145.0, 'expiration': '2025-12-19', 'price': 2.5}
            ]
        })
        cache.set('options_scan_complete', True)
        
        client.force_login(user)
        response = client.get('/scanner/scan/status/')
        
        # Should include curated_stocks in context
        assert 'curated_stocks' in response.context
        
        curated_stocks = response.context['curated_stocks']
        assert 'AAPL' in curated_stocks
        assert curated_stocks['AAPL'] == stock
    
    def test_curated_stocks_context_empty_results(self, client, user):
        """curated_stocks context is empty dict when no scan results."""
        from django.core.cache import cache
        
        # Clear cache
        cache.delete('options_scan_results')
        
        client.force_login(user)
        response = client.get('/scanner/scan/status/')
        
        # Should have empty dict for curated_stocks
        assert 'curated_stocks' in response.context
        assert response.context['curated_stocks'] == {}
    
    def test_curated_stocks_context_multiple_symbols(self, client, user):
        """curated_stocks context includes all symbols from results."""
        from scanner.factories import CuratedStockFactory
        from django.core.cache import cache
        
        # Create multiple stocks
        stock1 = CuratedStockFactory(symbol='AAPL', is_active=True)
        stock2 = CuratedStockFactory(symbol='MSFT', is_active=True)
        stock3 = CuratedStockFactory(symbol='TSLA', is_active=True)
        
        # Set up scan results with multiple symbols
        cache.set('options_scan_results', {
            'AAPL': [{'strike': 145.0}],
            'MSFT': [{'strike': 200.0}],
            'TSLA': [{'strike': 100.0}]
        })
        
        client.force_login(user)
        response = client.get('/scanner/scan/status/')
        
        curated_stocks = response.context['curated_stocks']
        
        # Should include all three stocks
        assert len(curated_stocks) == 3
        assert curated_stocks['AAPL'] == stock1
        assert curated_stocks['MSFT'] == stock2
        assert curated_stocks['TSLA'] == stock3
    
    def test_curated_stocks_context_ignores_inactive(self, client, user):
        """curated_stocks context excludes inactive stocks."""
        from scanner.factories import CuratedStockFactory
        from django.core.cache import cache
        
        # Create active and inactive stocks
        active_stock = CuratedStockFactory(symbol='AAPL', is_active=True)
        inactive_stock = CuratedStockFactory(symbol='INACTIVE', is_active=False)
        
        # Results include both symbols (shouldn't happen, but test edge case)
        cache.set('options_scan_results', {
            'AAPL': [{'strike': 145.0}],
            'INACTIVE': [{'strike': 50.0}]
        })
        
        client.force_login(user)
        response = client.get('/scanner/scan/status/')
        
        curated_stocks = response.context['curated_stocks']
        
        # Should only include active stock
        assert 'AAPL' in curated_stocks
        assert 'INACTIVE' not in curated_stocks
```

**Run tests**:
```bash
just test scanner/tests/test_scanner_views.py::TestScannerViewsIntrinsicValueContext
```

### Step 4: Manual testing checklist for complete feature

Perform thorough manual testing of all Phase 5 features.

**Setup test environment**:

```bash
# Ensure test data exists
just exec python manage.py shell
```

```python
from scanner.models import CuratedStock
from decimal import Decimal
from django.utils import timezone

# Create test stocks with various IV states

# Stock 1: Both EPS and FCF values, EPS preferred
stock1 = CuratedStock.objects.filter(symbol='AAPL').first()
if stock1:
    stock1.intrinsic_value = Decimal('150.00')
    stock1.intrinsic_value_fcf = Decimal('148.00')
    stock1.preferred_valuation_method = 'eps'
    stock1.last_calculation_date = timezone.now()
    stock1.save()

# Stock 2: Both values, FCF preferred
stock2 = CuratedStock.objects.filter(symbol='MSFT').first()
if stock2:
    stock2.intrinsic_value = Decimal('200.00')
    stock2.intrinsic_value_fcf = Decimal('195.00')
    stock2.preferred_valuation_method = 'fcf'
    stock2.last_calculation_date = timezone.now()
    stock2.save()

# Stock 3: NULL intrinsic values (never calculated)
stock3 = CuratedStock.objects.filter(symbol='TSLA').first()
if stock3:
    stock3.intrinsic_value = None
    stock3.intrinsic_value_fcf = None
    stock3.last_calculation_date = None
    stock3.save()

print("Test data setup complete!")
```

**Manual Testing Checklist**:

**A. Scanner Page - Visual Indicators**

- [ ] **Navigate to scanner page** (`/scanner/`)
- [ ] **Click "Scan for Options"** button
- [ ] **Wait for scan to complete**
- [ ] **Verify accordion headers show badges**:
  - [ ] Green ✓ badge for stocks with at least one option strike ≤ IV
  - [ ] Red ✗ badge for stocks with all options strike > IV
  - [ ] Yellow ⚠ badge for stocks with NULL IV
- [ ] **Expand accordion for stock with good options**:
  - [ ] Verify green "✓ Good" badges on options with strike ≤ IV
  - [ ] Verify red "✗ High" badges on options with strike > IV
- [ ] **Expand accordion for stock with NULL IV**:
  - [ ] Verify all options show yellow "⚠ N/A" badges
- [ ] **Check table layout**:
  - [ ] New "Status" column appears first
  - [ ] Badges don't break table layout
  - [ ] Table remains responsive

**B. Valuations Page - Display**

- [ ] **Navigate via navbar dropdown**:
  - [ ] Click "Scanner" dropdown in navbar
  - [ ] Click "Stock Valuations" link
  - [ ] Page loads successfully
- [ ] **Verify table content**:
  - [ ] All active stocks displayed
  - [ ] Columns: Ticker, Company, IV (EPS), IV (FCF), Preferred, Last Calc, Assumptions
  - [ ] Data formatted correctly (currency, percentages, dates)
- [ ] **Verify NULL value handling**:
  - [ ] Stocks with NULL IV show "-"
  - [ ] Stocks never calculated show "Never" for date
  - [ ] No errors or blank cells
- [ ] **Check preferred method badges**:
  - [ ] EPS badge shows blue "EPS"
  - [ ] FCF badge shows light blue "FCF"
  - [ ] Badges are clear and readable

**C. Navigation**

- [ ] **Navbar dropdown**:
  - [ ] Dropdown toggle works (click to open/close)
  - [ ] "Options Scanner" link goes to `/scanner/`
  - [ ] "Stock Valuations" link goes to `/scanner/valuations/`
  - [ ] Dropdown works in mobile view (collapsed navbar)
- [ ] **Authentication**:
  - [ ] Logout and try to access `/scanner/valuations/`
  - [ ] Should redirect to login page
  - [ ] Login and verify access works

**D. Responsive Design**

- [ ] **Desktop (>992px)**:
  - [ ] Scanner table displays all columns without scroll
  - [ ] Valuations table displays all columns clearly
  - [ ] Badges are appropriately sized
- [ ] **Tablet (768px - 991px)**:
  - [ ] Tables use horizontal scroll if needed
  - [ ] Navbar collapses to hamburger
  - [ ] Content remains readable
- [ ] **Mobile (<768px)**:
  - [ ] Tables scroll horizontally (expected)
  - [ ] Badges still visible and clear
  - [ ] Navbar hamburger works
  - [ ] Touch targets adequate size

**E. Edge Cases**

- [ ] **No active stocks**:
  - [ ] Set all stocks to `is_active=False`
  - [ ] Visit valuations page
  - [ ] Should show "No active stocks" message
- [ ] **Scan finds no options**:
  - [ ] Trigger scan that finds nothing
  - [ ] Should handle gracefully (no errors)
- [ ] **Stock not in curated list** (if possible):
  - [ ] Verify gray "-" badge appears

**F. Browser Compatibility**

- [ ] **Chrome**: All features work
- [ ] **Firefox**: All features work
- [ ] **Safari** (if available): All features work

### Step 5: Fix any bugs or issues discovered

Document and fix any issues found during testing.

**Bug tracking template**:

```markdown
## Bug: [Brief description]

**Severity**: High / Medium / Low

**Steps to reproduce**:
1. Step 1
2. Step 2
3. Step 3

**Expected behavior**:
What should happen

**Actual behavior**:
What actually happens

**Fix**:
How it was fixed

**Files modified**:
- file1.py
- file2.html
```

**Common issues to watch for**:

1. **Template syntax errors**:
   - Missing `{% endwith %}` or `{% endif %}`
   - Incorrect template tag usage
   - Fix: Review template syntax carefully

2. **Context key errors**:
   - `curated_stocks` not in context
   - Fix: Ensure views add context correctly

3. **NULL comparison issues**:
   - Comparing None with Decimal fails
   - Fix: Check for None before comparison

4. **Bootstrap dropdown not working**:
   - Missing Bootstrap JS
   - Fix: Ensure Bootstrap JS is included in base.html

5. **Badge alignment issues**:
   - Badges break layout
   - Fix: Add custom CSS for alignment

**Testing after fixes**:
- Re-run automated tests
- Re-check manual testing checklist
- Verify fix doesn't break other features

## Acceptance Criteria

### Unit Test Requirements

- [ ] All 6 unit tests for `get_effective_intrinsic_value()` pass
- [ ] Tests cover EPS method, FCF method, NULL values, and edge cases
- [ ] Tests use proper pytest fixtures and factories

### Integration Test Requirements

- [ ] All 7 valuation list view tests pass
- [ ] All 4 scanner view context tests pass
- [ ] Tests cover authentication, data filtering, and context content
- [ ] Tests handle edge cases (no stocks, NULL values)

### Manual Testing Requirements

- [ ] All items in manual testing checklist completed
- [ ] Scanner page badges display correctly
- [ ] Valuations page displays all data correctly
- [ ] Navigation works on all devices
- [ ] Responsive design verified on multiple screen sizes
- [ ] No errors in browser console
- [ ] No errors in Django logs

### Bug Fix Requirements

- [ ] All discovered bugs documented
- [ ] All high and medium severity bugs fixed
- [ ] All fixes tested and verified
- [ ] No regressions introduced by fixes

### Overall Requirements

- [ ] All automated tests pass
- [ ] Manual testing completed successfully
- [ ] No breaking changes to existing functionality
- [ ] Code follows project conventions
- [ ] Performance is acceptable

## Files Involved

### Modified Test Files

- `scanner/tests/test_scanner_models.py`
  - Add `TestCuratedStockValuationMethods` class with 6 tests

- `scanner/tests/test_scanner_views.py`
  - Add `TestValuationListView` class with 7 tests
  - Add `TestScannerViewsIntrinsicValueContext` class with 4 tests

### Potentially Modified Files (Bug Fixes)

- `scanner/views.py` - Fix context issues
- `scanner/models.py` - Fix method issues
- `templates/scanner/partials/options_results.html` - Fix template issues
- `templates/scanner/valuations.html` - Fix display issues
- `static/css/styles.css` - Fix styling issues

## Notes

### Test Data Management

**Using factories**:
- Use `CuratedStockFactory` for consistent test data
- Set specific values for intrinsic value testing
- Clean up test data in fixtures (handled by pytest-django)

**Test isolation**:
- Each test should be independent
- Use pytest fixtures for setup/teardown
- Database rolled back after each test

### pytest vs unittest

**This project uses pytest**:
- Test methods don't need `self.assert*`
- Use plain `assert` statements
- Fixtures via function arguments
- More concise test code

**Example**:
```python
# pytest style (use this)
def test_something(client, user):
    assert value == expected

# unittest style (don't use)
def test_something(self):
    self.assertEqual(value, expected)
```

### Running Specific Tests

```bash
# Run all Phase 5 tests
just test scanner/tests/test_scanner_models.py::TestCuratedStockValuationMethods
just test scanner/tests/test_scanner_views.py::TestValuationListView
just test scanner/tests/test_scanner_views.py::TestScannerViewsIntrinsicValueContext

# Run single test
just test scanner/tests/test_scanner_models.py::TestCuratedStockValuationMethods::test_get_effective_intrinsic_value_eps_method

# Run all scanner tests
just test scanner/tests/

# Run with verbose output
just test scanner/tests/ -v

# Run with print statements visible
just test scanner/tests/ -s
```

### Manual Testing Best Practices

**Use different user accounts**:
- Test with different permission levels
- Verify authentication works correctly

**Test data variety**:
- Stocks with various IV states
- Different preferred methods
- Recent and old calculation dates

**Browser dev tools**:
- Check console for JavaScript errors
- Inspect network tab for failed requests
- Use responsive design mode for mobile testing

**Screenshot comparisons**:
- Take screenshots of working state
- Compare after changes to detect visual regressions

## Dependencies

- Requires Tasks 024, 025, 026, 027 completed
- Uses pytest-django for testing
- Uses factory_boy for test factories
- Requires test database (configured in settings)

## Reference

**pytest Documentation**:
- Fixtures: https://docs.pytest.org/en/stable/fixture.html
- Assertions: https://docs.pytest.org/en/stable/assert.html

**pytest-django**:
- https://pytest-django.readthedocs.io/

**Django Testing**:
- Test client: https://docs.djangoproject.com/en/5.1/topics/testing/tools/#the-test-client
- Testing views: https://docs.djangoproject.com/en/5.1/topics/testing/tools/#testing-views

**factory_boy**:
- https://factoryboy.readthedocs.io/
