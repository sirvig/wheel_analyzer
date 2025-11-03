"""
Verification command to check that CuratedStock model is working correctly
and that the scanner commands can access the stock data.
"""

from django.core.management.base import BaseCommand
from django.db import connection

from scanner.models import CuratedStock


class Command(BaseCommand):
    help = "Verify CuratedStock model and data migration"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("CuratedStock Verification"))
        self.stdout.write(self.style.SUCCESS("=" * 60))

        # Check database table exists
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'scanner_curatedstock'
                );
            """
            )
            table_exists = cursor.fetchone()[0]

        if table_exists:
            self.stdout.write(
                self.style.SUCCESS("✓ Database table 'scanner_curatedstock' exists")
            )
        else:
            self.stdout.write(
                self.style.ERROR("✗ Database table 'scanner_curatedstock' not found!")
            )
            return

        # Check total count
        total_count = CuratedStock.objects.count()
        self.stdout.write(
            self.style.SUCCESS(f"✓ Total CuratedStock records: {total_count}")
        )

        if total_count == 0:
            self.stdout.write(
                self.style.WARNING(
                    "⚠ No stocks found! Data migration may not have run."
                )
            )
            return

        # Check active vs inactive
        active_count = CuratedStock.objects.filter(active=True).count()
        inactive_count = CuratedStock.objects.filter(active=False).count()

        self.stdout.write(self.style.SUCCESS(f"✓ Active stocks: {active_count}"))
        self.stdout.write(self.style.SUCCESS(f"✓ Inactive stocks: {inactive_count}"))

        # List all stocks
        self.stdout.write(self.style.SUCCESS("\nStock Symbols:"))
        stocks = CuratedStock.objects.all().order_by("symbol")
        for i, stock in enumerate(stocks, 1):
            status = "✓" if stock.active else "✗"
            self.stdout.write(f"  {i:2d}. {status} {stock.symbol}")

        # Expected symbols from original options.json
        expected_symbols = [
            "AAPL",
            "ADBE",
            "AMZN",
            "ANET",
            "ASML",
            "AVGO",
            "CRM",
            "CRWD",
            "DDOG",
            "DUOL",
            "GOOGL",
            "JPM",
            "MA",
            "META",
            "MSFT",
            "NFLX",
            "NOW",
            "NVDA",
            "PANW",
            "PLTR",
            "PYPL",
            "SHOP",
            "SPGI",
            "SPOT",
            "UBER",
            "V",
        ]

        # Check if all expected symbols are present
        actual_symbols = set(CuratedStock.objects.values_list("symbol", flat=True))
        expected_set = set(expected_symbols)
        missing_symbols = expected_set - actual_symbols
        extra_symbols = actual_symbols - expected_set

        if missing_symbols:
            self.stdout.write(
                self.style.WARNING(
                    f"\n⚠ Missing expected symbols: {', '.join(sorted(missing_symbols))}"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("\n✓ All expected symbols are present")
            )

        if extra_symbols:
            self.stdout.write(
                self.style.WARNING(
                    f"⚠ Extra symbols found: {', '.join(sorted(extra_symbols))}"
                )
            )

        # Test querying active stocks (what the scanner commands will do)
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
        self.stdout.write(self.style.SUCCESS("Scanner Command Compatibility Check"))
        self.stdout.write(self.style.SUCCESS("=" * 60))

        active_tickers = list(
            CuratedStock.objects.filter(active=True).values_list("symbol", flat=True)
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"✓ Active tickers available for scanning: {len(active_tickers)}"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(f"  Symbols: {', '.join(sorted(active_tickers))}")
        )

        # Final summary
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
        self.stdout.write(self.style.SUCCESS("Verification Summary"))
        self.stdout.write(self.style.SUCCESS("=" * 60))

        if (
            total_count == 26
            and active_count == 26
            and not missing_symbols
            and not extra_symbols
        ):
            self.stdout.write(
                self.style.SUCCESS(
                    "✓ ALL CHECKS PASSED! CuratedStock model is working correctly."
                )
            )
            self.stdout.write(
                self.style.SUCCESS(
                    "✓ Scanner commands should work with the new database model."
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "⚠ Some checks did not pass. Review the output above."
                )
            )
