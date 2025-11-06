"""
DCF (Discounted Cash Flow) valuation functions for stock intrinsic value calculation.

This module provides functions to calculate the intrinsic value of stocks using
both EPS-based and FCF-based DCF models. The calculations project future values,
calculate terminal value, and discount everything to present value.
"""

import logging
from decimal import Decimal
from typing import Dict, List

logger = logging.getLogger(__name__)


def project_eps(
    current_eps: Decimal, growth_rate: Decimal, years: int
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
        >>> project_eps(Decimal("5.00"), Decimal("10.0"), 5)
        [Decimal('5.50'), Decimal('6.05'), Decimal('6.66'), Decimal('7.32'), Decimal('8.05')]
    """
    projected_eps = []
    growth_multiplier = Decimal("1.0") + (growth_rate / Decimal("100"))

    for year in range(1, years + 1):
        # EPS for this year = current_eps * (1 + growth_rate)^year
        eps_for_year = current_eps * (growth_multiplier**year)
        projected_eps.append(eps_for_year.quantize(Decimal("0.01")))

    return projected_eps


def calculate_terminal_value(final_year_eps: Decimal, eps_multiple: Decimal) -> Decimal:
    """
    Calculate terminal value using EPS multiple method.

    Formula: Terminal Value = Final Year EPS × EPS Multiple

    Args:
        final_year_eps: Projected EPS in the final year
        eps_multiple: Multiple to apply (e.g., 20.0 for 20x earnings)

    Returns:
        Terminal value

    Example:
        >>> calculate_terminal_value(Decimal("8.05"), Decimal("20.0"))
        Decimal('161.00')
    """
    terminal_value = final_year_eps * eps_multiple
    return terminal_value.quantize(Decimal("0.01"))


def discount_to_present_value(
    future_value: Decimal, discount_rate: Decimal, years: int
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
        >>> discount_to_present_value(Decimal("100.00"), Decimal("15.0"), 5)
        Decimal('49.72')
    """
    discount_multiplier = Decimal("1.0") + (discount_rate / Decimal("100"))
    present_value = future_value / (discount_multiplier**years)
    return present_value.quantize(Decimal("0.01"))


def discount_eps_series(
    projected_eps: List[Decimal], discount_rate: Decimal
) -> List[Decimal]:
    """
    Discount a series of projected EPS values to present value.

    Args:
        projected_eps: List of projected EPS for each year
        discount_rate: Annual discount rate as percentage (e.g., 15.0 for 15%)

    Returns:
        List of present values, one for each year

    Example:
        >>> eps = [Decimal("5.50"), Decimal("6.05"), Decimal("6.66")]
        >>> discount_eps_series(eps, Decimal("15.0"))
        [Decimal('4.78'), Decimal('4.58'), Decimal('4.38')]
    """
    present_values = []

    for year, eps in enumerate(projected_eps, start=1):
        pv = discount_to_present_value(eps, discount_rate, year)
        present_values.append(pv)

    return present_values


def calculate_intrinsic_value(
    current_eps: Decimal,
    eps_growth_rate: Decimal,
    eps_multiple: Decimal,
    desired_return: Decimal,
    projection_years: int = 5,
) -> Dict:
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

    Example:
        >>> result = calculate_intrinsic_value(
        ...     current_eps=Decimal("5.00"),
        ...     eps_growth_rate=Decimal("10.0"),
        ...     eps_multiple=Decimal("20.0"),
        ...     desired_return=Decimal("15.0"),
        ...     projection_years=5,
        ... )
        >>> print(result["intrinsic_value"])
        Decimal('101.97')
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
        terminal_value, desired_return, projection_years
    )
    logger.debug(f"PV of terminal value: {pv_of_terminal}")

    # Step 5: Calculate intrinsic value (sum of all present values)
    intrinsic_value = sum_pv_eps + pv_of_terminal
    intrinsic_value = intrinsic_value.quantize(Decimal("0.01"))

    logger.info(f"Calculated intrinsic value: {intrinsic_value}")

    return {
        "intrinsic_value": intrinsic_value,
        "projected_eps": projected_eps,
        "terminal_value": terminal_value,
        "pv_of_eps": pv_of_eps,
        "sum_pv_eps": sum_pv_eps,
        "pv_of_terminal": pv_of_terminal,
    }


# ============================================================================
# EPS TTM Calculation Functions
# ============================================================================


def calculate_eps_ttm_from_quarters(quarterly_data: dict) -> Decimal:
    """
    Calculate Trailing Twelve Months (TTM) Earnings Per Share from quarterly data.

    Formula: EPS TTM = Sum of reportedEPS from last 4 quarters

    Args:
        quarterly_data: Dictionary with quarterly earnings from Alpha Vantage EARNINGS endpoint
        Expected structure:
        {
            "quarterlyEarnings": [
                {
                    "fiscalDateEnding": "2024-09-30",
                    "reportedEPS": "1.64"
                },
                # ... 3 more quarters (4 total required)
            ]
        }

    Returns:
        TTM Earnings Per Share

    Raises:
        ValueError: If fewer than 4 quarters available
        ValueError: If data is malformed or missing required fields

    Example:
        >>> quarterly_data = {
        ...     "quarterlyEarnings": [
        ...         {"fiscalDateEnding": "2024-09-30", "reportedEPS": "1.64"},
        ...         {"fiscalDateEnding": "2024-06-30", "reportedEPS": "1.40"},
        ...         {"fiscalDateEnding": "2024-03-31", "reportedEPS": "1.53"},
        ...         {"fiscalDateEnding": "2023-12-31", "reportedEPS": "2.18"},
        ...     ]
        ... }
        >>> calculate_eps_ttm_from_quarters(quarterly_data)
        Decimal('6.75')
    """
    # Validate quarterly data structure
    if "quarterlyEarnings" not in quarterly_data:
        raise ValueError("Missing 'quarterlyEarnings' in earnings data")

    reports = quarterly_data["quarterlyEarnings"]

    if len(reports) < 4:
        raise ValueError(
            f"Insufficient quarterly data: need 4 quarters, got {len(reports)}"
        )

    # Take the most recent 4 quarters
    recent_quarters = reports[:4]

    eps_ttm = Decimal("0")

    for quarter in recent_quarters:
        # Validate required field
        if "reportedEPS" not in quarter:
            raise ValueError("Missing 'reportedEPS' field in quarterly earnings")

        # Parse value - handle both string and numeric types
        try:
            reported_eps = Decimal(str(quarter["reportedEPS"]))
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid reportedEPS value: {e}")

        # Sum up the quarterly EPS
        eps_ttm += reported_eps

    logger.debug(f"Calculated EPS TTM: {eps_ttm}")

    return eps_ttm.quantize(Decimal("0.01"))


# ============================================================================
# FCF-based DCF Functions
# ============================================================================


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
        Decimal('51700000000.00')
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


def calculate_fcf_per_share(ttm_fcf: Decimal, shares_outstanding: Decimal) -> Decimal:
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
) -> List[Decimal]:
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


def calculate_intrinsic_value_fcf(
    current_fcf_per_share: Decimal,
    fcf_growth_rate: Decimal,
    fcf_multiple: Decimal,
    desired_return: Decimal,
    projection_years: int = 5,
) -> Dict:
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
