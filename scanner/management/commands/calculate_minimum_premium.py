import logging

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)
DEBUG = False


class Command(BaseCommand):
    help = "Calculate minimum premium for a given strike price"

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument("strike", type=str)
        parser.add_argument("dte", type=str)
        parser.add_argument("--annualized", type=float, required=False, default=0.30)
        parser.add_argument("--debug", type=bool, required=False, default=False)

    def handle(self, *args, **options):
        strike = float(options["strike"].upper())
        dte = int(options["dte"].lower())
        annualized_return = float(options["annualized"])

        minimum_premium = (strike * annualized_return * dte) / 365
        print(
            f"Minimum premium for {strike} strike and {dte} DTE: {minimum_premium:.2f}"
        )
