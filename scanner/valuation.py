"""
DCF (Discounted Cash Flow) valuation functions for stock intrinsic value calculation.

This module provides functions to calculate the intrinsic value of stocks using
an EPS-based DCF model. The calculation projects future EPS, calculates terminal
value, and discounts everything to present value.
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
