"""
Management command to fetch current stock prices from marketdata.app.
Usage:
    python manage.py fetch_stock_prices
    python manage.py fetch_stock_prices --symbols AAPL MSFT
    python manage.py fetch_stock_prices --force --dry-run
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from scanner.models import CuratedStock
from scanner.marketdata.quotes import get_stock_quote
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Fetch current stock prices for curated stocks from marketdata.app'

    def add_arguments(self, parser):
        parser.add_argument(
            '--symbols',
            nargs='+',
            help='Specific stock symbols to fetch (e.g., AAPL MSFT)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force fetching outside normal hours (testing)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Log actions without saving to database'
        )

    def handle(self, *args, **options):
        # Market hours check (unless --force)
        if not options['force']:
            current_hour = timezone.localtime().hour
            if not (17 <= current_hour <= 20):  # 5 PM - 8 PM ET
                self.stdout.write(
                    self.style.WARNING(
                        'Outside normal update window (5-8 PM ET). Use --force to override.'
                    )
                )
                return

        # Get stocks to update
        if options['symbols']:
            stocks = CuratedStock.objects.filter(
                symbol__in=[s.upper() for s in options['symbols']]
            )
        else:
            stocks = CuratedStock.objects.filter(active=True)

        total = stocks.count()
        updated = 0
        failed = []

        self.stdout.write(f"Fetching prices for {total} stocks...")

        for stock in stocks:
            quote_data = get_stock_quote(stock.symbol)

            if quote_data:
                if options['dry_run']:
                    self.stdout.write(
                        f"[DRY RUN] Would update {stock.symbol}: ${quote_data['price']}"
                    )
                else:
                    stock.current_price = quote_data['price']
                    stock.price_updated_at = timezone.now()
                    stock.save(update_fields=['current_price', 'price_updated_at'])

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✓ {stock.symbol}: ${quote_data['price']}"
                        )
                    )
                updated += 1
            else:
                failed.append(stock.symbol)
                self.stdout.write(
                    self.style.ERROR(f"✗ {stock.symbol}: Failed to fetch")
                )

        # Summary
        self.stdout.write("\n" + "="*50)
        self.stdout.write(f"Updated: {updated}/{total} stocks")
        if failed:
            self.stdout.write(
                self.style.WARNING(f"Failed: {', '.join(failed)}")
            )

        if options['dry_run']:
            self.stdout.write(self.style.WARNING("\n[DRY RUN MODE - No changes saved]"))
