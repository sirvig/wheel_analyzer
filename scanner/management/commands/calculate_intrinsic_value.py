"""
Django management command to calculate intrinsic value for curated stocks.

This command fetches EPS TTM and FCF data from Alpha Vantage and calculates
the intrinsic value (fair value) for all active stocks in the curated list
using both EPS-based and FCF-based DCF models.

EPS is calculated as Trailing Twelve Months (TTM) by summing the 4 most recent
quarterly reportedEPS values from the EARNINGS endpoint.

The command makes 3 API calls per stock:
- EARNINGS: to calculate EPS TTM from quarterly data
- OVERVIEW: to fetch SharesOutstanding (needed for FCF calculation)
- CASH_FLOW: to calculate FCF TTM from quarterly data

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

            # Process EPS (existing logic)
            try:
                eps_result = self._process_stock(
                    stock, force_refresh=options.get("force_refresh", False)
                )

                if eps_result["status"] == "success":
                    eps_success += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  ✓ EPS intrinsic value: ${eps_result['intrinsic_value']}"
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

            # Process FCF (new logic)
            # Get overview_data for shares outstanding
            try:
                # Fetch overview data (may be cached from EPS processing)
                overview_data = self._fetch_eps_data(
                    stock.symbol, force_refresh=False  # Use cache if available
                )

                if overview_data and "SharesOutstanding" in overview_data:
                    fcf_result = self._process_stock_fcf(
                        stock,
                        overview_data,
                        force_refresh=options.get("force_refresh", False),
                    )

                    if fcf_result["status"] == "success":
                        fcf_success += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  ✓ FCF intrinsic value: ${fcf_result['intrinsic_value_fcf']}"
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

        self.stdout.write(self.style.SUCCESS(f"\n{'=' * 60}"))
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
        self.stdout.write(self.style.SUCCESS(f"\n  Duration: {duration:.2f} seconds"))
        self.stdout.write(self.style.SUCCESS(f"{'=' * 60}\n"))

        # Log command completion
        logger.info("=" * 60)
        logger.info(f"Command completed in {duration:.2f} seconds")
        logger.info(
            f"EPS - Success: {eps_success}, Skipped: {eps_skipped}, Errors: {eps_error}"
        )
        logger.info(
            f"FCF - Success: {fcf_success}, Skipped: {fcf_skipped}, Errors: {fcf_error}"
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
                    self.style.WARNING(
                        f"  ⚠ Falling back to annual EPS from OVERVIEW"
                    )
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
        Fetch EPS data from Alpha Vantage OVERVIEW endpoint with Redis caching.

        DEPRECATED: This method fetches annual EPS from OVERVIEW.
        New implementation uses _fetch_earnings_data() for quarterly EPS TTM.
        Still used to fetch SharesOutstanding for FCF calculations.

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
                self.stdout.write(self.style.SUCCESS("  Using cached overview data"))
                logger.debug(f"Overview cache hit for {symbol}")
                return cached_data

        # Fetch from API
        self.stdout.write("  Fetching overview from Alpha Vantage API...")
        logger.debug(f"Overview cache miss for {symbol}, fetching from API")

        url = f"function=OVERVIEW&symbol={symbol}"
        overview_data = get_market_data(url)

        # Cache the response
        if overview_data:
            cache.set(cache_key, overview_data, CACHE_TTL)
            logger.debug(f"Cached overview data for {symbol} (TTL: {CACHE_TTL}s)")

        return overview_data

    def _fetch_earnings_data(self, symbol, force_refresh=False):
        """
        Fetch quarterly earnings data from Alpha Vantage EARNINGS endpoint with Redis caching.

        This is used to calculate EPS TTM (sum of 4 most recent quarterly reportedEPS).

        Cache TTL: 7 days (604800 seconds)
        Cache key format: av_earnings_{symbol}

        Args:
            symbol: Stock ticker symbol
            force_refresh: Bypass cache and fetch fresh data

        Returns:
            Dictionary with earnings data from Alpha Vantage
        """
        cache_key = f"av_earnings_{symbol}"

        # Try to get from cache (unless force refresh)
        if not force_refresh:
            cached_data = cache.get(cache_key)
            if cached_data:
                self.stdout.write(self.style.SUCCESS("  Using cached earnings data"))
                logger.debug(f"Earnings cache hit for {symbol}")
                return cached_data

        # Fetch from API
        self.stdout.write("  Fetching earnings from Alpha Vantage API...")
        logger.debug(f"Earnings cache miss for {symbol}, fetching from API")

        url = f"function=EARNINGS&symbol={symbol}"
        earnings_data = get_market_data(url)

        # Cache the response
        if earnings_data:
            cache.set(cache_key, earnings_data, CACHE_TTL)
            logger.debug(f"Cached earnings data for {symbol} (TTL: {CACHE_TTL}s)")

        return earnings_data

    def _fetch_cash_flow_data(self, symbol, force_refresh=False):
        """
        Fetch cash flow data from Alpha Vantage with Redis caching.

        Cache TTL: 7 days (same as OVERVIEW)
        Cache key format: av_cashflow_{symbol}

        Args:
            symbol: Stock ticker symbol
            force_refresh: Bypass cache and fetch fresh data

        Returns:
            Dictionary with cash flow data from Alpha Vantage
        """
        cache_key = f"av_cashflow_{symbol}"

        # Try to get from cache (unless force refresh)
        if not force_refresh:
            cached_data = cache.get(cache_key)
            if cached_data:
                self.stdout.write(self.style.SUCCESS("  Using cached cash flow data"))
                logger.debug(f"Cash flow cache hit for {symbol}")
                return cached_data

        # Fetch from API
        self.stdout.write("  Fetching cash flow from Alpha Vantage API...")
        logger.debug(f"Cash flow cache miss for {symbol}, fetching from API")

        url = f"function=CASH_FLOW&symbol={symbol}"
        cash_flow_data = get_market_data(url)

        # Cache the response
        if cash_flow_data:
            cache.set(cache_key, cash_flow_data, CACHE_TTL)
            logger.debug(f"Cached cash flow data for {symbol} (TTL: {CACHE_TTL}s)")

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
        """Clear all cached Alpha Vantage data (EARNINGS, OVERVIEW, and CASH_FLOW)."""
        # Get all curated stocks to clear their cache
        symbols = CuratedStock.objects.values_list("symbol", flat=True)

        cleared = 0
        for symbol in symbols:
            # Clear EARNINGS cache
            if cache.delete(f"av_earnings_{symbol}"):
                cleared += 1
            # Clear OVERVIEW cache
            if cache.delete(f"av_overview_{symbol}"):
                cleared += 1
            # Clear CASH_FLOW cache
            if cache.delete(f"av_cashflow_{symbol}"):
                cleared += 1

        self.stdout.write(self.style.SUCCESS(f"Cleared {cleared} cached entries"))
        logger.info(f"Cleared {cleared} Alpha Vantage cache entries")
