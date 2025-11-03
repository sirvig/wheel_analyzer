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
