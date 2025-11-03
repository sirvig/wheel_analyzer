from django.contrib.auth import get_user_model
from django.db import models

from .managers import OptionsWatchQuerySet

User = get_user_model()


class CuratedStock(models.Model):
    symbol = models.CharField(max_length=10, unique=True)
    active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.symbol

    class Meta:
        ordering = ["symbol"]
        verbose_name = "Curated Stock"
        verbose_name_plural = "Curated Stocks"


class OptionsWatch(models.Model):
    TYPE_CHOICES = (
        ("put", "Put"),
        ("call", "Call"),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    stock = models.CharField(max_length=10)
    active = models.BooleanField(blank=True, null=True)
    type = models.CharField(max_length=7, choices=TYPE_CHOICES)
    strike_price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = OptionsWatchQuerySet.as_manager()

    def __str__(self):
        return self.stock

    class Meta:
        verbose_name_plural = "Options Watch"
