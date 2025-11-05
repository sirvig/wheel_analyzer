"""
Django management command to calculate intrinsic value for curated stocks.

This command fetches current EPS data from Alpha Vantage and calculates
the intrinsic value (fair value) for all active stocks in the curated list
using an EPS-based DCF model.

Usage:
    python manage.py calculate_intrinsic_value
    python manage.py calculate_intrinsic_value --symbols AAPL MSFT
    python manage.py calculate_intrinsic_value --force-refresh
    python manage.py calculate_intrinsic_value --clear-cache

Schedule:
    Run weekly on Monday evenings via cron:
    0 20 * * 1 cd /path/to/project && python manage.py calculate_intrinsic_value
"""

import logging
import time
from decimal import Decimal

from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from scanner.alphavantage.util import get_market_data
from scanner.models import CuratedStock
from scanner.valuation import calculate_intrinsic_value

logger = logging.getLogger(__name__)

# Rate limiting configuration
ALPHA_VANTAGE_CALLS_PER_MINUTE = 5
RATE_LIMIT_DELAY = 60 / ALPHA_VANTAGE_CALLS_PER_MINUTE  # 12 seconds
CACHE_TTL = 60 * 60 * 24 * 7  # 7 days in seconds


class Command(BaseCommand):
    help = "Calculate intrinsic value for curated stocks using DCF model"

    def add_arguments(self, parser):
        parser.add_argument(
            "--symbols",
            nargs="+",
            type=str,
            help="Specific stock symbols to calculate (default: all active stocks)",
        )
        parser.add_argument(
            "--force-refresh",
            action="store_true",
            help="Force refresh of cached API data",
        )
        parser.add_argument(
            "--clear-cache",
            action="store_true",
            help="Clear all cached Alpha Vantage data before processing",
        )

    def handle(self, *args, **options):
        """Main command execution."""
        # Log command start
        logger.info("=" * 60)
        logger.info("Starting intrinsic value calculation command")
        logger.info(f"Options: {options}")
        logger.info("=" * 60)

        start_time = timezone.now()

        self.stdout.write(self.style.SUCCESS("Starting intrinsic value calculation..."))

        # Clear cache if requested
        if options.get("clear_cache"):
            self._clear_alpha_vantage_cache()

        # Get stocks to process
        try:
            stocks = self._get_stocks_to_process(options.get("symbols"))
        except CommandError as e:
            self.stdout.write(self.style.ERROR(str(e)))
            return

        total_stocks = len(stocks)

        if total_stocks == 0:
            self.stdout.write(self.style.WARNING("No stocks to process"))
            return

        self.stdout.write(f"Processing {total_stocks} stock(s)...")

        # Process each stock
        success_count = 0
        error_count = 0
        skipped_count = 0

        for index, stock in enumerate(stocks, start=1):
            self.stdout.write(
                f"\n[{index}/{total_stocks}] Processing {stock.symbol}..."
            )

            try:
                result = self._process_stock(
                    stock, force_refresh=options.get("force_refresh", False)
                )

                if result["status"] == "success":
                    success_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  ✓ Calculated intrinsic value: ${result['intrinsic_value']}"
                        )
                    )
                elif result["status"] == "skipped":
                    skipped_count += 1
                    self.stdout.write(
                        self.style.WARNING(f"  ⊘ Skipped: {result['reason']}")
                    )

            except Exception as e:
                error_count += 1
                logger.error(f"Error processing {stock.symbol}: {e}", exc_info=True)
                self.stdout.write(self.style.ERROR(f"  ✗ Error: {str(e)}"))

            # Rate limiting: wait between API calls
            if index < total_stocks:
                self._rate_limit_delay()

        # Summary
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()

        self.stdout.write(self.style.SUCCESS(f"\n{'=' * 60}"))
        self.stdout.write(self.style.SUCCESS("SUMMARY:"))
        self.stdout.write(self.style.SUCCESS(f"  Total processed: {total_stocks}"))
        self.stdout.write(self.style.SUCCESS(f"  Successful: {success_count}"))
        self.stdout.write(self.style.WARNING(f"  Skipped: {skipped_count}"))
        self.stdout.write(self.style.ERROR(f"  Errors: {error_count}"))
        self.stdout.write(self.style.SUCCESS(f"  Duration: {duration:.2f} seconds"))
        self.stdout.write(self.style.SUCCESS(f"{'=' * 60}\n"))

        # Log command completion
        logger.info("=" * 60)
        logger.info(f"Command completed in {duration:.2f} seconds")
        logger.info(
            f"Success: {success_count}, Skipped: {skipped_count}, Errors: {error_count}"
        )
        logger.info("=" * 60)

    def _get_stocks_to_process(self, symbols=None):
        """
        Get list of CuratedStock objects to process.

        Args:
            symbols: Optional list of specific symbols to process

        Returns:
            QuerySet of CuratedStock objects
        """
        if symbols:
            # Process specific symbols
            stocks = CuratedStock.objects.filter(
                symbol__in=[s.upper() for s in symbols]
            )

            if not stocks.exists():
                raise CommandError(
                    f"No stocks found with symbols: {', '.join(symbols)}"
                )

            # Warn about inactive stocks
            inactive = stocks.filter(active=False)
            if inactive.exists():
                self.stdout.write(
                    self.style.WARNING(
                        f"Note: {inactive.count()} inactive stock(s) will be processed"
                    )
                )
        else:
            # Process all active stocks
            stocks = CuratedStock.objects.filter(active=True)

        return stocks.order_by("symbol")

    def _process_stock(self, stock, force_refresh=False):
        """
        Process a single stock: fetch EPS, calculate intrinsic value, save.

        Args:
            stock: CuratedStock instance
            force_refresh: Force refresh of cached API data

        Returns:
            Dictionary with status and result details
        """
        # Check if stock has valid DCF assumptions
        if not self._validate_assumptions(stock):
            return {"status": "skipped", "reason": "Missing or invalid DCF assumptions"}

        # Fetch current EPS from Alpha Vantage (with caching)
        try:
            overview_data = self._fetch_eps_data(
                stock.symbol, force_refresh=force_refresh
            )

            if not overview_data or "EPS" not in overview_data:
                return {
                    "status": "skipped",
                    "reason": "EPS data not available from API",
                }

            # Check for API error messages
            if "Error Message" in overview_data:
                return {
                    "status": "skipped",
                    "reason": f"API error: {overview_data['Error Message']}",
                }

            if "Note" in overview_data:
                return {
                    "status": "skipped",
                    "reason": f"API rate limit: {overview_data['Note']}",
                }

            current_eps = Decimal(overview_data["EPS"])

            if current_eps <= 0:
                return {
                    "status": "skipped",
                    "reason": f"Invalid EPS value: {current_eps}",
                }

        except (ValueError, KeyError) as e:
            logger.warning(f"Invalid data for {stock.symbol}: {e}")
            return {"status": "skipped", "reason": f"Invalid data: {str(e)}"}
        except Exception as e:
            logger.error(f"Error fetching EPS for {stock.symbol}: {e}")
            return {"status": "error", "reason": f"API error: {str(e)}"}

        # Update current_eps in database
        stock.current_eps = current_eps

        # Calculate intrinsic value using DCF model
        try:
            dcf_result = calculate_intrinsic_value(
                current_eps=current_eps,
                eps_growth_rate=stock.eps_growth_rate,
                eps_multiple=stock.eps_multiple,
                desired_return=stock.desired_return,
                projection_years=stock.projection_years,
            )

            intrinsic_value = dcf_result["intrinsic_value"]

        except Exception as e:
            logger.error(f"Error calculating intrinsic value for {stock.symbol}: {e}")
            return {"status": "error", "reason": f"Calculation error: {str(e)}"}

        # Save results to database
        stock.intrinsic_value = intrinsic_value
        stock.last_calculation_date = timezone.now()
        stock.save()

        logger.info(
            f"Updated {stock.symbol}: EPS=${current_eps}, "
            f"Intrinsic Value=${intrinsic_value}"
        )

        return {
            "status": "success",
            "intrinsic_value": intrinsic_value,
            "current_eps": current_eps,
            "dcf_details": dcf_result,
        }

    def _validate_assumptions(self, stock):
        """
        Validate that stock has required DCF assumptions.

        Returns:
            True if assumptions are valid, False otherwise
        """
        # Check that required fields are set
        required_fields = [
            "eps_growth_rate",
            "eps_multiple",
            "desired_return",
            "projection_years",
        ]

        for field in required_fields:
            value = getattr(stock, field)
            if value is None or (isinstance(value, (int, Decimal)) and value <= 0):
                self.stdout.write(self.style.WARNING(f"  Invalid {field}: {value}"))
                return False

        return True

    def _fetch_eps_data(self, symbol, force_refresh=False):
        """
        Fetch EPS data from Alpha Vantage with Redis caching.

        Cache TTL: 7 days (604800 seconds)
        Cache key format: av_overview_{symbol}

        Args:
            symbol: Stock ticker symbol
            force_refresh: Bypass cache and fetch fresh data

        Returns:
            Dictionary with overview data from Alpha Vantage
        """
        cache_key = f"av_overview_{symbol}"

        # Try to get from cache (unless force refresh)
        if not force_refresh:
            cached_data = cache.get(cache_key)
            if cached_data:
                self.stdout.write(self.style.SUCCESS("  Using cached data"))
                logger.debug(f"Cache hit for {symbol}")
                return cached_data

        # Fetch from API
        self.stdout.write("  Fetching from Alpha Vantage API...")
        logger.debug(f"Cache miss for {symbol}, fetching from API")

        url = f"function=OVERVIEW&symbol={symbol}"
        overview_data = get_market_data(url)

        # Cache the response
        if overview_data:
            cache.set(cache_key, overview_data, CACHE_TTL)
            logger.debug(f"Cached data for {symbol} (TTL: {CACHE_TTL}s)")

        return overview_data

    def _rate_limit_delay(self):
        """
        Implement rate limiting: 5 calls per minute = 12 seconds between calls.
        """
        self.stdout.write(
            self.style.WARNING(
                f"  Rate limiting: waiting {RATE_LIMIT_DELAY:.0f} seconds..."
            )
        )

        time.sleep(RATE_LIMIT_DELAY)

    def _clear_alpha_vantage_cache(self):
        """Clear all cached Alpha Vantage overview data."""
        # Get all curated stocks to clear their cache
        symbols = CuratedStock.objects.values_list("symbol", flat=True)

        cleared = 0
        for symbol in symbols:
            cache_key = f"av_overview_{symbol}"
            if cache.delete(cache_key):
                cleared += 1

        self.stdout.write(self.style.SUCCESS(f"Cleared {cleared} cached entries"))
        logger.info(f"Cleared {cleared} Alpha Vantage cache entries")
