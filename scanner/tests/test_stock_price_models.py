"""
Tests for Phase 8: Stock Price Integration - CuratedStock model methods.

This module tests the price-related model methods added in Phase 8:
- get_discount_percentage()
- get_undervaluation_tier()
- is_undervalued()
- is_price_stale()
- price_age_display property
"""

import pytest
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone

from scanner.factories import CuratedStockFactory
from scanner.models import CuratedStock


# ===== get_discount_percentage() Tests =====

@pytest.mark.django_db
class TestGetDiscountPercentage:
    """Tests for get_discount_percentage() model method."""

    def test_get_discount_percentage_undervalued_stock(self):
        """Test discount calculation when price < intrinsic value (undervalued)."""
        # Arrange
        stock = CuratedStockFactory(
            symbol="AAPL",
            intrinsic_value=Decimal('150.00'),
            current_price=Decimal('120.00'),
            preferred_valuation_method='EPS'
        )

        # Act
        discount = stock.get_discount_percentage()

        # Assert
        # ((150 - 120) / 150) * 100 = 20.0%
        assert discount == Decimal('20.0')

    def test_get_discount_percentage_overvalued_stock(self):
        """Test discount calculation when price > intrinsic value (negative discount)."""
        # Arrange
        stock = CuratedStockFactory(
            symbol="MSFT",
            intrinsic_value=Decimal('100.00'),
            current_price=Decimal('120.00'),
            preferred_valuation_method='EPS'
        )

        # Act
        discount = stock.get_discount_percentage()

        # Assert
        # ((100 - 120) / 100) * 100 = -20.0%
        assert discount == Decimal('-20.0')

    def test_get_discount_percentage_fairly_valued_stock(self):
        """Test discount calculation when price equals intrinsic value."""
        # Arrange
        stock = CuratedStockFactory(
            symbol="GOOGL",
            intrinsic_value=Decimal('100.00'),
            current_price=Decimal('100.00'),
            preferred_valuation_method='EPS'
        )

        # Act
        discount = stock.get_discount_percentage()

        # Assert
        # ((100 - 100) / 100) * 100 = 0.0%
        assert discount == Decimal('0.0')

    def test_get_discount_percentage_uses_fcf_when_preferred(self):
        """Test that FCF intrinsic value is used when preferred method is FCF."""
        # Arrange
        stock = CuratedStockFactory(
            symbol="AMZN",
            intrinsic_value=Decimal('100.00'),  # EPS method
            intrinsic_value_fcf=Decimal('150.00'),  # FCF method
            current_price=Decimal('120.00'),
            preferred_valuation_method='FCF'  # Prefer FCF
        )

        # Act
        discount = stock.get_discount_percentage()

        # Assert
        # Uses FCF: ((150 - 120) / 150) * 100 = 20.0%
        assert discount == Decimal('20.0')

    def test_get_discount_percentage_missing_price_returns_none(self):
        """Test that None price returns None discount."""
        # Arrange
        stock = CuratedStockFactory(
            symbol="TSLA",
            intrinsic_value=Decimal('150.00'),
            current_price=None,
            preferred_valuation_method='EPS'
        )

        # Act
        discount = stock.get_discount_percentage()

        # Assert
        assert discount is None

    def test_get_discount_percentage_missing_intrinsic_value_returns_none(self):
        """Test that None intrinsic value returns None discount."""
        # Arrange
        stock = CuratedStockFactory(
            symbol="NVDA",
            intrinsic_value=None,
            current_price=Decimal('120.00'),
            preferred_valuation_method='EPS'
        )

        # Act
        discount = stock.get_discount_percentage()

        # Assert
        assert discount is None

    def test_get_discount_percentage_both_missing_returns_none(self):
        """Test that missing both price and IV returns None."""
        # Arrange
        stock = CuratedStockFactory(
            symbol="META",
            intrinsic_value=None,
            current_price=None,
            preferred_valuation_method='EPS'
        )

        # Act
        discount = stock.get_discount_percentage()

        # Assert
        assert discount is None

    def test_get_discount_percentage_rounds_to_one_decimal(self):
        """Test that discount percentage is rounded to 1 decimal place."""
        # Arrange
        stock = CuratedStockFactory(
            symbol="IBM",
            intrinsic_value=Decimal('123.45'),
            current_price=Decimal('100.00'),
            preferred_valuation_method='EPS'
        )

        # Act
        discount = stock.get_discount_percentage()

        # Assert
        # ((123.45 - 100) / 123.45) * 100 = 18.9818... → 19.0
        assert discount == Decimal('19.0')


# ===== get_undervaluation_tier() Tests =====

@pytest.mark.django_db
class TestGetUndervaluationTier:
    """Tests for get_undervaluation_tier() model method."""

    def test_get_undervaluation_tier_overvalued(self):
        """Test tier for overvalued stock (negative discount)."""
        # Arrange
        stock = CuratedStockFactory(
            symbol="OVR1",
            intrinsic_value=Decimal('100.00'),
            current_price=Decimal('120.00'),
            preferred_valuation_method='EPS'
        )

        # Act
        tier = stock.get_undervaluation_tier()

        # Assert
        assert tier == 'overvalued'

    def test_get_undervaluation_tier_slate(self):
        """Test tier for 0-9% discount (slate tier)."""
        # Arrange
        stock = CuratedStockFactory(
            symbol="SLT1",
            intrinsic_value=Decimal('100.00'),
            current_price=Decimal('95.00'),  # 5% discount
            preferred_valuation_method='EPS'
        )

        # Act
        tier = stock.get_undervaluation_tier()

        # Assert
        assert tier == 'slate'

    def test_get_undervaluation_tier_slate_edge_case(self):
        """Test tier at 9.9% discount (still slate)."""
        # Arrange
        stock = CuratedStockFactory(
            symbol="SLT2",
            intrinsic_value=Decimal('100.00'),
            current_price=Decimal('90.10'),  # 9.9% discount
            preferred_valuation_method='EPS'
        )

        # Act
        tier = stock.get_undervaluation_tier()

        # Assert
        assert tier == 'slate'

    def test_get_undervaluation_tier_yellow(self):
        """Test tier for 10-19% discount (yellow tier)."""
        # Arrange
        stock = CuratedStockFactory(
            symbol="YLW1",
            intrinsic_value=Decimal('100.00'),
            current_price=Decimal('85.00'),  # 15% discount
            preferred_valuation_method='EPS'
        )

        # Act
        tier = stock.get_undervaluation_tier()

        # Assert
        assert tier == 'yellow'

    def test_get_undervaluation_tier_yellow_boundary(self):
        """Test tier at exactly 10% discount (yellow)."""
        # Arrange
        stock = CuratedStockFactory(
            symbol="YLW2",
            intrinsic_value=Decimal('100.00'),
            current_price=Decimal('90.00'),  # Exactly 10%
            preferred_valuation_method='EPS'
        )

        # Act
        tier = stock.get_undervaluation_tier()

        # Assert
        assert tier == 'yellow'

    def test_get_undervaluation_tier_orange(self):
        """Test tier for 20-29% discount (orange tier)."""
        # Arrange
        stock = CuratedStockFactory(
            symbol="ORG1",
            intrinsic_value=Decimal('100.00'),
            current_price=Decimal('75.00'),  # 25% discount
            preferred_valuation_method='EPS'
        )

        # Act
        tier = stock.get_undervaluation_tier()

        # Assert
        assert tier == 'orange'

    def test_get_undervaluation_tier_orange_boundary(self):
        """Test tier at exactly 20% discount (orange)."""
        # Arrange
        stock = CuratedStockFactory(
            symbol="ORG2",
            intrinsic_value=Decimal('100.00'),
            current_price=Decimal('80.00'),  # Exactly 20%
            preferred_valuation_method='EPS'
        )

        # Act
        tier = stock.get_undervaluation_tier()

        # Assert
        assert tier == 'orange'

    def test_get_undervaluation_tier_green(self):
        """Test tier for 30%+ discount (green tier - best deal)."""
        # Arrange
        stock = CuratedStockFactory(
            symbol="GRN1",
            intrinsic_value=Decimal('100.00'),
            current_price=Decimal('60.00'),  # 40% discount
            preferred_valuation_method='EPS'
        )

        # Act
        tier = stock.get_undervaluation_tier()

        # Assert
        assert tier == 'green'

    def test_get_undervaluation_tier_green_boundary(self):
        """Test tier at exactly 30% discount (green)."""
        # Arrange
        stock = CuratedStockFactory(
            symbol="GRN2",
            intrinsic_value=Decimal('100.00'),
            current_price=Decimal('70.00'),  # Exactly 30%
            preferred_valuation_method='EPS'
        )

        # Act
        tier = stock.get_undervaluation_tier()

        # Assert
        assert tier == 'green'

    def test_get_undervaluation_tier_missing_data_returns_none(self):
        """Test that missing price or IV returns None tier."""
        # Arrange
        stock = CuratedStockFactory(
            symbol="NONE",
            intrinsic_value=None,
            current_price=None,
            preferred_valuation_method='EPS'
        )

        # Act
        tier = stock.get_undervaluation_tier()

        # Assert
        assert tier is None


# ===== is_undervalued() Tests =====

@pytest.mark.django_db
class TestIsUndervalued:
    """Tests for is_undervalued() model method."""

    def test_is_undervalued_returns_true_when_price_below_iv(self):
        """Test that undervalued stock returns True."""
        # Arrange
        stock = CuratedStockFactory(
            symbol="AAPL",
            intrinsic_value=Decimal('150.00'),
            current_price=Decimal('120.00'),
            preferred_valuation_method='EPS'
        )

        # Act
        result = stock.is_undervalued()

        # Assert
        assert result is True

    def test_is_undervalued_returns_false_when_price_above_iv(self):
        """Test that overvalued stock returns False."""
        # Arrange
        stock = CuratedStockFactory(
            symbol="MSFT",
            intrinsic_value=Decimal('100.00'),
            current_price=Decimal('120.00'),
            preferred_valuation_method='EPS'
        )

        # Act
        result = stock.is_undervalued()

        # Assert
        assert result is False

    def test_is_undervalued_returns_false_when_price_equals_iv(self):
        """Test that fairly valued stock returns False (not undervalued)."""
        # Arrange
        stock = CuratedStockFactory(
            symbol="GOOGL",
            intrinsic_value=Decimal('100.00'),
            current_price=Decimal('100.00'),
            preferred_valuation_method='EPS'
        )

        # Act
        result = stock.is_undervalued()

        # Assert
        assert result is False

    def test_is_undervalued_uses_fcf_method_when_preferred(self):
        """Test that FCF intrinsic value is used when preferred."""
        # Arrange
        stock = CuratedStockFactory(
            symbol="AMZN",
            intrinsic_value=Decimal('100.00'),  # EPS - would be overvalued
            intrinsic_value_fcf=Decimal('150.00'),  # FCF - is undervalued
            current_price=Decimal('120.00'),
            preferred_valuation_method='FCF'
        )

        # Act
        result = stock.is_undervalued()

        # Assert
        assert result is True  # 120 < 150 (FCF)

    def test_is_undervalued_returns_false_when_price_missing(self):
        """Test that missing price returns False."""
        # Arrange
        stock = CuratedStockFactory(
            symbol="TSLA",
            intrinsic_value=Decimal('150.00'),
            current_price=None,
            preferred_valuation_method='EPS'
        )

        # Act
        result = stock.is_undervalued()

        # Assert
        assert result is False

    def test_is_undervalued_returns_false_when_iv_missing(self):
        """Test that missing intrinsic value returns False."""
        # Arrange
        stock = CuratedStockFactory(
            symbol="NVDA",
            intrinsic_value=None,
            current_price=Decimal('120.00'),
            preferred_valuation_method='EPS'
        )

        # Act
        result = stock.is_undervalued()

        # Assert
        assert result is False

    def test_is_undervalued_returns_false_when_both_missing(self):
        """Test that missing both price and IV returns False."""
        # Arrange
        stock = CuratedStockFactory(
            symbol="META",
            intrinsic_value=None,
            current_price=None,
            preferred_valuation_method='EPS'
        )

        # Act
        result = stock.is_undervalued()

        # Assert
        assert result is False


# ===== is_price_stale() Tests =====

@pytest.mark.django_db
class TestIsPriceStale:
    """Tests for is_price_stale() model method."""

    def test_is_price_stale_returns_false_for_recent_update(self):
        """Test that recently updated price is not stale."""
        # Arrange
        now = timezone.now()
        stock = CuratedStockFactory(
            symbol="AAPL",
            current_price=Decimal('150.00'),
            price_updated_at=now - timedelta(hours=1)  # 1 hour ago
        )

        # Act
        result = stock.is_price_stale()

        # Assert
        assert result is False

    def test_is_price_stale_returns_true_at_24_hour_boundary(self):
        """Test that price exactly 24 hours old is stale (implementation uses <)."""
        # Arrange
        now = timezone.now()
        stock = CuratedStockFactory(
            symbol="MSFT",
            current_price=Decimal('100.00'),
            price_updated_at=now - timedelta(hours=24)  # Exactly 24 hours
        )

        # Act
        result = stock.is_price_stale()

        # Assert
        assert result is True  # Implementation: price_updated_at < threshold

    def test_is_price_stale_returns_true_for_old_update(self):
        """Test that price older than 24 hours is stale."""
        # Arrange
        now = timezone.now()
        stock = CuratedStockFactory(
            symbol="GOOGL",
            current_price=Decimal('100.00'),
            price_updated_at=now - timedelta(hours=25)  # 25 hours ago
        )

        # Act
        result = stock.is_price_stale()

        # Assert
        assert result is True

    def test_is_price_stale_returns_true_for_very_old_update(self):
        """Test that price from days ago is stale."""
        # Arrange
        now = timezone.now()
        stock = CuratedStockFactory(
            symbol="AMZN",
            current_price=Decimal('150.00'),
            price_updated_at=now - timedelta(days=7)  # 1 week ago
        )

        # Act
        result = stock.is_price_stale()

        # Assert
        assert result is True

    def test_is_price_stale_returns_true_when_timestamp_missing(self):
        """Test that missing timestamp is considered stale."""
        # Arrange
        stock = CuratedStockFactory(
            symbol="TSLA",
            current_price=Decimal('200.00'),
            price_updated_at=None
        )

        # Act
        result = stock.is_price_stale()

        # Assert
        assert result is True

    def test_is_price_stale_custom_threshold_hours(self):
        """Test is_price_stale() with custom threshold."""
        # Arrange
        now = timezone.now()
        stock = CuratedStockFactory(
            symbol="NVDA",
            current_price=Decimal('100.00'),
            price_updated_at=now - timedelta(hours=10)
        )

        # Act & Assert
        assert stock.is_price_stale(hours=12) is False  # 10 hours < 12 hours
        assert stock.is_price_stale(hours=8) is True   # 10 hours > 8 hours


# ===== price_age_display Property Tests =====

@pytest.mark.django_db
class TestPriceAgeDisplay:
    """Tests for price_age_display property."""

    def test_price_age_display_returns_never_when_no_timestamp(self):
        """Test that missing timestamp returns 'Never'."""
        # Arrange
        stock = CuratedStockFactory(
            symbol="AAPL",
            current_price=None,
            price_updated_at=None
        )

        # Act
        result = stock.price_age_display

        # Assert
        assert result == "Never"

    def test_price_age_display_shows_recent_update(self):
        """Test that recent update shows human-readable time."""
        # Arrange
        now = timezone.now()
        stock = CuratedStockFactory(
            symbol="MSFT",
            current_price=Decimal('100.00'),
            price_updated_at=now - timedelta(minutes=30)
        )

        # Act
        result = stock.price_age_display

        # Assert
        assert "ago" in result
        assert "minute" in result or "30" in result

    def test_price_age_display_shows_hours_ago(self):
        """Test that hours-old update is formatted correctly."""
        # Arrange
        now = timezone.now()
        stock = CuratedStockFactory(
            symbol="GOOGL",
            current_price=Decimal('100.00'),
            price_updated_at=now - timedelta(hours=5)
        )

        # Act
        result = stock.price_age_display

        # Assert
        assert "ago" in result
        assert "hour" in result or "5" in result

    def test_price_age_display_shows_days_ago(self):
        """Test that days-old update is formatted correctly."""
        # Arrange
        now = timezone.now()
        stock = CuratedStockFactory(
            symbol="AMZN",
            current_price=Decimal('150.00'),
            price_updated_at=now - timedelta(days=3)
        )

        # Act
        result = stock.price_age_display

        # Assert
        assert "ago" in result
        assert "day" in result or "3" in result


# ===== Integration Tests =====

@pytest.mark.django_db
class TestStockPriceModelIntegration:
    """Integration tests for stock price model methods."""

    def test_complete_workflow_undervalued_stock_with_fresh_price(self):
        """Test complete workflow for an undervalued stock with fresh price."""
        # Arrange
        now = timezone.now()
        stock = CuratedStockFactory(
            symbol="BARGAIN",
            intrinsic_value=Decimal('150.00'),
            current_price=Decimal('100.00'),
            price_updated_at=now - timedelta(hours=2),
            preferred_valuation_method='EPS'
        )

        # Act & Assert
        assert stock.is_undervalued() is True
        assert stock.is_price_stale() is False
        assert stock.get_discount_percentage() == Decimal('33.3')
        assert stock.get_undervaluation_tier() == 'green'
        assert "ago" in stock.price_age_display

    def test_complete_workflow_overvalued_stock_with_stale_price(self):
        """Test complete workflow for an overvalued stock with stale price."""
        # Arrange
        now = timezone.now()
        stock = CuratedStockFactory(
            symbol="EXPENSIVE",
            intrinsic_value=Decimal('100.00'),
            current_price=Decimal('150.00'),
            price_updated_at=now - timedelta(days=2),
            preferred_valuation_method='EPS'
        )

        # Act & Assert
        assert stock.is_undervalued() is False
        assert stock.is_price_stale() is True
        assert stock.get_discount_percentage() == Decimal('-50.0')
        assert stock.get_undervaluation_tier() == 'overvalued'
        assert "day" in stock.price_age_display

    def test_complete_workflow_missing_price_data(self):
        """Test complete workflow when price data is missing."""
        # Arrange
        stock = CuratedStockFactory(
            symbol="NODATA",
            intrinsic_value=Decimal('150.00'),
            current_price=None,
            price_updated_at=None,
            preferred_valuation_method='EPS'
        )

        # Act & Assert
        assert stock.is_undervalued() is False
        assert stock.is_price_stale() is True
        assert stock.get_discount_percentage() is None
        assert stock.get_undervaluation_tier() is None
        assert stock.price_age_display == "Never"

    def test_complete_workflow_missing_intrinsic_value(self):
        """Test complete workflow when intrinsic value is missing."""
        # Arrange
        now = timezone.now()
        stock = CuratedStockFactory(
            symbol="NOIV",
            intrinsic_value=None,
            current_price=Decimal('100.00'),
            price_updated_at=now - timedelta(hours=1),
            preferred_valuation_method='EPS'
        )

        # Act & Assert
        assert stock.is_undervalued() is False
        assert stock.is_price_stale() is False
        assert stock.get_discount_percentage() is None
        assert stock.get_undervaluation_tier() is None
        assert "ago" in stock.price_age_display

    def test_fcf_method_preference_across_all_methods(self):
        """Test that FCF preference is respected across all price methods."""
        # Arrange
        now = timezone.now()
        stock = CuratedStockFactory(
            symbol="FCFPREF",
            intrinsic_value=Decimal('100.00'),  # EPS
            intrinsic_value_fcf=Decimal('200.00'),  # FCF
            current_price=Decimal('150.00'),
            price_updated_at=now - timedelta(hours=1),
            preferred_valuation_method='FCF'
        )

        # Act & Assert - All methods should use FCF value (200.00)
        assert stock.is_undervalued() is True  # 150 < 200
        assert stock.get_discount_percentage() == Decimal('25.0')  # (200-150)/200
        assert stock.get_undervaluation_tier() == 'orange'  # 25% discount
