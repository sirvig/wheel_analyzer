import csv
from datetime import datetime
import logging
from django.core.management.base import BaseCommand
from tracker.models import User, Account, Campaign, Transaction

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Import csv data"
    
    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument("csv-file", type=str)


    def handle(self, *args, **options):
        filename = options["csv-file"]
        logging.info(f"CSV file: {filename}")
        
        with open(filename, mode='r') as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=",")
            transaction_date = None
            for row in csv_reader:
                date = row[0]
                stock = row[1]
                action = row[2]
                strike = row[3].strip('"').replace('$','').replace(',','')
                contracts = row[4]
                exp_date = row[5]
                premium = row[6].strip('"').replace('$','').replace(',','')
                account_name = row[7]
                
                if date:
                    transaction_date = date
                
                print(f"Date: {transaction_date}, Stock: {stock}, Action: {action}, Strike: {strike}, Contracts: {contracts}, Expiration: {exp_date}, Premium: {premium}, Account: {account_name}")
                
                account_translator = {
                    "FID": "Fidelity",
                    "IRA": "IRA",
                    "ROTH": "ROTH",
                    "RH": "Robinhood"
                }
                
                # Convert dates for models
                date_transaction_date = datetime.strptime(transaction_date, "%m/%d/%Y").date()
                
                if exp_date:
                    date_exp_date = datetime.strptime(exp_date, "%m/%d/%Y").date()
                
                user = User.objects.get(username="sirvig")
                account = Account.objects.get(user=user, name=account_translator[account_name])
                campaign_list = Campaign.objects.filter(
                    user = user,
                    account = account,
                    stock = stock,
                    active = True
                )
                
                if not campaign_list:
                    campaign = Campaign.objects.get_or_create(
                            user = user,
                            account = account,
                            stock = stock,
                            active = True,
                            start_date = date_transaction_date
                        )[0]
                else:
                    campaign = campaign_list[0]
                
                if not stock:
                    # This is likely an INT action - we can deal with that later
                    next
                
                # Record the transaction
                print(premium)
                transaction = Transaction.objects.get_or_create(
                    campaign = campaign,
                    type = action.lower(),
                    transaction_date = date_transaction_date,
                )
                
                if exp_date:
                    transaction[0].expiration_date = date_exp_date
                    transaction[0].save()
                
                if contracts:
                    transaction[0].contracts = contracts
                    transaction[0].save()
                    
                if strike:
                    transaction[0].strike_price = strike
                    transaction[0].save()
                
                if premium:
                    transaction[0].premium = premium
                    transaction[0].save()
                
                
                if action.lower() == "sell":
                    # We need to end the campaign
                    campaign.active = False
                    campaign.end_date = date_transaction_date
                    campaign.save()
                    
        