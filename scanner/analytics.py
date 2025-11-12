"""
Analytics module for valuation trend analysis and statistics.

This module provides functions to calculate analytics on historical valuation data,
including volatility, CAGR, correlation, and sensitivity analysis. All functions are
pure (no side effects) and use standard library where possible.
"""

import logging
import statistics
from decimal import Decimal
from typing import Any, Dict, List, Optional

from scanner.models import CuratedStock, ValuationHistory
from scanner.valuation import calculate_intrinsic_value, calculate_intrinsic_value_fcf

logger = logging.getLogger(__name__)


def calculate_volatility(values: List[float]) -> Dict[str, Optional[float]]:
    """
    Calculate standard deviation and coefficient of variation for a series of values.

    The coefficient of variation (CV) is the ratio of the standard deviation to the mean,
    expressed as a percentage. It provides a standardized measure of dispersion.

    Args:
        values: List of numeric values (e.g., intrinsic values over time)

    Returns:
        Dictionary containing:
            - std_dev: Standard deviation (None if < 2 data points)
            - coefficient_of_variation: CV as percentage (None if < 2 data points or mean is zero)
            - mean: Average of values

    Example:
        >>> calculate_volatility([100.0, 105.0, 110.0, 102.0])
        {'std_dev': 4.27, 'coefficient_of_variation': 4.03, 'mean': 104.25}
    """
    # Handle edge cases
    if not values:
        return {"std_dev": None, "coefficient_of_variation": None, "mean": None}

    if len(values) == 1:
        return {
            "std_dev": None,
            "coefficient_of_variation": None,
            "mean": values[0],
        }

    # Filter out None values
    clean_values = [v for v in values if v is not None]

    if len(clean_values) < 2:
        return {"std_dev": None, "coefficient_of_variation": None, "mean": None}

    # Calculate statistics
    mean_val = statistics.mean(clean_values)
    std_dev = statistics.stdev(clean_values)

    # Calculate coefficient of variation (avoid division by zero)
    if mean_val != 0:
        cv = (std_dev / mean_val) * 100
    else:
        cv = None

    return {
        "std_dev": round(std_dev, 2),
        "coefficient_of_variation": round(cv, 2) if cv is not None else None,
        "mean": round(mean_val, 2),
    }


def calculate_cagr(
    start_value: float, end_value: float, periods: int
) -> Optional[float]:
    """
    Calculate Compound Annual Growth Rate (CAGR).

    CAGR represents the mean annual growth rate over a specified period,
    assuming the value grows at a steady rate.

    Formula: CAGR = ((end_value / start_value) ^ (1 / years)) - 1

    Args:
        start_value: Initial value
        end_value: Final value
        periods: Number of quarters (will be converted to years by dividing by 4)

    Returns:
        CAGR as a percentage (annualized), or None if calculation not possible

    Example:
        >>> calculate_cagr(100.0, 121.0, 8)  # 8 quarters = 2 years
        10.0  # 10% annual growth
    """
    # Handle edge cases
    if start_value is None or end_value is None:
        return None

    if start_value <= 0 or end_value <= 0:
        logger.warning(
            f"CAGR requires positive values: start={start_value}, end={end_value}"
        )
        return None

    if periods < 1:
        return None

    # Convert quarters to years
    years = periods / 4.0

    if years == 0:
        return None

    # Calculate CAGR
    try:
        cagr = ((end_value / start_value) ** (1 / years) - 1) * 100
        return round(cagr, 2)
    except (ValueError, ZeroDivisionError, OverflowError) as e:
        logger.warning(f"CAGR calculation error: {e}")
        return None


def calculate_correlation(
    x_values: List[float], y_values: List[float]
) -> Optional[float]:
    """
    Calculate Pearson correlation coefficient between two series.

    The correlation coefficient ranges from -1 to +1:
    - +1: Perfect positive correlation
    -  0: No correlation
    - -1: Perfect negative correlation

    Args:
        x_values: First series (e.g., EPS intrinsic values)
        y_values: Second series (e.g., FCF intrinsic values)

    Returns:
        Pearson correlation coefficient, or None if calculation not possible

    Example:
        >>> calculate_correlation([100, 105, 110], [98, 103, 108])
        0.99  # High positive correlation
    """
    # Handle edge cases
    if not x_values or not y_values:
        return None

    if len(x_values) != len(y_values):
        logger.warning(
            f"Correlation requires equal length series: {len(x_values)} vs {len(y_values)}"
        )
        return None

    # Filter out pairs where either value is None
    clean_pairs = [
        (x, y) for x, y in zip(x_values, y_values) if x is not None and y is not None
    ]

    if len(clean_pairs) < 2:
        return None

    clean_x, clean_y = zip(*clean_pairs)

    # Calculate correlation
    try:
        # Python 3.10+ has statistics.correlation()
        correlation = statistics.correlation(clean_x, clean_y)
        return round(correlation, 3)
    except (statistics.StatisticsError, ValueError) as e:
        logger.warning(f"Correlation calculation error: {e}")
        return None


def calculate_sensitivity(
    stock: CuratedStock, assumption: str, delta: float
) -> Dict[str, Any]:
    """
    Calculate sensitivity of intrinsic value to changes in DCF assumptions.

    Tests how a percentage point change in a specific assumption affects
    the calculated intrinsic value. Uses the stock's preferred method.

    Args:
        stock: CuratedStock instance with valuation parameters
        assumption: Which assumption to adjust - one of:
            - 'growth_rate': EPS or FCF growth rate
            - 'discount_rate': Desired return rate
            - 'terminal_growth_rate': Not currently used in models (returns None)
        delta: Percentage point change (e.g., 0.02 for +2%, -0.03 for -3%)

    Returns:
        Dictionary containing:
            - original_iv: Intrinsic value with original assumptions
            - adjusted_iv: Intrinsic value with adjusted assumption
            - change_pct: Percentage change in IV
            - assumption: Which assumption was adjusted
            - delta: The adjustment made
            - method: 'EPS' or 'FCF'

    Example:
        >>> sensitivity = calculate_sensitivity(stock, 'growth_rate', 0.02)
        >>> sensitivity['change_pct']
        15.3  # IV increased by 15.3% with +2% growth rate
    """
    # Determine which method to use
    method = "EPS" if stock.preferred_valuation_method == "EPS" else "FCF"

    # Terminal growth rate not implemented in current models
    if assumption == "terminal_growth_rate":
        return {
            "original_iv": None,
            "adjusted_iv": None,
            "change_pct": None,
            "assumption": assumption,
            "delta": delta,
            "method": method,
            "error": "Terminal growth rate not implemented in current DCF models",
        }

    try:
        if method == "EPS":
            # Calculate original IV
            original_result = calculate_intrinsic_value(
                current_eps=stock.current_eps,
                eps_growth_rate=stock.eps_growth_rate,
                eps_multiple=stock.eps_multiple,
                desired_return=stock.desired_return,
                projection_years=stock.projection_years,
            )
            original_iv = float(original_result["intrinsic_value"])

            # Adjust assumption and recalculate
            if assumption == "growth_rate":
                adjusted_rate = stock.eps_growth_rate + Decimal(str(delta * 100))
                adjusted_result = calculate_intrinsic_value(
                    current_eps=stock.current_eps,
                    eps_growth_rate=adjusted_rate,
                    eps_multiple=stock.eps_multiple,
                    desired_return=stock.desired_return,
                    projection_years=stock.projection_years,
                )
            elif assumption == "discount_rate":
                adjusted_rate = stock.desired_return + Decimal(str(delta * 100))
                adjusted_result = calculate_intrinsic_value(
                    current_eps=stock.current_eps,
                    eps_growth_rate=stock.eps_growth_rate,
                    eps_multiple=stock.eps_multiple,
                    desired_return=adjusted_rate,
                    projection_years=stock.projection_years,
                )
            else:
                return {
                    "original_iv": original_iv,
                    "adjusted_iv": None,
                    "change_pct": None,
                    "assumption": assumption,
                    "delta": delta,
                    "method": method,
                    "error": f"Unknown assumption: {assumption}",
                }

            adjusted_iv = float(adjusted_result["intrinsic_value"])

        else:  # FCF method
            # Calculate original IV
            original_result = calculate_intrinsic_value_fcf(
                current_fcf_per_share=stock.current_fcf_per_share,
                fcf_growth_rate=stock.fcf_growth_rate,
                fcf_multiple=stock.fcf_multiple,
                desired_return=stock.desired_return_fcf,
                projection_years=stock.projection_years_fcf,
            )
            original_iv = float(original_result["intrinsic_value"])

            # Adjust assumption and recalculate
            if assumption == "growth_rate":
                adjusted_rate = stock.fcf_growth_rate + Decimal(str(delta * 100))
                adjusted_result = calculate_intrinsic_value_fcf(
                    current_fcf_per_share=stock.current_fcf_per_share,
                    fcf_growth_rate=adjusted_rate,
                    fcf_multiple=stock.fcf_multiple,
                    desired_return=stock.desired_return_fcf,
                    projection_years=stock.projection_years_fcf,
                )
            elif assumption == "discount_rate":
                adjusted_rate = stock.desired_return_fcf + Decimal(str(delta * 100))
                adjusted_result = calculate_intrinsic_value_fcf(
                    current_fcf_per_share=stock.current_fcf_per_share,
                    fcf_growth_rate=stock.fcf_growth_rate,
                    fcf_multiple=stock.fcf_multiple,
                    desired_return=adjusted_rate,
                    projection_years=stock.projection_years_fcf,
                )
            else:
                return {
                    "original_iv": original_iv,
                    "adjusted_iv": None,
                    "change_pct": None,
                    "assumption": assumption,
                    "delta": delta,
                    "method": method,
                    "error": f"Unknown assumption: {assumption}",
                }

            adjusted_iv = float(adjusted_result["intrinsic_value"])

        # Calculate percentage change
        if original_iv != 0:
            change_pct = ((adjusted_iv - original_iv) / original_iv) * 100
        else:
            change_pct = None

        return {
            "original_iv": round(original_iv, 2),
            "adjusted_iv": round(adjusted_iv, 2),
            "change_pct": round(change_pct, 2) if change_pct is not None else None,
            "assumption": assumption,
            "delta": delta,
            "method": method,
        }

    except Exception as e:
        logger.error(f"Sensitivity calculation error for {stock.symbol}: {e}")
        return {
            "original_iv": None,
            "adjusted_iv": None,
            "change_pct": None,
            "assumption": assumption,
            "delta": delta,
            "method": method,
            "error": str(e),
        }


def get_stock_analytics(symbol: str) -> Dict[str, Any]:
    """
    Get comprehensive analytics for a single stock.

    Retrieves valuation history and calculates volatility, CAGR, correlation,
    and other metrics for the stock's intrinsic value over time.

    Args:
        symbol: Stock ticker symbol

    Returns:
        Dictionary containing:
            - symbol: Stock ticker
            - data_points: Number of historical snapshots
            - eps_volatility: Volatility metrics for EPS method
            - fcf_volatility: Volatility metrics for FCF method
            - eps_cagr: CAGR for EPS intrinsic value
            - fcf_cagr: CAGR for FCF intrinsic value
            - correlation: Correlation between EPS and FCF methods
            - latest_eps_iv: Most recent EPS intrinsic value
            - latest_fcf_iv: Most recent FCF intrinsic value
            - highest_iv: Highest intrinsic value recorded
            - lowest_iv: Lowest intrinsic value recorded
            - average_iv: Average intrinsic value
            - preferred_method: Stock's preferred valuation method

    Raises:
        CuratedStock.DoesNotExist: If stock not found
    """
    stock = CuratedStock.objects.get(symbol=symbol)

    # Get historical data ordered by date
    history = ValuationHistory.objects.filter(stock=stock).order_by("snapshot_date")

    if not history.exists():
        return {
            "symbol": symbol,
            "data_points": 0,
            "eps_volatility": {},
            "fcf_volatility": {},
            "eps_cagr": None,
            "fcf_cagr": None,
            "correlation": None,
            "latest_eps_iv": None,
            "latest_fcf_iv": None,
            "highest_iv": None,
            "lowest_iv": None,
            "average_iv": None,
            "preferred_method": stock.preferred_valuation_method,
        }

    # Extract EPS and FCF intrinsic values
    eps_values = [
        float(h.intrinsic_value)
        for h in history
        if h.intrinsic_value is not None
    ]
    fcf_values = [
        float(h.intrinsic_value_fcf)
        for h in history
        if h.intrinsic_value_fcf is not None
    ]

    # Get effective intrinsic values (based on preferred method)
    effective_values = [
        float(h.get_effective_intrinsic_value())
        for h in history
        if h.get_effective_intrinsic_value() is not None
    ]

    # Calculate volatility
    eps_volatility = calculate_volatility(eps_values)
    fcf_volatility = calculate_volatility(fcf_values)
    effective_volatility = calculate_volatility(effective_values)

    # Calculate CAGR (need at least 2 data points)
    eps_cagr = None
    fcf_cagr = None
    effective_cagr = None

    if len(eps_values) >= 2:
        eps_cagr = calculate_cagr(eps_values[0], eps_values[-1], len(eps_values))

    if len(fcf_values) >= 2:
        fcf_cagr = calculate_cagr(fcf_values[0], fcf_values[-1], len(fcf_values))

    if len(effective_values) >= 2:
        effective_cagr = calculate_cagr(
            effective_values[0], effective_values[-1], len(effective_values)
        )

    # Calculate correlation between EPS and FCF methods
    correlation = calculate_correlation(eps_values, fcf_values)

    # Get latest values
    latest = history.last()
    latest_eps_iv = float(latest.intrinsic_value) if latest.intrinsic_value else None
    latest_fcf_iv = float(latest.intrinsic_value_fcf) if latest.intrinsic_value_fcf else None

    # Calculate highest, lowest, average based on preferred method
    if effective_values:
        highest_iv = max(effective_values)
        lowest_iv = min(effective_values)
        average_iv = statistics.mean(effective_values)
    else:
        highest_iv = lowest_iv = average_iv = None

    return {
        "symbol": symbol,
        "data_points": history.count(),
        "eps_volatility": eps_volatility,
        "fcf_volatility": fcf_volatility,
        "effective_volatility": effective_volatility,
        "eps_cagr": eps_cagr,
        "fcf_cagr": fcf_cagr,
        "effective_cagr": effective_cagr,
        "correlation": correlation,
        "latest_eps_iv": round(latest_eps_iv, 2) if latest_eps_iv else None,
        "latest_fcf_iv": round(latest_fcf_iv, 2) if latest_fcf_iv else None,
        "highest_iv": round(highest_iv, 2) if highest_iv else None,
        "lowest_iv": round(lowest_iv, 2) if lowest_iv else None,
        "average_iv": round(average_iv, 2) if average_iv else None,
        "preferred_method": stock.preferred_valuation_method,
    }


def get_portfolio_analytics() -> Dict[str, Any]:
    """
    Get portfolio-wide analytics across all active curated stocks.

    Aggregates analytics from all stocks with valuation history and calculates
    portfolio-level metrics.

    Returns:
        Dictionary containing:
            - total_stocks: Total number of active stocks
            - stocks_with_history: Number of stocks with valuation history
            - portfolio_stats: Aggregate statistics
                - average_iv: Average intrinsic value across portfolio
                - total_data_points: Sum of all historical snapshots
                - average_volatility: Mean volatility across stocks
                - average_cagr: Mean CAGR across stocks
            - stock_analytics: List of per-stock analytics dictionaries
    """
    active_stocks = CuratedStock.objects.filter(active=True)
    total_stocks = active_stocks.count()

    # Get analytics for each stock
    stock_analytics_list = []
    stocks_with_history = 0

    for stock in active_stocks:
        try:
            analytics = get_stock_analytics(stock.symbol)
            if analytics["data_points"] > 0:
                stock_analytics_list.append(analytics)
                stocks_with_history += 1
        except Exception as e:
            logger.warning(f"Error getting analytics for {stock.symbol}: {e}")
            continue

    # Calculate portfolio-wide statistics
    if stock_analytics_list:
        # Average intrinsic value (using latest values)
        latest_ivs = [
            a.get("average_iv")
            for a in stock_analytics_list
            if a.get("average_iv") is not None
        ]
        average_iv = statistics.mean(latest_ivs) if latest_ivs else None

        # Total data points
        total_data_points = sum(a["data_points"] for a in stock_analytics_list)

        # Average volatility (using effective volatility std_dev)
        volatilities = [
            a["effective_volatility"].get("std_dev")
            for a in stock_analytics_list
            if a.get("effective_volatility")
            and a["effective_volatility"].get("std_dev") is not None
        ]
        average_volatility = statistics.mean(volatilities) if volatilities else None

        # Average CAGR (using effective CAGR)
        cagrs = [
            a["effective_cagr"]
            for a in stock_analytics_list
            if a.get("effective_cagr") is not None
        ]
        average_cagr = statistics.mean(cagrs) if cagrs else None
    else:
        average_iv = None
        total_data_points = 0
        average_volatility = None
        average_cagr = None

    return {
        "total_stocks": total_stocks,
        "stocks_with_history": stocks_with_history,
        "portfolio_stats": {
            "average_iv": round(average_iv, 2) if average_iv else None,
            "total_data_points": total_data_points,
            "average_volatility": round(average_volatility, 2)
            if average_volatility
            else None,
            "average_cagr": round(average_cagr, 2) if average_cagr else None,
        },
        "stock_analytics": stock_analytics_list,
    }
