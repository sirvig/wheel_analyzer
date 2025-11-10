"""Core scanner functionality for finding options."""

import logging
from datetime import datetime

from scanner.marketdata.options import find_options
from scanner.marketdata.util import is_market_open
from scanner.models import CuratedStock

logger = logging.getLogger(__name__)


def perform_scan(debug=False):
    """
    Perform an options scan for all active curated stocks.

    This function scans for put options and returns the results. The caller
    is responsible for caching the results using Django cache.

    Args:
        debug: If True, skip market hours check and enable debug logging

    Returns:
        dict: Scan results with keys:
            - success (bool): Whether scan completed successfully
            - message (str): Status message
            - scanned_count (int): Number of tickers scanned
            - timestamp (str): Completion timestamp
            - scan_results (dict): Dictionary of {ticker: options_list} if successful
    """
    try:
        # Get active stocks from database
        tickers = list(
            CuratedStock.objects.filter(active=True).values_list("symbol", flat=True)
        )

        # Check if market is open
        test_open = is_market_open()
        if not test_open and not debug:
            logger.info("Market is closed")
            return {
                "success": False,
                "message": "Market is closed. Scans only run during market hours (9:30 AM - 4:00 PM ET).",
                "scanned_count": 0,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "scan_results": {},
            }

        # Find puts
        contract_type = "put"
        total_tickers = len(tickers)
        scan_results = {}

        logger.info(f"Starting scan of {total_tickers} tickers")

        for ticker in tickers:
            logger.debug(f"Finding options for {ticker}")

            options = find_options(ticker, contract_type)
            if options:
                scan_results[ticker] = options

        # Last scan timestamp
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M")

        logger.info(f"Scan completed successfully. Scanned {total_tickers} tickers")

        return {
            "success": True,
            "message": f"Scan completed successfully at {timestamp}",
            "scanned_count": total_tickers,
            "timestamp": timestamp,
            "scan_results": scan_results,
        }

    except Exception as e:
        logger.error(f"Error during scan: {e}", exc_info=True)
        return {
            "success": False,
            "message": "An error occurred during the scan. Please check logs for details.",
            "scanned_count": 0,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "error": str(e),
            "scan_results": {},
        }
