# Task 036: Create Quarterly Snapshot Management Command

## Progress Summary

**Status**: Not Started

- [ ] Step 1: Create management command file structure
- [ ] Step 2: Implement command class with arguments
- [ ] Step 3: Implement quarterly date determination logic
- [ ] Step 4: Implement snapshot creation logic
- [ ] Step 5: Add idempotency and error handling
- [ ] Step 6: Write command integration tests
- [ ] Step 7: Manual testing with sample data
- [ ] Step 8: Document cron scheduling

## Overview

Create a Django management command `create_quarterly_valuation_snapshot` that generates quarterly snapshots of intrinsic value calculations for all active curated stocks. This command will be scheduled to run quarterly (Jan 1, Apr 1, Jul 1, Oct 1) via cron, capturing valuation data and DCF assumptions for historical tracking.

**Current State**:
- `ValuationHistory` model exists but no snapshots created
- No mechanism to populate historical data
- Manual snapshot creation would be error-prone

**Target State**:
- Management command creates snapshots for all active stocks
- Idempotent (safe to run multiple times)
- Supports backfilling with `--date` flag
- Supports specific stocks with `--symbols` flag
- Dry-run mode for testing
- Force overwrite mode for corrections
- Comprehensive logging and summary output

## High-Level Specifications

### Command Features

- **Default behavior**: Creates snapshots for current quarter date (Jan 1, Apr 1, Jul 1, Oct 1)
- **Options**:
  - `--date YYYY-MM-DD`: Override snapshot date (for backfilling)
  - `--symbols AAPL MSFT`: Create snapshot for specific stocks only
  - `--force`: Overwrite existing snapshots for the given date
  - `--dry-run`: Preview what would be created without writing to database
- **Idempotency**: Skips existing snapshots unless `--force` flag used
- **Error handling**: Each stock processed in try/except, errors don't stop batch
- **Logging**: Detailed logs for each operation, summary statistics at end

### Snapshot Logic

1. Determine snapshot date (current quarter or from `--date` flag)
2. Query active CuratedStock instances (all or filtered by `--symbols`)
3. For each stock:
   - Check if snapshot already exists (idempotency)
   - If exists and not force: skip
   - If no valuation data: skip with warning
   - Create ValuationHistory record from current CuratedStock values
4. Output summary: created, skipped, errors

### Cron Scheduling

- **Frequency**: Quarterly on Jan 1, Apr 1, Jul 1, Oct 1
- **Time**: 11:00 PM ET (after market close and daily calculations)
- **Cron expression**: `0 23 1 1,4,7,10 *`

## Relevant Files

### Files to Create
- `scanner/management/commands/create_quarterly_valuation_snapshot.py` - Main command file

### Files to Modify
- None (new command)

### Files for Testing
- `scanner/tests/test_quarterly_snapshot_command.py` - Integration tests (15+ tests)

## Acceptance Criteria

### Command Implementation
- [ ] Command file created at correct path
- [ ] Command class extends `BaseCommand`
- [ ] Help text describes command purpose
- [ ] `add_arguments()` defines all 4 options (date, symbols, force, dry-run)
- [ ] `handle()` method implements main logic
- [ ] `_get_current_quarter_date()` helper determines quarter dates
- [ ] `_create_snapshot()` helper creates individual snapshots with transaction.atomic

### Idempotency Requirements
- [ ] Checks for existing snapshots before creating
- [ ] Skips existing snapshots by default
- [ ] `--force` flag allows overwriting existing snapshots
- [ ] Unique constraint prevents duplicates at database level
- [ ] Summary shows created vs skipped counts

### Error Handling Requirements
- [ ] Each stock processed in try/except block
- [ ] Errors logged but don't stop entire batch
- [ ] Stocks with no valuation data skipped with warning
- [ ] Database transaction rollback on error
- [ ] Summary shows error count and details

### Logging Requirements
- [ ] Logger configured with `__name__`
- [ ] INFO level: Command start/end, snapshot date, stock counts
- [ ] DEBUG level: Per-stock snapshot creation
- [ ] WARNING level: Skipped stocks, non-quarterly dates
- [ ] ERROR level: Failed snapshot creation with traceback
- [ ] Summary output to stdout and logger

### Testing Requirements
- [ ] Test: Create snapshots for all active stocks
- [ ] Test: Skip inactive stocks
- [ ] Test: Idempotency (skip existing snapshots)
- [ ] Test: Force overwrite with `--force` flag
- [ ] Test: Dry-run mode doesn't create records
- [ ] Test: Custom date with `--date` flag
- [ ] Test: Specific symbols with `--symbols` flag
- [ ] Test: Quarterly date validation warning
- [ ] Test: Skip stocks with no valuation data
- [ ] Test: Error handling for individual stock failure
- [ ] Test: Summary statistics correct
- [ ] All 15+ tests pass

### Documentation Requirements
- [ ] Docstring explains command purpose
- [ ] Usage examples in docstring
- [ ] Cron schedule documented in docstring
- [ ] Help text for each argument
- [ ] AGENTS.md updated with command reference

## Implementation Steps

### Step 1: Create management command file structure

Create the command file with proper Django structure.

**File to create**: `scanner/management/commands/create_quarterly_valuation_snapshot.py`

**Initial structure**:
```python
"""
Create quarterly valuation snapshots for curated stocks.

This command captures quarterly snapshots (Jan 1, Apr 1, Jul 1, Oct 1) of
intrinsic value calculations and DCF assumptions from the CuratedStock model
into the ValuationHistory model.

Usage:
    # Create snapshot for current quarter
    python manage.py create_quarterly_valuation_snapshot

    # Create snapshot for specific date
    python manage.py create_quarterly_valuation_snapshot --date 2025-01-01

    # Create snapshot for specific stocks
    python manage.py create_quarterly_valuation_snapshot --symbols AAPL MSFT

    # Preview without creating
    python manage.py create_quarterly_valuation_snapshot --dry-run

    # Force overwrite existing snapshots
    python manage.py create_quarterly_valuation_snapshot --force

Schedule:
    Run quarterly via cron on Jan 1, Apr 1, Jul 1, Oct 1:
    0 23 1 1,4,7,10 * cd /path/to/project && python manage.py create_quarterly_valuation_snapshot
"""

import logging
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from scanner.models import CuratedStock, ValuationHistory

logger = logging.getLogger(__name__)

# Quarterly snapshot dates (month, day)
QUARTERLY_DATES = [(1, 1), (4, 1), (7, 1), (10, 1)]


class Command(BaseCommand):
    help = "Create quarterly valuation snapshots for curated stocks"

    def add_arguments(self, parser):
        # TODO: Implement in Step 2
        pass

    def handle(self, *args, **options):
        # TODO: Implement in Step 3-5
        pass
```

**Verify file created**:
```bash
ls -la scanner/management/commands/create_quarterly_valuation_snapshot.py
```

### Step 2: Implement command class with arguments

Add argument parsing to the command.

**Update `add_arguments()` method**:
```python
def add_arguments(self, parser):
    parser.add_argument(
        '--date',
        type=str,
        help='Snapshot date (YYYY-MM-DD), defaults to current quarter date'
    )
    parser.add_argument(
        '--symbols',
        nargs='+',
        type=str,
        help='Specific stock symbols to snapshot (default: all active)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Overwrite existing snapshots for the given date'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview what would be created without writing to database'
    )
```

**Test argument parsing**:
```bash
# Show help
uv run python manage.py create_quarterly_valuation_snapshot --help

# Should show all 4 options with descriptions
```

### Step 3: Implement quarterly date determination logic

Add helper method to determine current quarter date.

**Add `_get_current_quarter_date()` method to Command class**:
```python
def _get_current_quarter_date(self):
    """
    Get the current quarter snapshot date (Jan 1, Apr 1, Jul 1, Oct 1).

    Returns:
        date: The snapshot date for the current quarter
    """
    today = date.today()
    year = today.year

    # Determine which quarter we're in
    if today.month < 4:
        return date(year, 1, 1)
    elif today.month < 7:
        return date(year, 4, 1)
    elif today.month < 10:
        return date(year, 7, 1)
    else:
        return date(year, 10, 1)
```

**Test logic manually**:
```python
# In Django shell
from scanner.management.commands.create_quarterly_valuation_snapshot import Command
from datetime import date

cmd = Command()

# Test current quarter
print(cmd._get_current_quarter_date())
# Should return nearest past quarter date
```

### Step 4: Implement snapshot creation logic

Add main command logic in `handle()` method.

**Update `handle()` method**:
```python
def handle(self, *args, **options):
    """Main command execution."""
    logger.info("=" * 60)
    logger.info("Starting quarterly valuation snapshot creation")
    logger.info(f"Options: {options}")
    logger.info("=" * 60)

    # Determine snapshot date
    if options.get('date'):
        try:
            snapshot_date = date.fromisoformat(options['date'])
        except ValueError:
            raise CommandError(f"Invalid date format: {options['date']}. Use YYYY-MM-DD")
    else:
        snapshot_date = self._get_current_quarter_date()

    self.stdout.write(f"Snapshot date: {snapshot_date.isoformat()}")

    # Validate it's a quarterly date
    if (snapshot_date.month, snapshot_date.day) not in QUARTERLY_DATES:
        self.stdout.write(
            self.style.WARNING(
                f"⚠ Warning: {snapshot_date} is not a standard quarterly date "
                f"(Jan 1, Apr 1, Jul 1, Oct 1)"
            )
        )

    # Get stocks to snapshot
    if options.get('symbols'):
        stocks = CuratedStock.objects.filter(
            symbol__in=[s.upper() for s in options['symbols']]
        )
        if not stocks.exists():
            raise CommandError(
                f"No stocks found with symbols: {', '.join(options['symbols'])}"
            )
    else:
        stocks = CuratedStock.objects.filter(active=True)

    total_stocks = stocks.count()
    self.stdout.write(f"Processing {total_stocks} stock(s)...")

    if options.get('dry_run'):
        self.stdout.write(self.style.WARNING("DRY RUN - No changes will be made"))

    # Process each stock
    created = 0
    skipped = 0
    errors = 0

    for stock in stocks:
        try:
            result = self._create_snapshot(
                stock=stock,
                snapshot_date=snapshot_date,
                force=options.get('force', False),
                dry_run=options.get('dry_run', False)
            )

            if result == 'created':
                created += 1
                self.stdout.write(
                    self.style.SUCCESS(f"  ✓ {stock.symbol}: Snapshot created")
                )
            elif result == 'skipped':
                skipped += 1
                self.stdout.write(
                    self.style.WARNING(f"  ⊘ {stock.symbol}: Snapshot already exists")
                )
            elif result == 'no_data':
                skipped += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"  ⊘ {stock.symbol}: No valuation data to snapshot"
                    )
                )
        except Exception as e:
            errors += 1
            logger.error(f"Error creating snapshot for {stock.symbol}: {e}", exc_info=True)
            self.stdout.write(self.style.ERROR(f"  ✗ {stock.symbol}: Error - {str(e)}"))

    # Summary
    self.stdout.write(self.style.SUCCESS(f"\n{'=' * 65}"))
    self.stdout.write(self.style.SUCCESS("SUMMARY:"))
    self.stdout.write(f"  Snapshot date: {snapshot_date.isoformat()}")
    self.stdout.write(f"  Total stocks: {total_stocks}")
    self.stdout.write(self.style.SUCCESS(f"  Created: {created}"))
    self.stdout.write(self.style.WARNING(f"  Skipped: {skipped}"))
    self.stdout.write(self.style.ERROR(f"  Errors: {errors}"))

    if options.get('dry_run'):
        self.stdout.write(self.style.WARNING("\n  (DRY RUN - No changes were made)"))

    self.stdout.write(self.style.SUCCESS(f"{'=' * 65}\n"))

    logger.info(f"Snapshot creation complete: {created} created, {skipped} skipped, {errors} errors")
```

### Step 5: Add idempotency and error handling

Add helper method to create individual snapshots with proper checks.

**Add `_create_snapshot()` method**:
```python
@transaction.atomic
def _create_snapshot(self, stock, snapshot_date, force=False, dry_run=False):
    """
    Create a valuation snapshot for a single stock.

    Args:
        stock: CuratedStock instance
        snapshot_date: date object for the snapshot
        force: Whether to overwrite existing snapshot
        dry_run: Whether to preview without creating

    Returns:
        str: 'created', 'skipped', or 'no_data'
    """
    # Check if snapshot already exists
    existing = ValuationHistory.objects.filter(
        stock=stock,
        snapshot_date=snapshot_date
    ).first()

    if existing and not force:
        return 'skipped'

    # Check if stock has valuation data to snapshot
    if stock.intrinsic_value is None and stock.intrinsic_value_fcf is None:
        return 'no_data'

    # Preview in dry-run mode
    if dry_run:
        return 'created'  # Would be created

    # Delete existing if force=True
    if existing and force:
        existing.delete()
        logger.info(f"Deleted existing snapshot for {stock.symbol} on {snapshot_date}")

    # Create new snapshot from current CuratedStock values
    ValuationHistory.objects.create(
        stock=stock,
        snapshot_date=snapshot_date,
        # EPS values
        intrinsic_value=stock.intrinsic_value,
        current_eps=stock.current_eps,
        eps_growth_rate=stock.eps_growth_rate,
        eps_multiple=stock.eps_multiple,
        # FCF values
        intrinsic_value_fcf=stock.intrinsic_value_fcf,
        current_fcf_per_share=stock.current_fcf_per_share,
        fcf_growth_rate=stock.fcf_growth_rate,
        fcf_multiple=stock.fcf_multiple,
        # Shared assumptions
        desired_return=stock.desired_return,
        projection_years=stock.projection_years,
        preferred_valuation_method=stock.preferred_valuation_method,
    )

    logger.info(f"Created snapshot for {stock.symbol} on {snapshot_date}")
    return 'created'
```

**Verify command runs**:
```bash
# Test dry-run (should not create any snapshots)
uv run python manage.py create_quarterly_valuation_snapshot --dry-run

# Expected: Shows what would be created, no database changes
```

### Step 6: Write command integration tests

Create comprehensive integration tests for the command.

**File to create**: `scanner/tests/test_quarterly_snapshot_command.py`

**Content**:
```python
"""
Tests for create_quarterly_valuation_snapshot management command.

Test coverage:
- Create snapshots for all active stocks
- Skip inactive stocks
- Idempotency (skip existing snapshots)
- Force overwrite with --force flag
- Dry-run mode doesn't create records
- Custom date with --date flag
- Specific symbols with --symbols flag
- Quarterly date validation
- Error handling for missing data
"""

import pytest
from datetime import date
from decimal import Decimal
from io import StringIO
from django.core.management import call_command

from scanner.models import CuratedStock, ValuationHistory


@pytest.mark.django_db
class TestQuarterlySnapshotCommand:
    """Tests for create_quarterly_valuation_snapshot command."""

    def test_create_snapshot_all_stocks(self):
        """Test creating snapshots for all active stocks."""
        # Create stocks
        stock1 = CuratedStock.objects.create(
            symbol="AAPL",
            active=True,
            intrinsic_value=Decimal("150.00"),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        stock2 = CuratedStock.objects.create(
            symbol="MSFT",
            active=True,
            intrinsic_value=Decimal("300.00"),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        # Run command
        out = StringIO()
        call_command('create_quarterly_valuation_snapshot', '--date', '2025-01-01', stdout=out)

        # Verify snapshots created
        assert ValuationHistory.objects.count() == 2

        snapshot1 = ValuationHistory.objects.get(stock=stock1)
        assert snapshot1.snapshot_date == date(2025, 1, 1)
        assert snapshot1.intrinsic_value == Decimal("150.00")

        snapshot2 = ValuationHistory.objects.get(stock=stock2)
        assert snapshot2.snapshot_date == date(2025, 1, 1)
        assert snapshot2.intrinsic_value == Decimal("300.00")

        output = out.getvalue()
        assert "Created: 2" in output
        assert "Skipped: 0" in output

    def test_skip_inactive_stocks(self):
        """Test that inactive stocks are not included."""
        CuratedStock.objects.create(
            symbol="ACTIVE",
            active=True,
            intrinsic_value=Decimal("100.00"),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        CuratedStock.objects.create(
            symbol="INACTIVE",
            active=False,
            intrinsic_value=Decimal("200.00"),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        # Run command
        out = StringIO()
        call_command('create_quarterly_valuation_snapshot', '--date', '2025-01-01', stdout=out)

        # Only active stock should have snapshot
        assert ValuationHistory.objects.count() == 1
        assert ValuationHistory.objects.filter(stock__symbol="ACTIVE").exists()
        assert not ValuationHistory.objects.filter(stock__symbol="INACTIVE").exists()

    def test_skip_existing_snapshot(self):
        """Test idempotency - skip if snapshot already exists."""
        stock = CuratedStock.objects.create(
            symbol="AAPL",
            active=True,
            intrinsic_value=Decimal("150.00"),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        # Create existing snapshot
        ValuationHistory.objects.create(
            stock=stock,
            snapshot_date=date(2025, 1, 1),
            intrinsic_value=Decimal("145.00"),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        # Run command
        out = StringIO()
        call_command('create_quarterly_valuation_snapshot', '--date', '2025-01-01', stdout=out)

        # Verify skipped
        assert ValuationHistory.objects.count() == 1

        # Verify value not changed
        snapshot = ValuationHistory.objects.get(stock=stock)
        assert snapshot.intrinsic_value == Decimal("145.00")

        output = out.getvalue()
        assert "Created: 0" in output
        assert "Skipped: 1" in output

    def test_force_overwrite(self):
        """Test --force flag overwrites existing snapshot."""
        stock = CuratedStock.objects.create(
            symbol="AAPL",
            active=True,
            intrinsic_value=Decimal("150.00"),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        # Create existing snapshot
        ValuationHistory.objects.create(
            stock=stock,
            snapshot_date=date(2025, 1, 1),
            intrinsic_value=Decimal("145.00"),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        # Run command with --force
        out = StringIO()
        call_command('create_quarterly_valuation_snapshot', '--date', '2025-01-01', '--force', stdout=out)

        # Verify overwritten
        assert ValuationHistory.objects.count() == 1

        snapshot = ValuationHistory.objects.get(stock=stock)
        assert snapshot.intrinsic_value == Decimal("150.00")  # Updated

        output = out.getvalue()
        assert "Created: 1" in output

    def test_dry_run_mode(self):
        """Test --dry-run flag doesn't create records."""
        stock = CuratedStock.objects.create(
            symbol="AAPL",
            active=True,
            intrinsic_value=Decimal("150.00"),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        # Run command with --dry-run
        out = StringIO()
        call_command('create_quarterly_valuation_snapshot', '--date', '2025-01-01', '--dry-run', stdout=out)

        # Verify nothing created
        assert ValuationHistory.objects.count() == 0

        output = out.getvalue()
        assert "DRY RUN" in output
        assert "Created: 1" in output  # Would be created

    def test_custom_date(self):
        """Test --date flag with custom date."""
        stock = CuratedStock.objects.create(
            symbol="AAPL",
            active=True,
            intrinsic_value=Decimal("150.00"),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        # Run command with custom date
        call_command('create_quarterly_valuation_snapshot', '--date', '2024-07-01')

        # Verify snapshot has custom date
        snapshot = ValuationHistory.objects.get(stock=stock)
        assert snapshot.snapshot_date == date(2024, 7, 1)

    def test_specific_symbols(self):
        """Test --symbols flag with specific stocks."""
        stock1 = CuratedStock.objects.create(
            symbol="AAPL",
            active=True,
            intrinsic_value=Decimal("150.00"),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        stock2 = CuratedStock.objects.create(
            symbol="MSFT",
            active=True,
            intrinsic_value=Decimal("300.00"),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        # Run command for AAPL only
        call_command('create_quarterly_valuation_snapshot', '--date', '2025-01-01', '--symbols', 'AAPL')

        # Only AAPL should have snapshot
        assert ValuationHistory.objects.count() == 1
        assert ValuationHistory.objects.filter(stock=stock1).exists()
        assert not ValuationHistory.objects.filter(stock=stock2).exists()

    def test_skip_stocks_with_no_data(self):
        """Test stocks with no valuation data are skipped."""
        stock = CuratedStock.objects.create(
            symbol="NODATA",
            active=True,
            intrinsic_value=None,
            intrinsic_value_fcf=None,
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        # Run command
        out = StringIO()
        call_command('create_quarterly_valuation_snapshot', '--date', '2025-01-01', stdout=out)

        # Verify no snapshot created
        assert ValuationHistory.objects.count() == 0

        output = out.getvalue()
        assert "Skipped: 1" in output
        assert "No valuation data" in output

    def test_invalid_date_format(self):
        """Test command raises error for invalid date format."""
        from django.core.management.base import CommandError

        with pytest.raises(CommandError):
            call_command('create_quarterly_valuation_snapshot', '--date', 'invalid-date')

    def test_nonexistent_symbols(self):
        """Test command raises error for nonexistent symbols."""
        from django.core.management.base import CommandError

        with pytest.raises(CommandError):
            call_command('create_quarterly_valuation_snapshot', '--symbols', 'NONEXISTENT')

    def test_non_quarterly_date_warning(self):
        """Test warning displayed for non-quarterly dates."""
        stock = CuratedStock.objects.create(
            symbol="AAPL",
            active=True,
            intrinsic_value=Decimal("150.00"),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        # Run command with non-quarterly date
        out = StringIO()
        call_command('create_quarterly_valuation_snapshot', '--date', '2025-02-15', stdout=out)

        output = out.getvalue()
        assert "Warning" in output
        assert "not a standard quarterly date" in output

    def test_summary_statistics(self):
        """Test summary statistics are correct."""
        # Create 3 stocks: one to create, one to skip, one to error
        CuratedStock.objects.create(
            symbol="CREATE",
            active=True,
            intrinsic_value=Decimal("100.00"),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        skip_stock = CuratedStock.objects.create(
            symbol="SKIP",
            active=True,
            intrinsic_value=Decimal("200.00"),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        # Create existing snapshot for SKIP
        ValuationHistory.objects.create(
            stock=skip_stock,
            snapshot_date=date(2025, 1, 1),
            intrinsic_value=Decimal("200.00"),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        CuratedStock.objects.create(
            symbol="NODATA",
            active=True,
            intrinsic_value=None,
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        # Run command
        out = StringIO()
        call_command('create_quarterly_valuation_snapshot', '--date', '2025-01-01', stdout=out)

        output = out.getvalue()
        assert "Created: 1" in output
        assert "Skipped: 2" in output
        assert "Errors: 0" in output
```

**Run tests**:
```bash
just test scanner/tests/test_quarterly_snapshot_command.py -v
```

**Expected**: All 14 tests pass

### Step 7: Manual testing with sample data

Test command with real data to verify functionality.

**Setup test data**:
```bash
# Django shell
uv run python manage.py shell

>>> from scanner.models import CuratedStock
>>> from decimal import Decimal

>>> # Create test stocks
>>> CuratedStock.objects.create(
...     symbol="TEST1",
...     name="Test Company 1",
...     active=True,
...     intrinsic_value=Decimal("100.00"),
...     intrinsic_value_fcf=Decimal("95.00"),
...     current_eps=Decimal("5.00"),
...     eps_growth_rate=Decimal("10.0"),
...     eps_multiple=Decimal("20.0"),
...     fcf_growth_rate=Decimal("10.0"),
...     fcf_multiple=Decimal("20.0"),
...     desired_return=Decimal("15.0"),
...     projection_years=5,
... )

>>> exit()
```

**Test command**:
```bash
# Test dry-run
uv run python manage.py create_quarterly_valuation_snapshot --dry-run

# Test actual creation
uv run python manage.py create_quarterly_valuation_snapshot --date 2025-01-01

# Test idempotency (run again)
uv run python manage.py create_quarterly_valuation_snapshot --date 2025-01-01

# Test force overwrite
uv run python manage.py create_quarterly_valuation_snapshot --date 2025-01-01 --force

# Test specific symbols
uv run python manage.py create_quarterly_valuation_snapshot --date 2025-01-01 --symbols TEST1
```

**Verify in database**:
```bash
just dbconsole

# In psql
SELECT stock_id, snapshot_date, intrinsic_value, intrinsic_value_fcf
FROM scanner_valuationhistory
WHERE stock_id IN (SELECT id FROM scanner_curatedstock WHERE symbol = 'TEST1');

\q
```

**Cleanup test data**:
```bash
uv run python manage.py shell

>>> from scanner.models import CuratedStock
>>> CuratedStock.objects.filter(symbol="TEST1").delete()
>>> exit()
```

### Step 8: Document cron scheduling

Add cron scheduling documentation to AGENTS.md.

**File to update**: `AGENTS.md`

**Add to Custom Management Commands section**:
```markdown
- `python manage.py create_quarterly_valuation_snapshot` - Create quarterly snapshots of intrinsic valuations
  - Options: `--date YYYY-MM-DD`, `--symbols AAPL MSFT`, `--force`, `--dry-run`
  - Scheduled: Quarterly via cron on Jan 1, Apr 1, Jul 1, Oct 1 at 11 PM ET
  - Cron: `0 23 1 1,4,7,10 * cd /path/to/project && python manage.py create_quarterly_valuation_snapshot`
```

**Verify all tests still pass**:
```bash
just test
```

**Expected**: All 230+ tests pass (216 existing + 12 model + 14 command)

## Summary of Changes

[Leave empty - will be filled during implementation]

## Notes

### Command Design Rationale

**Idempotency**:
- Essential for cron jobs (may run multiple times due to system issues)
- Unique constraint at database level prevents duplicates
- Command checks before creating for efficiency

**Error Handling**:
- Per-stock try/except ensures one failure doesn't stop entire batch
- Errors logged with traceback for debugging
- Summary shows error count for monitoring

**Flags**:
- `--date`: Enables backfilling historical data
- `--symbols`: Useful for testing or correcting specific stocks
- `--force`: Allows corrections if assumptions changed
- `--dry-run`: Safe testing before actual execution

### Cron Scheduling

**Why 11 PM ET?**:
- After market close (4 PM ET)
- After daily intrinsic value calculations (assume 8 PM ET)
- Before midnight (ensures consistent date)

**Quarterly dates**:
- Q1: January 1 (after year-end)
- Q2: April 1 (after Q1 earnings)
- Q3: July 1 (after Q2 earnings)
- Q4: October 1 (after Q3 earnings)

**Monitoring**:
- Command output logged to stdout/stderr
- Cron can email output (configure in crontab)
- Summary statistics show success/failure counts

### Backfilling Historical Data

To backfill past quarters:
```bash
# Create snapshots for all of 2024
python manage.py create_quarterly_valuation_snapshot --date 2024-01-01
python manage.py create_quarterly_valuation_snapshot --date 2024-04-01
python manage.py create_quarterly_valuation_snapshot --date 2024-07-01
python manage.py create_quarterly_valuation_snapshot --date 2024-10-01

# Or use a shell script
for date in 2024-01-01 2024-04-01 2024-07-01 2024-10-01; do
    python manage.py create_quarterly_valuation_snapshot --date $date
done
```

## Dependencies

- Task 035 completed (ValuationHistory model exists)
- Django management command framework
- CuratedStock model with valuation data
- pytest-django for testing

## Reference

**Django management commands**:
- https://docs.djangoproject.com/en/5.1/howto/custom-management-commands/
- https://docs.djangoproject.com/en/5.1/ref/django-admin/

**Implementation spec**:
- See: `/Users/danvigliotti/Development/Sirvig/wheel-analyzer/specs/phase-6-historical-valuations.md`
- Section 3: Data Collection Strategy
- Section 7: Testing Strategy
