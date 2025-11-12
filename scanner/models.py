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

    def get_effective_intrinsic_value(self):
        """
        Get the intrinsic value based on the preferred valuation method.

        Returns:
            Decimal or None: The intrinsic value for the preferred method,
                             or None if not calculated.

        Example:
            >>> stock = CuratedStock.objects.get(symbol="AAPL")
            >>> stock.preferred_valuation_method = "EPS"
            >>> stock.get_effective_intrinsic_value()
            Decimal('150.25')
        """
        if self.preferred_valuation_method == "FCF":
            return self.intrinsic_value_fcf
        else:  # Default to EPS
            return self.intrinsic_value

    class Meta:
        ordering = ["symbol"]
        verbose_name = "Curated Stock"
        verbose_name_plural = "Curated Stocks"


class ValuationHistory(models.Model):
    """
    Historical record of quarterly valuation calculations for curated stocks.

    Stores quarterly snapshots (Jan 1, Apr 1, Jul 1, Oct 1) of intrinsic value
    calculations along with the DCF assumptions used at that time. This enables
    historical trend analysis and comparison of valuations over time.

    Design decisions:
    - Quarterly snapshots balance data granularity with storage efficiency
    - Store both EPS and FCF calculations for consistency with current model
    - Capture all DCF assumptions for reproducibility and assumption tracking
    - Never auto-delete (indefinite retention)
    - Foreign key to CuratedStock with CASCADE (if stock deleted, history deleted)
    """

    # Relationships
    stock = models.ForeignKey(
        'CuratedStock',
        on_delete=models.CASCADE,
        related_name='valuation_history',
        help_text="The stock this valuation history belongs to"
    )

    # Snapshot Metadata
    snapshot_date = models.DateField(
        db_index=True,  # Index for efficient date-range queries
        help_text="Quarter-end date when this snapshot was taken (Jan 1, Apr 1, Jul 1, Oct 1)"
    )

    calculated_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when this snapshot was created (may differ from snapshot_date)"
    )

    # EPS Valuation Results
    intrinsic_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Intrinsic value calculated using EPS DCF model"
    )

    current_eps = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Trailing Twelve Months EPS at time of snapshot"
    )

    eps_growth_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="EPS growth rate assumption (%) used in calculation"
    )

    eps_multiple = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Terminal value multiple applied to Year 5 EPS"
    )

    # FCF Valuation Results
    intrinsic_value_fcf = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Intrinsic value calculated using FCF DCF model"
    )

    current_fcf_per_share = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Trailing Twelve Months FCF per share at time of snapshot"
    )

    fcf_growth_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="FCF growth rate assumption (%) used in calculation"
    )

    fcf_multiple = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Terminal value multiple applied to Year 5 FCF"
    )

    # Shared DCF Assumptions
    desired_return = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Desired annual return rate (%) used as discount rate"
    )

    projection_years = models.IntegerField(
        help_text="Number of years projected in DCF model"
    )

    # Valuation Method Preference
    preferred_valuation_method = models.CharField(
        max_length=3,
        choices=[
            ("EPS", "EPS-based"),
            ("FCF", "FCF-based"),
        ],
        default="EPS",
        help_text="Preferred valuation method at time of snapshot"
    )

    # Notes
    notes = models.TextField(
        blank=True,
        help_text="Optional notes about this valuation snapshot (e.g., assumption changes)"
    )

    class Meta:
        ordering = ['-snapshot_date', 'stock__symbol']
        verbose_name = "Valuation History"
        verbose_name_plural = "Valuation Histories"
        indexes = [
            models.Index(fields=['stock', '-snapshot_date']),  # Per-stock queries
            models.Index(fields=['snapshot_date']),  # Quarterly queries
            models.Index(fields=['stock', 'snapshot_date']),  # Unique constraint support
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['stock', 'snapshot_date'],
                name='unique_stock_snapshot_date',
                violation_error_message="A valuation snapshot already exists for this stock and date."
            )
        ]

    def __str__(self):
        return f"{self.stock.symbol} - {self.snapshot_date}"

    def get_effective_intrinsic_value(self):
        """
        Get the intrinsic value based on the preferred valuation method.

        Returns:
            Decimal or None: The intrinsic value for the preferred method.
        """
        if self.preferred_valuation_method == "FCF":
            return self.intrinsic_value_fcf
        else:
            return self.intrinsic_value

    @property
    def quarter_label(self):
        """
        Return a human-readable quarter label (e.g., 'Q1 2025').

        Returns:
            str: Quarter label like 'Q1 2025', 'Q2 2025', etc.
        """
        quarter_map = {1: 'Q1', 4: 'Q2', 7: 'Q3', 10: 'Q4'}
        quarter = quarter_map.get(self.snapshot_date.month, 'Q?')
        return f"{quarter} {self.snapshot_date.year}"


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
