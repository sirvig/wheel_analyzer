# Task 035: Create ValuationHistory Model and Migration

## Progress Summary

**Status**: Not Started

- [ ] Step 1: Add ValuationHistory model to scanner/models.py
- [ ] Step 2: Create migration with makemigrations
- [ ] Step 3: Apply migration to database
- [ ] Step 4: Register model in Django admin
- [ ] Step 5: Write model unit tests
- [ ] Step 6: Verify migration and model functionality

## Overview

Create a new Django model `ValuationHistory` to store quarterly snapshots of intrinsic value calculations for curated stocks. This model will enable historical trend analysis by capturing both valuation results (EPS and FCF) and all DCF assumptions at each quarter-end date.

**Current State**:
- `CuratedStock` model stores only current point-in-time valuations
- No historical tracking of valuation changes
- Previous calculations are overwritten when `calculate_intrinsic_value` runs

**Target State**:
- `ValuationHistory` model stores quarterly snapshots
- Captures Jan 1, Apr 1, Jul 1, Oct 1 snapshots indefinitely
- Foreign key relationship to `CuratedStock` with CASCADE delete
- Unique constraint on (stock, snapshot_date) prevents duplicates
- Indexes for efficient per-stock and date-range queries

## High-Level Specifications

### Model Structure

The `ValuationHistory` model will include:
- **Relationships**: Foreign key to `CuratedStock`
- **Snapshot Metadata**: `snapshot_date` (quarter-end), `calculated_at` (timestamp)
- **EPS Valuation**: `intrinsic_value`, `current_eps`, `eps_growth_rate`, `eps_multiple`
- **FCF Valuation**: `intrinsic_value_fcf`, `current_fcf_per_share`, `fcf_growth_rate`, `fcf_multiple`
- **Shared DCF Assumptions**: `desired_return`, `projection_years`
- **Preferences**: `preferred_valuation_method` (EPS or FCF)
- **Notes**: Optional text field for annotations

### Key Features

- **Unique Constraint**: (stock, snapshot_date) prevents duplicate snapshots
- **Database Indexes**: Optimize queries on `snapshot_date` and `(stock, snapshot_date)`
- **CASCADE Delete**: If stock deleted, all history deleted automatically
- **Helper Methods**: `get_effective_intrinsic_value()` returns value for preferred method
- **Property**: `quarter_label` returns human-readable format like "Q1 2025"
- **Ordering**: Default order by snapshot_date descending (newest first)

## Relevant Files

### Files to Create
- None (adding to existing files)

### Files to Modify
- `scanner/models.py` - Add `ValuationHistory` model class
- `scanner/admin.py` - Register `ValuationHistory` with custom admin
- `scanner/migrations/` - New migration file will be auto-generated

### Files for Testing
- `scanner/tests/test_valuation_history_model.py` - New test file with 10+ tests

## Acceptance Criteria

### Model Requirements
- [ ] `ValuationHistory` model defined in `scanner/models.py`
- [ ] All 19 fields correctly defined with appropriate types
- [ ] Foreign key to `CuratedStock` with CASCADE and related_name='valuation_history'
- [ ] Unique constraint on (stock, snapshot_date) with error message
- [ ] Three database indexes: snapshot_date, (stock, -snapshot_date), (stock, snapshot_date)
- [ ] Meta class with correct ordering, verbose names, and constraints
- [ ] `__str__` method returns "{symbol} - {snapshot_date}"
- [ ] `get_effective_intrinsic_value()` method returns correct value based on preferred method
- [ ] `quarter_label` property returns "Q1 2025" format

### Migration Requirements
- [ ] Migration file created with `makemigrations` command
- [ ] Migration named `0007_create_valuation_history` (or next in sequence)
- [ ] Migration applies successfully with `migrate` command
- [ ] Migration is reversible (can be rolled back)
- [ ] Database constraints properly created (unique, indexes)

### Admin Requirements
- [ ] `ValuationHistoryAdmin` registered in `scanner/admin.py`
- [ ] List display shows: stock symbol, quarter_label, intrinsic_value, intrinsic_value_fcf
- [ ] List filters for: snapshot_date, preferred_valuation_method
- [ ] Search by: stock__symbol
- [ ] Fieldsets organized: Snapshot Info, EPS Valuation, FCF Valuation, Shared Assumptions
- [ ] Read-only fields: calculated_at

### Testing Requirements
- [ ] Test file `test_valuation_history_model.py` created
- [ ] Test: Create snapshot with all fields
- [ ] Test: Unique constraint prevents duplicate snapshots
- [ ] Test: `get_effective_intrinsic_value()` returns EPS value when preferred
- [ ] Test: `get_effective_intrinsic_value()` returns FCF value when preferred
- [ ] Test: `quarter_label` property returns correct format for all quarters
- [ ] Test: CASCADE delete removes history when stock deleted
- [ ] Test: Default ordering is snapshot_date descending
- [ ] Test: Can query history with foreign key reverse relation
- [ ] Test: NULL intrinsic values handled gracefully
- [ ] All 10+ tests pass

## Implementation Steps

### Step 1: Add ValuationHistory model to scanner/models.py

Add the complete `ValuationHistory` model class to `scanner/models.py`.

**Location**: After the `CuratedStock` model definition (around line 250)

**Code to add**:
```python
class ValuationHistory(models.Model):
    """
    Historical record of quarterly valuation calculations for curated stocks.

    Stores quarterly snapshots (Jan 1, Apr 1, Jul 1, Oct 1) of intrinsic value
    calculations along with the DCF assumptions used at that time. This enables
    historical trend analysis and comparison of valuations over time.

    Design decisions:
    - Quarterly snapshots balance data granularity with storage efficiency
    - Store both EPS and FCF calculations for consistency with current model
    - Capture all DCF assumptions for reproducibility and assumption tracking
    - Never auto-delete (indefinite retention)
    - Foreign key to CuratedStock with CASCADE (if stock deleted, history deleted)
    """

    # Relationships
    stock = models.ForeignKey(
        'CuratedStock',
        on_delete=models.CASCADE,
        related_name='valuation_history',
        help_text="The stock this valuation history belongs to"
    )

    # Snapshot Metadata
    snapshot_date = models.DateField(
        db_index=True,  # Index for efficient date-range queries
        help_text="Quarter-end date when this snapshot was taken (Jan 1, Apr 1, Jul 1, Oct 1)"
    )

    calculated_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when this snapshot was created (may differ from snapshot_date)"
    )

    # EPS Valuation Results
    intrinsic_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Intrinsic value calculated using EPS DCF model"
    )

    current_eps = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Trailing Twelve Months EPS at time of snapshot"
    )

    eps_growth_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="EPS growth rate assumption (%) used in calculation"
    )

    eps_multiple = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Terminal value multiple applied to Year 5 EPS"
    )

    # FCF Valuation Results
    intrinsic_value_fcf = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Intrinsic value calculated using FCF DCF model"
    )

    current_fcf_per_share = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Trailing Twelve Months FCF per share at time of snapshot"
    )

    fcf_growth_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="FCF growth rate assumption (%) used in calculation"
    )

    fcf_multiple = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Terminal value multiple applied to Year 5 FCF"
    )

    # Shared DCF Assumptions
    desired_return = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Desired annual return rate (%) used as discount rate"
    )

    projection_years = models.IntegerField(
        help_text="Number of years projected in DCF model"
    )

    # Valuation Method Preference
    preferred_valuation_method = models.CharField(
        max_length=3,
        choices=[
            ("EPS", "EPS-based"),
            ("FCF", "FCF-based"),
        ],
        default="EPS",
        help_text="Preferred valuation method at time of snapshot"
    )

    # Notes
    notes = models.TextField(
        blank=True,
        help_text="Optional notes about this valuation snapshot (e.g., assumption changes)"
    )

    class Meta:
        ordering = ['-snapshot_date', 'stock__symbol']
        verbose_name = "Valuation History"
        verbose_name_plural = "Valuation Histories"
        indexes = [
            models.Index(fields=['stock', '-snapshot_date']),  # Per-stock queries
            models.Index(fields=['snapshot_date']),  # Quarterly queries
            models.Index(fields=['stock', 'snapshot_date']),  # Unique constraint support
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['stock', 'snapshot_date'],
                name='unique_stock_snapshot_date',
                violation_error_message="A valuation snapshot already exists for this stock and date."
            )
        ]

    def __str__(self):
        return f"{self.stock.symbol} - {self.snapshot_date}"

    def get_effective_intrinsic_value(self):
        """
        Get the intrinsic value based on the preferred valuation method.

        Returns:
            Decimal or None: The intrinsic value for the preferred method.
        """
        if self.preferred_valuation_method == "FCF":
            return self.intrinsic_value_fcf
        else:
            return self.intrinsic_value

    @property
    def quarter_label(self):
        """
        Return a human-readable quarter label (e.g., 'Q1 2025').

        Returns:
            str: Quarter label like 'Q1 2025', 'Q2 2025', etc.
        """
        quarter_map = {1: 'Q1', 4: 'Q2', 7: 'Q3', 10: 'Q4'}
        quarter = quarter_map.get(self.snapshot_date.month, 'Q?')
        return f"{quarter} {self.snapshot_date.year}"
```

**Verify**:
```bash
# Check Python syntax
uv run python -m py_compile scanner/models.py
```

### Step 2: Create migration with makemigrations

Generate Django migration for the new model.

**Run command**:
```bash
just exec python manage.py makemigrations scanner --name create_valuation_history
```

**Expected output**:
```
Migrations for 'scanner':
  scanner/migrations/0007_create_valuation_history.py
    - Create model ValuationHistory
    - Create index on fields ['stock', '-snapshot_date']
    - Create index on fields ['snapshot_date']
    - Create index on fields ['stock', 'snapshot_date']
    - Add constraint unique_stock_snapshot_date on fields ['stock', 'snapshot_date']
```

**Review migration file**:
```bash
cat scanner/migrations/0007_create_valuation_history.py
```

**Verify migration contents**:
- CreateModel operation with all 19 fields
- AddIndex operations for 3 indexes
- AddConstraint operation for unique constraint
- Correct field types (DecimalField, DateField, etc.)

### Step 3: Apply migration to database

Apply the migration to create the database table.

**Run command**:
```bash
just exec python manage.py migrate scanner
```

**Expected output**:
```
Operations to perform:
  Apply all migrations: scanner
Running migrations:
  Applying scanner.0007_create_valuation_history... OK
```

**Verify table created**:
```bash
just dbconsole

# In psql
\d scanner_valuationhistory

# Should show:
# - All 19 columns
# - Foreign key constraint to scanner_curatedstock
# - Unique constraint on (stock_id, snapshot_date)
# - 3 indexes

\q
```

**Verify migration is reversible**:
```bash
# Show current migrations
just exec python manage.py showmigrations scanner

# Verify 0007 is applied (marked with [X])
```

### Step 4: Register model in Django admin

Add `ValuationHistory` to Django admin interface.

**File to modify**: `scanner/admin.py`

**Add after `CuratedStockAdmin`**:
```python
@admin.register(ValuationHistory)
class ValuationHistoryAdmin(admin.ModelAdmin):
    """Admin interface for ValuationHistory model."""

    list_display = [
        'stock_symbol',
        'quarter_label',
        'intrinsic_value',
        'intrinsic_value_fcf',
        'preferred_valuation_method',
        'snapshot_date',
    ]

    list_filter = [
        'snapshot_date',
        'preferred_valuation_method',
    ]

    search_fields = [
        'stock__symbol',
        'stock__name',
    ]

    readonly_fields = ['calculated_at']

    fieldsets = (
        ('Snapshot Information', {
            'fields': ('stock', 'snapshot_date', 'calculated_at', 'preferred_valuation_method')
        }),
        ('EPS Valuation', {
            'fields': ('intrinsic_value', 'current_eps', 'eps_growth_rate', 'eps_multiple')
        }),
        ('FCF Valuation', {
            'fields': ('intrinsic_value_fcf', 'current_fcf_per_share', 'fcf_growth_rate', 'fcf_multiple')
        }),
        ('Shared Assumptions', {
            'fields': ('desired_return', 'projection_years')
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )

    def stock_symbol(self, obj):
        """Display stock symbol in list view."""
        return obj.stock.symbol
    stock_symbol.short_description = 'Stock'
    stock_symbol.admin_order_field = 'stock__symbol'
```

**Add import at top of file** (if not present):
```python
from scanner.models import ValuationHistory
```

**Verify admin registration**:
```bash
# Start dev server
just run

# Login to admin: http://localhost:8000/admin/
# Navigate to Scanner -> Valuation Histories
# Should see empty list with correct columns
```

### Step 5: Write model unit tests

Create comprehensive unit tests for the `ValuationHistory` model.

**File to create**: `scanner/tests/test_valuation_history_model.py`

**Content**:
```python
"""
Tests for ValuationHistory model.

Test coverage:
- Model creation with all fields
- Unique constraint on (stock, snapshot_date)
- get_effective_intrinsic_value() method
- quarter_label property
- Foreign key CASCADE behavior
- Ordering and indexes
"""

import pytest
from datetime import date
from decimal import Decimal
from django.db import IntegrityError

from scanner.models import CuratedStock, ValuationHistory


@pytest.mark.django_db
class TestValuationHistoryModel:
    """Tests for ValuationHistory model."""

    def test_create_snapshot(self):
        """Test creating a valuation snapshot with all fields."""
        stock = CuratedStock.objects.create(
            symbol="AAPL",
            name="Apple Inc."
        )

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
        )

        assert snapshot.id is not None
        assert snapshot.stock == stock
        assert snapshot.intrinsic_value == Decimal("150.25")
        assert snapshot.snapshot_date == date(2025, 1, 1)
        assert snapshot.calculated_at is not None

    def test_unique_constraint(self):
        """Test unique constraint prevents duplicate snapshots for same stock and date."""
        stock = CuratedStock.objects.create(symbol="AAPL")

        # Create first snapshot
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

        # Attempt to create duplicate snapshot
        with pytest.raises(IntegrityError):
            ValuationHistory.objects.create(
                stock=stock,
                snapshot_date=date(2025, 1, 1),
                eps_growth_rate=Decimal("12.0"),
                eps_multiple=Decimal("22.0"),
                fcf_growth_rate=Decimal("12.0"),
                fcf_multiple=Decimal("22.0"),
                desired_return=Decimal("15.0"),
                projection_years=5,
            )

    def test_get_effective_intrinsic_value_eps(self):
        """Test get_effective_intrinsic_value() returns EPS value when preferred."""
        stock = CuratedStock.objects.create(symbol="AAPL")
        snapshot = ValuationHistory.objects.create(
            stock=stock,
            snapshot_date=date(2025, 1, 1),
            intrinsic_value=Decimal("150.00"),
            intrinsic_value_fcf=Decimal("145.00"),
            preferred_valuation_method="EPS",
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        assert snapshot.get_effective_intrinsic_value() == Decimal("150.00")

    def test_get_effective_intrinsic_value_fcf(self):
        """Test get_effective_intrinsic_value() returns FCF value when preferred."""
        stock = CuratedStock.objects.create(symbol="AAPL")
        snapshot = ValuationHistory.objects.create(
            stock=stock,
            snapshot_date=date(2025, 1, 1),
            intrinsic_value=Decimal("150.00"),
            intrinsic_value_fcf=Decimal("145.00"),
            preferred_valuation_method="FCF",
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        assert snapshot.get_effective_intrinsic_value() == Decimal("145.00")

    def test_get_effective_intrinsic_value_null(self):
        """Test get_effective_intrinsic_value() returns None when value is NULL."""
        stock = CuratedStock.objects.create(symbol="AAPL")
        snapshot = ValuationHistory.objects.create(
            stock=stock,
            snapshot_date=date(2025, 1, 1),
            intrinsic_value=None,
            intrinsic_value_fcf=None,
            preferred_valuation_method="EPS",
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        assert snapshot.get_effective_intrinsic_value() is None

    def test_quarter_label_property_q1(self):
        """Test quarter_label returns 'Q1 YYYY' for January 1."""
        stock = CuratedStock.objects.create(symbol="AAPL")
        snapshot = ValuationHistory.objects.create(
            stock=stock,
            snapshot_date=date(2025, 1, 1),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        assert snapshot.quarter_label == "Q1 2025"

    def test_quarter_label_property_all_quarters(self):
        """Test quarter_label returns correct format for all quarters."""
        stock = CuratedStock.objects.create(symbol="AAPL")

        quarters = [
            (date(2025, 1, 1), "Q1 2025"),
            (date(2025, 4, 1), "Q2 2025"),
            (date(2025, 7, 1), "Q3 2025"),
            (date(2025, 10, 1), "Q4 2025"),
        ]

        for snapshot_date, expected_label in quarters:
            snapshot = ValuationHistory.objects.create(
                stock=stock,
                snapshot_date=snapshot_date,
                eps_growth_rate=Decimal("10.0"),
                eps_multiple=Decimal("20.0"),
                fcf_growth_rate=Decimal("10.0"),
                fcf_multiple=Decimal("20.0"),
                desired_return=Decimal("15.0"),
                projection_years=5,
            )
            assert snapshot.quarter_label == expected_label

    def test_cascade_delete(self):
        """Test CASCADE delete removes history when stock deleted."""
        stock = CuratedStock.objects.create(symbol="AAPL")

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

        assert ValuationHistory.objects.filter(stock=stock).count() == 1

        # Delete stock
        stock.delete()

        # History should be deleted too
        assert ValuationHistory.objects.filter(stock=stock).count() == 0

    def test_ordering(self):
        """Test default ordering is by snapshot_date descending."""
        stock = CuratedStock.objects.create(symbol="AAPL")

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

        # Query all snapshots
        history = list(ValuationHistory.objects.filter(stock=stock))

        # Newest should be first
        assert history[0] == snapshot2
        assert history[1] == snapshot1

    def test_reverse_relation_from_stock(self):
        """Test can access history from stock via reverse relation."""
        stock = CuratedStock.objects.create(symbol="AAPL")

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

        # Access via reverse relation
        history = stock.valuation_history.all()

        assert history.count() == 1
        assert history.first().stock == stock

    def test_str_method(self):
        """Test __str__ method returns correct format."""
        stock = CuratedStock.objects.create(symbol="AAPL")
        snapshot = ValuationHistory.objects.create(
            stock=stock,
            snapshot_date=date(2025, 1, 1),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        assert str(snapshot) == "AAPL - 2025-01-01"
```

**Run tests**:
```bash
just test scanner/tests/test_valuation_history_model.py -v
```

**Expected**: All 12 tests pass

### Step 6: Verify migration and model functionality

Final verification that everything works correctly.

**Check model in Django shell**:
```bash
uv run python manage.py shell

>>> from scanner.models import CuratedStock, ValuationHistory
>>> from datetime import date
>>> from decimal import Decimal

>>> # Create test stock
>>> stock = CuratedStock.objects.create(symbol="TEST")

>>> # Create test snapshot
>>> snapshot = ValuationHistory.objects.create(
...     stock=stock,
...     snapshot_date=date(2025, 1, 1),
...     intrinsic_value=Decimal("100.00"),
...     eps_growth_rate=Decimal("10.0"),
...     eps_multiple=Decimal("20.0"),
...     fcf_growth_rate=Decimal("10.0"),
...     fcf_multiple=Decimal("20.0"),
...     desired_return=Decimal("15.0"),
...     projection_years=5,
... )

>>> # Verify methods
>>> snapshot.quarter_label
'Q1 2025'

>>> snapshot.get_effective_intrinsic_value()
Decimal('100.00')

>>> # Verify reverse relation
>>> stock.valuation_history.count()
1

>>> # Cleanup
>>> stock.delete()
>>> exit()
```

**Verify all tests still pass**:
```bash
just test
```

**Expected**: All 216+ tests pass (180 scanner + 36 tracker + 12 new)

**Check admin interface**:
1. Start server: `just run`
2. Login to admin: http://localhost:8000/admin/
3. Navigate to Scanner → Valuation Histories
4. Verify empty list with correct columns
5. Try creating a snapshot manually via admin

## Summary of Changes

[Leave empty - will be filled during implementation]

## Notes

### Design Rationale

**Quarterly Snapshots**:
- Balance between data granularity and storage efficiency
- Align with earnings report frequency (quarterly)
- 4 snapshots/year × 50 stocks × 5 years = 1,000 records (manageable)

**Unique Constraint**:
- Prevents accidental duplicate snapshots
- Database-level enforcement (not just application-level)
- Idempotent snapshot creation

**CASCADE Delete**:
- If stock removed from curated list, history becomes irrelevant
- Alternative: PROTECT would prevent stock deletion (too restrictive)
- Consider soft delete for audit trail (future enhancement)

**Index Strategy**:
- `snapshot_date` index: Fast quarterly queries (all stocks for Q1 2025)
- `(stock, -snapshot_date)` index: Fast per-stock history queries (newest first)
- `(stock, snapshot_date)` index: Supports unique constraint and lookups

### Storage Projections

**5-year retention**:
- Records: 50 stocks × 4 quarters/year × 5 years = 1,000
- Size per record: ~200 bytes (19 fields + indexes)
- Total: ~200 KB (negligible for PostgreSQL)

**10-year retention**:
- Records: 2,000
- Total: ~400 KB

**Query performance**: O(log n) with indexes, fast even with decades of data

## Dependencies

- Django 5.1+ ORM
- PostgreSQL 14.1+ database
- Existing `CuratedStock` model
- pytest-django for testing

## Reference

**Django models documentation**:
- https://docs.djangoproject.com/en/5.1/topics/db/models/
- https://docs.djangoproject.com/en/5.1/ref/models/fields/
- https://docs.djangoproject.com/en/5.1/ref/models/constraints/

**Implementation spec**:
- See: `/Users/danvigliotti/Development/Sirvig/wheel-analyzer/specs/phase-6-historical-valuations.md`
- Section 2: Database Schema Design
- Section 7: Testing Strategy
