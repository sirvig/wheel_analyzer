"""Core scanner functionality for finding options."""

import json
import logging
import os
from datetime import datetime

import redis

from scanner.marketdata.options import find_options
from scanner.marketdata.util import is_market_open
from scanner.models import CuratedStock

logger = logging.getLogger(__name__)

TTL = 30 * 60  # 30 minutes


def perform_scan(debug=False):
    """
    Perform an options scan for all active curated stocks.

    Args:
        debug: If True, skip market hours check and enable debug logging

    Returns:
        dict: Scan results with keys:
            - success (bool): Whether scan completed successfully
            - message (str): Status message
            - scanned_count (int): Number of tickers scanned
            - timestamp (str): Completion timestamp
    """
    try:
        r = redis.Redis.from_url(os.environ.get("REDIS_URL"))

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
            }

        # Find puts
        contract_type = "put"
        total_tickers = len(tickers)
        counter = 0

        logger.info(f"Starting scan of {total_tickers} tickers")

        for ticker in tickers:
            logger.debug(f"Finding options for {ticker}")

            # Calculate the percentage of the loop remaining
            counter += 1
            percentage_completed = (counter / total_tickers) * 100
            r.set(
                "last_run", f"Currently Running - {percentage_completed:.2f}% completed"
            )

            options = find_options(ticker, contract_type)
            hash_key = f"{contract_type}_{ticker}"
            r.hset(hash_key, "options", json.dumps(options))
            now = datetime.now()
            r.hset(hash_key, "last_scan", now.strftime("%Y-%m-%d %H:%M"))
            r.expire(hash_key, TTL)

        # Last scan timestamp
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M")
        r.set("last_run", timestamp)

        logger.info(f"Scan completed successfully. Scanned {total_tickers} tickers")

        return {
            "success": True,
            "message": f"Scan completed successfully at {timestamp}",
            "scanned_count": total_tickers,
            "timestamp": timestamp,
        }

    except Exception as e:
        logger.error(f"Error during scan: {e}", exc_info=True)
        return {
            "success": False,
            "message": "An error occurred during the scan. Please check logs for details.",
            "scanned_count": 0,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "error": str(e),
        }
