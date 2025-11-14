import csv
import json
import logging
import threading
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db import IntegrityError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_POST

from django_ratelimit.decorators import ratelimit
from scanner.analytics import get_portfolio_analytics, get_stock_analytics
from scanner.forms import IndividualStockScanForm
from scanner.models import CuratedStock, SavedSearch, ScanStatus, ScanUsage, ValuationHistory
from scanner.quota import (
    check_and_record_scan,
    get_remaining_quota,
    get_todays_usage_count,
    get_usage_history,
    get_user_quota,
    get_seconds_until_reset,
)
from scanner.scanner import perform_scan

logger = logging.getLogger(__name__)



# Rate limiting and caching helpers
def conditionally_cache(timeout):
    """Apply cache_page decorator only in non-test environments."""
    def decorator(view_func):
        if settings.ENVIRONMENT != "TESTING":
            return cache_page(timeout)(view_func)
        return view_func
    return decorator

SCAN_LOCK_KEY = "scan_in_progress"
SCAN_LOCK_TIMEOUT = 600  # 10 minutes


@login_required
def index(request):
    """
    Display scanner index page with cached options results.

    Returns:
        Rendered scanner/index.html template with options data

    Note:
        Returns safe defaults if Redis is unavailable.
        Uses get_scan_results() helper for consistent context across views.
    """
    # Use helper function to get scan results with curated stocks
    context = get_scan_results()
    return render(request, "scanner/index.html", context)


@login_required
def options_list(request, ticker):
    """
    Display options list for a specific ticker using Django cache.

    Args:
        ticker: Stock symbol to fetch options for

    Returns:
        Rendered options_list.html template with options data
    """
    # Get all ticker options from cache
    ticker_options = cache.get(
        f"{settings.CACHE_KEY_PREFIX_SCANNER}:ticker_options", default={}
    )

    # Get options for this specific ticker
    options = ticker_options.get(ticker, [])

    context = {"ticker": ticker, "options": options}

    return render(request, "scanner/options_list.html", context)


def run_scan_in_background():
    """
    Execute the scan in a background thread using Django cache.

    This function is responsible for:
    - Creating a ScanStatus database record
    - Running the actual scan
    - Storing results in Django cache
    - Updating ScanStatus with results
    - Releasing the scan lock when complete
    - Handling errors and setting appropriate status messages
    """
    # Create scan status record
    scan_status = ScanStatus.objects.create(
        scan_type='curated',
        status='in_progress'
    )

    try:
        logger.info(f"Background scan thread started (scan_id={scan_status.id})")
        # Allow scans outside market hours in LOCAL environment
        debug_mode = settings.ENVIRONMENT == "LOCAL"
        if debug_mode:
            logger.info("Running in LOCAL environment - bypassing market hours check")
        result = perform_scan(debug=debug_mode)

        if result["success"]:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            completion_message = f"Scan completed successfully at {timestamp}"

            # Store scan results in Django cache
            scan_results = result.get("scan_results", {})
            ticker_options = {}
            ticker_scan_times = {}

            # Count total results
            total_results = sum(len(options) for options in scan_results.values())

            for ticker, options in scan_results.items():
                if options:  # Only store if options found
                    ticker_options[ticker] = options
                    ticker_scan_times[ticker] = timestamp

            # Store in cache with 45-minute TTL
            cache.set(
                f"{settings.CACHE_KEY_PREFIX_SCANNER}:ticker_options",
                ticker_options,
                timeout=settings.CACHE_TTL_OPTIONS,
            )

            cache.set(
                f"{settings.CACHE_KEY_PREFIX_SCANNER}:ticker_scan_times",
                ticker_scan_times,
                timeout=settings.CACHE_TTL_OPTIONS,
            )

            # Update last run status
            cache.set(
                f"{settings.CACHE_KEY_PREFIX_SCANNER}:last_run",
                completion_message,
                timeout=settings.CACHE_TTL_OPTIONS,
            )

            # Update scan status in database
            scan_status.mark_completed(
                result_count=total_results,
                tickers_scanned=result['scanned_count']
            )

            logger.info(
                f"Background scan completed successfully: {result['scanned_count']} tickers, "
                f"{total_results} results (scan_id={scan_status.id})"
            )
        else:
            logger.warning(f"Background scan failed: {result['message']} (scan_id={scan_status.id})")
            # Set last_run to error message so it displays in the UI
            cache.set(
                f"{settings.CACHE_KEY_PREFIX_SCANNER}:last_run",
                result["message"],
                timeout=settings.CACHE_TTL_OPTIONS,
            )

            # Mark scan as failed in database
            scan_status.mark_failed(error_message=result["message"])

    except Exception as e:
        logger.error(f"Error during background scan: {e} (scan_id={scan_status.id})", exc_info=True)
        # Set last_run to error message
        error_msg = "An error occurred during the scan. Please check logs."
        cache.set(
            f"{settings.CACHE_KEY_PREFIX_SCANNER}:last_run",
            error_msg,
            timeout=settings.CACHE_TTL_OPTIONS,
        )

        # Mark scan as failed in database
        scan_status.mark_failed(error_message=f"{error_msg} Error: {str(e)}")

    finally:
        # Always release the lock
        cache.delete(f"{settings.CACHE_KEY_PREFIX_SCANNER}:{SCAN_LOCK_KEY}")
        logger.debug(f"Background scan complete, lock released (scan_id={scan_status.id})")


def get_scan_results():
    """
    Helper function to fetch current scan results from Django cache.

    Returns:
        dict: Context with ticker_options, ticker_scan, last_scan, and curated_stocks

    Note:
        Returns safe defaults (empty dicts) if cache is unavailable.
        Uses Django cache backend instead of direct Redis client.
    """
    try:
        # Fetch all ticker options in single cache hit
        ticker_options = cache.get(
            f"{settings.CACHE_KEY_PREFIX_SCANNER}:ticker_options", default={}
        )

        # Fetch scan timestamps
        ticker_scan = cache.get(
            f"{settings.CACHE_KEY_PREFIX_SCANNER}:ticker_scan_times", default={}
        )

        # Fetch last run status
        last_scan = cache.get(
            f"{settings.CACHE_KEY_PREFIX_SCANNER}:last_run", default="Never"
        )

        # Sort ticker options by ticker symbol
        sorted_ticker_options = {k: ticker_options[k] for k in sorted(ticker_options)}

        # Fetch CuratedStock instances for all symbols in results
        if sorted_ticker_options:
            symbols = list(sorted_ticker_options.keys())
            curated_stocks = CuratedStock.objects.filter(
                symbol__in=symbols, active=True
            )
            curated_stocks_dict = {stock.symbol: stock for stock in curated_stocks}
        else:
            curated_stocks_dict = {}

        # Defensive: ensure curated_stocks_dict is actually a dict
        if not isinstance(curated_stocks_dict, dict):
            logger.warning(
                f"curated_stocks_dict is not a dict: {type(curated_stocks_dict).__name__}. "
                f"Resetting to empty dict."
            )
            curated_stocks_dict = {}

        return {
            "ticker_options": sorted_ticker_options,
            "ticker_scan": ticker_scan,
            "last_scan": last_scan,
            "curated_stocks": curated_stocks_dict,
            "is_local_environment": settings.ENVIRONMENT == "LOCAL",
        }

    except Exception as e:
        # Catch any cache errors (ConnectionError, TimeoutError, etc.)
        logger.warning(f"Cache error in get_scan_results: {e}", exc_info=True)
        return {
            "ticker_options": {},
            "ticker_scan": {},
            "last_scan": "Data temporarily unavailable. Please refresh the page.",
            "curated_stocks": {},  # ALWAYS dict, never None
            "is_local_environment": settings.ENVIRONMENT == "LOCAL",
        }


@login_required
@require_POST
def scan_view(request):
    """
    Trigger a manual options scan asynchronously using Django cache.

    Starts a background thread to perform the scan and immediately returns
    a polling partial that will update as results become available.
    """
    scan_lock_key = f"{settings.CACHE_KEY_PREFIX_SCANNER}:{SCAN_LOCK_KEY}"

    # Check if a scan is already in progress
    if cache.get(scan_lock_key):
        logger.info("Scan already in progress, allowing user to watch")
        # Allow user to watch the existing scan by returning polling partial
        context = get_scan_results()
        return render(request, "scanner/partials/scan_polling.html", context)

    # Set the lock with a timeout to prevent it from getting stuck
    cache.set(scan_lock_key, True, timeout=SCAN_LOCK_TIMEOUT)

    # Set initial status before starting scan
    cache.set(
        f"{settings.CACHE_KEY_PREFIX_SCANNER}:last_run",
        "Scanning in progress...",
        timeout=settings.CACHE_TTL_OPTIONS,
    )

    logger.info("Starting manual scan in background thread")

    # Start the scan in a background thread
    scan_thread = threading.Thread(target=run_scan_in_background, daemon=True)
    scan_thread.start()

    # Get current results (likely from previous scan or empty)
    context = get_scan_results()

    # Return the polling partial immediately
    return render(request, "scanner/partials/scan_polling.html", context)


@login_required
def scan_status(request):
    """
    Polling endpoint to check scan status and return updated results using Django cache.

    This endpoint is called every 15 seconds by the frontend to check if
    the scan is complete and to fetch updated results.

    Returns:
        - scan_polling.html if scan is still in progress (continues polling)
        - options_results.html if scan is complete (stops polling)
    """
    # Get current results from cache
    context = get_scan_results()

    scan_lock_key = f"{settings.CACHE_KEY_PREFIX_SCANNER}:{SCAN_LOCK_KEY}"

    # Check if scan is still in progress
    if cache.get(scan_lock_key):
        logger.debug("Scan status check: scan in progress")
        # Return polling partial to continue polling
        return render(request, "scanner/partials/scan_polling.html", context)
    else:
        logger.debug("Scan status check: scan complete")
        # Return final results partial to stop polling
        return render(request, "scanner/partials/options_results.html", context)


@login_required
def valuation_list_view(request):
    """
    Display all active curated stocks with their valuation data.

    Shows intrinsic values (EPS and FCF methods), calculation assumptions,
    and last calculation dates for all active stocks in the curated list.

    This page provides a comprehensive overview of the portfolio's intrinsic
    value calculations, allowing users to review valuation metrics across
    all monitored stocks.

    Template: scanner/valuations.html

    Context:
        stocks (QuerySet): All active CuratedStock instances ordered by symbol

    Example:
        Access via: /scanner/valuations/
        Template receives list of stocks with all valuation fields
    """
    # Query all active curated stocks, ordered alphabetically
    stocks = CuratedStock.objects.filter(active=True).order_by("symbol")

    logger.info(f"Valuation list view accessed by {request.user.username}")
    logger.debug(f"Displaying {stocks.count()} active curated stocks")

    context = {
        "stocks": stocks,
    }

    return render(request, "scanner/valuations.html", context)


@login_required
@ratelimit(key='user', rate='10/m', method='GET')
@conditionally_cache(60 * 5)  # 5-minute view cache (disabled in tests)
def stock_history_view(request, symbol):
    """
    Display valuation history for a single stock.

    Shows quarterly snapshots with trend visualization and assumption tracking.

    Args:
        symbol: Stock ticker symbol

    Returns:
        Rendered scanner/stock_history.html template

    Context:
        stock: CuratedStock instance
        history: QuerySet of ValuationHistory ordered by date descending
        has_history: Boolean indicating if any snapshots exist
        analytics: Stock analytics dictionary
        chart_data_json: JSON string with chart data
        quick_stats: Dictionary with highest, lowest, average IVs
    """
    # Get stock
    stock = get_object_or_404(CuratedStock, symbol=symbol.upper(), active=True)

    # Get history ordered by date (newest first for display)
    history = ValuationHistory.objects.filter(stock=stock).order_by('-snapshot_date')

    # Get analytics
    stock_analytics = None
    chart_data = None
    quick_stats = None

    if history.exists():
        try:
            stock_analytics = get_stock_analytics(symbol.upper())

            # Prepare chart data (chronological order for chart)
            history_chronological = history.order_by('snapshot_date')

            chart_labels = [h.quarter_label for h in history_chronological]
            eps_data = [
                float(h.intrinsic_value) if h.intrinsic_value else None
                for h in history_chronological
            ]
            fcf_data = [
                float(h.intrinsic_value_fcf) if h.intrinsic_value_fcf else None
                for h in history_chronological
            ]

            # Determine line widths based on preferred method
            eps_width = 3 if stock.preferred_valuation_method == 'EPS' else 2
            fcf_width = 3 if stock.preferred_valuation_method == 'FCF' else 2

            chart_data = {
                'labels': chart_labels,
                'datasets': [
                    {
                        'label': 'EPS Method',
                        'data': eps_data,
                        'borderColor': 'rgb(59, 130, 246)',
                        'backgroundColor': 'rgba(59, 130, 246, 0.1)',
                        'borderWidth': eps_width,
                        'pointRadius': 4,
                        'pointHoverRadius': 6,
                    },
                    {
                        'label': 'FCF Method',
                        'data': fcf_data,
                        'borderColor': 'rgb(34, 197, 94)',
                        'backgroundColor': 'rgba(34, 197, 94, 0.1)',
                        'borderWidth': fcf_width,
                        'pointRadius': 4,
                        'pointHoverRadius': 6,
                    }
                ]
            }

            # Calculate quick stats
            effective_values = [
                float(h.get_effective_intrinsic_value())
                for h in history_chronological
                if h.get_effective_intrinsic_value()
            ]

            if effective_values:
                highest_iv = max(effective_values)
                lowest_iv = min(effective_values)
                average_iv = sum(effective_values) / len(effective_values)
                current_iv = effective_values[-1]

                # Find dates for highest and lowest
                highest_snapshot = max(
                    history_chronological,
                    key=lambda h: float(h.get_effective_intrinsic_value() or 0)
                )
                lowest_snapshot = min(
                    history_chronological,
                    key=lambda h: float(h.get_effective_intrinsic_value() or 0) if h.get_effective_intrinsic_value() else float('inf')
                )

                quick_stats = {
                    'highest_iv': round(highest_iv, 2),
                    'highest_date': highest_snapshot.snapshot_date,
                    'lowest_iv': round(lowest_iv, 2),
                    'lowest_date': lowest_snapshot.snapshot_date,
                    'average_iv': round(average_iv, 2),
                    'current_iv': round(current_iv, 2),
                    'vs_average_pct': round(((current_iv - average_iv) / average_iv) * 100, 1) if average_iv else None,
                }
        except Exception as e:
            logger.warning(f"Error calculating analytics for {symbol}: {e}")

    logger.info(f"Stock history view accessed by {request.user.username} for {symbol}")
    logger.debug(f"Found {history.count()} historical snapshots for {symbol}")

    context = {
        'stock': stock,
        'history': history,
        'has_history': history.exists(),
        'analytics': stock_analytics,
        'chart_data_json': json.dumps(chart_data, ensure_ascii=True) if chart_data else None,
        'quick_stats': quick_stats,
    }

    return render(request, 'scanner/stock_history.html', context)


@login_required
@ratelimit(key='user', rate='10/m', method='GET')
@conditionally_cache(60 * 5)  # 5-minute view cache (disabled in tests)
def valuation_comparison_view(request):
    """
    Display comparison report of current vs. historical valuations.

    Compares current intrinsic values to previous quarter and year-ago snapshots.

    Returns:
        Rendered scanner/valuation_comparison.html template

    Context:
        stocks: List of dictionaries with comparison data per stock
        comparison_date_quarter: Date of previous quarter snapshot
        comparison_date_year: Date of year-ago snapshot
    """
    # Determine comparison dates
    today = date.today()
    previous_quarter_date = _get_previous_quarter_date(today)
    year_ago_date = _get_year_ago_quarter_date(today)

    # Get all active stocks with current valuations
    stocks = CuratedStock.objects.filter(active=True).order_by('symbol')

    comparison_data = []
    for stock in stocks:
        # Get historical snapshots
        quarter_snapshot = ValuationHistory.objects.filter(
            stock=stock,
            snapshot_date=previous_quarter_date
        ).first()

        year_snapshot = ValuationHistory.objects.filter(
            stock=stock,
            snapshot_date=year_ago_date
        ).first()

        # Calculate deltas
        current_value = stock.get_effective_intrinsic_value()
        quarter_value = quarter_snapshot.get_effective_intrinsic_value() if quarter_snapshot else None
        year_value = year_snapshot.get_effective_intrinsic_value() if year_snapshot else None

        quarter_delta = None
        quarter_pct = None
        if current_value and quarter_value:
            quarter_delta = current_value - quarter_value
            quarter_pct = (quarter_delta / quarter_value) * 100

        year_delta = None
        year_pct = None
        if current_value and year_value:
            year_delta = current_value - year_value
            year_pct = (year_delta / year_value) * 100

        comparison_data.append({
            'stock': stock,
            'current_value': current_value,
            'quarter_value': quarter_value,
            'quarter_delta': quarter_delta,
            'quarter_pct': quarter_pct,
            'year_value': year_value,
            'year_delta': year_delta,
            'year_pct': year_pct,
        })

    # Prepare chart data for bar chart
    chart_labels = [stock.symbol for stock in stocks]
    eps_data = [
        float(stock.intrinsic_value) if stock.intrinsic_value else 0
        for stock in stocks
    ]
    fcf_data = [
        float(stock.intrinsic_value_fcf) if stock.intrinsic_value_fcf else 0
        for stock in stocks
    ]

    chart_data = {
        'labels': chart_labels,
        'datasets': [
            {
                'label': 'EPS Method',
                'data': eps_data,
                'backgroundColor': 'rgba(59, 130, 246, 0.8)',
                'borderColor': 'rgb(59, 130, 246)',
                'borderWidth': 1,
            },
            {
                'label': 'FCF Method',
                'data': fcf_data,
                'backgroundColor': 'rgba(34, 197, 94, 0.8)',
                'borderColor': 'rgb(34, 197, 94)',
                'borderWidth': 1,
            }
        ]
    }

    logger.info(f"Valuation comparison view accessed by {request.user.username}")
    logger.debug(f"Comparing {len(comparison_data)} stocks")

    context = {
        'stocks': comparison_data,
        'comparison_date_quarter': previous_quarter_date,
        'comparison_date_year': year_ago_date,
        'chart_data_json': json.dumps(chart_data, ensure_ascii=True),
    }

    return render(request, 'scanner/valuation_comparison.html', context)


def _get_previous_quarter_date(today):
    """Get the previous quarter snapshot date."""
    year = today.year
    month = today.month

    if month < 4:
        return date(year - 1, 10, 1)
    elif month < 7:
        return date(year, 1, 1)
    elif month < 10:
        return date(year, 4, 1)
    else:
        return date(year, 7, 1)


def _get_year_ago_quarter_date(today):
    """Get the snapshot date from one year ago (same quarter)."""
    year = today.year - 1
    month = today.month

    if month < 4:
        return date(year, 1, 1)
    elif month < 7:
        return date(year, 4, 1)
    elif month < 10:
        return date(year, 7, 1)
    else:
        return date(year, 10, 1)


@login_required
def export_valuation_history_csv(request, symbol=None):
    """
    Export valuation history to CSV.

    Args:
        symbol: Optional stock symbol. If None, exports all stocks.

    Returns:
        CSV file download
    """
    # Build filename
    if symbol:
        filename = f"valuation_history_{symbol.upper()}_{date.today().isoformat()}.csv"
        stocks = CuratedStock.objects.filter(symbol=symbol.upper(), active=True)
    else:
        filename = f"valuation_history_all_{date.today().isoformat()}.csv"
        stocks = CuratedStock.objects.filter(active=True)

    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)

    # Write header
    writer.writerow([
        'Symbol',
        'Quarter',
        'Snapshot Date',
        'Calculated At',
        'Intrinsic Value (EPS)',
        'Current EPS',
        'EPS Growth Rate (%)',
        'EPS Multiple',
        'Intrinsic Value (FCF)',
        'Current FCF/Share',
        'FCF Growth Rate (%)',
        'FCF Multiple',
        'Desired Return (%)',
        'Projection Years',
        'Preferred Method',
        'Notes',
    ])

    # Write data rows
    for stock in stocks:
        history = ValuationHistory.objects.filter(stock=stock).order_by('-snapshot_date')

        for snapshot in history:
            writer.writerow([
                stock.symbol,
                snapshot.quarter_label,
                snapshot.snapshot_date.isoformat(),
                snapshot.calculated_at.strftime('%Y-%m-%d %H:%M:%S'),
                snapshot.intrinsic_value,
                snapshot.current_eps,
                snapshot.eps_growth_rate,
                snapshot.eps_multiple,
                snapshot.intrinsic_value_fcf,
                snapshot.current_fcf_per_share,
                snapshot.fcf_growth_rate,
                snapshot.fcf_multiple,
                snapshot.desired_return,
                snapshot.projection_years,
                snapshot.preferred_valuation_method,
                snapshot.notes,
            ])

    logger.info(f"CSV export requested by {request.user.username} for symbol={symbol}")

    return response


def _generate_chart_color(index: int) -> str:
    """
    Generate a consistent color for chart lines based on index.

    Uses a predefined palette of distinct colors for chart visualization.

    Args:
        index: Index for color selection

    Returns:
        RGB color string (e.g., 'rgb(59, 130, 246)')
    """
    colors = [
        'rgb(59, 130, 246)',   # Blue
        'rgb(34, 197, 94)',    # Green
        'rgb(239, 68, 68)',    # Red
        'rgb(251, 146, 60)',   # Orange
        'rgb(168, 85, 247)',   # Purple
        'rgb(236, 72, 153)',   # Pink
        'rgb(14, 165, 233)',   # Sky
        'rgb(132, 204, 22)',   # Lime
        'rgb(251, 191, 36)',   # Amber
        'rgb(6, 182, 212)',    # Cyan
        'rgb(244, 63, 94)',    # Rose
        'rgb(124, 58, 237)',   # Violet
        'rgb(34, 211, 238)',   # Light blue
        'rgb(163, 230, 53)',   # Yellow-green
        'rgb(249, 115, 22)',   # Deep orange
        'rgb(217, 70, 239)',   # Fuchsia
        'rgb(20, 184, 166)',   # Teal
        'rgb(234, 179, 8)',    # Yellow
        'rgb(225, 29, 72)',    # Deep red
        'rgb(99, 102, 241)',   # Indigo
    ]
    return colors[index % len(colors)]


@login_required
@ratelimit(key='user', rate='10/m', method='GET')
@conditionally_cache(60 * 5)  # 5-minute view cache (disabled in tests)
def analytics_view(request):
    """
    Display comprehensive analytics dashboard with portfolio metrics and trends.

    Shows:
    - Portfolio overview with aggregate metrics
    - Multi-line trend chart of intrinsic values over time
    - Stock-by-stock analytics table with volatility, CAGR, correlation
    - Method comparison visualizations

    Returns:
        Rendered analytics.html template with chart data and metrics
    """
    # Get portfolio-wide analytics
    portfolio_analytics = get_portfolio_analytics()

    # Prepare chart data for trend visualization
    # Collect all unique snapshot dates across all stocks
    all_dates = set()
    stocks_data = {}

    active_stocks = CuratedStock.objects.filter(active=True).prefetch_related(
        'valuation_history'
    )

    for stock in active_stocks:
        history = stock.valuation_history.all().order_by('snapshot_date')
        if history.exists():
            stocks_data[stock.symbol] = {
                'history': list(history),
                'color': _generate_chart_color(len(stocks_data)),
            }
            all_dates.update(h.snapshot_date for h in history)

    # Sort dates chronologically
    sorted_dates = sorted(all_dates)

    # Build chart datasets
    chart_labels = [d.strftime('%Y-%m-%d') for d in sorted_dates]
    chart_datasets = []

    for symbol, data in stocks_data.items():
        # Create a mapping of date -> value
        date_value_map = {
            h.snapshot_date: float(h.get_effective_intrinsic_value())
            for h in data['history']
            if h.get_effective_intrinsic_value() is not None
        }

        # Build data array with None for missing dates
        chart_data_points = [
            date_value_map.get(d) for d in sorted_dates
        ]

        chart_datasets.append({
            'label': symbol,
            'data': chart_data_points,
            'borderColor': data['color'],
            'backgroundColor': data['color'],
            'borderWidth': 2,
            'fill': False,
            'spanGaps': True,  # Connect lines even if there are gaps
        })

    chart_data = {
        'labels': chart_labels,
        'datasets': chart_datasets,
    }

    context = {
        'analytics': portfolio_analytics,
        'chart_data_json': json.dumps(chart_data, ensure_ascii=True),
        'date_range': 'All Time',
    }

    logger.info(f"Analytics page accessed by {request.user.username}")

    return render(request, 'scanner/analytics.html', context)


# ===== Individual Stock Search Views =====


def run_individual_scan_in_background(user_id, ticker, option_type, weeks):
    """
    Execute individual stock scan in background thread.

    Args:
        user_id: User ID for cache key scoping
        ticker: Stock ticker symbol (uppercase)
        option_type: 'put' or 'call'
        weeks: Number of weeks to scan (1-52)

    Stores results in user-specific cache keys.
    """
    from scanner.marketdata.options import find_options

    try:
        logger.info(f"Individual scan started for user {user_id}: {ticker} {option_type}s")

        # Set status
        cache.set(
            f"{settings.CACHE_KEY_PREFIX_SCANNER}:individual_scan_status:{user_id}",
            f"Scanning {ticker} for {option_type} options...",
            timeout=600,
        )

        # Allow scans outside market hours in LOCAL environment
        debug_mode = settings.ENVIRONMENT == "LOCAL"

        # Call find_options (reuse existing logic)
        options = find_options(ticker, option_type, weeks, debug_mode)

        # Check if stock is in curated list for IV comparison
        try:
            curated_stock = CuratedStock.objects.get(symbol=ticker, active=True)
            has_intrinsic_value = True
            intrinsic_value = float(curated_stock.get_effective_intrinsic_value()) if curated_stock.get_effective_intrinsic_value() else None
            valuation_method = curated_stock.preferred_valuation_method
        except CuratedStock.DoesNotExist:
            has_intrinsic_value = False
            intrinsic_value = None
            valuation_method = None

        # Store results
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cache.set(
            f"{settings.CACHE_KEY_PREFIX_SCANNER}:individual_scan_results:{user_id}",
            {
                'ticker': ticker,
                'option_type': option_type,
                'options': options,
                'intrinsic_value': intrinsic_value,
                'valuation_method': valuation_method,
                'has_intrinsic_value': has_intrinsic_value,
                'timestamp': timestamp,
            },
            timeout=600,
        )

        cache.set(
            f"{settings.CACHE_KEY_PREFIX_SCANNER}:individual_scan_status:{user_id}",
            f"Scan completed at {timestamp}. Found {len(options)} options.",
            timeout=600,
        )

        logger.info(f"Individual scan completed for user {user_id}: {ticker} - {len(options)} options found")

    except Exception as e:
        logger.error(f"Error during individual scan for user {user_id}: {e}", exc_info=True)
        cache.set(
            f"{settings.CACHE_KEY_PREFIX_SCANNER}:individual_scan_status:{user_id}",
            f"Error scanning {ticker}: {str(e)}",
            timeout=600,
        )

    finally:
        # Release lock
        cache.delete(f"{settings.CACHE_KEY_PREFIX_SCANNER}:individual_scan_lock:{user_id}")
        logger.debug(f"Individual scan lock released for user {user_id}")


@login_required
def individual_search_view(request):
    """
    Display individual stock search form.

    Returns:
        Rendered scanner/search.html template with form
    """
    form = IndividualStockScanForm()

    context = {
        'form': form,
        'is_local_environment': settings.ENVIRONMENT == "LOCAL",
    }

    return render(request, 'scanner/search.html', context)


@login_required
@require_POST
def individual_scan_view(request):
    """
    Trigger individual stock scan in background.

    Enforces quota limit before starting scan. Blocks if quota exceeded.

    Returns:
        HTMX partial: quota_exceeded.html or search_polling.html or form with errors
    """
    form = IndividualStockScanForm(request.POST)

    if not form.is_valid():
        # Return form with validation errors
        context = {
            'form': form,
            'is_local_environment': settings.ENVIRONMENT == "LOCAL",
        }
        return render(request, 'scanner/search.html', context)

    ticker = form.cleaned_data['ticker']
    option_type = form.cleaned_data['option_type']
    weeks = form.cleaned_data.get('weeks', 4)

    user_id = request.user.id

    # CHECK QUOTA AND RECORD USAGE ATOMICALLY (prevents race conditions)
    success, scan_record, error_message = check_and_record_scan(request.user, 'individual', ticker)

    if not success:
        logger.warning(f"Quota exceeded for user {user_id}, blocking individual scan: {ticker} {option_type}")

        # Get current quota info for display
        remaining = get_remaining_quota(request.user)
        limit = get_user_quota(request.user)
        used = limit - remaining

        context = {
            'ticker': ticker,
            'option_type': option_type,
            'used': used,
            'limit': limit,
            'remaining': remaining,
        }

        # Return 200 so HTMX will swap the content (HTMX doesn't swap on 4xx by default)
        # The error is communicated via the HTML content, not the status code
        return render(
            request,
            'scanner/partials/quota_exceeded.html',
            context,
            status=200
        )

    lock_key = f"{settings.CACHE_KEY_PREFIX_SCANNER}:individual_scan_lock:{user_id}"

    # Check if scan already in progress for this user
    if cache.get(lock_key):
        logger.info(f"Scan already in progress for user {user_id}")
        context = _get_individual_scan_context(user_id)
        return render(request, 'scanner/partials/search_polling.html', context)

    # Clear any previous scan results before starting new scan
    prefix = settings.CACHE_KEY_PREFIX_SCANNER
    cache.delete(f"{prefix}:individual_scan_results:{user_id}")
    cache.delete(f"{prefix}:individual_scan_status:{user_id}")

    # Set lock
    cache.set(lock_key, True, timeout=600)

    # Store scan metadata for polling
    cache.set(
        f"{settings.CACHE_KEY_PREFIX_SCANNER}:individual_scan_ticker:{user_id}",
        ticker,
        timeout=600,
    )
    cache.set(
        f"{settings.CACHE_KEY_PREFIX_SCANNER}:individual_scan_type:{user_id}",
        option_type,
        timeout=600,
    )

    logger.info(f"Starting individual scan for user {user_id}: {ticker} {option_type}s")

    # Set initial status for immediate feedback
    cache.set(
        f"{prefix}:individual_scan_status:{user_id}",
        f"Initializing scan for {ticker} {option_type} options...",
        timeout=600,
    )

    # Start background thread
    scan_thread = threading.Thread(
        target=run_individual_scan_in_background,
        args=(user_id, ticker, option_type, weeks),
        daemon=True,
    )
    scan_thread.start()

    # Return polling partial
    context = _get_individual_scan_context(user_id)
    return render(request, 'scanner/partials/search_polling.html', context)


@login_required
def individual_scan_status_view(request):
    """
    Polling endpoint for individual scan progress.

    Returns:
        - search_polling.html if scan in progress
        - search_results.html if scan complete
    """
    user_id = request.user.id
    lock_key = f"{settings.CACHE_KEY_PREFIX_SCANNER}:individual_scan_lock:{user_id}"

    context = _get_individual_scan_context(user_id)

    if cache.get(lock_key):
        # Scan still in progress
        logger.debug(f"Individual scan status check for user {user_id}: in progress")
        return render(request, 'scanner/partials/search_polling.html', context)
    else:
        # Scan complete
        logger.debug(f"Individual scan status check for user {user_id}: complete")
        return render(request, 'scanner/partials/search_results.html', context)


def _get_individual_scan_context(user_id):
    """
    Helper to fetch individual scan context from cache.

    Args:
        user_id: User ID for cache key scoping

    Returns:
        dict: Context with ticker, option_type, status, results
    """
    prefix = settings.CACHE_KEY_PREFIX_SCANNER

    results = cache.get(f"{prefix}:individual_scan_results:{user_id}")
    status = cache.get(f"{prefix}:individual_scan_status:{user_id}", "Initializing scan...")
    ticker = cache.get(f"{prefix}:individual_scan_ticker:{user_id}", "")
    option_type = cache.get(f"{prefix}:individual_scan_type:{user_id}", "")

    context = {
        'ticker': ticker,
        'option_type': option_type,
        'status': status,
        'is_local_environment': settings.ENVIRONMENT == "LOCAL",
    }

    if results:
        context.update(results)

    return context


# ===== Saved Searches Views (Phase 7.1) =====


@login_required
def saved_searches_view(request):
    """
    Display user's saved searches with sorting options.

    Query params:
        sort: 'name' | 'date' | 'frequency' | 'recent' (default: 'date')
    """
    sort_by = request.GET.get('sort', 'date')

    # Base queryset: user's active searches
    searches = SavedSearch.objects.for_user(request.user)

    # Apply sorting
    if sort_by == 'name':
        searches = searches.order_by('ticker')
    elif sort_by == 'frequency':
        searches = searches.order_by('-scan_count', '-last_scanned_at')
    elif sort_by == 'recent':
        # Sort by last_scanned_at with NULL values last
        from django.db.models import F
        searches = searches.order_by(
            F('last_scanned_at').desc(nulls_last=True),
            '-created_at'
        )
    else:  # 'date' (default)
        searches = searches.order_by('-created_at')

    context = {
        'searches': searches,
        'sort_by': sort_by,
    }

    return render(request, 'scanner/saved_searches.html', context)


@login_required
@require_POST
def save_search_view(request):
    """
    Save current search from results page.

    POST params:
        ticker: Stock symbol
        option_type: 'put' or 'call'

    Returns HTMX partial with success/duplicate message.
    """
    ticker = request.POST.get('ticker', '').strip().upper()
    option_type = request.POST.get('option_type', '').strip().lower()

    if not ticker or option_type not in ['put', 'call']:
        context = {
            'status': 'error',
            'message': 'Invalid ticker or option type.'
        }
        return render(request, 'scanner/partials/save_search_message.html', context)

    try:
        saved_search, created = SavedSearch.objects.get_or_create(
            user=request.user,
            ticker=ticker,
            option_type=option_type,
            is_deleted=False,
            defaults={'notes': ''}
        )

        if created:
            logger.info(f"User {request.user.id} saved search: {ticker} {option_type}")
            context = {
                'status': 'success',
                'message': f'Saved {ticker} {option_type}s to your searches!'
            }
        else:
            logger.debug(f"Duplicate save attempt by user {request.user.id}: {ticker} {option_type}")
            context = {
                'status': 'duplicate',
                'message': f'{ticker} {option_type}s is already in your saved searches.'
            }

    except IntegrityError as e:
        logger.error(f"Error saving search for user {request.user.id}: {e}")
        context = {
            'status': 'error',
            'message': 'Failed to save search. Please try again.'
        }

    return render(request, 'scanner/partials/save_search_message.html', context)


@login_required
@require_POST
def delete_search_view(request, pk):
    """
    Soft delete a saved search.

    Args:
        pk: SavedSearch primary key

    Returns redirect to saved searches list.
    """
    saved_search = get_object_or_404(
        SavedSearch.objects.active(),
        pk=pk,
        user=request.user
    )

    saved_search.soft_delete()
    logger.info(f"User {request.user.id} deleted saved search: {saved_search.ticker} {saved_search.option_type}")

    messages.success(request, f'Removed {saved_search.ticker} {saved_search.option_type}s from saved searches.')

    return redirect('scanner:saved_searches')


@login_required
@require_POST
def quick_scan_view(request, pk):
    """
    Trigger background scan from saved search.

    Enforces quota limit before starting scan.

    Args:
        pk: SavedSearch primary key

    Increments scan_count and last_scanned_at, then redirects to scan flow.
    """
    saved_search = get_object_or_404(
        SavedSearch.objects.active(),
        pk=pk,
        user=request.user
    )

    # CHECK QUOTA AND RECORD USAGE ATOMICALLY (prevents race conditions)
    success, scan_record, error_message = check_and_record_scan(request.user, 'individual', saved_search.ticker)

    if not success:
        logger.warning(f"Quota exceeded for user {request.user.id}, blocking quick scan: {saved_search.ticker}")

        # Get current quota info for display
        remaining = get_remaining_quota(request.user)
        limit = get_user_quota(request.user)
        used = limit - remaining

        context = {
            'ticker': saved_search.ticker,
            'option_type': saved_search.option_type,
            'used': used,
            'limit': limit,
            'remaining': remaining,
        }

        # Return 200 so HTMX will swap the content (HTMX doesn't swap on 4xx by default)
        # The error is communicated via the HTML content, not the status code
        return render(
            request,
            'scanner/partials/quota_exceeded.html',
            context,
            status=200
        )

    # Increment usage statistics
    saved_search.increment_scan_count()
    logger.info(f"Quick scan triggered by user {request.user.id}: {saved_search.ticker} {saved_search.option_type} (count: {saved_search.scan_count})")

    # Prepare scan parameters
    ticker = saved_search.ticker
    option_type = saved_search.option_type
    weeks = 4  # Default weeks for quick scan

    user_id = request.user.id
    lock_key = f"{settings.CACHE_KEY_PREFIX_SCANNER}:individual_scan_lock:{user_id}"

    # Check if scan already in progress
    if cache.get(lock_key):
        logger.info(f"Scan already in progress for user {user_id}")
        context = _get_individual_scan_context(user_id)
        return render(request, 'scanner/partials/search_polling.html', context)

    # Clear any previous scan results before starting new scan
    prefix = settings.CACHE_KEY_PREFIX_SCANNER
    cache.delete(f"{prefix}:individual_scan_results:{user_id}")
    cache.delete(f"{prefix}:individual_scan_status:{user_id}")

    # Set lock
    cache.set(lock_key, True, timeout=600)

    # Store scan metadata
    cache.set(
        f"{settings.CACHE_KEY_PREFIX_SCANNER}:individual_scan_ticker:{user_id}",
        ticker,
        timeout=600,
    )
    cache.set(
        f"{settings.CACHE_KEY_PREFIX_SCANNER}:individual_scan_type:{user_id}",
        option_type,
        timeout=600,
    )

    # Set initial status for immediate feedback
    cache.set(
        f"{prefix}:individual_scan_status:{user_id}",
        "Initializing scan...",
        timeout=600,
    )

    logger.info(f"Starting quick scan for user {user_id}: {ticker} {option_type}s")

    # Start background thread (reuse Phase 7 logic)
    scan_thread = threading.Thread(
        target=run_individual_scan_in_background,
        args=(user_id, ticker, option_type, weeks),
        daemon=True,
    )
    scan_thread.start()

    # Return polling partial
    context = _get_individual_scan_context(user_id)
    return render(request, 'scanner/partials/search_polling.html', context)


@login_required
@require_POST
def edit_search_notes_view(request, pk):
    """
    Update notes field for saved search.

    Args:
        pk: SavedSearch primary key

    POST params:
        notes: Updated notes text

    Returns HTMX partial with updated notes display.
    """
    saved_search = get_object_or_404(
        SavedSearch.objects.active(),
        pk=pk,
        user=request.user
    )

    notes = request.POST.get('notes', '').strip()
    saved_search.notes = notes
    saved_search.save(update_fields=['notes'])

    logger.info(f"User {request.user.id} updated notes for {saved_search.ticker} {saved_search.option_type}")

    context = {
        'search': saved_search,
        'status': 'success',
    }

    return render(request, 'scanner/partials/search_notes_display.html', context)


@login_required
def usage_dashboard_view(request):
    """
    Display user's API usage dashboard.

    Shows current usage, quota limit, progress bar, countdown timer,
    and historical usage chart.
    """
    user = request.user

    # Get usage statistics
    used = get_todays_usage_count(user)
    limit = get_user_quota(user)
    remaining = get_remaining_quota(user)
    percentage = (used / limit * 100) if limit > 0 else 0

    # Determine progress bar color
    if percentage < 70:
        progress_color = 'green'
    elif percentage < 90:
        progress_color = 'yellow'
    else:
        progress_color = 'red'

    # Get breakdown by scan type (today only)
    eastern = ZoneInfo('US/Eastern')
    now_eastern = datetime.now(eastern)
    today_start = now_eastern.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    curated_count = ScanUsage.objects.filter(
        user=user,
        scan_type='curated',
        timestamp__gte=today_start,
        timestamp__lt=today_end
    ).count()

    individual_count = ScanUsage.objects.filter(
        user=user,
        scan_type='individual',
        timestamp__gte=today_start,
        timestamp__lt=today_end
    ).count()

    # Get historical data for chart (last 7 days)
    history = get_usage_history(user, days=7)

    # Calculate seconds until reset
    seconds_until_reset = get_seconds_until_reset()

    context = {
        'used': used,
        'limit': limit,
        'remaining': remaining,
        'percentage': round(percentage, 1),
        'progress_color': progress_color,
        'curated_count': curated_count,
        'individual_count': individual_count,
        'chart_labels': json.dumps(history['labels']),
        'chart_data': json.dumps(history['data']),
        'seconds_until_reset': seconds_until_reset,
        'is_superuser': user.is_superuser,
    }

    return render(request, 'scanner/usage_dashboard.html', context)


# ========================
# Staff Monitoring Views
# ========================


@staff_member_required
def scan_monitor_view(request):
    """
    Staff-only page to monitor scan operations and diagnose issues.

    Shows:
    - Current scan status from database
    - Redis lock state (exists/clear, TTL)
    - Ability to clear stuck locks
    """
    scan_lock_key = f"{settings.CACHE_KEY_PREFIX_SCANNER}:{SCAN_LOCK_KEY}"

    # Get the most recent scan status from database
    latest_scan = ScanStatus.objects.first()  # Ordered by -start_time

    # Check Redis lock state
    lock_exists = cache.get(scan_lock_key) is not None
    lock_value = cache.get(scan_lock_key)

    # Get TTL for the lock (if it exists)
    # Note: Django's cache backend doesn't expose TTL directly,
    # so we'll use redis-py to get it for this diagnostic view
    lock_ttl = None
    if lock_exists:
        try:
            from django_redis import get_redis_connection
            redis_conn = get_redis_connection("default")
            # The cache key includes the prefix "wheel_analyzer:1:"
            full_key = f"wheel_analyzer:1:{scan_lock_key}"
            lock_ttl = redis_conn.ttl(full_key)
        except Exception as e:
            logger.warning(f"Could not get lock TTL: {e}")

    # Format duration for template
    duration_str = None
    if latest_scan and latest_scan.duration is not None:
        total_seconds = int(latest_scan.duration)
        minutes, seconds = divmod(total_seconds, 60)
        if minutes > 0:
            duration_str = f"{minutes}m {seconds}s"
        else:
            duration_str = f"{seconds}s"

    context = {
        'latest_scan': latest_scan,
        'lock_exists': lock_exists,
        'lock_value': lock_value,
        'lock_ttl': lock_ttl,
        'lock_key': scan_lock_key,
        'duration_str': duration_str,
    }

    return render(request, 'scanner/scan_monitor.html', context)


@staff_member_required
@require_POST
def clear_scan_lock_view(request):
    """
    Clear the Redis scan lock and abort any in-progress scan in the database.

    This is used when a scan gets stuck and needs manual intervention.
    """
    scan_lock_key = f"{settings.CACHE_KEY_PREFIX_SCANNER}:{SCAN_LOCK_KEY}"

    # Delete the Redis lock
    cache.delete(scan_lock_key)
    logger.info(f"Staff user {request.user.username} cleared scan lock: {scan_lock_key}")

    # Find any active scans and mark them as aborted
    active_scans = ScanStatus.objects.filter(status__in=['pending', 'in_progress'])
    aborted_count = 0

    for scan in active_scans:
        scan.mark_aborted(reason=f'Manually aborted by staff user {request.user.username}')
        aborted_count += 1
        logger.info(f"Marked scan {scan.id} as aborted by {request.user.username}")

    # Return HTMX-friendly response
    return render(request, 'scanner/partials/lock_cleared_message.html', {
        'aborted_count': aborted_count,
        'username': request.user.username,
    })
