from django.urls import path
from tracker import views


urlpatterns = [
    path("", views.index, name="index"),
    path("healthcheck/", views.healthcheck, name="healthcheck"),
    path("campaigns/", views.campaigns_list, name="campaigns-list"),
    path("campaigns/create/", views.create_campaign, name="create-campaign"),
    path(
        "transactions/<int:campaign_id>/",
        views.transactions_list,
        name="transactions-list",
    ),
    path(
        "transactions/<int:campaign_id>/create/",
        views.create_transaction,
        name="create-transaction",
    ),
]
