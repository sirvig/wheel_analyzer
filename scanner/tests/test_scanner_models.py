import pytest
from django.db import IntegrityError

from scanner.factories import CuratedStockFactory
from scanner.models import CuratedStock, OptionsWatch


# CuratedStock Model Tests
@pytest.mark.django_db
def test_curated_stock_creation():
    """Test that a CuratedStock can be created with required fields"""
    stock = CuratedStockFactory()
    assert stock.symbol is not None
    assert stock.active is True
    assert stock.created_at is not None
    assert stock.updated_at is not None


@pytest.mark.django_db
def test_curated_stock_unique_symbol():
    """Test that symbol field enforces uniqueness"""
    stock = CuratedStockFactory()
    with pytest.raises(IntegrityError):
        CuratedStockFactory(symbol=stock.symbol)


@pytest.mark.django_db
def test_curated_stock_str_representation():
    """Test the string representation of CuratedStock"""
    stock = CuratedStockFactory()
    assert str(stock) == stock.symbol


@pytest.mark.django_db
def test_curated_stock_default_active():
    """Test that active field defaults to True"""
    stock = CuratedStockFactory()
    assert stock.active is True


@pytest.mark.django_db
def test_curated_stock_optional_notes():
    """Test that notes field is optional"""
    stock = CuratedStockFactory(notes="")
    assert stock.notes == ""
    stock_with_notes = CuratedStockFactory(notes="High priority stock")
    assert stock_with_notes.notes == "High priority stock"


@pytest.mark.django_db
def test_curated_stock_ordering():
    """Test that CuratedStock queryset is ordered by symbol"""
    # Use unique symbols that won't conflict with data migration
    CuratedStockFactory(symbol="ZTEST")
    CuratedStockFactory(symbol="ATEST")
    CuratedStockFactory(symbol="MTEST")

    stocks = CuratedStock.objects.filter(
        symbol__in=["ZTEST", "ATEST", "MTEST"]
    ).order_by("symbol")

    assert stocks[0].symbol == "ATEST"
    assert stocks[1].symbol == "MTEST"
    assert stocks[2].symbol == "ZTEST"


@pytest.mark.django_db
def test_curated_stock_filter_active():
    """Test filtering CuratedStock by active status"""
    # Create stocks with unique test symbols
    active_symbols = [f"ATST{i}" for i in range(5)]
    inactive_symbols = [f"ITST{i}" for i in range(3)]

    for symbol in active_symbols:
        CuratedStockFactory(symbol=symbol, active=True)

    for symbol in inactive_symbols:
        CuratedStockFactory(symbol=symbol, active=False)

    active_stocks = CuratedStock.objects.filter(symbol__in=active_symbols, active=True)
    inactive_stocks = CuratedStock.objects.filter(
        symbol__in=inactive_symbols, active=False
    )

    assert active_stocks.count() == 5
    assert inactive_stocks.count() == 3


# OptionsWatch Model Tests
@pytest.mark.django_db
def test_queryset_get_active_method(options_watch):
    qs = OptionsWatch.objects.get_active()
    assert qs.count() > 0
    assert all([watch.active for watch in qs])


@pytest.mark.django_db
def test_queryset_get_inactive_method(options_watch):
    qs = OptionsWatch.objects.get_inactive()
    assert qs.count() > 0
    assert all([not watch.active for watch in qs])


# CuratedStock Valuation Method Tests
@pytest.mark.django_db
def test_get_effective_intrinsic_value_eps_method():
    """get_effective_intrinsic_value returns EPS value when preferred method is 'EPS'."""
    from decimal import Decimal

    stock = CuratedStockFactory(
        symbol="TESTEPS",
        intrinsic_value=Decimal("150.25"),
        intrinsic_value_fcf=Decimal("148.50"),
        preferred_valuation_method="EPS",
    )

    effective_iv = stock.get_effective_intrinsic_value()

    assert effective_iv == Decimal("150.25")
    assert effective_iv == stock.intrinsic_value


@pytest.mark.django_db
def test_get_effective_intrinsic_value_fcf_method():
    """get_effective_intrinsic_value returns FCF value when preferred method is 'FCF'."""
    from decimal import Decimal

    stock = CuratedStockFactory(
        symbol="TESTFCF",
        intrinsic_value=Decimal("200.00"),
        intrinsic_value_fcf=Decimal("195.75"),
        preferred_valuation_method="FCF",
    )

    effective_iv = stock.get_effective_intrinsic_value()

    assert effective_iv == Decimal("195.75")
    assert effective_iv == stock.intrinsic_value_fcf


@pytest.mark.django_db
def test_get_effective_intrinsic_value_null_eps():
    """get_effective_intrinsic_value returns None when EPS value is NULL."""
    from decimal import Decimal

    stock = CuratedStockFactory(
        symbol="TESTNULL1",
        intrinsic_value=None,
        intrinsic_value_fcf=Decimal("100.00"),
        preferred_valuation_method="EPS",
    )

    effective_iv = stock.get_effective_intrinsic_value()

    assert effective_iv is None


@pytest.mark.django_db
def test_get_effective_intrinsic_value_null_fcf():
    """get_effective_intrinsic_value returns None when FCF value is NULL."""
    from decimal import Decimal

    stock = CuratedStockFactory(
        symbol="TESTNULL2",
        intrinsic_value=Decimal("85.00"),
        intrinsic_value_fcf=None,
        preferred_valuation_method="FCF",
    )

    effective_iv = stock.get_effective_intrinsic_value()

    assert effective_iv is None


@pytest.mark.django_db
def test_get_effective_intrinsic_value_both_null():
    """get_effective_intrinsic_value returns None when both values are NULL."""
    stock = CuratedStockFactory(
        symbol="TESTNULL3",
        intrinsic_value=None,
        intrinsic_value_fcf=None,
        preferred_valuation_method="EPS",
    )

    effective_iv = stock.get_effective_intrinsic_value()

    assert effective_iv is None


@pytest.mark.django_db
def test_get_effective_intrinsic_value_defaults_to_eps():
    """get_effective_intrinsic_value defaults to EPS for unknown method."""
    from decimal import Decimal

    stock = CuratedStockFactory(
        symbol="TESTDEF",
        intrinsic_value=Decimal("120.00"),
        intrinsic_value_fcf=Decimal("115.00"),
        preferred_valuation_method="XXX",  # Invalid method (3 chars max)
    )

    effective_iv = stock.get_effective_intrinsic_value()

    # Should default to EPS
    assert effective_iv == Decimal("120.00")
