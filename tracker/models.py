from django.db import models
from django.contrib.auth.models import AbstractUser
from .managers import CampaignsQuerySet, TransactionsQuerySet


class User(AbstractUser):
    pass


class Account(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    taxable = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Campaign(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    stock = models.CharField(max_length=10)
    active = models.BooleanField(blank=True, null=True)
    start_date = models.DateField(auto_now=False, blank=True, null=True)
    end_date = models.DateField(auto_now=False, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = CampaignsQuerySet.as_manager()

    def __str__(self):
        return f"Stock: {self.stock} Account: {self.account.name} Started: {self.start_date} Active: {self.active}"

    class Meta:
        ordering = ["stock", "account", "-start_date"]


class Transaction(models.Model):
    TRANSACTION_TYPE_CHOICES = (
        ("put", "Put"),
        ("call", "Call"),
        ("roll", "Roll"),
        ("buy", "Buy"),
        ("sell", "Sell"),
        ("btc", "Buy To Close"),
        ("div", "Dividend"),
    )

    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE)
    type = models.CharField(max_length=7, choices=TRANSACTION_TYPE_CHOICES)
    premium = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    transaction_date = models.DateField()
    expiration_date = models.DateField(blank=True, null=True)
    strike_price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    contracts = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = TransactionsQuerySet.as_manager()

    def __str__(self):
        return f"{self.transaction_date} - {self.campaign.stock} - {self.campaign.account.name}"

    class Meta:
        ordering = ["transaction_date"]
