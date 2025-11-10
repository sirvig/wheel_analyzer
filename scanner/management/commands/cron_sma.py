import logging

from django.core.management.base import BaseCommand

from scanner.alphavantage.technical_analysis import find_sma
from scanner.models import CuratedStock

logger = logging.getLogger(__name__)
DEBUG = False


class Command(BaseCommand):
    help = "Calculate and cache SMA data for curated stocks"

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument("--debug", type=bool, required=False, default=False)

    def handle(self, *args, **options):
        DEBUG = options["debug"]

        # Get active stocks from database
        tickers = CuratedStock.objects.filter(active=True).values_list(
            "symbol", flat=True
        )

        success_count = 0
        for ticker in tickers:
            logger.debug(f"Finding SMA for {ticker}")
            try:
                # Call find_sma which uses get_market_data with Django cache
                # Data is automatically cached for 7 days (CACHE_TTL_ALPHAVANTAGE)
                fifty_day_sma = find_sma(ticker, 50)
                two_hundred_day_sma = find_sma(ticker, 200)

                if fifty_day_sma or two_hundred_day_sma:
                    success_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"✓ Cached SMA data for {ticker}")
                    )
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f"✗ Failed to cache SMA for {ticker}: {e}")
                )
                logger.exception(f"Error caching SMA for {ticker}")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSMA caching complete: {success_count}/{len(tickers)} tickers"
            )
        )
