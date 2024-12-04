import logging
from django.core.management.base import BaseCommand
from scanner.marketdata.options import find_options

logger = logging.getLogger(__name__)
DEBUG = False

class Command(BaseCommand):
    help = "Find options"
    
    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument("ticker", type=str)
        parser.add_argument("type", type=str)
        parser.add_argument("--weeks", type=int, required=False, default=5)
        parser.add_argument("--debug", type=bool, required=False, default=False)

    def handle(self, *args, **options):
        ticker = options["ticker"].upper()
        contract_type = options["type"].lower()
        
        print(f"Checking {contract_type}s for {ticker}...")
        options = find_options(ticker, contract_type, options["weeks"], options["debug"])
        
        last_date = None 
        for option in options:
            if last_date and last_date != option['date']:
                print("\n")
            message = (
                f"Date: {option['date']} Strike: {option['strike']} "
                f"Change: {option['change']:.2f}% Price: {option['price']} "
                f"Delta: {option['delta']:.2f} Annualized: {option['annualized']:.2f} "
                f"IV: {option['iv']:.2f}"
            ) 
            last_date = option['date']
            print(message)
