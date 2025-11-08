import json
import logging
import os
import threading
from datetime import datetime

import redis
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_POST

from scanner.models import CuratedStock
from scanner.scanner import perform_scan

logger = logging.getLogger(__name__)

SCAN_LOCK_KEY = "scan_in_progress"
SCAN_LOCK_TIMEOUT = 600  # 10 minutes


@login_required
def index(request):
    r = redis.Redis.from_url(os.environ.get("REDIS_URL"))
    keys = r.keys("put_*")

    context = {}
    ticker_options = {}
    ticker_scan = {}

    for hash_key in keys:
        ticker = hash_key.decode("utf-8").split("_")[1]
        options = json.loads(r.hget(hash_key, "options").decode("utf-8"))
        if len(options) > 0:
            ticker_options[ticker] = options
            ticker_scan[ticker] = r.hget(hash_key, "last_scan").decode("utf-8")

    sorted_ticker_options = {k: ticker_options[k] for k in sorted(ticker_options)}
    context["ticker_options"] = sorted_ticker_options
    context["ticker_scan"] = ticker_scan
    context["last_scan"] = r.get("last_run").decode("utf-8")

    return render(request, "scanner/index.html", context)


@login_required
def options_list(request, ticker):
    r = redis.Redis.from_url(os.environ.get("REDIS_URL"))
    hash_key = f"put_{ticker}"
    options = json.loads(r.hget(hash_key, "options").decode("utf-8"))

    context = {"ticker": ticker, "options": options}

    return render(request, "scanner/options_list.html", context)


def run_scan_in_background():
    r = redis.Redis.from_url(os.environ.get("REDIS_URL"))
    """
    Execute the scan in a background thread.

    This function is responsible for:
    - Running the actual scan
    - Releasing the Redis lock when complete
    - Handling errors and setting appropriate status messages
    """
    try:
        logger.info("Background scan thread started")
        result = perform_scan(debug=False)

        if result["success"]:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            completion_message = f"Scan completed successfully at {timestamp}"
            r.set("last_run", completion_message)
            logger.info(
                f"Background scan completed successfully: {result['scanned_count']} tickers"
            )
        else:
            logger.warning(f"Background scan failed: {result['message']}")
            # Set last_run to error message so it displays in the UI
            r.set("last_run", result["message"])

    except Exception as e:
        logger.error(f"Error during background scan: {e}", exc_info=True)
        # Set last_run to error message
        r.set("last_run", "An error occurred during the scan. Please check logs.")

    finally:
        # Always release the lock
        r.delete(SCAN_LOCK_KEY)
        logger.debug("Background scan complete, lock released")


def get_scan_results():
    r = redis.Redis.from_url(os.environ.get("REDIS_URL"))
    """
    Helper function to fetch current scan results from Redis.

    Returns:
        dict: Context with ticker_options, ticker_scan, last_scan, and curated_stocks
    """
    keys = r.keys("put_*")
    ticker_options = {}
    ticker_scan = {}

    for hash_key in keys:
        ticker = hash_key.decode("utf-8").split("_")[1]
        options_data = r.hget(hash_key, "options")
        if options_data:
            options = json.loads(options_data.decode("utf-8"))
            if len(options) > 0:
                ticker_options[ticker] = options
                last_scan_data = r.hget(hash_key, "last_scan")
                if last_scan_data:
                    ticker_scan[ticker] = last_scan_data.decode("utf-8")

    sorted_ticker_options = {k: ticker_options[k] for k in sorted(ticker_options)}

    # Get last_run status
    last_run_data = r.get("last_run")
    last_scan = last_run_data.decode("utf-8") if last_run_data else "Never"

    # Fetch CuratedStock instances for all symbols in results
    if sorted_ticker_options:
        symbols = list(sorted_ticker_options.keys())
        curated_stocks = CuratedStock.objects.filter(symbol__in=symbols, is_active=True)
        curated_stocks_dict = {stock.symbol: stock for stock in curated_stocks}
    else:
        curated_stocks_dict = {}

    return {
        "ticker_options": sorted_ticker_options,
        "ticker_scan": ticker_scan,
        "last_scan": last_scan,
        "curated_stocks": curated_stocks_dict,
    }


@login_required
@require_POST
def scan_view(request):
    r = redis.Redis.from_url(os.environ.get("REDIS_URL"))
    """
    Trigger a manual options scan asynchronously.

    Starts a background thread to perform the scan and immediately returns
    a polling partial that will update as results become available.
    """
    # Check if a scan is already in progress
    if r.exists(SCAN_LOCK_KEY):
        logger.info("Scan already in progress, allowing user to watch")
        # Allow user to watch the existing scan by returning polling partial
        context = get_scan_results()
        return render(request, "scanner/partials/scan_polling.html", context)

    # Set the lock with a timeout to prevent it from getting stuck
    r.setex(SCAN_LOCK_KEY, SCAN_LOCK_TIMEOUT, "1")

    # Set initial status before starting scan
    r.set("last_run", "Scanning in progress...")

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
    r = redis.Redis.from_url(os.environ.get("REDIS_URL"))
    """
    Polling endpoint to check scan status and return updated results.

    This endpoint is called every 15 seconds by the frontend to check if
    the scan is complete and to fetch updated results.

    Returns:
        - scan_polling.html if scan is still in progress (continues polling)
        - options_results.html if scan is complete (stops polling)
    """
    # Get current results from Redis
    context = get_scan_results()

    # Check if scan is still in progress
    if r.exists(SCAN_LOCK_KEY):
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
    stocks = CuratedStock.objects.filter(is_active=True).order_by("symbol")

    logger.info(f"Valuation list view accessed by {request.user.username}")
    logger.debug(f"Displaying {stocks.count()} active curated stocks")

    context = {
        "stocks": stocks,
    }

    return render(request, "scanner/valuations.html", context)
