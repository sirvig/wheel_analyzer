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
from django.db import IntegrityError

from scanner.models import CuratedStock, ValuationHistory


@pytest.mark.django_db
class TestQuarterlySnapshotCommand:

    def test_create_snapshot_all_stocks(self):
        """Test creating snapshots for all active stocks."""
        # Create stocks
        stock1 = CuratedStock.objects.create(
            symbol="TEST1",
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
            symbol="TEST2",
            active=True,
            intrinsic_value=Decimal("300.00"),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        # Run command with specific symbols
        out = StringIO()
        call_command(
            'create_quarterly_valuation_snapshot',
            '--date', '2025-01-01',
            '--symbols', 'TEST1', 'TEST2',
            stdout=out
        )

        # Verify snapshots created
        assert ValuationHistory.objects.filter(stock__in=[stock1, stock2]).count() == 2

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
        """Test that inactive stocks are not included in snapshots."""
        # Create active and inactive stocks
        stock_active = CuratedStock.objects.create(
            symbol="TEST1",
            active=True,
            intrinsic_value=Decimal("150.00"),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        stock_inactive = CuratedStock.objects.create(
            symbol="TEST2",
            active=False,
            intrinsic_value=Decimal("300.00"),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        # Run command (without --symbols, so only active stocks)
        out = StringIO()
        call_command('create_quarterly_valuation_snapshot', '--date', '2025-01-01', stdout=out)

        # Verify only active stock has snapshot
        assert ValuationHistory.objects.count() == 1
        assert ValuationHistory.objects.filter(stock=stock_active).exists()
        assert not ValuationHistory.objects.filter(stock=stock_inactive).exists()

        output = out.getvalue()
        assert "Created: 1" in output

    def test_skip_existing_snapshot(self):
        """Test idempotency - skip if snapshot already exists."""
        stock = CuratedStock.objects.create(
            symbol="TEST1",
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

        # Run command with specific symbol
        out = StringIO()
        call_command(
            'create_quarterly_valuation_snapshot',
            '--date', '2025-01-01',
            '--symbols', 'TEST1',
            stdout=out
        )

        # Verify skipped
        assert ValuationHistory.objects.filter(stock=stock).count() == 1

        # Verify value not changed
        snapshot = ValuationHistory.objects.get(stock=stock)
        assert snapshot.intrinsic_value == Decimal("145.00")

        output = out.getvalue()
        assert "Created: 0" in output
        assert "Skipped: 1" in output

    def test_force_overwrite(self):
        """Test --force flag overwrites existing snapshot."""
        stock = CuratedStock.objects.create(
            symbol="TEST1",
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
            symbol="TEST1",
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
            symbol="TEST1",
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
        out = StringIO()
        call_command('create_quarterly_valuation_snapshot', '--date', '2024-07-01', stdout=out)

        # Verify snapshot created with custom date
        assert ValuationHistory.objects.count() == 1
        snapshot = ValuationHistory.objects.get(stock=stock)
        assert snapshot.snapshot_date == date(2024, 7, 1)

    def test_specific_symbols(self):
        """Test --symbols flag creates snapshots for specific stocks."""
        stock1 = CuratedStock.objects.create(
            symbol="TEST1",
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
            symbol="TEST2",
            active=True,
            intrinsic_value=Decimal("300.00"),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        stock3 = CuratedStock.objects.create(
            symbol="TEST3",
            active=True,
            intrinsic_value=Decimal("200.00"),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        # Run command with specific symbols
        out = StringIO()
        call_command(
            'create_quarterly_valuation_snapshot',
            '--date', '2025-01-01',
            '--symbols', 'TEST1', 'TEST3',
            stdout=out
        )

        # Verify only specified stocks have snapshots
        assert ValuationHistory.objects.count() == 2
        assert ValuationHistory.objects.filter(stock=stock1).exists()
        assert not ValuationHistory.objects.filter(stock=stock2).exists()
        assert ValuationHistory.objects.filter(stock=stock3).exists()

        output = out.getvalue()
        assert "Created: 2" in output

    def test_no_valuation_data(self):
        """Test that stocks without valuation data are skipped."""
        stock = CuratedStock.objects.create(
            symbol="TEST1",
            active=True,
            intrinsic_value=None,  # No valuation data
            intrinsic_value_fcf=None,
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        # Run command with specific symbol
        out = StringIO()
        call_command(
            'create_quarterly_valuation_snapshot',
            '--date', '2025-01-01',
            '--symbols', 'TEST1',
            stdout=out
        )

        # Verify no snapshot created
        assert ValuationHistory.objects.filter(stock=stock).count() == 0

        output = out.getvalue()
        assert "Skipped: 1" in output
        assert "No valuation data" in output

    def test_quarterly_date_warning(self):
        """Test warning for non-quarterly dates."""
        stock = CuratedStock.objects.create(
            symbol="TEST1",
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

        # Verify warning in output
        output = out.getvalue()
        assert "Warning" in output
        assert "not a standard quarterly date" in output

        # But snapshot should still be created
        assert ValuationHistory.objects.count() == 1

    def test_snapshot_copies_all_fields(self):
        """Test that snapshot copies all valuation fields from stock."""
        stock = CuratedStock.objects.create(
            symbol="TEST1",
            active=True,
            # EPS fields
            intrinsic_value=Decimal("150.25"),
            current_eps=Decimal("6.42"),
            eps_growth_rate=Decimal("12.5"),
            eps_multiple=Decimal("22.0"),
            # FCF fields
            intrinsic_value_fcf=Decimal("148.50"),
            current_fcf_per_share=Decimal("7.20"),
            fcf_growth_rate=Decimal("11.5"),
            fcf_multiple=Decimal("21.0"),
            # Shared fields
            desired_return=Decimal("16.0"),
            projection_years=7,
            preferred_valuation_method="FCF",
        )

        # Run command
        out = StringIO()
        call_command('create_quarterly_valuation_snapshot', '--date', '2025-01-01', stdout=out)

        # Verify all fields copied
        snapshot = ValuationHistory.objects.get(stock=stock)
        assert snapshot.intrinsic_value == Decimal("150.25")
        assert snapshot.current_eps == Decimal("6.42")
        assert snapshot.eps_growth_rate == Decimal("12.5")
        assert snapshot.eps_multiple == Decimal("22.0")
        assert snapshot.intrinsic_value_fcf == Decimal("148.50")
        assert snapshot.current_fcf_per_share == Decimal("7.20")
        assert snapshot.fcf_growth_rate == Decimal("11.5")
        assert snapshot.fcf_multiple == Decimal("21.0")
        assert snapshot.desired_return == Decimal("16.0")
        assert snapshot.projection_years == 7
        assert snapshot.preferred_valuation_method == "FCF"
