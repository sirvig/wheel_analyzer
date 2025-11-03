import logging

from django.core.management.base import BaseCommand

from scanner.scanner import perform_scan

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Scan options"

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument("--debug", type=bool, required=False, default=False)

    def handle(self, *args, **options):
        debug = options["debug"]

        result = perform_scan(debug=debug)

        if result["success"]:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Scan completed: {result['scanned_count']} tickers at {result['timestamp']}"
                )
            )
        else:
            self.stdout.write(self.style.WARNING(f"Scan failed: {result['message']}"))
            if not result.get("scanned_count", 0):
                exit(0)  # Exit cleanly if market is closed
