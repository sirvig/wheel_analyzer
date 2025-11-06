import pytest
from decimal import Decimal

from scanner.valuation import (
    calculate_fcf_from_quarters,
    calculate_fcf_per_share,
    calculate_intrinsic_value,
    calculate_intrinsic_value_fcf,
    calculate_terminal_value,
    discount_eps_series,
    discount_to_present_value,
    project_eps,
    project_fcf,
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


class TestProjectEPSEdgeCases:
    """Additional edge cases for EPS projection."""

    def test_very_high_eps(self):
        """Test with very high EPS values ($1000+)."""
        result = project_eps(Decimal("1000.00"), Decimal("5.0"), 5)
        assert all(eps > Decimal("1000.00") for eps in result)
        # Verify no overflow or precision loss
        assert result[-1] == result[-1].quantize(Decimal("0.01"))

    def test_very_low_eps(self):
        """Test with very low EPS values ($0.01)."""
        result = project_eps(Decimal("0.01"), Decimal("10.0"), 5)
        # With very low EPS, rounding may cause year 1 to round to same value
        # Check that at least year 5 is higher
        assert result[-1] > Decimal("0.01")  # Year 5 should be higher
        assert all(eps > Decimal("0") for eps in result)

    def test_extreme_growth_rate(self):
        """Test with extreme growth rate (100%+)."""
        result = project_eps(Decimal("5.00"), Decimal("100.0"), 3)
        # 100% growth = doubling each year
        assert result[0] == Decimal("10.00")
        assert result[1] == Decimal("20.00")
        assert result[2] == Decimal("40.00")

    def test_large_negative_growth(self):
        """Test with large negative growth (-50%)."""
        result = project_eps(Decimal("10.00"), Decimal("-50.0"), 3)
        assert result[0] == Decimal("5.00")
        assert result[1] == Decimal("2.50")
        assert result[2] == Decimal("1.25")

    def test_many_years_projection(self):
        """Test projecting 20+ years."""
        result = project_eps(Decimal("5.00"), Decimal("8.0"), 20)
        assert len(result) == 20
        assert result[-1] > result[0]  # Should be larger
        # Verify compound growth accuracy
        assert all(eps == eps.quantize(Decimal("0.01")) for eps in result)


class TestCalculateIntrinsicValueEdgeCases:
    """Additional edge cases for intrinsic value calculation."""

    def test_zero_desired_return(self):
        """Test with 0% desired return (no discounting)."""
        result = calculate_intrinsic_value(
            current_eps=Decimal("5.00"),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            desired_return=Decimal("0.0"),
            projection_years=5,
        )

        # With 0% discount, PV = FV
        # Should be sum of all projected EPS + terminal value
        assert result["intrinsic_value"] > Decimal("180.00")

    def test_very_high_desired_return(self):
        """Test with very high desired return (50%+)."""
        result = calculate_intrinsic_value(
            current_eps=Decimal("5.00"),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            desired_return=Decimal("50.0"),
            projection_years=5,
        )

        # High discount rate should result in lower intrinsic value
        assert result["intrinsic_value"] < Decimal("50.00")

    def test_growth_exceeds_return(self):
        """Test when growth rate exceeds desired return."""
        result = calculate_intrinsic_value(
            current_eps=Decimal("5.00"),
            eps_growth_rate=Decimal("25.0"),  # Higher growth
            eps_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),  # Lower return
            projection_years=5,
        )

        # High growth should result in high intrinsic value
        assert result["intrinsic_value"] > Decimal("150.00")

    def test_return_exceeds_growth(self):
        """Test when desired return exceeds growth rate."""
        result = calculate_intrinsic_value(
            current_eps=Decimal("5.00"),
            eps_growth_rate=Decimal("5.0"),  # Lower growth
            eps_multiple=Decimal("20.0"),
            desired_return=Decimal("20.0"),  # Higher return
            projection_years=5,
        )

        # Low growth + high discount should result in lower IV
        assert result["intrinsic_value"] < Decimal("75.00")

    def test_very_long_projection(self):
        """Test with 15-year projection period."""
        result = calculate_intrinsic_value(
            current_eps=Decimal("5.00"),
            eps_growth_rate=Decimal("10.0"),
            eps_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=15,
        )

        assert len(result["projected_eps"]) == 15
        assert result["intrinsic_value"] > Decimal("0")

    def test_decimal_precision_maintained(self):
        """Test that decimal precision is maintained throughout calculation."""
        result = calculate_intrinsic_value(
            current_eps=Decimal("3.14159"),
            eps_growth_rate=Decimal("7.77"),
            eps_multiple=Decimal("18.88"),
            desired_return=Decimal("13.33"),
            projection_years=5,
        )

        # All results should be quantized to 2 decimal places
        assert result["intrinsic_value"] == result["intrinsic_value"].quantize(
            Decimal("0.01")
        )
        for eps in result["projected_eps"]:
            assert eps == eps.quantize(Decimal("0.01"))


# ============================================================================
# FCF-based DCF Tests
# ============================================================================


class TestCalculateFCFFromQuarters:
    """Test FCF calculation from quarterly data."""

    def test_calculate_fcf_valid_4_quarters(self):
        """Test FCF calculation with valid 4 quarters of data."""
        quarterly_data = {
            "quarterlyReports": [
                {
                    "operatingCashflow": "10000000000",
                    "capitalExpenditures": "-2000000000",
                },
                {
                    "operatingCashflow": "11000000000",
                    "capitalExpenditures": "-2100000000",
                },
                {
                    "operatingCashflow": "10500000000",
                    "capitalExpenditures": "-1900000000",
                },
                {
                    "operatingCashflow": "12000000000",
                    "capitalExpenditures": "-2200000000",
                },
            ]
        }
        result = calculate_fcf_from_quarters(quarterly_data)
        # Sum: (10B+2B) + (11B+2.1B) + (10.5B+1.9B) + (12B+2.2B) = 51.7B
        assert result == Decimal("51700000000.00")

    def test_calculate_fcf_insufficient_quarters(self):
        """Test that error is raised with fewer than 4 quarters."""
        quarterly_data = {
            "quarterlyReports": [
                {
                    "operatingCashflow": "10000000000",
                    "capitalExpenditures": "-2000000000",
                },
                {
                    "operatingCashflow": "11000000000",
                    "capitalExpenditures": "-2100000000",
                },
            ]
        }
        with pytest.raises(ValueError, match="Insufficient quarterly data"):
            calculate_fcf_from_quarters(quarterly_data)

    def test_calculate_fcf_missing_fields(self):
        """Test error handling with missing required fields."""
        quarterly_data = {
            "quarterlyReports": [
                {"operatingCashflow": "10000000000"},  # Missing capitalExpenditures
                {
                    "operatingCashflow": "11000000000",
                    "capitalExpenditures": "-2100000000",
                },
                {
                    "operatingCashflow": "10500000000",
                    "capitalExpenditures": "-1900000000",
                },
                {
                    "operatingCashflow": "12000000000",
                    "capitalExpenditures": "-2200000000",
                },
            ]
        }
        with pytest.raises(ValueError, match="Missing required fields"):
            calculate_fcf_from_quarters(quarterly_data)

    def test_calculate_fcf_negative_fcf(self):
        """Test that negative FCF is calculated (company burning cash)."""
        quarterly_data = {
            "quarterlyReports": [
                {
                    "operatingCashflow": "1000000000",
                    "capitalExpenditures": "3000000000",  # Positive capex (unusual but tests negative result)
                },
                {
                    "operatingCashflow": "1100000000",
                    "capitalExpenditures": "3100000000",
                },
                {
                    "operatingCashflow": "1050000000",
                    "capitalExpenditures": "2900000000",
                },
                {
                    "operatingCashflow": "1200000000",
                    "capitalExpenditures": "3200000000",
                },
            ]
        }
        result = calculate_fcf_from_quarters(quarterly_data)
        # Negative FCF should be calculated (company burning cash)
        # OCF - (+capex) = negative
        assert result < Decimal("0")

    def test_calculate_fcf_with_extra_quarters(self):
        """Test that only most recent 4 quarters are used."""
        quarterly_data = {
            "quarterlyReports": [
                {
                    "operatingCashflow": "10000000000",
                    "capitalExpenditures": "-2000000000",
                },
                {
                    "operatingCashflow": "11000000000",
                    "capitalExpenditures": "-2100000000",
                },
                {
                    "operatingCashflow": "10500000000",
                    "capitalExpenditures": "-1900000000",
                },
                {
                    "operatingCashflow": "12000000000",
                    "capitalExpenditures": "-2200000000",
                },
                {
                    "operatingCashflow": "9000000000",
                    "capitalExpenditures": "-1800000000",
                },  # 5th quarter - should be ignored
            ]
        }
        result = calculate_fcf_from_quarters(quarterly_data)
        # Should use first 4 quarters only
        assert result == Decimal("51700000000.00")

    def test_calculate_fcf_string_numbers(self):
        """Test handling of string-formatted numbers."""
        quarterly_data = {
            "quarterlyReports": [
                {
                    "operatingCashflow": "10000000000.50",
                    "capitalExpenditures": "-2000000000.25",
                },
                {
                    "operatingCashflow": "11000000000.75",
                    "capitalExpenditures": "-2100000000.50",
                },
                {
                    "operatingCashflow": "10500000000.25",
                    "capitalExpenditures": "-1900000000.75",
                },
                {
                    "operatingCashflow": "12000000000.00",
                    "capitalExpenditures": "-2200000000.00",
                },
            ]
        }
        result = calculate_fcf_from_quarters(quarterly_data)
        # Should handle decimal strings correctly
        assert result > Decimal("51700000000")

    def test_calculate_fcf_very_large_numbers(self):
        """Test with very large cash flow numbers."""
        quarterly_data = {
            "quarterlyReports": [
                {
                    "operatingCashflow": "100000000000",
                    "capitalExpenditures": "-20000000000",
                },
                {
                    "operatingCashflow": "110000000000",
                    "capitalExpenditures": "-21000000000",
                },
                {
                    "operatingCashflow": "105000000000",
                    "capitalExpenditures": "-19000000000",
                },
                {
                    "operatingCashflow": "120000000000",
                    "capitalExpenditures": "-22000000000",
                },
            ]
        }
        result = calculate_fcf_from_quarters(quarterly_data)
        assert result > Decimal("0")
        assert result == result.quantize(Decimal("0.01"))

    def test_calculate_fcf_missing_quarterly_reports_key(self):
        """Test error when quarterlyReports key is missing."""
        quarterly_data = {"annualReports": []}  # Wrong key
        with pytest.raises(ValueError, match="Missing 'quarterlyReports'"):
            calculate_fcf_from_quarters(quarterly_data)


class TestCalculateFCFPerShare:
    """Test FCF per share calculation."""

    def test_fcf_per_share_basic(self):
        """Test basic FCF per share calculation."""
        result = calculate_fcf_per_share(
            Decimal("33300000000"), Decimal("15000000000")
        )
        assert result == Decimal("2.22")

    def test_fcf_per_share_zero_shares(self):
        """Test that zero shares raises error."""
        with pytest.raises(ValueError, match="Shares outstanding must be greater than 0"):
            calculate_fcf_per_share(Decimal("33300000000"), Decimal("0"))

    def test_fcf_per_share_negative_shares(self):
        """Test that negative shares raises error."""
        with pytest.raises(ValueError, match="Shares outstanding must be greater than 0"):
            calculate_fcf_per_share(Decimal("33300000000"), Decimal("-1000000"))

    def test_fcf_per_share_precision(self):
        """Test precision is maintained."""
        result = calculate_fcf_per_share(Decimal("12345678.90"), Decimal("5000000"))
        assert result == result.quantize(Decimal("0.01"))

    def test_fcf_per_share_negative_fcf(self):
        """Test FCF per share with negative TTM FCF."""
        result = calculate_fcf_per_share(Decimal("-5000000000"), Decimal("1000000000"))
        assert result < Decimal("0")
        assert result == Decimal("-5.00")


class TestProjectFCF:
    """Test FCF projection."""

    def test_project_fcf_matches_eps_logic(self):
        """Test that FCF projection matches EPS projection logic."""
        fcf_result = project_fcf(Decimal("2.22"), Decimal("10.0"), 5)
        eps_result = project_eps(Decimal("2.22"), Decimal("10.0"), 5)

        # Should produce identical results
        assert fcf_result == eps_result

    def test_project_fcf_basic(self):
        """Test basic FCF projection."""
        result = project_fcf(Decimal("2.00"), Decimal("10.0"), 3)
        assert len(result) == 3
        assert result[0] == Decimal("2.20")
        assert result[1] == Decimal("2.42")
        assert result[2] == Decimal("2.66")


class TestCalculateIntrinsicValueFCF:
    """Test complete FCF-based intrinsic value calculation."""

    def test_intrinsic_value_fcf_basic(self):
        """Test FCF intrinsic value with typical values."""
        result = calculate_intrinsic_value_fcf(
            current_fcf_per_share=Decimal("2.22"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        assert "intrinsic_value" in result
        assert "projected_fcf" in result
        assert "terminal_value" in result
        assert result["intrinsic_value"] > Decimal("0")
        assert len(result["projected_fcf"]) == 5

    def test_intrinsic_value_fcf_invalid_fcf(self):
        """Test that negative or zero FCF raises error."""
        with pytest.raises(
            ValueError, match="Current FCF per share must be greater than 0"
        ):
            calculate_intrinsic_value_fcf(
                current_fcf_per_share=Decimal("0.00"),
                fcf_growth_rate=Decimal("10.0"),
                fcf_multiple=Decimal("20.0"),
                desired_return=Decimal("15.0"),
            )

    def test_intrinsic_value_fcf_negative_fcf(self):
        """Test that negative FCF raises error."""
        with pytest.raises(
            ValueError, match="Current FCF per share must be greater than 0"
        ):
            calculate_intrinsic_value_fcf(
                current_fcf_per_share=Decimal("-2.50"),
                fcf_growth_rate=Decimal("10.0"),
                fcf_multiple=Decimal("20.0"),
                desired_return=Decimal("15.0"),
            )

    def test_intrinsic_value_fcf_known_calculation(self):
        """Test with known values to verify accuracy."""
        result = calculate_intrinsic_value_fcf(
            current_fcf_per_share=Decimal("2.22"),
            fcf_growth_rate=Decimal("10.0"),
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )

        # Expected calculation:
        # Year 1-5 FCF: 2.44, 2.69, 2.95, 3.25, 3.58
        # Terminal: 3.58 × 20 = 71.60
        # PV calculations at 15% discount...
        # Should be around $45
        assert Decimal("44.00") < result["intrinsic_value"] < Decimal("46.00")

    def test_intrinsic_value_fcf_very_low_fcf(self):
        """Test with very low FCF per share."""
        result = calculate_intrinsic_value_fcf(
            current_fcf_per_share=Decimal("0.01"),
            fcf_growth_rate=Decimal("5.0"),
            fcf_multiple=Decimal("15.0"),
            desired_return=Decimal("12.0"),
            projection_years=5,
        )
        assert result["intrinsic_value"] > Decimal("0")
        assert result["intrinsic_value"] < Decimal("1.00")

    def test_intrinsic_value_fcf_high_growth(self):
        """Test with high FCF growth rate."""
        result = calculate_intrinsic_value_fcf(
            current_fcf_per_share=Decimal("3.00"),
            fcf_growth_rate=Decimal("30.0"),  # High growth
            fcf_multiple=Decimal("20.0"),
            desired_return=Decimal("15.0"),
            projection_years=5,
        )
        # High growth should result in high intrinsic value
        assert result["intrinsic_value"] > Decimal("100.00")

    def test_intrinsic_value_fcf_vs_eps_comparison(self):
        """Test that FCF and EPS methods produce reasonable results."""
        # Same inputs for both methods
        current_value = Decimal("5.00")
        growth = Decimal("10.0")
        multiple = Decimal("20.0")
        discount = Decimal("15.0")
        years = 5

        eps_result = calculate_intrinsic_value(
            current_eps=current_value,
            eps_growth_rate=growth,
            eps_multiple=multiple,
            desired_return=discount,
            projection_years=years,
        )

        fcf_result = calculate_intrinsic_value_fcf(
            current_fcf_per_share=current_value,
            fcf_growth_rate=growth,
            fcf_multiple=multiple,
            desired_return=discount,
            projection_years=years,
        )

        # With same inputs, should produce same results
        assert eps_result["intrinsic_value"] == fcf_result["intrinsic_value"]

    def test_intrinsic_value_fcf_invalid_years(self):
        """Test that invalid projection years raises ValueError."""
        with pytest.raises(ValueError, match="Projection years must be at least 1"):
            calculate_intrinsic_value_fcf(
                current_fcf_per_share=Decimal("2.22"),
                fcf_growth_rate=Decimal("10.0"),
                fcf_multiple=Decimal("20.0"),
                desired_return=Decimal("15.0"),
                projection_years=0,
            )

    def test_intrinsic_value_fcf_all_components_present(self):
        """Test that all expected components are in the result."""
        result = calculate_intrinsic_value_fcf(
            current_fcf_per_share=Decimal("3.50"),
            fcf_growth_rate=Decimal("12.0"),
            fcf_multiple=Decimal("18.0"),
            desired_return=Decimal("14.0"),
            projection_years=5,
        )

        # Verify all expected keys exist
        assert "intrinsic_value" in result
        assert "projected_fcf" in result
        assert "terminal_value" in result
        assert "pv_of_fcf" in result
        assert "sum_pv_fcf" in result
        assert "pv_of_terminal" in result

        # Verify intrinsic value calculation
        calculated_iv = result["sum_pv_fcf"] + result["pv_of_terminal"]
        assert result["intrinsic_value"] == calculated_iv.quantize(Decimal("0.01"))
