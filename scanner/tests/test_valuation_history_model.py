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

    def test_create_snapshot(self):
        """Test creating a valuation snapshot."""
        stock = CuratedStock.objects.create(symbol="TEST1")

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

    def test_unique_constraint(self):
        """Test unique constraint prevents duplicate snapshots."""
        stock = CuratedStock.objects.create(symbol="TEST2")

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

        # Attempt to create duplicate
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
        stock = CuratedStock.objects.create(symbol="TEST3")
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
        stock = CuratedStock.objects.create(symbol="TEST4")
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

    def test_quarter_label_property(self):
        """Test quarter_label returns correct format."""
        stock = CuratedStock.objects.create(symbol="TEST5")

        # Q1
        snapshot_q1 = ValuationHistory.objects.create(
            stock=stock,
            snapshot_date=date(2025, 1, 1),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )
        assert snapshot_q1.quarter_label == "Q1 2025"

        # Q2
        snapshot_q2 = ValuationHistory.objects.create(
            stock=stock,
            snapshot_date=date(2025, 4, 1),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )
        assert snapshot_q2.quarter_label == "Q2 2025"

        # Q3
        snapshot_q3 = ValuationHistory.objects.create(
            stock=stock,
            snapshot_date=date(2025, 7, 1),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )
        assert snapshot_q3.quarter_label == "Q3 2025"

        # Q4
        snapshot_q4 = ValuationHistory.objects.create(
            stock=stock,
            snapshot_date=date(2025, 10, 1),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )
        assert snapshot_q4.quarter_label == "Q4 2025"

    def test_cascade_delete(self):
        """Test CASCADE delete removes history when stock deleted."""
        stock = CuratedStock.objects.create(symbol="TEST6")
        stock_id = stock.id

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

        assert ValuationHistory.objects.filter(stock_id=stock_id).count() == 1

        stock.delete()

        assert ValuationHistory.objects.filter(stock_id=stock_id).count() == 0

    def test_ordering(self):
        """Test default ordering is by snapshot_date descending."""
        stock = CuratedStock.objects.create(symbol="TEST7")

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

        history = list(ValuationHistory.objects.filter(stock=stock))

        assert history[0] == snapshot2  # Newest first
        assert history[1] == snapshot1

    def test_str_representation(self):
        """Test __str__ returns correct format."""
        stock = CuratedStock.objects.create(symbol="TEST8")
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

        assert str(snapshot) == "TEST8 - 2025-01-01"

    def test_notes_field(self):
        """Test notes field is optional and stores text."""
        stock = CuratedStock.objects.create(symbol="TEST9")
        snapshot = ValuationHistory.objects.create(
            stock=stock,
            snapshot_date=date(2025, 1, 1),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
            notes="Adjusted growth rate due to market conditions",
        )

        assert snapshot.notes == "Adjusted growth rate due to market conditions"
