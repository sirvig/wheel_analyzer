"""
Django management command to calculate intrinsic value for curated stocks.

This command fetches EPS TTM and FCF data from Alpha Vantage and calculates
the intrinsic value (fair value) for stocks in the curated list using both
EPS-based and FCF-based DCF models.

The command implements a smart selection strategy to respect AlphaVantage's
25 API calls/day limit on the free tier. By default, it processes 7 stocks
per run (21 API calls), prioritizing never-calculated stocks and then
selecting the oldest-calculated stocks for a rolling update approach.

EPS is calculated as Trailing Twelve Months (TTM) by summing the 4 most recent
quarterly reportedEPS values from the EARNINGS endpoint.

The command makes 3 API calls per stock:
- EARNINGS: to calculate EPS TTM from quarterly data
- OVERVIEW: to fetch SharesOutstanding (needed for FCF calculation)
- CASH_FLOW: to calculate FCF TTM from quarterly data

All API responses are cached in Django cache for 7 days to minimize API usage.

Usage:
    # Default: smart select 7 stocks (21 API calls)
    python manage.py calculate_intrinsic_value

    # Custom limit: process 10 stocks
    python manage.py calculate_intrinsic_value --limit 10

    # Force all: process all active stocks (shows warning if >25 calls)
    python manage.py calculate_intrinsic_value --force-all

    # Specific symbols (bypasses smart selection)
    python manage.py calculate_intrinsic_value --symbols AAPL MSFT

    # Force refresh API data (bypass cache)
    python manage.py calculate_intrinsic_value --force-refresh

    # Clear cache before processing
    python manage.py calculate_intrinsic_value --clear-cache

Schedule:
    Run daily at 8 PM via cron for rolling updates:
    0 20 * * * cd /path/to/project && python manage.py calculate_intrinsic_value

    With 7 stocks/day, all stocks refresh within ~7 days (for 50 stocks).

Smart Selection Logic:
    1. Prioritize stocks with NULL last_calculation_date (never calculated)
    2. Then select stocks with oldest last_calculation_date (stale valuations)
    3. Limit to N stocks (default: 7) to respect API quotas

API Rate Limiting:
    - AlphaVantage free tier: 25 calls/day
    - Default: 7 stocks × 3 calls = 21 API calls (conservative)
    - Rate limiting: 20 seconds between stocks (3 calls/minute)
    - Cache: 7-day TTL reduces actual API calls significantly
    - Use --force-all carefully to avoid rate limits

Reporting:
    - Detailed per-stock output with before/after values
    - Delta and percentage change calculations
    - API call tracking (actual calls vs cache hits)
    - Cache hit rate statistics
    - Remaining stocks to calculate
"""

import logging
import time
from decimal import Decimal

from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from scanner.alphavantage.util import get_market_data
from scanner.models import CuratedStock
from scanner.valuation import (
    calculate_eps_ttm_from_quarters,
    calculate_fcf_from_quarters,
    calculate_fcf_per_share,
    calculate_intrinsic_value,
    calculate_intrinsic_value_fcf,
)

logger = logging.getLogger(__name__)

# Rate limiting configuration
# Conservative: 3 calls/minute due to triple API calls per stock:
# - EARNINGS (for EPS TTM calculation)
# - OVERVIEW (for SharesOutstanding, needed for FCF calculation)
# - CASH_FLOW (for FCF calculation)
ALPHA_VANTAGE_CALLS_PER_MINUTE = 3
RATE_LIMIT_DELAY = 60 / ALPHA_VANTAGE_CALLS_PER_MINUTE  # 20 seconds
CACHE_TTL = 60 * 60 * 24 * 7  # 7 days in seconds


class Command(BaseCommand):
    help = "Calculate intrinsic value for curated stocks using DCF model"

    def add_arguments(self, parser):
        parser.add_argument(
            "--symbols",
            nargs="+",
            type=str,
            help="Specific stock symbols to calculate (default: smart selection)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=7,
            help="Number of stocks to process (default: 7 for ~21 API calls)",
        )
        parser.add_argument(
            "--force-all",
            action="store_true",
            help="Process ALL active stocks (ignores --limit, may exceed API limits)",
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

        # Initialize API tracking counters
        self.api_calls_made = 0
        self.cache_hits = 0

        self.stdout.write(self.style.SUCCESS("Starting intrinsic value calculation..."))

        # Clear cache if requested
        if options.get("clear_cache"):
            self._clear_alpha_vantage_cache()

        # Get stocks to process
        try:
            stocks = self._get_stocks_to_process(
                symbols=options.get("symbols"),
                limit=options.get("limit", 7),
                force_all=options.get("force_all", False),
            )
        except CommandError as e:
            self.stdout.write(self.style.ERROR(str(e)))
            return

        total_stocks = len(stocks)

        if total_stocks == 0:
            self.stdout.write(self.style.WARNING("No stocks to process"))
            return

        # Print pre-execution summary
        self._print_pre_execution_summary(
            stocks,
            force_all=options.get("force_all", False),
            limit=options.get("limit", 7),
        )

        self.stdout.write(f"Processing {total_stocks} stock(s)...")

        # Process each stock - track separate statistics for EPS and FCF
        eps_success = 0
        eps_skipped = 0
        eps_error = 0
        fcf_success = 0
        fcf_skipped = 0
        fcf_error = 0

        for index, stock in enumerate(stocks, start=1):
            self.stdout.write(
                f"\n[{index}/{total_stocks}] Processing {stock.symbol}..."
            )

            # Store previous values for comparison
            prev_eps_value = stock.intrinsic_value
            prev_fcf_value = stock.intrinsic_value_fcf
            prev_calc_date = stock.last_calculation_date

            # Show previous values
            if prev_calc_date:
                self.stdout.write(
                    f"  Previous values (Last calc: {prev_calc_date.strftime('%Y-%m-%d %H:%M:%S')}):"
                )
                if prev_eps_value:
                    self.stdout.write(f"    EPS intrinsic value: ${prev_eps_value}")
                else:
                    self.stdout.write("    EPS intrinsic value: None")

                if prev_fcf_value:
                    self.stdout.write(f"    FCF intrinsic value: ${prev_fcf_value}")
                else:
                    self.stdout.write("    FCF intrinsic value: None")
            else:
                self.stdout.write("  Previous values: Never calculated")

            self.stdout.write("")  # Blank line

            # Process EPS (existing logic with delta calculation)
            try:
                eps_result = self._process_stock(
                    stock, force_refresh=options.get("force_refresh", False)
                )

                if eps_result["status"] == "success":
                    eps_success += 1
                    new_value = eps_result["intrinsic_value"]

                    # Calculate delta
                    if prev_eps_value:
                        delta = new_value - prev_eps_value
                        pct_change = (delta / prev_eps_value) * 100
                        delta_str = (
                            f"(+${delta:.2f}, +{pct_change:.2f}%)"
                            if delta >= 0
                            else f"(${delta:.2f}, {pct_change:.2f}%)"
                        )
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  ✓ EPS intrinsic value: ${new_value} {delta_str}"
                            )
                        )
                    else:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  ✓ EPS intrinsic value: ${new_value} (new)"
                            )
                        )
                elif eps_result["status"] == "skipped":
                    eps_skipped += 1
                    self.stdout.write(
                        self.style.WARNING(f"  ⊘ EPS skipped: {eps_result['reason']}")
                    )
            except Exception as e:
                eps_error += 1
                logger.error(
                    f"EPS processing error for {stock.symbol}: {e}", exc_info=True
                )
                self.stdout.write(self.style.ERROR(f"  ✗ EPS error: {str(e)}"))

            # Process FCF (new logic with delta calculation)
            # Get overview_data for shares outstanding
            try:
                # Fetch overview data (may be cached from EPS processing)
                overview_data = self._fetch_eps_data(
                    stock.symbol,
                    force_refresh=False,  # Use cache if available
                )

                if overview_data and "SharesOutstanding" in overview_data:
                    fcf_result = self._process_stock_fcf(
                        stock,
                        overview_data,
                        force_refresh=options.get("force_refresh", False),
                    )

                    if fcf_result["status"] == "success":
                        fcf_success += 1
                        new_fcf_value = fcf_result["intrinsic_value_fcf"]

                        # Calculate delta
                        if prev_fcf_value:
                            delta = new_fcf_value - prev_fcf_value
                            pct_change = (delta / prev_fcf_value) * 100
                            delta_str = (
                                f"(+${delta:.2f}, +{pct_change:.2f}%)"
                                if delta >= 0
                                else f"(${delta:.2f}, {pct_change:.2f}%)"
                            )
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"  ✓ FCF intrinsic value: ${new_fcf_value} {delta_str}"
                                )
                            )
                        else:
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"  ✓ FCF intrinsic value: ${new_fcf_value} (new)"
                                )
                            )
                    elif fcf_result["status"] == "skipped":
                        fcf_skipped += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f"  ⊘ FCF skipped: {fcf_result['reason']}"
                            )
                        )
                else:
                    fcf_skipped += 1
                    self.stdout.write(
                        self.style.WARNING(
                            "  ⊘ FCF skipped: OVERVIEW data not available"
                        )
                    )
            except Exception as e:
                fcf_error += 1
                logger.error(
                    f"FCF processing error for {stock.symbol}: {e}", exc_info=True
                )
                self.stdout.write(self.style.ERROR(f"  ✗ FCF error: {str(e)}"))

            # Rate limiting: wait between API calls
            if index < total_stocks:
                self._rate_limit_delay()

        # Summary
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()

        # Get remaining work stats
        remaining_stats = self._get_calculation_stats()

        self.stdout.write(self.style.SUCCESS(f"\n{'=' * 65}"))
        self.stdout.write(self.style.SUCCESS("SUMMARY:"))
        self.stdout.write(self.style.SUCCESS(f"  Total processed: {total_stocks}"))
        self.stdout.write(self.style.SUCCESS("\n  EPS Method:"))
        self.stdout.write(self.style.SUCCESS(f"    Successful: {eps_success}"))
        self.stdout.write(self.style.WARNING(f"    Skipped: {eps_skipped}"))
        self.stdout.write(self.style.ERROR(f"    Errors: {eps_error}"))
        self.stdout.write(self.style.SUCCESS("\n  FCF Method:"))
        self.stdout.write(self.style.SUCCESS(f"    Successful: {fcf_success}"))
        self.stdout.write(self.style.WARNING(f"    Skipped: {fcf_skipped}"))
        self.stdout.write(self.style.ERROR(f"    Errors: {fcf_error}"))

        # API usage statistics
        self.stdout.write(self.style.SUCCESS("\n  API USAGE:"))
        self.stdout.write(f"    API calls made: {self.api_calls_made}")
        self.stdout.write(f"    Cache hits: {self.cache_hits}")
        total_requests = self.api_calls_made + self.cache_hits
        if total_requests > 0:
            cache_hit_rate = (self.cache_hits / total_requests) * 100
            self.stdout.write(f"    Cache hit rate: {cache_hit_rate:.2f}%")

        # Remaining work
        self.stdout.write(self.style.SUCCESS("\n  REMAINING WORK:"))
        self.stdout.write(
            f"    Stocks never calculated: {remaining_stats['never_calculated']}"
        )
        self.stdout.write(
            f"    Stocks previously calculated: {remaining_stats['previously_calculated']}"
        )
        self.stdout.write(f"    Total active stocks: {remaining_stats['total']}")

        self.stdout.write(self.style.SUCCESS(f"\n  Duration: {duration:.2f} seconds"))
        self.stdout.write(self.style.SUCCESS(f"{'=' * 65}\n"))

        # Log command completion
        logger.info("=" * 60)
        logger.info(f"Command completed in {duration:.2f} seconds")
        logger.info(
            f"EPS - Success: {eps_success}, Skipped: {eps_skipped}, Errors: {eps_error}"
        )
        logger.info(
            f"FCF - Success: {fcf_success}, Skipped: {fcf_skipped}, Errors: {fcf_error}"
        )
        logger.info(
            f"API - Calls: {self.api_calls_made}, Cache hits: {self.cache_hits}"
        )
        logger.info("=" * 60)

    def _get_stocks_to_process(self, symbols=None, limit=7, force_all=False):
        """
        Get list of CuratedStock objects to process with smart selection.

        Priority:
        1. If --symbols provided: process those specific symbols
        2. If --force-all: process all active stocks
        3. Otherwise: smart select `limit` stocks (default 7)

        Smart selection logic:
        - First priority: stocks with NULL last_calculation_date (never calculated)
        - Second priority: stocks with oldest last_calculation_date
        - Combine both lists and take first `limit` stocks

        Args:
            symbols: Optional list of specific symbols to process
            limit: Number of stocks to process (default: 7)
            force_all: Process all active stocks (default: False)

        Returns:
            List of CuratedStock objects (preserves priority order)
        """
        # Case 1: Specific symbols requested
        if symbols:
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

            return list(stocks.order_by("symbol"))

        # Case 2: Force all active stocks
        if force_all:
            stocks = CuratedStock.objects.filter(active=True).order_by("symbol")

            # Show API limit warning if exceeding 25 calls
            estimated_calls = stocks.count() * 3
            if estimated_calls > 25:
                self.stdout.write(
                    self.style.WARNING(
                        f"\n⚠ WARNING: Processing {stocks.count()} stocks will make "
                        f"~{estimated_calls} API calls."
                    )
                )
                self.stdout.write(
                    self.style.WARNING(
                        "⚠ This exceeds the AlphaVantage free tier limit of 25 calls/day."
                    )
                )
                self.stdout.write(
                    self.style.WARNING("⚠ You may encounter rate limit errors.")
                )
                self.stdout.write("")  # Blank line

            return list(stocks)

        # Case 3: Smart selection with limit
        # Get stocks never calculated (NULL last_calculation_date)
        never_calculated = CuratedStock.objects.filter(
            active=True, last_calculation_date__isnull=True
        ).order_by("symbol")

        # Get stocks previously calculated, ordered by oldest first
        previously_calculated = CuratedStock.objects.filter(
            active=True, last_calculation_date__isnull=False
        ).order_by("last_calculation_date", "symbol")

        # Combine: prioritize never_calculated, then oldest
        never_calc_list = list(never_calculated)
        prev_calc_list = list(previously_calculated)

        # Take up to `limit` stocks total
        combined = never_calc_list + prev_calc_list
        selected = combined[:limit]

        return selected

    def _get_calculation_stats(self):
        """
        Get statistics about calculation status across all active stocks.

        Returns:
            Dictionary with calculation statistics
        """
        total = CuratedStock.objects.filter(active=True).count()
        never_calculated = CuratedStock.objects.filter(
            active=True, last_calculation_date__isnull=True
        ).count()
        previously_calculated = total - never_calculated

        # Get oldest calculation date
        oldest = (
            CuratedStock.objects.filter(
                active=True, last_calculation_date__isnull=False
            )
            .order_by("last_calculation_date")
            .first()
        )

        oldest_date = oldest.last_calculation_date if oldest else None
        oldest_symbol = oldest.symbol if oldest else None

        return {
            "total": total,
            "never_calculated": never_calculated,
            "previously_calculated": previously_calculated,
            "oldest_date": oldest_date,
            "oldest_symbol": oldest_symbol,
        }

    def _print_pre_execution_summary(self, stocks, force_all=False, limit=7):
        """
        Print detailed pre-execution summary.

        Args:
            stocks: List/QuerySet of stocks to process
            force_all: Whether --force-all was used
            limit: The limit value used
        """
        stats = self._get_calculation_stats()
        stocks_to_process = len(stocks)
        estimated_calls = stocks_to_process * 3

        self.stdout.write("=" * 65)
        self.stdout.write(self.style.SUCCESS("CALCULATION STATISTICS:"))
        self.stdout.write(f"  Total active curated stocks: {stats['total']}")
        self.stdout.write(f"  Never calculated: {stats['never_calculated']}")
        self.stdout.write(f"  Previously calculated: {stats['previously_calculated']}")

        if stats["oldest_date"]:
            self.stdout.write(
                f"  Oldest calculation: {stats['oldest_date'].strftime('%Y-%m-%d')} "
                f"({stats['oldest_symbol']})"
            )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("EXECUTION PLAN:"))
        self.stdout.write(f"  Stocks to process this run: {stocks_to_process}")
        self.stdout.write(f"  Estimated API calls: {estimated_calls}", ending="")

        if estimated_calls <= 25:
            self.stdout.write(self.style.SUCCESS(" (under 25/day limit ✓)"))
        else:
            self.stdout.write(self.style.WARNING(" (EXCEEDS 25/day limit ⚠)"))

        # List selected stocks
        if stocks_to_process > 0 and stocks_to_process <= 20:
            self.stdout.write("")
            self.stdout.write("  Selected stocks (in processing order):")
            for i, stock in enumerate(stocks, start=1):
                if stock.last_calculation_date:
                    date_str = stock.last_calculation_date.strftime("%Y-%m-%d")
                    self.stdout.write(
                        f"    {i}. {stock.symbol} (last calculated: {date_str})"
                    )
                else:
                    self.stdout.write(f"    {i}. {stock.symbol} (never calculated)")

        self.stdout.write("=" * 65)
        self.stdout.write("")

    def _process_stock(self, stock, force_refresh=False):
        """
        Process a single stock: fetch EPS TTM, calculate intrinsic value, save.

        Args:
            stock: CuratedStock instance
            force_refresh: Force refresh of cached API data

        Returns:
            Dictionary with status and result details
        """
        # Check if stock has valid DCF assumptions
        if not self._validate_assumptions(stock):
            return {"status": "skipped", "reason": "Missing or invalid DCF assumptions"}

        # Fetch current EPS TTM from Alpha Vantage EARNINGS endpoint (with caching)
        try:
            earnings_data = self._fetch_earnings_data(
                stock.symbol, force_refresh=force_refresh
            )

            if not earnings_data:
                return {
                    "status": "skipped",
                    "reason": "Earnings data not available from API",
                }

            # Check for API error messages
            if "Error Message" in earnings_data:
                return {
                    "status": "skipped",
                    "reason": f"API error: {earnings_data['Error Message']}",
                }

            if "Note" in earnings_data:
                return {
                    "status": "skipped",
                    "reason": f"API rate limit: {earnings_data['Note']}",
                }

            # Try to calculate EPS TTM from quarterly data
            try:
                current_eps = calculate_eps_ttm_from_quarters(earnings_data)
            except ValueError as e:
                # Fallback to OVERVIEW endpoint if insufficient quarterly data
                logger.warning(
                    f"Insufficient quarterly earnings for {stock.symbol}: {e}. "
                    f"Falling back to OVERVIEW endpoint."
                )
                self.stdout.write(
                    self.style.WARNING("  ⚠ Falling back to annual EPS from OVERVIEW")
                )

                overview_data = self._fetch_eps_data(
                    stock.symbol, force_refresh=force_refresh
                )

                if not overview_data or "EPS" not in overview_data:
                    return {
                        "status": "skipped",
                        "reason": "EPS data not available from OVERVIEW fallback",
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
            f"Updated {stock.symbol}: EPS TTM=${current_eps}, "
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
        Fetch EPS data from Alpha Vantage OVERVIEW endpoint.

        DEPRECATED: This method fetches annual EPS from OVERVIEW.
        New implementation uses _fetch_earnings_data() for quarterly EPS TTM.
        Still used to fetch SharesOutstanding for FCF calculations.

        Tracks API calls and cache hits for reporting.

        Cache is now handled by get_market_data() in scanner/alphavantage/util.py
        with standardized cache key format: alphavantage:overview:{symbol}

        Args:
            symbol: Stock ticker symbol
            force_refresh: Bypass cache and fetch fresh data (clears cache first)

        Returns:
            Dictionary with overview data from Alpha Vantage
        """
        # If force refresh, clear the cache first
        if force_refresh:
            cache_key = f"{settings.CACHE_KEY_PREFIX_ALPHAVANTAGE}:overview:{symbol}"
            cache.delete(cache_key)
            self.stdout.write("  Clearing cache and fetching fresh data...")

        # Track whether we're using cache (check before API call)
        cache_key = f"{settings.CACHE_KEY_PREFIX_ALPHAVANTAGE}:overview:{symbol}"
        cached_before = cache.get(cache_key) is not None

        # Fetch from API (cache is handled internally by get_market_data)
        url = f"function=OVERVIEW&symbol={symbol}"
        overview_data = get_market_data(url)

        # Track API call vs cache hit for reporting
        if cached_before and not force_refresh:
            self.cache_hits += 1
            self.stdout.write(self.style.SUCCESS("  Using cached overview data"))
        else:
            self.api_calls_made += 1
            self.stdout.write("  Fetching overview from Alpha Vantage API...")

        return overview_data

    def _fetch_earnings_data(self, symbol, force_refresh=False):
        """
        Fetch quarterly earnings data from Alpha Vantage EARNINGS endpoint.

        This is used to calculate EPS TTM (sum of 4 most recent quarterly reportedEPS).

        Tracks API calls and cache hits for reporting.

        Cache is now handled by get_market_data() in scanner/alphavantage/util.py
        with standardized cache key format: alphavantage:earnings:{symbol}

        Args:
            symbol: Stock ticker symbol
            force_refresh: Bypass cache and fetch fresh data (clears cache first)

        Returns:
            Dictionary with earnings data from Alpha Vantage
        """
        # If force refresh, clear the cache first
        if force_refresh:
            cache_key = f"{settings.CACHE_KEY_PREFIX_ALPHAVANTAGE}:earnings:{symbol}"
            cache.delete(cache_key)
            self.stdout.write("  Clearing cache and fetching fresh data...")

        # Track whether we're using cache (check before API call)
        cache_key = f"{settings.CACHE_KEY_PREFIX_ALPHAVANTAGE}:earnings:{symbol}"
        cached_before = cache.get(cache_key) is not None

        # Fetch from API (cache is handled internally by get_market_data)
        url = f"function=EARNINGS&symbol={symbol}"
        earnings_data = get_market_data(url)

        # Track API call vs cache hit for reporting
        if cached_before and not force_refresh:
            self.cache_hits += 1
            self.stdout.write(self.style.SUCCESS("  Using cached earnings data"))
        else:
            self.api_calls_made += 1
            self.stdout.write("  Fetching earnings from Alpha Vantage API...")

        return earnings_data

    def _fetch_cash_flow_data(self, symbol, force_refresh=False):
        """
        Fetch cash flow data from Alpha Vantage.

        Tracks API calls and cache hits for reporting.

        Cache is now handled by get_market_data() in scanner/alphavantage/util.py
        with standardized cache key format: alphavantage:cash_flow:{symbol}

        Args:
            symbol: Stock ticker symbol
            force_refresh: Bypass cache and fetch fresh data (clears cache first)

        Returns:
            Dictionary with cash flow data from Alpha Vantage
        """
        # If force refresh, clear the cache first
        if force_refresh:
            cache_key = f"{settings.CACHE_KEY_PREFIX_ALPHAVANTAGE}:cash_flow:{symbol}"
            cache.delete(cache_key)
            self.stdout.write("  Clearing cache and fetching fresh data...")

        # Track whether we're using cache (check before API call)
        cache_key = f"{settings.CACHE_KEY_PREFIX_ALPHAVANTAGE}:cash_flow:{symbol}"
        cached_before = cache.get(cache_key) is not None

        # Fetch from API (cache is handled internally by get_market_data)
        url = f"function=CASH_FLOW&symbol={symbol}"
        cash_flow_data = get_market_data(url)

        # Track API call vs cache hit for reporting
        if cached_before and not force_refresh:
            self.cache_hits += 1
            self.stdout.write(self.style.SUCCESS("  Using cached cash flow data"))
        else:
            self.api_calls_made += 1
            self.stdout.write("  Fetching cash flow from Alpha Vantage API...")

        return cash_flow_data

    def _process_stock_fcf(self, stock, overview_data, force_refresh=False):
        """
        Process FCF-based intrinsic value calculation for a single stock.

        Args:
            stock: CuratedStock instance
            overview_data: Already fetched OVERVIEW data (contains shares outstanding)
            force_refresh: Force refresh of cached API data

        Returns:
            Dictionary with status and result details
        """
        # Validate FCF assumptions
        if stock.fcf_growth_rate is None or stock.fcf_growth_rate <= 0:
            return {"status": "skipped", "reason": "Invalid FCF growth rate"}

        if stock.fcf_multiple is None or stock.fcf_multiple <= 0:
            return {"status": "skipped", "reason": "Invalid FCF multiple"}

        # Fetch cash flow data
        try:
            cash_flow_data = self._fetch_cash_flow_data(
                stock.symbol, force_refresh=force_refresh
            )

            if not cash_flow_data:
                return {
                    "status": "skipped",
                    "reason": "Cash flow data not available from API",
                }

            # Check for API error messages
            if "Error Message" in cash_flow_data:
                return {
                    "status": "skipped",
                    "reason": f"API error: {cash_flow_data['Error Message']}",
                }

            if "Note" in cash_flow_data:
                return {
                    "status": "skipped",
                    "reason": f"API rate limit: {cash_flow_data['Note']}",
                }

            # Calculate TTM FCF
            ttm_fcf = calculate_fcf_from_quarters(cash_flow_data)

            # Get shares outstanding from overview data
            if "SharesOutstanding" not in overview_data:
                return {
                    "status": "skipped",
                    "reason": "Shares outstanding not available",
                }

            shares_outstanding = Decimal(overview_data["SharesOutstanding"])

            # Calculate FCF per share
            fcf_per_share = calculate_fcf_per_share(ttm_fcf, shares_outstanding)

            # Warn if FCF is negative but continue calculation
            if fcf_per_share < 0:
                logger.warning(
                    f"{stock.symbol} has negative FCF/share: {fcf_per_share}"
                )
                self.stdout.write(
                    self.style.WARNING(f"  ⚠ Negative FCF/share: ${fcf_per_share}")
                )

            # Update current FCF in database
            stock.current_fcf_per_share = fcf_per_share

        except ValueError as e:
            logger.warning(f"Invalid FCF data for {stock.symbol}: {e}")
            return {"status": "skipped", "reason": f"Invalid data: {str(e)}"}
        except Exception as e:
            logger.error(f"Error fetching FCF data for {stock.symbol}: {e}")
            return {"status": "error", "reason": f"API error: {str(e)}"}

        # Calculate intrinsic value using FCF DCF model
        # Skip if FCF per share is negative or zero (but save fcf_per_share for reference)
        if fcf_per_share <= 0:
            stock.save()  # Save the negative FCF per share
            return {
                "status": "skipped",
                "reason": f"Non-positive FCF/share: {fcf_per_share}",
            }

        try:
            fcf_result = calculate_intrinsic_value_fcf(
                current_fcf_per_share=fcf_per_share,
                fcf_growth_rate=stock.fcf_growth_rate,
                fcf_multiple=stock.fcf_multiple,
                desired_return=stock.desired_return,
                projection_years=stock.projection_years,
            )

            intrinsic_value_fcf = fcf_result["intrinsic_value"]

        except Exception as e:
            logger.error(
                f"Error calculating FCF intrinsic value for {stock.symbol}: {e}"
            )
            return {"status": "error", "reason": f"Calculation error: {str(e)}"}

        # Save results to database
        stock.intrinsic_value_fcf = intrinsic_value_fcf
        stock.save()

        logger.info(
            f"Updated {stock.symbol} FCF: FCF/share=${fcf_per_share}, "
            f"Intrinsic Value=${intrinsic_value_fcf}"
        )

        return {
            "status": "success",
            "intrinsic_value_fcf": intrinsic_value_fcf,
            "fcf_per_share": fcf_per_share,
            "fcf_details": fcf_result,
        }

    def _rate_limit_delay(self):
        """
        Implement rate limiting: 3 calls per minute = 20 seconds between stocks.
        """
        self.stdout.write(
            self.style.WARNING(
                f"  Rate limiting: waiting {RATE_LIMIT_DELAY:.0f} seconds..."
            )
        )

        time.sleep(RATE_LIMIT_DELAY)

    def _clear_alpha_vantage_cache(self):
        """
        Clear all cached Alpha Vantage data (EARNINGS, OVERVIEW, and CASH_FLOW).

        Uses new standardized cache key format: alphavantage:{function}:{symbol}
        """
        # Get all curated stocks to clear their cache
        symbols = CuratedStock.objects.values_list("symbol", flat=True)

        cleared = 0
        for symbol in symbols:
            # Clear EARNINGS cache (new format)
            if cache.delete(
                f"{settings.CACHE_KEY_PREFIX_ALPHAVANTAGE}:earnings:{symbol}"
            ):
                cleared += 1
            # Clear OVERVIEW cache (new format)
            if cache.delete(
                f"{settings.CACHE_KEY_PREFIX_ALPHAVANTAGE}:overview:{symbol}"
            ):
                cleared += 1
            # Clear CASH_FLOW cache (new format)
            if cache.delete(
                f"{settings.CACHE_KEY_PREFIX_ALPHAVANTAGE}:cash_flow:{symbol}"
            ):
                cleared += 1

            # Also clear old format keys for backward compatibility (can be removed later)
            cache.delete(f"av_earnings_{symbol}")
            cache.delete(f"av_overview_{symbol}")
            cache.delete(f"av_cashflow_{symbol}")

        self.stdout.write(self.style.SUCCESS(f"Cleared {cleared} cached entries"))
        logger.info(f"Cleared {cleared} Alpha Vantage cache entries")
