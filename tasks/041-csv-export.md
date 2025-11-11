# Task 041: CSV Export Functionality

## Progress Summary

**Status**: Not Started

- [ ] Step 1: Implement export_valuation_history_csv view
- [ ] Step 2: Add URL routing for CSV export
- [ ] Step 3: Write CSV export integration tests
- [ ] Step 4: Test CSV format and encoding
- [ ] Step 5: Test with large datasets
- [ ] Step 6: Manual download testing

## Overview

Implement CSV export functionality for valuation history, allowing users to download complete historical data for external analysis (Excel, Google Sheets, Python, R). The view will generate CSV files with all fields from the ValuationHistory model, supporting both single-stock and all-stocks exports.

**Current State**:
- Historical data stored in database
- UI has export buttons (Tasks 038, 040)
- No export mechanism implemented
- Buttons 404 when clicked

**Target State**:
- View generates CSV files on-demand
- Single-stock export: `/scanner/valuations/export/<symbol>/`
- All-stocks export: `/scanner/valuations/export/`
- Proper CSV formatting with headers
- Browser triggers download automatically
- Login required for access

## High-Level Specifications

### View Features

- **Function**: `export_valuation_history_csv(request, symbol=None)`
- **URLs**:
  - Single stock: `/scanner/valuations/export/<symbol>/`
  - All stocks: `/scanner/valuations/export/`
- **Authentication**: `@login_required`
- **Response**: CSV file download (Content-Type: text/csv)
- **Filename convention**:
  - Single: `valuation_history_AAPL_2025-11-11.csv`
  - All: `valuation_history_all_2025-11-11.csv`

### CSV Format

**Headers** (16 columns):
- Symbol, Quarter, Snapshot Date, Calculated At
- Intrinsic Value (EPS), Current EPS, EPS Growth Rate (%), EPS Multiple
- Intrinsic Value (FCF), Current FCF/Share, FCF Growth Rate (%), FCF Multiple
- Desired Return (%), Projection Years, Preferred Method, Notes

**Data rows**:
- One row per ValuationHistory snapshot
- Ordered by symbol (asc), snapshot_date (desc)
- NULL values output as empty strings
- Dates in ISO format (YYYY-MM-DD)
- Timestamps in YYYY-MM-DD HH:MM:SS format

## Relevant Files

### Files to Create
- None (adding to existing files)

### Files to Modify
- `scanner/views.py` - Add `export_valuation_history_csv` function
- `scanner/urls.py` - Add 2 URL patterns for export

### Files for Testing
- `scanner/tests/test_csv_export.py` - New test file with 6+ tests

## Acceptance Criteria

### View Implementation
- [ ] `export_valuation_history_csv` function defined
- [ ] `@login_required` decorator applied
- [ ] Takes optional `symbol` parameter
- [ ] Filters by symbol if provided, else all stocks
- [ ] Filters for active stocks only
- [ ] Creates HttpResponse with CSV content type
- [ ] Generates proper filename with date
- [ ] Writes CSV headers
- [ ] Writes data rows for all snapshots
- [ ] Orders by stock symbol, then snapshot date descending
- [ ] Logging at INFO level

### URL Configuration
- [ ] URL pattern for single stock: `valuations/export/<str:symbol>/`
- [ ] URL pattern for all stocks: `valuations/export/`
- [ ] URL names: `export_stock_history`, `export_all_history`
- [ ] Follows scanner namespace

### CSV Format
- [ ] Headers match specification (16 columns)
- [ ] Data rows match headers (correct column order)
- [ ] NULL values render as empty strings
- [ ] Dates in ISO format (YYYY-MM-DD)
- [ ] No special characters causing CSV parsing errors
- [ ] Proper CSV escaping (quotes, commas in text fields)

### Testing Requirements
- [ ] Test: Single stock export returns CSV
- [ ] Test: All stocks export returns CSV
- [ ] Test: CSV has correct headers
- [ ] Test: CSV has correct number of rows
- [ ] Test: Requires authentication
- [ ] Test: 404 for nonexistent symbol
- [ ] Test: Handles stocks with no history
- [ ] All 6+ tests pass

### File Download
- [ ] Browser triggers download (doesn't display in browser)
- [ ] Filename includes stock symbol and date
- [ ] File opens correctly in Excel/Google Sheets
- [ ] No encoding issues (UTF-8)

### Performance
- [ ] Export completes in <1s for 100 snapshots
- [ ] Export completes in <3s for 1000 snapshots
- [ ] No memory issues with large datasets

## Implementation Steps

### Step 1: Implement export_valuation_history_csv view

Add the CSV export view function.

**File to modify**: `scanner/views.py`

**Add after `valuation_comparison_view`**:

```python
@login_required
def export_valuation_history_csv(request, symbol=None):
    """
    Export valuation history to CSV.

    Args:
        symbol: Optional stock symbol. If None, exports all stocks.

    Returns:
        CSV file download (HttpResponse with text/csv content type)
    """
    import csv
    from django.http import HttpResponse

    # Build filename
    if symbol:
        filename = f"valuation_history_{symbol.upper()}_{date.today().isoformat()}.csv"
        stocks = CuratedStock.objects.filter(symbol=symbol.upper(), active=True)

        if not stocks.exists():
            # Return 404 if symbol not found
            raise Http404(f"Stock '{symbol}' not found")

        logger.info(f"CSV export requested by {request.user.username} for {symbol}")
    else:
        filename = f"valuation_history_all_{date.today().isoformat()}.csv"
        stocks = CuratedStock.objects.filter(active=True).order_by('symbol')
        logger.info(f"CSV export (all stocks) requested by {request.user.username}")

    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)

    # Write header
    writer.writerow([
        'Symbol',
        'Quarter',
        'Snapshot Date',
        'Calculated At',
        'Intrinsic Value (EPS)',
        'Current EPS',
        'EPS Growth Rate (%)',
        'EPS Multiple',
        'Intrinsic Value (FCF)',
        'Current FCF/Share',
        'FCF Growth Rate (%)',
        'FCF Multiple',
        'Desired Return (%)',
        'Projection Years',
        'Preferred Method',
        'Notes',
    ])

    # Write data rows
    for stock in stocks:
        history = ValuationHistory.objects.filter(stock=stock).order_by('-snapshot_date')

        for snapshot in history:
            writer.writerow([
                stock.symbol,
                snapshot.quarter_label,
                snapshot.snapshot_date.isoformat(),
                snapshot.calculated_at.strftime('%Y-%m-%d %H:%M:%S'),
                snapshot.intrinsic_value if snapshot.intrinsic_value is not None else '',
                snapshot.current_eps if snapshot.current_eps is not None else '',
                snapshot.eps_growth_rate,
                snapshot.eps_multiple,
                snapshot.intrinsic_value_fcf if snapshot.intrinsic_value_fcf is not None else '',
                snapshot.current_fcf_per_share if snapshot.current_fcf_per_share is not None else '',
                snapshot.fcf_growth_rate,
                snapshot.fcf_multiple,
                snapshot.desired_return,
                snapshot.projection_years,
                snapshot.preferred_valuation_method,
                snapshot.notes,
            ])

    logger.info(f"CSV export complete: {filename}")

    return response
```

**Add import at top** (if not present):
```python
from django.http import Http404
```

**Verify Python syntax**:
```bash
uv run python -m py_compile scanner/views.py
```

### Step 2: Add URL routing for CSV export

Add URL patterns for both export modes.

**File to modify**: `scanner/urls.py`

**Add to urlpatterns** (after comparison URL):

```python
urlpatterns = [
    # ... existing URLs ...

    # Historical valuation URLs
    path('valuations/history/<str:symbol>/', views.stock_history_view, name='stock_history'),
    path('valuations/comparison/', views.valuation_comparison_view, name='valuation_comparison'),

    # CSV export URLs
    path('valuations/export/', views.export_valuation_history_csv, name='export_all_history'),
    path('valuations/export/<str:symbol>/', views.export_valuation_history_csv, name='export_stock_history'),
]
```

**Verify URL configuration**:
```bash
uv run python manage.py show_urls | grep export
```

**Expected**: Both export URLs visible

### Step 3: Write CSV export integration tests

Create comprehensive tests for CSV export.

**File to create**: `scanner/tests/test_csv_export.py`

**Content**:
```python
"""
Tests for CSV export functionality.

Test coverage:
- Single stock export
- All stocks export
- CSV headers correct
- CSV data rows correct
- Authentication required
- 404 for nonexistent symbol
- Handles stocks with no history
"""

import pytest
from datetime import date
from decimal import Decimal
from django.urls import reverse
import csv
from io import StringIO

from scanner.models import CuratedStock, ValuationHistory


@pytest.mark.django_db
class TestCSVExport:
    """Tests for CSV export views."""

    def test_single_stock_export_returns_csv(self, client, user):
        """Test single stock export returns CSV file."""
        client.force_login(user)

        # Create stock with history
        stock = CuratedStock.objects.create(
            symbol="AAPL",
            active=True,
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

        url = reverse('scanner:export_stock_history', kwargs={'symbol': 'AAPL'})
        response = client.get(url)

        assert response.status_code == 200
        assert response['Content-Type'] == 'text/csv'
        assert 'attachment' in response['Content-Disposition']
        assert 'valuation_history_AAPL' in response['Content-Disposition']

    def test_all_stocks_export_returns_csv(self, client, user):
        """Test all stocks export returns CSV file."""
        client.force_login(user)

        # Create multiple stocks with history
        for symbol in ['AAPL', 'MSFT']:
            stock = CuratedStock.objects.create(
                symbol=symbol,
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

        url = reverse('scanner:export_all_history')
        response = client.get(url)

        assert response.status_code == 200
        assert response['Content-Type'] == 'text/csv'
        assert 'valuation_history_all' in response['Content-Disposition']

    def test_csv_has_correct_headers(self, client, user):
        """Test CSV file has correct header row."""
        client.force_login(user)

        stock = CuratedStock.objects.create(symbol="AAPL", active=True)
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

        url = reverse('scanner:export_stock_history', kwargs={'symbol': 'AAPL'})
        response = client.get(url)

        # Parse CSV
        csv_content = response.content.decode('utf-8')
        reader = csv.reader(StringIO(csv_content))
        headers = next(reader)

        assert headers[0] == 'Symbol'
        assert headers[1] == 'Quarter'
        assert headers[2] == 'Snapshot Date'
        assert headers[3] == 'Calculated At'
        assert headers[4] == 'Intrinsic Value (EPS)'
        assert len(headers) == 16

    def test_csv_has_correct_number_of_rows(self, client, user):
        """Test CSV file has correct number of data rows."""
        client.force_login(user)

        stock = CuratedStock.objects.create(symbol="AAPL", active=True)

        # Create 3 snapshots
        for i in range(3):
            ValuationHistory.objects.create(
                stock=stock,
                snapshot_date=date(2024 + i, 1, 1),
                eps_growth_rate=Decimal("10.0"),
                eps_multiple=Decimal("20.0"),
                fcf_growth_rate=Decimal("10.0"),
                fcf_multiple=Decimal("20.0"),
                desired_return=Decimal("15.0"),
                projection_years=5,
            )

        url = reverse('scanner:export_stock_history', kwargs={'symbol': 'AAPL'})
        response = client.get(url)

        # Parse CSV
        csv_content = response.content.decode('utf-8')
        reader = csv.reader(StringIO(csv_content))
        rows = list(reader)

        # 1 header + 3 data rows = 4 total
        assert len(rows) == 4

    def test_export_requires_authentication(self, client):
        """Test CSV export requires login."""
        url = reverse('scanner:export_all_history')
        response = client.get(url)

        # Should redirect to login
        assert response.status_code == 302
        assert '/accounts/login/' in response.url

    def test_export_returns_404_for_nonexistent_symbol(self, client, user):
        """Test 404 returned for nonexistent stock symbol."""
        client.force_login(user)

        url = reverse('scanner:export_stock_history', kwargs={'symbol': 'NONEXISTENT'})
        response = client.get(url)

        assert response.status_code == 404

    def test_handles_stocks_with_no_history(self, client, user):
        """Test CSV export handles stocks with no history gracefully."""
        client.force_login(user)

        # Create stock with no history
        CuratedStock.objects.create(symbol="NEWSTOCK", active=True)

        url = reverse('scanner:export_stock_history', kwargs={'symbol': 'NEWSTOCK'})
        response = client.get(url)

        assert response.status_code == 200

        # Parse CSV
        csv_content = response.content.decode('utf-8')
        reader = csv.reader(StringIO(csv_content))
        rows = list(reader)

        # Only header row, no data rows
        assert len(rows) == 1  # Just headers

    def test_csv_data_values_correct(self, client, user):
        """Test CSV contains correct data values."""
        client.force_login(user)

        stock = CuratedStock.objects.create(symbol="TEST", active=True)
        snapshot = ValuationHistory.objects.create(
            stock=stock,
            snapshot_date=date(2025, 1, 1),
            intrinsic_value=Decimal("150.25"),
            current_eps=Decimal("6.42"),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            intrinsic_value_fcf=Decimal("148.50"),
            current_fcf_per_share=Decimal("7.20"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
            preferred_valuation_method="EPS",
            notes="Test note",
        )

        url = reverse('scanner:export_stock_history', kwargs={'symbol': 'TEST'})
        response = client.get(url)

        # Parse CSV
        csv_content = response.content.decode('utf-8')
        reader = csv.reader(StringIO(csv_content))
        rows = list(reader)

        # Check data row
        data_row = rows[1]
        assert data_row[0] == 'TEST'  # Symbol
        assert data_row[1] == 'Q1 2025'  # Quarter
        assert data_row[2] == '2025-01-01'  # Snapshot Date
        assert '150.25' in data_row[4]  # Intrinsic Value (EPS)
        assert '6.42' in data_row[5]  # Current EPS
        assert 'EPS' in data_row[14]  # Preferred Method
        assert 'Test note' in data_row[15]  # Notes


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
just test scanner/tests/test_csv_export.py -v
```

**Expected**: All 8 tests pass

### Step 4: Test CSV format and encoding

Verify CSV format is correct and opens properly in Excel/Google Sheets.

**Download test CSV**:
```bash
# Start server
just run

# Login and download via browser:
# http://localhost:8000/scanner/valuations/export/
```

**Verify in Excel/Google Sheets**:
1. Open downloaded CSV file
2. Check columns align correctly
3. Check special characters display properly
4. Check dates are formatted correctly
5. Check numbers are numeric (not text)

**Test special characters**:
```bash
uv run python manage.py shell

>>> from scanner.models import CuratedStock, ValuationHistory
>>> from datetime import date
>>> from decimal import Decimal

>>> stock = CuratedStock.objects.create(symbol="TEST", active=True)
>>> ValuationHistory.objects.create(
...     stock=stock,
...     snapshot_date=date(2025, 1, 1),
...     eps_growth_rate=Decimal("10.0"),
...     eps_multiple=Decimal("20.0"),
...     fcf_growth_rate=Decimal("10.0"),
...     fcf_multiple=Decimal("20.0"),
...     desired_return=Decimal("15.0"),
...     projection_years=5,
...     notes='Test with comma, "quotes", and newline\ncharacters'
... )
>>> exit()
```

**Download and verify**:
- Comma in notes should not break columns
- Quotes should be escaped properly
- Newline should be escaped or removed

**Cleanup**:
```bash
uv run python manage.py shell
>>> from scanner.models import CuratedStock
>>> CuratedStock.objects.filter(symbol="TEST").delete()
>>> exit()
```

### Step 5: Test with large datasets

Verify performance with many snapshots.

**Create large dataset**:
```bash
uv run python manage.py shell

>>> from scanner.models import CuratedStock, ValuationHistory
>>> from datetime import date
>>> from decimal import Decimal

>>> # Create stock with 100 snapshots
>>> stock = CuratedStock.objects.create(symbol="TESTBIG", active=True)

>>> for year in range(2000, 2025):
...     for quarter in [1, 4, 7, 10]:
...         ValuationHistory.objects.create(
...             stock=stock,
...             snapshot_date=date(year, quarter, 1),
...             intrinsic_value=Decimal("100.00"),
...             eps_growth_rate=Decimal("10.0"),
...             eps_multiple=Decimal("20.0"),
...             fcf_growth_rate=Decimal("10.0"),
...             fcf_multiple=Decimal("20.0"),
...             desired_return=Decimal("15.0"),
...             projection_years=5,
...         )

>>> print(f"Created {ValuationHistory.objects.filter(stock=stock).count()} snapshots")
>>> exit()
```

**Test export performance**:
```bash
# Time the export
time curl -s http://localhost:8000/scanner/valuations/export/TESTBIG/ -H "Cookie: sessionid=..." > test.csv

# Expected: <1 second for 100 snapshots
```

**Check file size**:
```bash
ls -lh test.csv
# Should be reasonable size (<50 KB for 100 rows)
```

**Cleanup**:
```bash
uv run python manage.py shell
>>> from scanner.models import CuratedStock
>>> CuratedStock.objects.filter(symbol="TESTBIG").delete()
>>> exit()

rm test.csv
```

### Step 6: Manual download testing

Comprehensive manual testing of download functionality.

**Test Checklist**:
```
Single Stock Export:
[ ] Navigate to stock history page
[ ] Click "Export CSV" button
[ ] Browser triggers download (doesn't open in browser)
[ ] Filename includes stock symbol and today's date
[ ] File downloads to default download folder
[ ] File opens correctly in Excel
[ ] All columns visible and aligned
[ ] Data looks correct

All Stocks Export:
[ ] Navigate to valuations page
[ ] Click "Export All CSV" button (if implemented in UI)
[ ] Navigate to comparison report page
[ ] Click "Export All CSV" button
[ ] Browser triggers download
[ ] Filename includes "all" and today's date
[ ] File contains data for all active stocks
[ ] Stocks ordered alphabetically

Edge Cases:
[ ] Export stock with no history (only headers)
[ ] Export with NULL intrinsic values (empty cells)
[ ] Export with special characters in notes
[ ] Export immediately after creating snapshot
[ ] Export from multiple browsers (Chrome, Firefox, Safari)
[ ] Export on mobile device (if applicable)
```

**Verify all tests pass**:
```bash
just test
```

**Expected**: All 254+ tests pass (248 existing + 8 new)

## Summary of Changes

[Leave empty - will be filled during implementation]

## Notes

### CSV Format Standards

**RFC 4180 compliance**:
- Fields separated by commas
- Records separated by newlines (CRLF or LF)
- Fields with commas/quotes/newlines enclosed in quotes
- Quotes escaped by doubling (`""`)

**Python csv module**:
- Automatically handles escaping
- Produces RFC 4180 compliant output
- No manual escaping needed

**Example**:
```csv
Symbol,Notes
AAPL,"Test with comma, ""quotes"", and newline"
```

### Content-Disposition Header

**Purpose**: Tells browser to download instead of display

**Format**:
```
Content-Disposition: attachment; filename="valuation_history_AAPL_2025-11-11.csv"
```

**Effect**:
- Browser triggers download dialog
- File saved with specified filename
- Doesn't open in browser tab

### Filename Convention

**Pattern**:
- Single: `valuation_history_{SYMBOL}_{DATE}.csv`
- All: `valuation_history_all_{DATE}.csv`

**Examples**:
- `valuation_history_AAPL_2025-11-11.csv`
- `valuation_history_all_2025-11-11.csv`

**Why include date?**:
- Multiple downloads don't overwrite
- Clear which data snapshot
- Sortable filenames

### NULL Value Handling

**In CSV**:
- NULL → empty string `''`
- Not "None" or "NULL" text
- Allows Excel to treat as empty cell

**Implementation**:
```python
snapshot.intrinsic_value if snapshot.intrinsic_value is not None else ''
```

**Effect in Excel**:
- Empty cells (not text)
- Can use SUM() functions
- Can filter for blanks

### Date Formatting

**Snapshot Date**: ISO format (YYYY-MM-DD)
- Example: `2025-01-01`
- Sortable
- Unambiguous (no US vs EU confusion)

**Calculated At**: Timestamp format (YYYY-MM-DD HH:MM:SS)
- Example: `2025-01-01 23:15:32`
- Includes time for precise tracking

**Implementation**:
```python
snapshot.snapshot_date.isoformat()  # 2025-01-01
snapshot.calculated_at.strftime('%Y-%m-%d %H:%M:%S')  # 2025-01-01 23:15:32
```

### Performance Optimization

**Current approach** (simple):
```python
for stock in stocks:
    history = ValuationHistory.objects.filter(stock=stock).order_by('-snapshot_date')
    for snapshot in history:
        writer.writerow([...])
```

**Trade-offs**:
- N+1 queries (one per stock)
- Simple to understand
- Acceptable for <100 stocks

**Optimized approach** (if needed):
```python
# Single query with select_related
history = ValuationHistory.objects.filter(
    stock__active=True
).select_related('stock').order_by('stock__symbol', '-snapshot_date')

for snapshot in history:
    writer.writerow([...])
```

**When to optimize**:
- If export takes >3s
- If stock count >100
- After profiling identifies bottleneck

### Use Cases for CSV Export

**Excel analysis**:
- Create pivot tables
- Calculate custom metrics
- Chart valuation trends
- Compare multiple stocks

**Google Sheets**:
- Share with team
- Collaborative analysis
- Use formulas/scripts

**Python/R analysis**:
- Import with pandas/readr
- Statistical analysis
- Machine learning models
- Custom visualizations

**Database import**:
- Load into BI tools
- Integrate with other systems
- Archive historical data

### Security Considerations

**Authentication**:
- `@login_required` prevents unauthorized access
- Users can only see their own data (if multi-tenant)

**Symbol validation**:
- Convert to uppercase
- Check exists with 404
- Prevent SQL injection (Django ORM handles this)

**File download**:
- No path traversal risk (filename generated by server)
- No user-supplied filename components
- Safe Content-Type (text/csv)

## Dependencies

- Tasks 035-040 completed (All historical features exist)
- Python csv module (built-in)
- Django HttpResponse
- CSV parsing for tests (StringIO)

## Reference

**Python csv module**:
- https://docs.python.org/3/library/csv.html

**RFC 4180 (CSV spec)**:
- https://tools.ietf.org/html/rfc4180

**Django HttpResponse**:
- https://docs.djangoproject.com/en/5.1/ref/request-response/#httpresponse-objects

**Implementation spec**:
- See: `/Users/danvigliotti/Development/Sirvig/wheel-analyzer/specs/phase-6-historical-valuations.md`
- Section 6: CSV Export
- Section 7: Testing Strategy
