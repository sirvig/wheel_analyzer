import factory

from tracker.factories import UserFactory

from .models import OptionsWatch


class OptionsWatchFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OptionsWatch

    user = factory.SubFactory(UserFactory)
    stock = factory.Iterator(["AAPL", "AAP", "CRM", "CSIQ", "NVDA", "UPS"])
    active = factory.Iterator([True, False])
    type = factory.Iterator([x[0] for x in OptionsWatch.TYPE_CHOICES])
    strike_price = factory.Faker("pyfloat", left_digits=3, right_digits=2)
