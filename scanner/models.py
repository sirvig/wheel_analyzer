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

    # Calculation Results (auto-populated by calculation command)
    intrinsic_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Calculated fair value per share based on DCF model",
    )
    last_calculation_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the intrinsic value was last calculated",
    )

    # DCF Assumptions (manually editable in admin)
    current_eps = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Current Earnings Per Share (fetched from Alpha Vantage)",
    )
    eps_growth_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10.0,
        help_text="Expected EPS growth rate (%)",
    )
    eps_multiple = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=20.0,
        help_text="Multiple applied to terminal year EPS for terminal value",
    )
    desired_return = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=15.0,
        help_text="Desired annual return rate (%) - used as discount rate",
    )
    projection_years = models.IntegerField(
        default=5, help_text="Number of years to project EPS growth"
    )

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
