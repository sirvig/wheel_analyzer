import logging
from datetime import datetime

from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand

from scanner.scanner import perform_scan

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Scan options and cache results for scanner UI"

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument("--debug", type=bool, required=False, default=False)

    def handle(self, *args, **options):
        debug = options["debug"]

        # Perform the scan
        result = perform_scan(debug=debug)

        if result["success"]:
            # Cache the scan results using Django cache
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            completion_message = f"Scan completed successfully at {timestamp}"

            # Build dictionaries for caching
            scan_results = result.get("scan_results", {})
            ticker_options = {}
            ticker_scan_times = {}

            for ticker, options in scan_results.items():
                if options:  # Only store if options found
                    ticker_options[ticker] = options
                    ticker_scan_times[ticker] = timestamp

            # Store in Django cache with 45-minute TTL
            try:
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

                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Scan completed: {result['scanned_count']} tickers at {result['timestamp']}"
                    )
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Cached {len(ticker_options)} tickers with options"
                    )
                )

            except Exception as e:
                self.stdout.write(self.style.WARNING(f"✗ Cache operation failed: {e}"))
                logger.exception("Failed to cache scan results")
                # Scan succeeded, only caching failed
                exit(1)

        else:
            # Scan failed
            self.stdout.write(self.style.WARNING(f"✗ Scan failed: {result['message']}"))

            # Update cache with failure message
            try:
                cache.set(
                    f"{settings.CACHE_KEY_PREFIX_SCANNER}:last_run",
                    result["message"],
                    timeout=settings.CACHE_TTL_OPTIONS,
                )
            except Exception as e:
                logger.warning(f"Failed to cache error message: {e}")

            if not result.get("scanned_count", 0):
                exit(0)  # Exit cleanly if market is closed
            else:
                exit(1)  # Exit with error if scan failed with other error
