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

    # EPS Calculation Results (auto-populated by calculation command)
    intrinsic_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Calculated fair value per share based on EPS DCF model",
    )
    
    # FCF Calculation Results (auto-populated by calculation command)
    intrinsic_value_fcf = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Calculated fair value per share based on FCF DCF model",
    )
    current_fcf_per_share = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Trailing twelve months Free Cash Flow per share",
    )
    
    last_calculation_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the intrinsic value was last calculated",
    )

    # EPS DCF Assumptions (manually editable in admin)
    current_eps = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Trailing Twelve Months Earnings Per Share (EPS TTM) - sum of 4 most recent quarterly reportedEPS from Alpha Vantage EARNINGS endpoint",
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
    
    # FCF DCF Assumptions (manually editable in admin)
    fcf_growth_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10.0,
        help_text="Expected FCF growth rate (%)",
    )
    fcf_multiple = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=20.0,
        help_text="Multiple applied to terminal year FCF for terminal value",
    )
    
    # Shared DCF Assumptions (used by both EPS and FCF methods)
    desired_return = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=15.0,
        help_text="Desired annual return rate (%) - used as discount rate",
    )
    projection_years = models.IntegerField(
        default=5, help_text="Number of years to project growth"
    )
    
    # Valuation Display Preference
    preferred_valuation_method = models.CharField(
        max_length=3,
        choices=[
            ("EPS", "EPS-based"),
            ("FCF", "FCF-based"),
        ],
        default="EPS",
        help_text="Preferred valuation method to display",
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
