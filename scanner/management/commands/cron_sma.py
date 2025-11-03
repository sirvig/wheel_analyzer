import logging
import os

import redis
from django.core.management.base import BaseCommand

from scanner.alphavantage.technical_analysis import find_sma
from scanner.models import CuratedStock

logger = logging.getLogger(__name__)
DEBUG = False

TTL = 15 * 60  # 15 minutes


class Command(BaseCommand):
    help = "Scan options"

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument("--debug", type=bool, required=False, default=False)

    def handle(self, *args, **options):
        DEBUG = options["debug"]
        r = redis.Redis.from_url(os.environ.get("REDIS_URL"))

        # Get active stocks from database
        tickers = CuratedStock.objects.filter(active=True).values_list(
            "symbol", flat=True
        )

        for ticker in tickers:
            logger.debug(f"Finding SMA for {ticker}")
            fifty_day_sma = find_sma(ticker, 50)
            two_hundred_day_sma = find_sma(ticker, 200)

            # Example data
            # {
            #     "Meta Data": {
            #         "1: Symbol": "ALB",
            #         "2: Indicator": "Simple Moving Average (SMA)",
            #         "3: Last Refreshed": "2024-12-13",
            #         "4: Interval": "daily",
            #         "5: Time Period": 200,
            #         "6: Series Type": "open",
            #         "7: Time Zone": "US/Eastern"
            #     },
            #     "Technical Analysis: SMA": {
            #         "2024-12-13": {
            #             "SMA": "104.3637"
            #         },
            #         "2024-12-12": {
            #             "SMA": "104.5257"
            #         },
            #         "2024-12-11": {
            #             "SMA": "104.6527"
            #         },

            # Get the last refreshed date
            # Look for the SMA for that date

            # hash_key = f"sma_{ticker}"
            # r.hset(hash_key, "sma", json.dumps(sma_data))
