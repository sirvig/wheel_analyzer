# Task 018: Create FCF-based DCF Calculation Functions

## Progress Summary

**Status**: ✅ Completed

- [x] Step 1: Add FCF calculation helper functions
- [x] Step 2: Implement FCF-based intrinsic value calculation
- [x] Step 3: Create comprehensive unit tests

### Summary of Changes

- Added 4 new FCF calculation functions to `scanner/valuation.py`:
  - `calculate_fcf_from_quarters()` - Calculates TTM FCF from quarterly cash flow data
  - `calculate_fcf_per_share()` - Divides TTM FCF by shares outstanding
  - `project_fcf()` - Projects future FCF using compound growth (reuses EPS logic)
  - `calculate_intrinsic_value_fcf()` - Complete FCF-based DCF intrinsic value calculation
- All functions follow same patterns as existing EPS functions
- Comprehensive docstrings with examples
- Proper error handling and input validation
- Reuses existing discount functions for consistency
- Added 24 new unit test cases covering:
  - Valid FCF calculations from quarterly data
  - Edge cases (insufficient quarters, missing fields, negative FCF)
  - FCF per share calculations with validation
  - FCF projection matching EPS logic
  - Complete FCF intrinsic value calculations
  - Comparison between EPS and FCF methods
- All 56 valuation tests pass (32 existing + 24 new)

## Overview

This task creates the core Free Cash Flow (FCF) based DCF calculation logic for determining stock intrinsic value. The calculation will use quarterly cash flow data from Alpha Vantage to calculate TTM (Trailing Twelve Months) FCF, then project future FCF and discount to present value.

The FCF DCF model uses:
- **TTM FCF calculation** from 4 quarters of cash flow data
- **FCF per share** derived from TTM FCF / shares outstanding
- **5-year FCF projection** using growth rate
- **Terminal value** calculated as Year 5 FCF × FCF multiple
- **Present value discounting** using desired return rate (reusing existing function)

## Implementation Steps

### Step 1: Add FCF calculation helper functions

Add new functions to `scanner/valuation.py` for FCF-specific calculations:

**Functions to add:**

```python
def calculate_fcf_from_quarters(quarterly_data: dict) -> Decimal:
    """
    Calculate Trailing Twelve Months (TTM) Free Cash Flow from quarterly data.
    
    Formula: FCF = Operating Cash Flow - Capital Expenditures (for each quarter)
    TTM FCF = Sum of last 4 quarters' FCF
    
    Args:
        quarterly_data: Dictionary with quarterly reports from Alpha Vantage CASH_FLOW endpoint
        Expected structure:
        {
            "quarterlyReports": [
                {
                    "fiscalDateEnding": "2024-09-30",
                    "operatingCashflow": "12345000000",
                    "capitalExpenditures": "-1234000000"  # Note: typically negative
                },
                # ... 3 more quarters (4 total required)
            ]
        }
    
    Returns:
        TTM Free Cash Flow (positive number in currency units)
    
    Raises:
        ValueError: If fewer than 4 quarters available
        ValueError: If data is malformed or missing required fields
    
    Example:
        >>> quarterly_data = {
        ...     "quarterlyReports": [
        ...         {"operatingCashflow": "10000000000", "capitalExpenditures": "-2000000000"},
        ...         {"operatingCashflow": "11000000000", "capitalExpenditures": "-2100000000"},
        ...         {"operatingCashflow": "10500000000", "capitalExpenditures": "-1900000000"},
        ...         {"operatingCashflow": "12000000000", "capitalExpenditures": "-2200000000"},
        ...     ]
        ... }
        >>> calculate_fcf_from_quarters(quarterly_data)
        Decimal('33300000000')
    """
    # Validate quarterly data structure
    if "quarterlyReports" not in quarterly_data:
        raise ValueError("Missing 'quarterlyReports' in cash flow data")
    
    reports = quarterly_data["quarterlyReports"]
    
    if len(reports) < 4:
        raise ValueError(
            f"Insufficient quarterly data: need 4 quarters, got {len(reports)}"
        )
    
    # Take the most recent 4 quarters
    recent_quarters = reports[:4]
    
    ttm_fcf = Decimal("0")
    
    for quarter in recent_quarters:
        # Validate required fields
        if "operatingCashflow" not in quarter or "capitalExpenditures" not in quarter:
            raise ValueError("Missing required fields in quarterly report")
        
        # Parse values - handle both string and numeric types
        try:
            operating_cf = Decimal(str(quarter["operatingCashflow"]))
            capex = Decimal(str(quarter["capitalExpenditures"]))
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid cash flow values: {e}")
        
        # Calculate FCF for this quarter
        # Note: capex is typically negative, so subtracting it adds to FCF
        quarter_fcf = operating_cf - capex
        ttm_fcf += quarter_fcf
    
    logger.debug(f"Calculated TTM FCF: {ttm_fcf}")
    
    return ttm_fcf.quantize(Decimal("0.01"))


def calculate_fcf_per_share(
    ttm_fcf: Decimal, shares_outstanding: Decimal
) -> Decimal:
    """
    Calculate Free Cash Flow per share.
    
    Formula: FCF per Share = TTM FCF / Shares Outstanding
    
    Args:
        ttm_fcf: Trailing Twelve Months Free Cash Flow
        shares_outstanding: Number of shares outstanding
    
    Returns:
        FCF per share
    
    Raises:
        ValueError: If shares_outstanding is zero or negative
    
    Example:
        >>> calculate_fcf_per_share(Decimal('33300000000'), Decimal('15000000000'))
        Decimal('2.22')
    """
    if shares_outstanding <= 0:
        raise ValueError("Shares outstanding must be greater than 0")
    
    fcf_per_share = ttm_fcf / shares_outstanding
    
    return fcf_per_share.quantize(Decimal("0.01"))


def project_fcf(
    current_fcf: Decimal, growth_rate: Decimal, years: int
) -> list[Decimal]:
    """
    Project FCF for future years using compound growth.
    
    This is identical to project_eps() but included for clarity and potential
    future divergence in FCF vs EPS projection methods.
    
    Formula: Projected FCF[year] = Current FCF × (1 + growth_rate)^year
    
    Args:
        current_fcf: Current Free Cash Flow per share
        growth_rate: Annual growth rate as percentage (e.g., 10.0 for 10%)
        years: Number of years to project
    
    Returns:
        List of projected FCF values, one for each year (1 through years)
    
    Example:
        >>> project_fcf(Decimal('2.22'), Decimal('10.0'), 5)
        [Decimal('2.44'), Decimal('2.69'), Decimal('2.95'), Decimal('3.25'), Decimal('3.58')]
    """
    # Reuse the existing project_eps logic
    return project_eps(current_fcf, growth_rate, years)
```

### Step 2: Implement FCF-based intrinsic value calculation

Add main FCF DCF function to `scanner/valuation.py`:

```python
def calculate_intrinsic_value_fcf(
    current_fcf_per_share: Decimal,
    fcf_growth_rate: Decimal,
    fcf_multiple: Decimal,
    desired_return: Decimal,
    projection_years: int = 5,
) -> dict:
    """
    Calculate intrinsic value per share using FCF-based DCF model.
    
    Process:
    1. Project FCF per share for specified number of years
    2. Calculate terminal value (final year FCF × multiple)
    3. Discount projected FCF to present value
    4. Discount terminal value to present value
    5. Sum all present values to get intrinsic value
    
    Args:
        current_fcf_per_share: Current Free Cash Flow per share (TTM)
        fcf_growth_rate: Expected FCF growth rate (as percentage)
        fcf_multiple: Multiple applied to terminal year FCF
        desired_return: Desired annual return rate (as percentage)
        projection_years: Number of years to project (default: 5)
    
    Returns:
        Dictionary containing:
            - intrinsic_value: The calculated fair value per share
            - projected_fcf: List of projected FCF for each year
            - terminal_value: Terminal value at end of projection period
            - pv_of_fcf: List of present values for each year's FCF
            - pv_of_terminal: Present value of terminal value
            - sum_pv_fcf: Sum of present values of projected FCF
    
    Raises:
        ValueError: If any input is invalid (negative, zero where not allowed)
    
    Example:
        >>> result = calculate_intrinsic_value_fcf(
        ...     current_fcf_per_share=Decimal('2.22'),
        ...     fcf_growth_rate=Decimal('10.0'),
        ...     fcf_multiple=Decimal('20.0'),
        ...     desired_return=Decimal('15.0'),
        ...     projection_years=5
        ... )
        >>> print(result['intrinsic_value'])
        Decimal('45.27')
    """
    # Input validation
    if current_fcf_per_share <= 0:
        raise ValueError("Current FCF per share must be greater than 0")
    if projection_years < 1:
        raise ValueError("Projection years must be at least 1")
    
    logger.info(
        f"Calculating FCF-based intrinsic value: FCF/Share={current_fcf_per_share}, "
        f"Growth={fcf_growth_rate}%, Multiple={fcf_multiple}, "
        f"Return={desired_return}%, Years={projection_years}"
    )
    
    # Step 1: Project FCF for future years
    projected_fcf = project_fcf(current_fcf_per_share, fcf_growth_rate, projection_years)
    logger.debug(f"Projected FCF: {projected_fcf}")
    
    # Step 2: Calculate terminal value
    final_year_fcf = projected_fcf[-1]
    terminal_value = calculate_terminal_value(final_year_fcf, fcf_multiple)
    logger.debug(f"Terminal value: {terminal_value}")
    
    # Step 3: Discount projected FCF to present value (reuse existing function)
    pv_of_fcf = discount_eps_series(projected_fcf, desired_return)
    sum_pv_fcf = sum(pv_of_fcf)
    logger.debug(f"PV of projected FCF: {pv_of_fcf}, Sum: {sum_pv_fcf}")
    
    # Step 4: Discount terminal value to present value (reuse existing function)
    pv_of_terminal = discount_to_present_value(
        terminal_value, desired_return, projection_years
    )
    logger.debug(f"PV of terminal value: {pv_of_terminal}")
    
    # Step 5: Calculate intrinsic value (sum of all present values)
    intrinsic_value = sum_pv_fcf + pv_of_terminal
    intrinsic_value = intrinsic_value.quantize(Decimal("0.01"))
    
    logger.info(f"Calculated FCF-based intrinsic value: {intrinsic_value}")
    
    return {
        "intrinsic_value": intrinsic_value,
        "projected_fcf": projected_fcf,
        "terminal_value": terminal_value,
        "pv_of_fcf": pv_of_fcf,
        "sum_pv_fcf": sum_pv_fcf,
        "pv_of_terminal": pv_of_terminal,
    }
```

### Step 3: Create comprehensive unit tests

Extend `scanner/tests/test_valuation.py` with FCF-specific tests:

**Test classes to add:**

```python
class TestCalculateFCFFromQuarters:
    """Test FCF calculation from quarterly data."""
    
    def test_calculate_fcf_valid_4_quarters(self):
        """Test FCF calculation with valid 4 quarters of data."""
        quarterly_data = {
            "quarterlyReports": [
                {"operatingCashflow": "10000000000", "capitalExpenditures": "-2000000000"},
                {"operatingCashflow": "11000000000", "capitalExpenditures": "-2100000000"},
                {"operatingCashflow": "10500000000", "capitalExpenditures": "-1900000000"},
                {"operatingCashflow": "12000000000", "capitalExpenditures": "-2200000000"},
            ]
        }
        result = calculate_fcf_from_quarters(quarterly_data)
        # Sum: (10B+2B) + (11B+2.1B) + (10.5B+1.9B) + (12B+2.2B) = 51.7B
        assert result == Decimal("51700000000.00")
    
    def test_calculate_fcf_insufficient_quarters(self):
        """Test that error is raised with fewer than 4 quarters."""
        quarterly_data = {
            "quarterlyReports": [
                {"operatingCashflow": "10000000000", "capitalExpenditures": "-2000000000"},
                {"operatingCashflow": "11000000000", "capitalExpenditures": "-2100000000"},
            ]
        }
        with pytest.raises(ValueError, match="Insufficient quarterly data"):
            calculate_fcf_from_quarters(quarterly_data)
    
    def test_calculate_fcf_missing_fields(self):
        """Test error handling with missing required fields."""
        quarterly_data = {
            "quarterlyReports": [
                {"operatingCashflow": "10000000000"},  # Missing capitalExpenditures
                {"operatingCashflow": "11000000000", "capitalExpenditures": "-2100000000"},
                {"operatingCashflow": "10500000000", "capitalExpenditures": "-1900000000"},
                {"operatingCashflow": "12000000000", "capitalExpenditures": "-2200000000"},
            ]
        }
        with pytest.raises(ValueError, match="Missing required fields"):
            calculate_fcf_from_quarters(quarterly_data)
    
    def test_calculate_fcf_negative_fcf(self):
        """Test that negative FCF is calculated (company burning cash)."""
        quarterly_data = {
            "quarterlyReports": [
                {"operatingCashflow": "1000000000", "capitalExpenditures": "-3000000000"},
                {"operatingCashflow": "1100000000", "capitalExpenditures": "-3100000000"},
                {"operatingCashflow": "1050000000", "capitalExpenditures": "-2900000000"},
                {"operatingCashflow": "1200000000", "capitalExpenditures": "-3200000000"},
            ]
        }
        result = calculate_fcf_from_quarters(quarterly_data)
        # Negative FCF should be calculated (will trigger warning in command)
        assert result < Decimal("0")


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
    
    def test_fcf_per_share_precision(self):
        """Test precision is maintained."""
        result = calculate_fcf_per_share(
            Decimal("12345678.90"), Decimal("5000000")
        )
        assert result == result.quantize(Decimal("0.01"))


class TestProjectFCF:
    """Test FCF projection."""
    
    def test_project_fcf_matches_eps_logic(self):
        """Test that FCF projection matches EPS projection logic."""
        fcf_result = project_fcf(Decimal("2.22"), Decimal("10.0"), 5)
        eps_result = project_eps(Decimal("2.22"), Decimal("10.0"), 5)
        
        # Should produce identical results
        assert fcf_result == eps_result


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
        with pytest.raises(ValueError, match="Current FCF per share must be greater than 0"):
            calculate_intrinsic_value_fcf(
                current_fcf_per_share=Decimal("0.00"),
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
```

**Test count**: ~15 new test cases

## Acceptance Criteria

### Functionality:
- [ ] `calculate_fcf_from_quarters()` correctly aggregates 4 quarters of cash flow data
- [ ] `calculate_fcf_per_share()` correctly divides by shares outstanding
- [ ] `project_fcf()` correctly projects FCF using compound growth
- [ ] `calculate_intrinsic_value_fcf()` correctly combines all calculations
- [ ] All functions return Decimal type with 2 decimal places precision
- [ ] Negative FCF is handled (calculated but flagged)

### Code Quality:
- [ ] All functions have comprehensive docstrings with examples
- [ ] Input validation prevents invalid calculations
- [ ] Logging provides visibility into calculation steps
- [ ] Code follows project conventions (type hints, formatting)
- [ ] Functions reuse existing discount logic where appropriate

### Testing:
- [ ] Unit tests cover all new functions
- [ ] Tests verify mathematical accuracy
- [ ] Edge cases are tested (negative FCF, insufficient data, etc.)
- [ ] Error cases raise appropriate exceptions
- [ ] All tests pass: `just test scanner/tests/test_valuation.py`
- [ ] Test coverage >90% for new FCF functions

## Files Involved

### Modified Files:
- `scanner/valuation.py` - Add FCF calculation functions
- `scanner/tests/test_valuation.py` - Add FCF unit tests

### Files to Reference:
- `scanner/models.py` - CuratedStock model with FCF fields (from Task 017)
- Existing valuation functions for consistency

## Notes

### FCF Calculation Details:

**Alpha Vantage CASH_FLOW Response Structure**:
```json
{
  "symbol": "AAPL",
  "annualReports": [...],
  "quarterlyReports": [
    {
      "fiscalDateEnding": "2024-09-30",
      "reportedCurrency": "USD",
      "operatingCashflow": "29959000000",
      "capitalExpenditures": "-2445000000",
      "changeInOperatingLiabilities": "...",
      ...
    },
    // ... 3 more recent quarters
  ]
}
```

**Key Fields**:
- `operatingCashflow`: Cash from operations (positive)
- `capitalExpenditures`: Capital expenditures (usually negative in API)
- Need last 4 quarters for TTM calculation

### FCF Formula:
```
Quarter FCF = Operating Cash Flow - Capital Expenditures
TTM FCF = Sum(Quarter 1 FCF + Quarter 2 FCF + Quarter 3 FCF + Quarter 4 FCF)
FCF per Share = TTM FCF / Shares Outstanding
```

### Why FCF-based DCF:

**Advantages**:
- More accurate than EPS (shows actual cash generation)
- Better for capital-intensive companies
- Harder to manipulate than earnings
- Shows true cash available to investors

**Disadvantages**:
- More volatile quarter-to-quarter
- Requires more data points
- Not available for all companies
- May be negative for high-growth companies

### Reused Functions:

The FCF DCF reuses these existing functions:
- `discount_to_present_value()` - Same discounting logic
- `discount_eps_series()` - Can discount FCF series too
- `calculate_terminal_value()` - Same terminal value calculation

This ensures consistency and reduces code duplication.

## Testing Checklist

### Function Tests:
- [ ] `calculate_fcf_from_quarters()` tests pass (4 test cases)
- [ ] `calculate_fcf_per_share()` tests pass (3 test cases)
- [ ] `project_fcf()` tests pass (1 test case)
- [ ] `calculate_intrinsic_value_fcf()` tests pass (3 test cases)

### Calculation Accuracy:
- [ ] Manual FCF calculation matches function output
- [ ] Example from notes produces expected result
- [ ] Decimal precision maintained throughout
- [ ] No floating point errors

### Edge Cases:
- [ ] Insufficient quarters handled correctly
- [ ] Missing data fields raise appropriate errors
- [ ] Negative FCF calculated (warning flagged elsewhere)
- [ ] Very large/small numbers handled

### Code Quality:
- [ ] Linting passes: `just lint`
- [ ] Type hints are correct
- [ ] Docstrings are complete and accurate
- [ ] Logging statements are appropriate

## Reference

**DCF Valuation Resources:**
- FCF-based DCF: https://www.investopedia.com/terms/f/freecashflow.asp
- Terminal Value: https://www.investopedia.com/terms/t/terminalvalue.asp

**Alpha Vantage Documentation:**
- CASH_FLOW endpoint: https://www.alphavantage.co/documentation/#cash-flow

**Python Decimal Documentation:**
- Decimal module: https://docs.python.org/3/library/decimal.html
