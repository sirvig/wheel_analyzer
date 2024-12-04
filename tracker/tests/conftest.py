import pytest
from tracker.factories import CampaignFactory, TransactionFactory, UserFactory


@pytest.fixture
def transactions():
    return TransactionFactory.create_batch(20)


@pytest.fixture
def user_transactions():
    user = UserFactory()
    campaign = CampaignFactory(user=user)
    return TransactionFactory.create_batch(20, campaign=campaign)
