from datetime import datetime
import factory
from .models import User, Account, Campaign, Stock, Transaction


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ("username",)

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    username = factory.Sequence(lambda n: "user%d" % n)


class StockFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Stock
        django_get_or_create = ("symbol",)

    symbol = factory.Iterator(["AAPL", "AAP", "CRM", "CSIQ", "NVDA", "UPS"])


class AccountFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Account

    user = factory.SubFactory(UserFactory)
    name = factory.Faker("word")
    taxable = factory.Iterator([True, False])


class CampaignFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Campaign

    user = factory.SubFactory(UserFactory)
    stock = factory.SubFactory(StockFactory)
    account = factory.SubFactory(AccountFactory)
    active = factory.Iterator([True, False])
    start_date = factory.Faker(
        "date_between",
        start_date=datetime(year=2023, month=1, day=1).date(),
        end_date=datetime.now().date(),
    )


class TransactionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Transaction

    campaign = factory.SubFactory(CampaignFactory)
    type = factory.Iterator([x[0] for x in Transaction.TRANSACTION_TYPE_CHOICES])
    premium = factory.Faker("pyfloat", left_digits=3, right_digits=2)
    transaction_date = factory.Faker(
        "date_between",
        start_date=datetime(year=2023, month=1, day=1).date(),
        end_date=datetime.now().date(),
    )
