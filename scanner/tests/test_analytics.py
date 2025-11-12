"""
Unit tests for analytics module functions.

Test coverage:
- calculate_volatility(): standard deviation, coefficient of variation, edge cases
- calculate_cagr(): growth rate calculations, quarterly to annual conversion
- calculate_correlation(): Pearson correlation coefficient, edge cases
- calculate_sensitivity(): DCF assumption adjustments for EPS and FCF methods
- get_stock_analytics(): comprehensive stock metrics compilation
- get_portfolio_analytics(): portfolio-wide aggregation

Edge cases tested:
- Empty data lists
- Single data point
- None values in data
- Zero division scenarios
- Mismatched list lengths
- Invalid assumption names
"""

import pytest
from decimal import Decimal
from datetime import date
from scanner.analytics import (
    calculate_volatility,
    calculate_cagr,
    calculate_correlation,
    calculate_sensitivity,
    get_stock_analytics,
    get_portfolio_analytics,
)
from scanner.models import CuratedStock, ValuationHistory


@pytest.mark.django_db
class TestCalculateVolatility:
    """Tests for calculate_volatility() function."""

    def test_volatility_with_valid_data(self):
        """Test volatility calculation with valid data points."""
        values = [100.0, 105.0, 110.0, 102.0, 108.0]
        result = calculate_volatility(values)

        assert result['std_dev'] is not None
        assert result['coefficient_of_variation'] is not None
        assert result['mean'] is not None
        assert result['std_dev'] > 0
        assert result['mean'] == pytest.approx(105.0, abs=0.1)

    def test_volatility_with_empty_list(self):
        """Test volatility with empty list returns None values."""
        result = calculate_volatility([])

        assert result['std_dev'] is None
        assert result['coefficient_of_variation'] is None
        assert result['mean'] is None

    def test_volatility_with_single_value(self):
        """Test volatility with single value returns mean only."""
        result = calculate_volatility([100.0])

        assert result['std_dev'] is None
        assert result['coefficient_of_variation'] is None
        assert result['mean'] == 100.0

    def test_volatility_with_none_values(self):
        """Test volatility filters out None values."""
        values = [100.0, None, 110.0, None, 105.0]
        result = calculate_volatility(values)

        # Should calculate based on 3 values: 100, 110, 105
        assert result['std_dev'] is not None
        assert result['mean'] == pytest.approx(105.0, abs=0.1)

    def test_volatility_with_all_none_values(self):
        """Test volatility with all None values returns None."""
        values = [None, None, None]
        result = calculate_volatility(values)

        assert result['std_dev'] is None
        assert result['coefficient_of_variation'] is None
        assert result['mean'] is None

    def test_volatility_with_zero_mean(self):
        """Test coefficient of variation with zero mean."""
        values = [0.0, 0.0, 0.0]
        result = calculate_volatility(values)

        assert result['std_dev'] == 0.0
        assert result['coefficient_of_variation'] is None
        assert result['mean'] == 0.0

    def test_volatility_coefficient_calculation(self):
        """Test coefficient of variation is calculated correctly."""
        values = [100.0, 110.0, 90.0]
        result = calculate_volatility(values)

        # CV = (std_dev / mean) * 100
        expected_cv = (result['std_dev'] / result['mean']) * 100
        assert result['coefficient_of_variation'] == pytest.approx(expected_cv, abs=0.01)


@pytest.mark.django_db
class TestCalculateCAGR:
    """Tests for calculate_cagr() function."""

    def test_cagr_with_valid_growth(self):
        """Test CAGR calculation with positive growth."""
        # 8 quarters = 2 years, 100 -> 121 = 10% annual growth
        result = calculate_cagr(100.0, 121.0, 8)

        assert result is not None
        assert result == pytest.approx(10.0, abs=0.1)

    def test_cagr_with_negative_growth(self):
        """Test CAGR calculation with negative growth."""
        # 8 quarters = 2 years, 100 -> 81 = -10% annual growth
        result = calculate_cagr(100.0, 81.0, 8)

        assert result is not None
        assert result < 0
        assert result == pytest.approx(-10.0, abs=0.1)

    def test_cagr_with_none_values(self):
        """Test CAGR with None values returns None."""
        assert calculate_cagr(None, 121.0, 8) is None
        assert calculate_cagr(100.0, None, 8) is None
        assert calculate_cagr(None, None, 8) is None

    def test_cagr_with_zero_start_value(self):
        """Test CAGR with zero start value returns None."""
        result = calculate_cagr(0.0, 100.0, 8)

        assert result is None

    def test_cagr_with_negative_start_value(self):
        """Test CAGR with negative start value returns None."""
        result = calculate_cagr(-100.0, 121.0, 8)

        assert result is None

    def test_cagr_with_zero_periods(self):
        """Test CAGR with zero periods returns None."""
        result = calculate_cagr(100.0, 121.0, 0)

        assert result is None

    def test_cagr_with_single_quarter(self):
        """Test CAGR with single quarter (0.25 years)."""
        # Single quarter growth
        result = calculate_cagr(100.0, 105.0, 1)

        assert result is not None
        # Should annualize the growth rate
        assert result > 0

    def test_cagr_quarterly_to_annual_conversion(self):
        """Test that quarters are correctly converted to years."""
        # 4 quarters = 1 year
        result_4q = calculate_cagr(100.0, 110.0, 4)
        # 8 quarters = 2 years
        result_8q = calculate_cagr(100.0, 110.0, 8)

        assert result_4q is not None
        assert result_8q is not None
        # Doubling the time period should roughly halve the CAGR
        assert result_8q < result_4q


@pytest.mark.django_db
class TestCalculateCorrelation:
    """Tests for calculate_correlation() function."""

    def test_correlation_with_perfect_positive(self):
        """Test correlation with perfect positive correlation."""
        x = [100.0, 105.0, 110.0, 115.0]
        y = [100.0, 105.0, 110.0, 115.0]
        result = calculate_correlation(x, y)

        assert result is not None
        assert result == pytest.approx(1.0, abs=0.01)

    def test_correlation_with_perfect_negative(self):
        """Test correlation with perfect negative correlation."""
        x = [100.0, 105.0, 110.0, 115.0]
        y = [115.0, 110.0, 105.0, 100.0]
        result = calculate_correlation(x, y)

        assert result is not None
        assert result == pytest.approx(-1.0, abs=0.01)

    def test_correlation_with_no_correlation(self):
        """Test correlation with no correlation."""
        x = [100.0, 100.0, 100.0, 100.0]
        y = [90.0, 110.0, 95.0, 105.0]
        result = calculate_correlation(x, y)

        # Should return None (constant x has no variance)
        assert result is None

    def test_correlation_with_empty_lists(self):
        """Test correlation with empty lists returns None."""
        assert calculate_correlation([], []) is None
        assert calculate_correlation([100.0], []) is None
        assert calculate_correlation([], [100.0]) is None

    def test_correlation_with_mismatched_lengths(self):
        """Test correlation with mismatched list lengths returns None."""
        x = [100.0, 105.0, 110.0]
        y = [100.0, 105.0]
        result = calculate_correlation(x, y)

        assert result is None

    def test_correlation_with_none_values(self):
        """Test correlation filters out None value pairs."""
        x = [100.0, None, 110.0, 115.0, None]
        y = [100.0, 105.0, None, 115.0, 120.0]
        result = calculate_correlation(x, y)

        # Should calculate based on pairs (100, 100) and (115, 115)
        assert result is not None

    def test_correlation_with_single_valid_pair(self):
        """Test correlation with only one valid pair returns None."""
        x = [100.0, None, None]
        y = [100.0, None, None]
        result = calculate_correlation(x, y)

        assert result is None

    def test_correlation_with_high_positive(self):
        """Test correlation with high positive correlation."""
        x = [100.0, 105.0, 110.0, 115.0]
        y = [98.0, 103.0, 108.0, 113.0]
        result = calculate_correlation(x, y)

        assert result is not None
        assert result > 0.95  # Should be very high positive


@pytest.mark.django_db
class TestCalculateSensitivity:
    """Tests for calculate_sensitivity() function."""

    def test_sensitivity_eps_growth_rate_increase(self):
        """Test sensitivity to EPS growth rate increase."""
        stock = CuratedStock.objects.create(
            symbol="TEST",
            active=True,
            current_eps=Decimal("5.00"),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
            preferred_valuation_method="EPS",
        )

        result = calculate_sensitivity(stock, 'growth_rate', 0.02)

        assert result['original_iv'] is not None
        assert result['adjusted_iv'] is not None
        assert result['change_pct'] is not None
        assert result['method'] == 'EPS'
        assert result['assumption'] == 'growth_rate'
        assert result['delta'] == 0.02
        # Higher growth rate should increase IV
        assert result['adjusted_iv'] > result['original_iv']
        assert result['change_pct'] > 0

    def test_sensitivity_eps_discount_rate_increase(self):
        """Test sensitivity to EPS discount rate increase."""
        stock = CuratedStock.objects.create(
            symbol="TEST",
            active=True,
            current_eps=Decimal("5.00"),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
            preferred_valuation_method="EPS",
        )

        result = calculate_sensitivity(stock, 'discount_rate', 0.02)

        assert result['original_iv'] is not None
        assert result['adjusted_iv'] is not None
        assert result['change_pct'] is not None
        # Higher discount rate should decrease IV
        assert result['adjusted_iv'] < result['original_iv']
        assert result['change_pct'] < 0

    def test_sensitivity_fcf_growth_rate_increase(self):
        """Test sensitivity to FCF growth rate increase."""
        stock = CuratedStock.objects.create(
            symbol="TEST",
            active=True,
            current_fcf_per_share=Decimal("6.00"),
            fcf_growth_rate=Decimal("8.0"),
            fcf_multiple=Decimal("15.0"),
            desired_return=Decimal("12.0"),
            projection_years=5,
            preferred_valuation_method="FCF",
        )

        result = calculate_sensitivity(stock, 'growth_rate', 0.02)

        assert result['original_iv'] is not None
        assert result['adjusted_iv'] is not None
        assert result['method'] == 'FCF'
        # Higher growth rate should increase IV
        assert result['adjusted_iv'] > result['original_iv']

    def test_sensitivity_fcf_discount_rate_decrease(self):
        """Test sensitivity to FCF discount rate decrease."""
        stock = CuratedStock.objects.create(
            symbol="TEST",
            active=True,
            current_fcf_per_share=Decimal("6.00"),
            fcf_growth_rate=Decimal("8.0"),
            fcf_multiple=Decimal("15.0"),
            desired_return=Decimal("12.0"),
            projection_years=5,
            preferred_valuation_method="FCF",
        )

        result = calculate_sensitivity(stock, 'discount_rate', -0.02)

        assert result['original_iv'] is not None
        assert result['adjusted_iv'] is not None
        # Lower discount rate should increase IV
        assert result['adjusted_iv'] > result['original_iv']
        assert result['change_pct'] > 0

    def test_sensitivity_terminal_growth_rate_not_implemented(self):
        """Test sensitivity for terminal_growth_rate returns error."""
        stock = CuratedStock.objects.create(
            symbol="TEST",
            active=True,
            current_eps=Decimal("5.00"),
            preferred_valuation_method="EPS",
        )

        result = calculate_sensitivity(stock, 'terminal_growth_rate', 0.02)

        assert result['original_iv'] is None
        assert result['adjusted_iv'] is None
        assert result['change_pct'] is None
        assert 'error' in result
        assert 'not implemented' in result['error'].lower()

    def test_sensitivity_invalid_assumption_name(self):
        """Test sensitivity with invalid assumption name."""
        stock = CuratedStock.objects.create(
            symbol="TEST",
            active=True,
            current_eps=Decimal("5.00"),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
            preferred_valuation_method="EPS",
        )

        result = calculate_sensitivity(stock, 'invalid_assumption', 0.02)

        assert 'error' in result
        assert 'Unknown assumption' in result['error']

    def test_sensitivity_zero_original_iv(self):
        """Test sensitivity when original IV is zero (edge case)."""
        stock = CuratedStock.objects.create(
            symbol="TEST",
            active=True,
            current_eps=Decimal("0.00"),  # Zero EPS
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
            preferred_valuation_method="EPS",
        )

        result = calculate_sensitivity(stock, 'growth_rate', 0.02)

        # Should handle gracefully with error
        assert result is not None
        assert 'error' in result


@pytest.mark.django_db
class TestGetStockAnalytics:
    """Tests for get_stock_analytics() function."""

    def test_stock_analytics_with_history(self):
        """Test stock analytics with historical data."""
        stock = CuratedStock.objects.create(
            symbol="TEST",
            active=True,
            intrinsic_value=Decimal("150.00"),
            intrinsic_value_fcf=Decimal("145.00"),
            preferred_valuation_method="EPS",
        )

        # Create historical snapshots
        ValuationHistory.objects.create(
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

        ValuationHistory.objects.create(
            stock=stock,
            snapshot_date=date(2024, 10, 1),
            intrinsic_value=Decimal("145.00"),
            intrinsic_value_fcf=Decimal("140.00"),
            preferred_valuation_method="EPS",
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        result = get_stock_analytics("TEST")

        assert result['symbol'] == "TEST"
        assert result['data_points'] == 2
        assert result['eps_volatility'] is not None
        assert result['fcf_volatility'] is not None
        assert result['latest_eps_iv'] == 150.00
        assert result['latest_fcf_iv'] == 145.00
        assert result['preferred_method'] == "EPS"

    def test_stock_analytics_with_no_history(self):
        """Test stock analytics with no historical data."""
        stock = CuratedStock.objects.create(
            symbol="TEST",
            active=True,
            preferred_valuation_method="FCF",
        )

        result = get_stock_analytics("TEST")

        assert result['symbol'] == "TEST"
        assert result['data_points'] == 0
        assert result['eps_volatility'] == {}
        assert result['fcf_volatility'] == {}
        assert result['eps_cagr'] is None
        assert result['fcf_cagr'] is None
        assert result['correlation'] is None
        assert result['latest_eps_iv'] is None
        assert result['latest_fcf_iv'] is None

    def test_stock_analytics_nonexistent_stock(self):
        """Test stock analytics for non-existent stock raises exception."""
        with pytest.raises(CuratedStock.DoesNotExist):
            get_stock_analytics("NONEXISTENT")

    def test_stock_analytics_calculates_highest_lowest_average(self):
        """Test stock analytics calculates highest, lowest, average IV."""
        stock = CuratedStock.objects.create(
            symbol="TEST",
            active=True,
            preferred_valuation_method="EPS",
        )

        # Create snapshots with varying values
        ValuationHistory.objects.create(
            stock=stock,
            snapshot_date=date(2025, 1, 1),
            intrinsic_value=Decimal("150.00"),
            preferred_valuation_method="EPS",
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        ValuationHistory.objects.create(
            stock=stock,
            snapshot_date=date(2024, 10, 1),
            intrinsic_value=Decimal("140.00"),
            preferred_valuation_method="EPS",
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        ValuationHistory.objects.create(
            stock=stock,
            snapshot_date=date(2024, 7, 1),
            intrinsic_value=Decimal("160.00"),
            preferred_valuation_method="EPS",
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        result = get_stock_analytics("TEST")

        assert result['highest_iv'] == 160.00
        assert result['lowest_iv'] == 140.00
        assert result['average_iv'] == pytest.approx(150.00, abs=0.01)

    def test_stock_analytics_cagr_calculation(self):
        """Test stock analytics calculates CAGR correctly."""
        stock = CuratedStock.objects.create(
            symbol="TEST",
            active=True,
            preferred_valuation_method="EPS",
        )

        # Create snapshots spanning 2 years (8 quarters)
        for i, snapshot_date in enumerate([
            date(2023, 1, 1),
            date(2023, 4, 1),
            date(2023, 7, 1),
            date(2023, 10, 1),
            date(2024, 1, 1),
            date(2024, 4, 1),
            date(2024, 7, 1),
            date(2024, 10, 1),
        ]):
            # Simulate 10% annual growth (approximately)
            value = Decimal("100.00") * Decimal(str(1.1 ** (i / 4)))
            ValuationHistory.objects.create(
                stock=stock,
                snapshot_date=snapshot_date,
                intrinsic_value=value,
                preferred_valuation_method="EPS",
                eps_growth_rate=Decimal("10.0"),
                eps_multiple=Decimal("20.0"),
                fcf_growth_rate=Decimal("10.0"),
                fcf_multiple=Decimal("20.0"),
                desired_return=Decimal("15.0"),
                projection_years=5,
            )

        result = get_stock_analytics("TEST")

        assert result['effective_cagr'] is not None
        # CAGR should be approximately 10%
        assert result["effective_cagr"] == pytest.approx(10.0, abs=2.0)


@pytest.mark.django_db
class TestGetPortfolioAnalytics:
    """Tests for get_portfolio_analytics() function."""

    def test_portfolio_analytics_with_multiple_stocks(self):
        """Test portfolio analytics with multiple active stocks."""
        # Create multiple stocks with history
        for i, symbol in enumerate(["TEST1", "TEST2", "TEST3"]):
            stock = CuratedStock.objects.create(
                symbol=symbol,
                active=True,
                preferred_valuation_method="EPS",
            )

            ValuationHistory.objects.create(
                stock=stock,
                snapshot_date=date(2025, 1, 1),
                intrinsic_value=Decimal(str(100.0 + i * 10)),
                preferred_valuation_method="EPS",
                eps_growth_rate=Decimal("10.0"),
                eps_multiple=Decimal("20.0"),
                fcf_growth_rate=Decimal("10.0"),
                fcf_multiple=Decimal("20.0"),
                desired_return=Decimal("15.0"),
                projection_years=5,
            )

        result = get_portfolio_analytics()

        assert result['total_stocks'] == 3
        assert result['stocks_with_history'] == 3
        assert result['portfolio_stats']['total_data_points'] == 3
        assert result['portfolio_stats']['average_iv'] is not None
        assert len(result['stock_analytics']) == 3

    def test_portfolio_analytics_with_no_stocks(self):
        """Test portfolio analytics with no active stocks."""
        result = get_portfolio_analytics()

        assert result['total_stocks'] == 0
        assert result['stocks_with_history'] == 0
        assert result['portfolio_stats']['average_iv'] is None
        assert result['portfolio_stats']['total_data_points'] == 0
        assert result['stock_analytics'] == []

    def test_portfolio_analytics_with_mixed_history(self):
        """Test portfolio analytics with some stocks having no history."""
        # Stock with history
        stock1 = CuratedStock.objects.create(
            symbol="TEST1",
            active=True,
            preferred_valuation_method="EPS",
        )

        ValuationHistory.objects.create(
            stock=stock1,
            snapshot_date=date(2025, 1, 1),
            intrinsic_value=Decimal("100.00"),
            preferred_valuation_method="EPS",
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        # Stock without history
        CuratedStock.objects.create(
            symbol="TEST2",
            active=True,
            preferred_valuation_method="FCF",
        )

        result = get_portfolio_analytics()

        assert result['total_stocks'] == 2
        assert result['stocks_with_history'] == 1
        assert len(result['stock_analytics']) == 1

    def test_portfolio_analytics_ignores_inactive_stocks(self):
        """Test portfolio analytics ignores inactive stocks."""
        # Active stock with history
        stock1 = CuratedStock.objects.create(
            symbol="TEST1",
            active=True,
            preferred_valuation_method="EPS",
        )

        ValuationHistory.objects.create(
            stock=stock1,
            snapshot_date=date(2025, 1, 1),
            intrinsic_value=Decimal("100.00"),
            preferred_valuation_method="EPS",
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        # Inactive stock with history (should be ignored)
        stock2 = CuratedStock.objects.create(
            symbol="TEST2",
            active=False,
            preferred_valuation_method="EPS",
        )

        ValuationHistory.objects.create(
            stock=stock2,
            snapshot_date=date(2025, 1, 1),
            intrinsic_value=Decimal("200.00"),
            preferred_valuation_method="EPS",
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        result = get_portfolio_analytics()

        assert result['total_stocks'] == 1
        assert result['stocks_with_history'] == 1

    def test_portfolio_analytics_aggregates_correctly(self):
        """Test portfolio analytics calculates correct aggregates."""
        # Create stocks with predictable values
        for symbol, iv_value in [("TEST1", "100.00"), ("TEST2", "200.00"), ("TEST3", "300.00")]:
            stock = CuratedStock.objects.create(
                symbol=symbol,
                active=True,
                preferred_valuation_method="EPS",
            )

            ValuationHistory.objects.create(
                stock=stock,
                snapshot_date=date(2025, 1, 1),
                intrinsic_value=Decimal(iv_value),
                preferred_valuation_method="EPS",
                eps_growth_rate=Decimal("10.0"),
                eps_multiple=Decimal("20.0"),
                fcf_growth_rate=Decimal("10.0"),
                fcf_multiple=Decimal("20.0"),
                desired_return=Decimal("15.0"),
                projection_years=5,
            )

        result = get_portfolio_analytics()

        # Average IV should be 200.00
        assert result['portfolio_stats']['average_iv'] == pytest.approx(200.0, abs=0.1)
        assert result['portfolio_stats']['total_data_points'] == 3
