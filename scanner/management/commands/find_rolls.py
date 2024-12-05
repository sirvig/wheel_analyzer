import logging

from django.core.management.base import BaseCommand

from scanner.marketdata.options import find_rolls

logger = logging.getLogger(__name__)
DEBUG = False


class Command(BaseCommand):
    help = "Find options"

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument("ticker", type=str)
        parser.add_argument("type", type=str)
        parser.add_argument("current_strike", type=str)
        parser.add_argument("current_expiration", type=str)
        parser.add_argument("--percent", type=float, required=False, default=20)
        parser.add_argument("--weeks", type=int, required=False, default=2)
        parser.add_argument("--debug", type=bool, required=False, default=False)

    def handle(self, *args, **options):
        ticker = options["ticker"].upper()
        contract_type = options["type"].lower()
        current_strike = float(options["current_strike"])
        current_expiration = options["current_expiration"]

        print(f"Checking {contract_type} rolls for {ticker}...")
        options = find_rolls(
            ticker,
            contract_type,
            current_strike,
            current_expiration,
            options["percent"],
            options["weeks"],
            options["debug"],
        )

        last_date = None
        for option in options:
            if last_date and last_date != option["date"]:
                print("\n")
            message = (
                f"Date: {option['date']} Strike: {option['strike']} "
                f"Change: {option['change']:.2f}% Price: {option['price']} Role Diff: {option['diff']:.2f} "
                f"Delta: {option['delta']:.2f} Annualized: {option['annualized']:.2f} "
                f"IV: {option['iv']:.2f}"
            )
            last_date = option["date"]
            print(message)
