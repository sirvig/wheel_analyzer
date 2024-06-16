import pytest
from tracker.models import Campaign, Transaction


@pytest.mark.django_db
def test_queryset_get_active_method(transactions):
    qs = Campaign.objects.get_active()
    assert qs.count() > 0
    assert all([campaign.active for campaign in qs])


@pytest.mark.django_db
def test_queryset_get_inactive_method(transactions):
    qs = Campaign.objects.get_inactive()
    assert qs.count() > 0
    assert all([not campaign.active for campaign in qs])


@pytest.mark.django_db
def test_queryset_get_total_method(transactions):
    qs = Transaction.objects.filter(campaign=1)
    total_premium = qs.get_total()
    assert total_premium == sum(t.premium for t in qs)
