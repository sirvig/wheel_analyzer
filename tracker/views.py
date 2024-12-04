from datetime import datetime
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
import json
import logging
from tracker.filters import CampaignFilter
from tracker.models import Campaign, Transaction
from tracker.forms import CampaignForm, TransactionForm

logger = logging.getLogger(__name__)


# Create your views here.
def index(request):
    return render(request, "tracker/index.html")


def healthcheck(request):
    return HttpResponse(
        json.dumps({"status": "OK"}), headers={"content-type": "application/json"}
    )


@login_required
def campaigns_list(request):
    campaign_filter = CampaignFilter(
        request.GET,
        queryset=Campaign.objects.filter(user=request.user).select_related(
            "account"
        ),
    )
    context = {"filter": campaign_filter}

    if request.htmx:
        return render(request, "tracker/partials/campaigns-container.html", context)

    return render(request, "tracker/campaigns-list.html", context)


@login_required
def create_campaign(request):
    if request.method == "POST":
        post_data = request.POST.copy()
        post_data["user"] = request.user
        form = CampaignForm(post_data, user=request.user)
        if form.is_valid():
            campaign = form.save(commit=False)
            campaign.start_date = datetime.now().date()
            campaign.active = True
            campaign.save()

            context = {
                "message": "Campaign was added successfully!",
            }
            return render(request, "tracker/partials/campaign-success.html", context)

    context = {"form": CampaignForm(user=request.user)}
    return render(request, "tracker/partials/create-campaign.html", context)


@login_required
def transactions_list(request, campaign_id):
    # TODO: add error checking here
    campaign = Campaign.objects.get(id=campaign_id)
    context = {"campaign": campaign}

    transactions = Transaction.objects.filter(campaign=campaign)
    if transactions:
        context["transactions"] = transactions

        total_premium = transactions.get_total()
        context["total_premium"] = total_premium
        
        days_in_trade = transactions.get_days_in_trade()
        context["days_in_trade"] = days_in_trade
        
        annualized_return = transactions.get_annualized_return()
        context["annualized_return"] = annualized_return

    if request.htmx:
        return render(request, "tracker/partials/transactions-container.html", context)

    return render(request, "tracker/transactions-list.html", context)


@login_required
def create_transaction(request, campaign_id):
    if request.method == "POST":
        post_data = request.POST.copy()
        post_data["campaign"] = campaign_id

        form = TransactionForm(post_data)
        if form.is_valid():
            transaction = form.save(commit=False)
            # transaction.transaction_date = datetime.now().date()
            transaction.save()

            context = {
                "message": "Transaction was added successfully!",
                "campaign_id": campaign_id,
            }
        else:
            context = {
                "message": "There was an error saving this transaction!",
                "campaign_id": campaign_id,
            }
            
        return render(request, "tracker/partials/transaction-success.html", context)

    context = {"form": TransactionForm(), "campaign_id": campaign_id}
    return render(request, "tracker/partials/create-transaction.html", context)
