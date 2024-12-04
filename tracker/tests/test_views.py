import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_total_values_appear_on_transaction_list_page(user_transactions, client):
    user = user_transactions[0].campaign.user
    campaign_id = user_transactions[0].campaign.id
    client.force_login(user)

    total_income = sum(t.premium for t in user_transactions)

    response = client.get(
        reverse("transactions-list", kwargs={"campaign_id": campaign_id})
    )
    assert float(round(response.context["total_premium"], 2)) == round(total_income, 2)


@pytest.mark.django_db
def test_campaign_status_filter(user_transactions, client):
    user = user_transactions[0].campaign.user
    client.force_login(user)

    # In-progress check
    GET_params = {"campaign_status": True}
    response = client.get(reverse("campaigns-list"), GET_params)

    qs = response.context["filter"].qs

    for campaign in qs:
        assert campaign.active

    # Completed check
    GET_params = {"campaign_status": False}
    response = client.get(reverse("campaigns-list"), GET_params)

    qs = response.context["filter"].qs

    for campaign in qs:
        assert not campaign.active
