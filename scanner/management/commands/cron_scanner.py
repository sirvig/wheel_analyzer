import json
import logging
import os
from datetime import datetime

import redis
from django.conf import settings
from django.core.management.base import BaseCommand

from scanner.marketdata.options import find_options
from scanner.marketdata.util import is_market_open

logger = logging.getLogger(__name__)
DEBUG = False

TTL = 30 * 60  # 30 minutes


class Command(BaseCommand):
    help = "Scan options"

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument("--debug", type=bool, required=False, default=False)

    def handle(self, *args, **options):
        DEBUG = options["debug"]
        r = redis.Redis.from_url(os.environ.get("REDIS_URL"))

        # Define the path to the JSON file
        json_file_path = os.path.join(
            f"{settings.BASE_DIR}/scanner/data", "options.json"
        )

        # Read the JSON file
        with open(json_file_path, "r") as file:
            data = json.load(file)

        test_open = is_market_open()
        if not test_open and not DEBUG:
            logger.info("Market is closed")
            exit(0)

        # Find puts
        contract_type = "put"
        total_tickers = len(data[contract_type])
        counter = 0
        for ticker in data[contract_type]:
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
        r.set("last_run", now.strftime("%Y-%m-%d %H:%M"))
