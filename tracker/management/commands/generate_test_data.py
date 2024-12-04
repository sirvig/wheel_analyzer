import random
from faker import Faker
from django.core.management.base import BaseCommand
from tracker.models import User, Account, Campaign, Transaction


class Command(BaseCommand):
    help = "Generates data for testing"

    def handle(self, *args, **options):
        fake = Faker()

        # get the user
        user = User.objects.filter(username="webvig").first()
        if not user:
            user = User.objects.create_superuser(username="webvig", password="test")

        # Create stocks
        stocks = ["AAP", "AAPL", "AMZN", "CRM", "CSIQ", "NVDA", "UPS"]

        # Create Accounts
        accounts = [
            "Fidelity",
            "IRA",
            "Roth",
        ]

        for account in accounts:
            Account.objects.get_or_create(user=user, name=account, taxable=True)

        # Create 5 campaigns
        accounts = Account.objects.all()
        for i in range(5):
            Campaign.objects.create(
                user=user,
                stock=random.choice(stocks),
                account=random.choice(accounts),
                start_date=fake.date_between(start_date="-1y", end_date="today"),
                active=True,
            )

        # Create 25 transactions
        campaigns = Campaign.objects.all()
        types = [x[0] for x in Transaction.TRANSACTION_TYPE_CHOICES]
        for i in range(25):
            transaction_date = fake.date_between(start_date="-1y", end_date="today")
            Transaction.objects.create(
                campaign=random.choice(campaigns),
                type=random.choice(types),
                premium=random.uniform(1, 2500),
                strike_price=random.uniform(1, 2500),
                contracts=int(random.uniform(1, 20)),
                transaction_date=transaction_date,
                expiration_date=fake.date_between(
                    start_date=transaction_date, end_date="today"
                ),
            )
