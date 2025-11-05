import pytest
from decimal import Decimal

from scanner.valuation import (
    calculate_intrinsic_value,
    calculate_terminal_value,
    discount_eps_series,
    discount_to_present_value,
    project_eps,
)


class TestProjectEPS:
    """Test EPS projection function."""

    def test_project_eps_with_10_percent_growth(self):
        """Test EPS projection with 10% annual growth over 5 years."""
        result = project_eps(Decimal("5.00"), Decimal("10.0"), 5)
        assert len(result) == 5
        assert result[0] == Decimal("5.50")  # Year 1: 5.00 * 1.10
        assert result[1] == Decimal("6.05")  # Year 2: 5.00 * 1.10^2
        assert result[4] == Decimal("8.05")  # Year 5: 5.00 * 1.10^5

    def test_project_eps_with_zero_growth(self):
        """Test EPS projection with 0% growth (should remain constant)."""
        result = project_eps(Decimal("5.00"), Decimal("0.0"), 5)
        assert all(eps == Decimal("5.00") for eps in result)

    def test_project_eps_with_negative_growth(self):
        """Test EPS projection with negative growth (declining earnings)."""
        result = project_eps(Decimal("5.00"), Decimal("-5.0"), 3)
        assert result[0] < Decimal("5.00")
        assert result[2] < result[1] < result[0]

    def test_project_eps_one_year(self):
        """Test EPS projection for single year."""
        result = project_eps(Decimal("10.00"), Decimal("15.0"), 1)
        assert len(result) == 1
        assert result[0] == Decimal("11.50")

    def test_project_eps_precision(self):
        """Test that results are rounded to 2 decimal places."""
        result = project_eps(Decimal("3.33"), Decimal("7.7"), 3)
        for eps in result:
            # Check that we have at most 2 decimal places
            assert eps == eps.quantize(Decimal("0.01"))


class TestCalculateTerminalValue:
    """Test terminal value calculation."""

    def test_terminal_value_basic(self):
        """Test basic terminal value calculation."""
        result = calculate_terminal_value(Decimal("8.05"), Decimal("20.0"))
        assert result == Decimal("161.00")

    def test_terminal_value_with_one_multiple(self):
        """Test terminal value with 1x multiple (should equal EPS)."""
        result = calculate_terminal_value(Decimal("10.00"), Decimal("1.0"))
        assert result == Decimal("10.00")

    def test_terminal_value_precision(self):
        """Test terminal value rounding to 2 decimal places."""
        result = calculate_terminal_value(Decimal("7.77"), Decimal("15.5"))
        assert result == result.quantize(Decimal("0.01"))


class TestDiscountToPresentValue:
    """Test present value discounting."""

    def test_discount_5_years_15_percent(self):
        """Test discounting $100 at 15% for 5 years."""
        result = discount_to_present_value(Decimal("100.00"), Decimal("15.0"), 5)
        # Expected: 100 / (1.15^5) ≈ 49.72
        assert result == Decimal("49.72")

    def test_discount_zero_rate(self):
        """Test discounting with 0% rate (should equal future value)."""
        result = discount_to_present_value(Decimal("100.00"), Decimal("0.0"), 5)
        assert result == Decimal("100.00")

    def test_discount_one_year(self):
        """Test discounting for 1 year."""
        result = discount_to_present_value(Decimal("115.00"), Decimal("15.0"), 1)
        assert result == Decimal("100.00")

    def test_discount_precision(self):
        """Test that result is rounded to 2 decimal places."""
        result = discount_to_present_value(Decimal("123.45"), Decimal("12.3"), 7)
        assert result == result.quantize(Decimal("0.01"))


class TestDiscountEPSSeries:
    """Test discounting series of EPS values."""

    def test_discount_series(self):
        """Test discounting a series of projected EPS."""
        eps = [Decimal("5.50"), Decimal("6.05"), Decimal("6.66")]
        result = discount_eps_series(eps, Decimal("15.0"))

        assert len(result) == 3
        # Each subsequent year should have progressively lower PV
        assert result[0] > result[1] > result[2]

    def test_discount_empty_series(self):
        """Test discounting empty list."""
        result = discount_eps_series([], Decimal("15.0"))
        assert result == []


class TestCalculateIntrinsicValue:
    """Test complete intrinsic value calculation."""

    def test_intrinsic_value_basic(self):
        """Test intrinsic value calculation with typical values."""
        result = calculate_intrinsic_value(
            current_eps=Decimal("5.00"),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        assert "intrinsic_value" in result
        assert "projected_eps" in result
        assert "terminal_value" in result
        assert "pv_of_eps" in result
        assert "pv_of_terminal" in result
        assert "sum_pv_eps" in result

        # Intrinsic value should be positive and reasonable
        assert result["intrinsic_value"] > Decimal("0")

        # Verify calculation components
        assert len(result["projected_eps"]) == 5
        assert len(result["pv_of_eps"]) == 5
        # Intrinsic value = sum of PV of EPS + PV of terminal value
        calculated_iv = result["sum_pv_eps"] + result["pv_of_terminal"]
        assert result["intrinsic_value"] == calculated_iv.quantize(Decimal("0.01"))

    def test_intrinsic_value_with_default_params(self):
        """Test using default parameter values from CuratedStock model."""
        result = calculate_intrinsic_value(
            current_eps=Decimal("6.00"),
            eps_growth_rate=Decimal("10.0"),  # Default
            eps_multiple=Decimal("20.0"),  # Default
            desired_return=Decimal("15.0"),  # Default
            projection_years=5,  # Default
        )

        assert result["intrinsic_value"] > Decimal("0")

    def test_intrinsic_value_high_growth(self):
        """Test with high growth rate."""
        result = calculate_intrinsic_value(
            current_eps=Decimal("5.00"),
            eps_growth_rate=Decimal("25.0"),  # High growth
            eps_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        # Higher growth should result in higher intrinsic value
        assert result["intrinsic_value"] > Decimal("100.00")

    def test_intrinsic_value_invalid_eps(self):
        """Test that negative or zero EPS raises ValueError."""
        with pytest.raises(ValueError, match="Current EPS must be greater than 0"):
            calculate_intrinsic_value(
                current_eps=Decimal("0.00"),
                eps_growth_rate=Decimal("10.0"),
                eps_multiple=Decimal("20.0"),
                desired_return=Decimal("15.0"),
            )

    def test_intrinsic_value_invalid_years(self):
        """Test that invalid projection years raises ValueError."""
        with pytest.raises(ValueError, match="Projection years must be at least 1"):
            calculate_intrinsic_value(
                current_eps=Decimal("5.00"),
                eps_growth_rate=Decimal("10.0"),
                eps_multiple=Decimal("20.0"),
                desired_return=Decimal("15.0"),
                projection_years=0,
            )

    def test_intrinsic_value_precision(self):
        """Test that intrinsic value is rounded to 2 decimal places."""
        result = calculate_intrinsic_value(
            current_eps=Decimal("7.77"),
            eps_growth_rate=Decimal("11.11"),
            eps_multiple=Decimal("18.88"),
            desired_return=Decimal("13.33"),
            projection_years=5,
        )

        assert result["intrinsic_value"] == result["intrinsic_value"].quantize(
            Decimal("0.01")
        )

    def test_intrinsic_value_known_calculation(self):
        """Test with known values to verify calculation accuracy."""
        # Using the example from the task documentation
        result = calculate_intrinsic_value(
            current_eps=Decimal("5.00"),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        # Expected: around $101.97 based on manual calculation
        # Allowing for rounding differences
        assert Decimal("101.00") < result["intrinsic_value"] < Decimal("103.00")

        # Verify terminal value
        assert result["terminal_value"] == Decimal("161.00")  # 8.05 * 20

        # Verify final year EPS
        assert result["projected_eps"][-1] == Decimal("8.05")
