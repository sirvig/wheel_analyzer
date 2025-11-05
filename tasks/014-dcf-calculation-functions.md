# Task 014: Create DCF Calculation Functions

## Progress Summary

**Status**: ✅ Completed

- [x] Step 1: Create scanner/valuation.py module
- [x] Step 2: Implement EPS projection function
- [x] Step 3: Implement terminal value calculation
- [x] Step 4: Implement present value discounting
- [x] Step 5: Implement intrinsic value calculation
- [x] Step 6: Create comprehensive unit tests

### Summary of Changes:
- Created `scanner/valuation.py` with complete DCF calculation functions
- Implemented `project_eps()` for EPS projection using compound growth
- Implemented `calculate_terminal_value()` for terminal value calculation
- Implemented `discount_to_present_value()` and `discount_eps_series()` for present value discounting
- Implemented `calculate_intrinsic_value()` as main function combining all calculations
- Created comprehensive test suite in `scanner/tests/test_valuation.py` with 21 test cases
- All tests pass successfully
- Functions use Decimal type for financial precision
- Comprehensive logging and error handling included

## Overview

This task creates the core DCF (Discounted Cash Flow) calculation logic for determining stock intrinsic value based on EPS (Earnings Per Share) projections. The calculation will use the assumptions stored in the `CuratedStock` model (added in Task 013) to project future earnings, calculate terminal value, and discount everything to present value.

The DCF model uses:
- **5-year EPS projection** using growth rate
- **Terminal value** calculated as Year 5 EPS × EPS multiple
- **Present value discounting** using desired return rate
- **Intrinsic value** as sum of all present values

## Implementation Steps

### Step 1: Create scanner/valuation.py module

Create a new Python module to house all valuation-related functions:

**Files to create:**
- `scanner/valuation.py`

**Initial module structure:**
```python
"""
DCF (Discounted Cash Flow) valuation functions for stock intrinsic value calculation.

This module provides functions to calculate the intrinsic value of stocks using
an EPS-based DCF model. The calculation projects future EPS, calculates terminal
value, and discounts everything to present value.
"""

from decimal import Decimal
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


def calculate_intrinsic_value(
    current_eps: Decimal,
    eps_growth_rate: Decimal,
    eps_multiple: Decimal,
    desired_return: Decimal,
    projection_years: int = 5
) -> Dict[str, Decimal]:
    """
    Calculate intrinsic value per share using EPS-based DCF model.
    
    Args:
        current_eps: Current Earnings Per Share
        eps_growth_rate: Expected EPS growth rate (as percentage, e.g., 10.0 for 10%)
        eps_multiple: Multiple applied to terminal year EPS
        desired_return: Desired annual return rate (as percentage, e.g., 15.0 for 15%)
        projection_years: Number of years to project (default: 5)
    
    Returns:
        Dictionary containing:
            - intrinsic_value: The calculated fair value per share
            - projected_eps: List of projected EPS for each year
            - terminal_value: Terminal value at end of projection period
            - pv_of_eps: Present value of projected EPS
            - pv_of_terminal: Present value of terminal value
    
    Example:
        >>> result = calculate_intrinsic_value(
        ...     current_eps=Decimal('5.00'),
        ...     eps_growth_rate=Decimal('10.0'),
        ...     eps_multiple=Decimal('20.0'),
        ...     desired_return=Decimal('15.0'),
        ...     projection_years=5
        ... )
        >>> print(result['intrinsic_value'])
        Decimal('123.45')
    """
    # Implementation in Step 5
    pass


# Helper functions will be added in Steps 2-4
```

### Step 2: Implement EPS projection function

Create a function to project EPS for the specified number of years:

**Function to add to scanner/valuation.py:**
```python
def project_eps(
    current_eps: Decimal,
    growth_rate: Decimal,
    years: int
) -> List[Decimal]:
    """
    Project EPS for future years using compound growth.
    
    Formula: Projected EPS[year] = Current EPS × (1 + growth_rate)^year
    
    Args:
        current_eps: Current Earnings Per Share
        growth_rate: Annual growth rate as percentage (e.g., 10.0 for 10%)
        years: Number of years to project
    
    Returns:
        List of projected EPS values, one for each year (1 through years)
    
    Example:
        >>> project_eps(Decimal('5.00'), Decimal('10.0'), 5)
        [Decimal('5.50'), Decimal('6.05'), Decimal('6.66'), Decimal('7.32'), Decimal('8.05')]
    """
    projected_eps = []
    growth_multiplier = Decimal('1.0') + (growth_rate / Decimal('100'))
    
    for year in range(1, years + 1):
        # EPS for this year = current_eps * (1 + growth_rate)^year
        eps_for_year = current_eps * (growth_multiplier ** year)
        projected_eps.append(eps_for_year.quantize(Decimal('0.01')))
    
    return projected_eps
```

**Unit tests to write** (in Step 6):
- Test with 10% growth rate over 5 years
- Test with 0% growth rate (should remain constant)
- Test with negative growth rate
- Test with 1 year vs. 10 years
- Verify compound growth formula

### Step 3: Implement terminal value calculation

Create a function to calculate terminal value using the EPS multiple method:

**Function to add to scanner/valuation.py:**
```python
def calculate_terminal_value(
    final_year_eps: Decimal,
    eps_multiple: Decimal
) -> Decimal:
    """
    Calculate terminal value using EPS multiple method.
    
    Formula: Terminal Value = Final Year EPS × EPS Multiple
    
    Args:
        final_year_eps: Projected EPS in the final year
        eps_multiple: Multiple to apply (e.g., 20.0 for 20x earnings)
    
    Returns:
        Terminal value
    
    Example:
        >>> calculate_terminal_value(Decimal('8.05'), Decimal('20.0'))
        Decimal('161.00')
    """
    terminal_value = final_year_eps * eps_multiple
    return terminal_value.quantize(Decimal('0.01'))
```

**Unit tests to write** (in Step 6):
- Test with various EPS values and multiples
- Test with multiple of 1.0 (should equal final year EPS)
- Test rounding behavior
- Verify precision (2 decimal places)

### Step 4: Implement present value discounting

Create functions to discount future values to present value:

**Functions to add to scanner/valuation.py:**
```python
def discount_to_present_value(
    future_value: Decimal,
    discount_rate: Decimal,
    years: int
) -> Decimal:
    """
    Discount a future value to present value.
    
    Formula: PV = FV / (1 + discount_rate)^years
    
    Args:
        future_value: Value in the future
        discount_rate: Annual discount rate as percentage (e.g., 15.0 for 15%)
        years: Number of years in the future
    
    Returns:
        Present value
    
    Example:
        >>> discount_to_present_value(Decimal('100.00'), Decimal('15.0'), 5)
        Decimal('49.72')
    """
    discount_multiplier = Decimal('1.0') + (discount_rate / Decimal('100'))
    present_value = future_value / (discount_multiplier ** years)
    return present_value.quantize(Decimal('0.01'))


def discount_eps_series(
    projected_eps: List[Decimal],
    discount_rate: Decimal
) -> List[Decimal]:
    """
    Discount a series of projected EPS values to present value.
    
    Args:
        projected_eps: List of projected EPS for each year
        discount_rate: Annual discount rate as percentage (e.g., 15.0 for 15%)
    
    Returns:
        List of present values, one for each year
    
    Example:
        >>> eps = [Decimal('5.50'), Decimal('6.05'), Decimal('6.66')]
        >>> discount_eps_series(eps, Decimal('15.0'))
        [Decimal('4.78'), Decimal('4.58'), Decimal('4.38')]
    """
    present_values = []
    
    for year, eps in enumerate(projected_eps, start=1):
        pv = discount_to_present_value(eps, discount_rate, year)
        present_values.append(pv)
    
    return present_values
```

**Unit tests to write** (in Step 6):
- Test discount calculation accuracy
- Test with 0% discount rate (should equal future value)
- Test with various time periods (1 year, 5 years, 10 years)
- Test series discounting with multiple values
- Verify time value of money concept

### Step 5: Implement intrinsic value calculation

Implement the main `calculate_intrinsic_value` function that combines all previous functions:

**Implementation for scanner/valuation.py:**
```python
def calculate_intrinsic_value(
    current_eps: Decimal,
    eps_growth_rate: Decimal,
    eps_multiple: Decimal,
    desired_return: Decimal,
    projection_years: int = 5
) -> Dict[str, any]:
    """
    Calculate intrinsic value per share using EPS-based DCF model.
    
    Process:
    1. Project EPS for specified number of years
    2. Calculate terminal value (final year EPS × multiple)
    3. Discount projected EPS to present value
    4. Discount terminal value to present value
    5. Sum all present values to get intrinsic value
    
    Args:
        current_eps: Current Earnings Per Share
        eps_growth_rate: Expected EPS growth rate (as percentage)
        eps_multiple: Multiple applied to terminal year EPS
        desired_return: Desired annual return rate (as percentage)
        projection_years: Number of years to project (default: 5)
    
    Returns:
        Dictionary containing:
            - intrinsic_value: The calculated fair value per share
            - projected_eps: List of projected EPS for each year
            - terminal_value: Terminal value at end of projection period
            - pv_of_eps: List of present values for each year's EPS
            - pv_of_terminal: Present value of terminal value
            - sum_pv_eps: Sum of present values of projected EPS
    
    Raises:
        ValueError: If any input is invalid (negative, zero where not allowed)
    """
    # Input validation
    if current_eps <= 0:
        raise ValueError("Current EPS must be greater than 0")
    if projection_years < 1:
        raise ValueError("Projection years must be at least 1")
    
    logger.info(
        f"Calculating intrinsic value: EPS={current_eps}, "
        f"Growth={eps_growth_rate}%, Multiple={eps_multiple}, "
        f"Return={desired_return}%, Years={projection_years}"
    )
    
    # Step 1: Project EPS for future years
    projected_eps = project_eps(current_eps, eps_growth_rate, projection_years)
    logger.debug(f"Projected EPS: {projected_eps}")
    
    # Step 2: Calculate terminal value
    final_year_eps = projected_eps[-1]
    terminal_value = calculate_terminal_value(final_year_eps, eps_multiple)
    logger.debug(f"Terminal value: {terminal_value}")
    
    # Step 3: Discount projected EPS to present value
    pv_of_eps = discount_eps_series(projected_eps, desired_return)
    sum_pv_eps = sum(pv_of_eps)
    logger.debug(f"PV of projected EPS: {pv_of_eps}, Sum: {sum_pv_eps}")
    
    # Step 4: Discount terminal value to present value
    pv_of_terminal = discount_to_present_value(
        terminal_value, 
        desired_return, 
        projection_years
    )
    logger.debug(f"PV of terminal value: {pv_of_terminal}")
    
    # Step 5: Calculate intrinsic value (sum of all present values)
    intrinsic_value = sum_pv_eps + pv_of_terminal
    intrinsic_value = intrinsic_value.quantize(Decimal('0.01'))
    
    logger.info(f"Calculated intrinsic value: {intrinsic_value}")
    
    return {
        'intrinsic_value': intrinsic_value,
        'projected_eps': projected_eps,
        'terminal_value': terminal_value,
        'pv_of_eps': pv_of_eps,
        'sum_pv_eps': sum_pv_eps,
        'pv_of_terminal': pv_of_terminal
    }
```

### Step 6: Create comprehensive unit tests

Create test file with comprehensive test coverage:

**Files to create:**
- `scanner/tests/test_valuation.py`

**Test structure:**
```python
import pytest
from decimal import Decimal
from scanner.valuation import (
    project_eps,
    calculate_terminal_value,
    discount_to_present_value,
    discount_eps_series,
    calculate_intrinsic_value
)


class TestProjectEPS:
    """Test EPS projection function."""
    
    def test_project_eps_with_10_percent_growth(self):
        """Test EPS projection with 10% annual growth over 5 years."""
        result = project_eps(Decimal('5.00'), Decimal('10.0'), 5)
        assert len(result) == 5
        assert result[0] == Decimal('5.50')  # Year 1: 5.00 * 1.10
        assert result[4] == Decimal('8.05')  # Year 5: 5.00 * 1.10^5
    
    def test_project_eps_with_zero_growth(self):
        """Test EPS projection with 0% growth (should remain constant)."""
        result = project_eps(Decimal('5.00'), Decimal('0.0'), 5)
        assert all(eps == Decimal('5.00') for eps in result)
    
    def test_project_eps_with_negative_growth(self):
        """Test EPS projection with negative growth (declining earnings)."""
        result = project_eps(Decimal('5.00'), Decimal('-5.0'), 3)
        assert result[0] < Decimal('5.00')
        assert result[2] < result[1] < result[0]
    
    def test_project_eps_one_year(self):
        """Test EPS projection for single year."""
        result = project_eps(Decimal('10.00'), Decimal('15.0'), 1)
        assert len(result) == 1
        assert result[0] == Decimal('11.50')
    
    def test_project_eps_precision(self):
        """Test that results are rounded to 2 decimal places."""
        result = project_eps(Decimal('3.33'), Decimal('7.7'), 3)
        for eps in result:
            # Check that we have at most 2 decimal places
            assert eps == eps.quantize(Decimal('0.01'))


class TestCalculateTerminalValue:
    """Test terminal value calculation."""
    
    def test_terminal_value_basic(self):
        """Test basic terminal value calculation."""
        result = calculate_terminal_value(Decimal('8.05'), Decimal('20.0'))
        assert result == Decimal('161.00')
    
    def test_terminal_value_with_one_multiple(self):
        """Test terminal value with 1x multiple (should equal EPS)."""
        result = calculate_terminal_value(Decimal('10.00'), Decimal('1.0'))
        assert result == Decimal('10.00')
    
    def test_terminal_value_precision(self):
        """Test terminal value rounding to 2 decimal places."""
        result = calculate_terminal_value(Decimal('7.77'), Decimal('15.5'))
        assert result == result.quantize(Decimal('0.01'))


class TestDiscountToPresentValue:
    """Test present value discounting."""
    
    def test_discount_5_years_15_percent(self):
        """Test discounting $100 at 15% for 5 years."""
        result = discount_to_present_value(Decimal('100.00'), Decimal('15.0'), 5)
        # Expected: 100 / (1.15^5) ≈ 49.72
        assert result == Decimal('49.72')
    
    def test_discount_zero_rate(self):
        """Test discounting with 0% rate (should equal future value)."""
        result = discount_to_present_value(Decimal('100.00'), Decimal('0.0'), 5)
        assert result == Decimal('100.00')
    
    def test_discount_one_year(self):
        """Test discounting for 1 year."""
        result = discount_to_present_value(Decimal('115.00'), Decimal('15.0'), 1)
        assert result == Decimal('100.00')
    
    def test_discount_precision(self):
        """Test that result is rounded to 2 decimal places."""
        result = discount_to_present_value(Decimal('123.45'), Decimal('12.3'), 7)
        assert result == result.quantize(Decimal('0.01'))


class TestDiscountEPSSeries:
    """Test discounting series of EPS values."""
    
    def test_discount_series(self):
        """Test discounting a series of projected EPS."""
        eps = [Decimal('5.50'), Decimal('6.05'), Decimal('6.66')]
        result = discount_eps_series(eps, Decimal('15.0'))
        
        assert len(result) == 3
        # Each subsequent year should have progressively lower PV
        assert result[0] > result[1] > result[2]
    
    def test_discount_empty_series(self):
        """Test discounting empty list."""
        result = discount_eps_series([], Decimal('15.0'))
        assert result == []


class TestCalculateIntrinsicValue:
    """Test complete intrinsic value calculation."""
    
    def test_intrinsic_value_basic(self):
        """Test intrinsic value calculation with typical values."""
        result = calculate_intrinsic_value(
            current_eps=Decimal('5.00'),
            eps_growth_rate=Decimal('10.0'),
            eps_multiple=Decimal('20.0'),
            desired_return=Decimal('15.0'),
            projection_years=5
        )
        
        assert 'intrinsic_value' in result
        assert 'projected_eps' in result
        assert 'terminal_value' in result
        assert 'pv_of_eps' in result
        assert 'pv_of_terminal' in result
        assert 'sum_pv_eps' in result
        
        # Intrinsic value should be positive and reasonable
        assert result['intrinsic_value'] > Decimal('0')
        
        # Verify calculation components
        assert len(result['projected_eps']) == 5
        assert len(result['pv_of_eps']) == 5
        assert result['intrinsic_value'] == (
            result['sum_pv_eps'] + result['pv_of_terminal']
        )
    
    def test_intrinsic_value_with_default_params(self):
        """Test using default parameter values from CuratedStock model."""
        result = calculate_intrinsic_value(
            current_eps=Decimal('6.00'),
            eps_growth_rate=Decimal('10.0'),  # Default
            eps_multiple=Decimal('20.0'),     # Default
            desired_return=Decimal('15.0'),   # Default
            projection_years=5                # Default
        )
        
        assert result['intrinsic_value'] > Decimal('0')
    
    def test_intrinsic_value_high_growth(self):
        """Test with high growth rate."""
        result = calculate_intrinsic_value(
            current_eps=Decimal('5.00'),
            eps_growth_rate=Decimal('25.0'),  # High growth
            eps_multiple=Decimal('20.0'),
            desired_return=Decimal('15.0'),
            projection_years=5
        )
        
        # Higher growth should result in higher intrinsic value
        assert result['intrinsic_value'] > Decimal('100.00')
    
    def test_intrinsic_value_invalid_eps(self):
        """Test that negative or zero EPS raises ValueError."""
        with pytest.raises(ValueError, match="Current EPS must be greater than 0"):
            calculate_intrinsic_value(
                current_eps=Decimal('0.00'),
                eps_growth_rate=Decimal('10.0'),
                eps_multiple=Decimal('20.0'),
                desired_return=Decimal('15.0')
            )
    
    def test_intrinsic_value_invalid_years(self):
        """Test that invalid projection years raises ValueError."""
        with pytest.raises(ValueError, match="Projection years must be at least 1"):
            calculate_intrinsic_value(
                current_eps=Decimal('5.00'),
                eps_growth_rate=Decimal('10.0'),
                eps_multiple=Decimal('20.0'),
                desired_return=Decimal('15.0'),
                projection_years=0
            )
    
    def test_intrinsic_value_precision(self):
        """Test that intrinsic value is rounded to 2 decimal places."""
        result = calculate_intrinsic_value(
            current_eps=Decimal('7.77'),
            eps_growth_rate=Decimal('11.11'),
            eps_multiple=Decimal('18.88'),
            desired_return=Decimal('13.33'),
            projection_years=5
        )
        
        assert result['intrinsic_value'] == result['intrinsic_value'].quantize(
            Decimal('0.01')
        )


# Run tests with: just test scanner/tests/test_valuation.py
```

**Additional edge case tests to consider:**
- Very high EPS values (e.g., $100+)
- Very low EPS values (e.g., $0.01)
- Extreme growth rates (100%+, -50%)
- Very long projection periods (10+ years)
- Different combinations of parameters

## Acceptance Criteria

### Functionality:
- [ ] `project_eps()` correctly projects EPS using compound growth formula
- [ ] `calculate_terminal_value()` correctly applies EPS multiple
- [ ] `discount_to_present_value()` correctly discounts future values
- [ ] `discount_eps_series()` correctly discounts list of values
- [ ] `calculate_intrinsic_value()` correctly combines all calculations
- [ ] All functions return Decimal type with 2 decimal places precision

### Code Quality:
- [ ] All functions have comprehensive docstrings with examples
- [ ] Input validation prevents invalid calculations
- [ ] Logging provides visibility into calculation steps
- [ ] Code follows project conventions (type hints, formatting)
- [ ] Functions are pure (no side effects)

### Testing:
- [ ] Unit tests cover all functions
- [ ] Tests verify mathematical accuracy
- [ ] Edge cases are tested (zero growth, negative growth, etc.)
- [ ] Error cases raise appropriate exceptions
- [ ] All tests pass: `just test scanner/tests/test_valuation.py`
- [ ] Test coverage is >90% for valuation.py

## Files Involved

### Created Files:
- `scanner/valuation.py` - DCF calculation functions
- `scanner/tests/test_valuation.py` - Comprehensive unit tests

### Files to Reference:
- `scanner/models.py` - CuratedStock model with DCF assumption fields
- `scanner/tests/test_scanner_models.py` - Example test patterns

## Notes

### DCF Formula Breakdown:

**Step 1: Project EPS**
```
Year 1 EPS = Current EPS × (1 + growth_rate)^1
Year 2 EPS = Current EPS × (1 + growth_rate)^2
...
Year 5 EPS = Current EPS × (1 + growth_rate)^5
```

**Step 2: Terminal Value**
```
Terminal Value = Year 5 EPS × EPS Multiple
```

**Step 3: Present Value of Projected EPS**
```
PV(Year 1 EPS) = Year 1 EPS / (1 + discount_rate)^1
PV(Year 2 EPS) = Year 2 EPS / (1 + discount_rate)^2
...
```

**Step 4: Present Value of Terminal Value**
```
PV(Terminal Value) = Terminal Value / (1 + discount_rate)^5
```

**Step 5: Intrinsic Value**
```
Intrinsic Value = Sum of PV(Projected EPS) + PV(Terminal Value)
```

### Example Calculation:
```
Current EPS: $5.00
Growth Rate: 10%
EPS Multiple: 20x
Desired Return: 15%
Years: 5

Projected EPS:
  Year 1: $5.50
  Year 2: $6.05
  Year 3: $6.66
  Year 4: $7.32
  Year 5: $8.05

Terminal Value: $8.05 × 20 = $161.00

PV of Projected EPS:
  Year 1: $4.78
  Year 2: $4.58
  Year 3: $4.38
  Year 4: $4.19
  Year 5: $4.00
  Sum: $21.93

PV of Terminal Value: $161.00 / (1.15)^5 = $80.04

Intrinsic Value: $21.93 + $80.04 = $101.97
```

### Decimal Precision:
- Use Python's `Decimal` type for financial calculations
- Avoid floating point arithmetic (can introduce rounding errors)
- Always round final results to 2 decimal places
- Use `quantize(Decimal('0.01'))` for rounding

### Testing Strategy:
- **Unit tests**: Test each function independently
- **Integration test**: Test full calculation in Task 015
- **Known values**: Verify calculations match manual calculations
- **Edge cases**: Test boundary conditions
- **Error cases**: Verify proper error handling

## Testing Checklist

### Function Tests:
- [ ] `project_eps()` tests pass (5 test cases)
- [ ] `calculate_terminal_value()` tests pass (3 test cases)
- [ ] `discount_to_present_value()` tests pass (4 test cases)
- [ ] `discount_eps_series()` tests pass (2 test cases)
- [ ] `calculate_intrinsic_value()` tests pass (7 test cases)

### Calculation Accuracy:
- [ ] Manual calculation matches function output
- [ ] Example from notes produces expected result ($101.94)
- [ ] Decimal precision maintained throughout
- [ ] No floating point errors

### Code Quality:
- [ ] Linting passes: `just lint`
- [ ] Type hints are correct
- [ ] Docstrings are complete and accurate
- [ ] Logging statements are appropriate

## Reference

**DCF Valuation Resources:**
- Investopedia DCF Guide: https://www.investopedia.com/terms/d/dcf.asp
- EPS Growth: https://www.investopedia.com/terms/e/eps.asp

**Python Decimal Documentation:**
- Decimal module: https://docs.python.org/3/library/decimal.html
- Quantize method: https://docs.python.org/3/library/decimal.html#decimal.Decimal.quantize

**Testing Resources:**
- pytest documentation: https://docs.pytest.org/
- pytest fixtures: https://docs.pytest.org/en/stable/fixture.html
