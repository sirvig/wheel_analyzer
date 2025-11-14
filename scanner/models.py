from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

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


class SavedSearchManager(models.Manager):
    """Custom manager for SavedSearch with active filter."""

    def active(self):
        """Return only non-deleted saved searches."""
        return self.filter(is_deleted=False)

    def for_user(self, user):
        """Return active searches for specific user."""
        return self.active().filter(user=user)


class SavedSearch(models.Model):
    """
    User's saved stock search for quick access.

    Tracks frequently searched tickers with usage statistics
    and optional categorization notes.
    """

    OPTION_TYPE_CHOICES = [
        ('put', 'Put Options'),
        ('call', 'Call Options'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='saved_searches',
        help_text="User who saved this search"
    )
    ticker = models.CharField(
        max_length=10,
        help_text="Stock ticker symbol (uppercase)"
    )
    option_type = models.CharField(
        max_length=4,
        choices=OPTION_TYPE_CHOICES,
        help_text="Type of options to scan"
    )
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Optional notes for categorization (e.g., 'earnings play')"
    )
    scan_count = models.IntegerField(
        default=0,
        help_text="Number of times quick scan was executed"
    )
    last_scanned_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Timestamp of most recent scan execution"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this search was saved"
    )
    is_deleted = models.BooleanField(
        default=False,
        help_text="Soft delete flag"
    )

    objects = SavedSearchManager()

    class Meta:
        db_table = 'scanner_saved_search'
        verbose_name = 'Saved Search'
        verbose_name_plural = 'Saved Searches'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_deleted']),
            models.Index(fields=['created_at']),
            models.Index(fields=['last_scanned_at']),
            models.Index(fields=['scan_count']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'ticker', 'option_type'],
                condition=models.Q(is_deleted=False),
                name='unique_active_saved_search'
            )
        ]

    def __str__(self):
        return f"{self.user.username} - {self.ticker} {self.option_type}"

    def increment_scan_count(self):
        """Increment scan counter and update last scanned timestamp."""
        self.scan_count += 1
        self.last_scanned_at = timezone.now()
        self.save(update_fields=['scan_count', 'last_scanned_at'])

    def soft_delete(self):
        """Mark as deleted without removing from database."""
        self.is_deleted = True
        self.save(update_fields=['is_deleted'])


class ScanUsage(models.Model):
    """
    Record of individual scan operation for quota tracking.

    Tracks when users execute scans (curated or individual) for
    rate limit enforcement and usage analytics.
    """

    SCAN_TYPE_CHOICES = [
        ('curated', 'Curated Scanner'),
        ('individual', 'Individual Search'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='scan_usage',
        help_text="User who performed the scan"
    )
    scan_type = models.CharField(
        max_length=20,
        choices=SCAN_TYPE_CHOICES,
        help_text="Type of scan operation"
    )
    ticker = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="Stock symbol (for individual scans only)"
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text="When the scan was executed"
    )

    class Meta:
        db_table = 'scanner_scan_usage'
        verbose_name = 'Scan Usage'
        verbose_name_plural = 'Scan Usage Records'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]

    def __str__(self):
        ticker_str = f" ({self.ticker})" if self.ticker else ""
        return f"{self.user.username} - {self.scan_type}{ticker_str} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"


class UserQuota(models.Model):
    """
    Per-user daily scan quota configuration.

    Stores the maximum number of scans allowed per day for each user.
    Default is 25 scans/day to align with Alpha Vantage free tier limits.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='quota',
        help_text="User this quota applies to"
    )
    daily_limit = models.IntegerField(
        default=25,
        help_text="Maximum scans allowed per day"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When quota was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Last modification timestamp"
    )

    class Meta:
        db_table = 'scanner_user_quota'
        verbose_name = 'User Quota'
        verbose_name_plural = 'User Quotas'

    def __str__(self):
        return f"{self.user.username} - {self.daily_limit}/day"

    @classmethod
    def get_quota_for_user(cls, user):
        """Get or create quota for user with default limit."""
        quota, created = cls.objects.get_or_create(
            user=user,
            defaults={'daily_limit': 25}
        )
        return quota


class ScanStatus(models.Model):
    """
    Track the status of background scan operations.

    This model provides visibility into the current state of scan operations
    and helps diagnose issues when scans fail or get stuck.
    """

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('aborted', 'Aborted'),
    ]

    SCAN_TYPE_CHOICES = [
        ('curated', 'Curated Stocks'),
        ('individual', 'Individual Stock'),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Current status of the scan operation"
    )
    scan_type = models.CharField(
        max_length=20,
        choices=SCAN_TYPE_CHOICES,
        default='curated',
        help_text="Type of scan being performed"
    )
    start_time = models.DateTimeField(
        auto_now_add=True,
        help_text="When the scan started"
    )
    end_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the scan completed/failed"
    )
    result_count = models.IntegerField(
        null=True,
        blank=True,
        help_text="Number of results found"
    )
    tickers_scanned = models.IntegerField(
        default=0,
        help_text="Number of tickers scanned"
    )
    error_message = models.TextField(
        blank=True,
        help_text="Error message if scan failed"
    )

    class Meta:
        db_table = 'scanner_scan_status'
        verbose_name = 'Scan Status'
        verbose_name_plural = 'Scan Statuses'
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['-start_time']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.scan_type} scan - {self.status} ({self.start_time})"

    @property
    def duration(self):
        """Calculate duration of the scan in seconds."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        elif self.status == 'in_progress':
            return (timezone.now() - self.start_time).total_seconds()
        return None

    @property
    def is_active(self):
        """Check if scan is currently active."""
        return self.status in ['pending', 'in_progress']

    def mark_completed(self, result_count=None, tickers_scanned=0):
        """Mark scan as completed with results."""
        self.status = 'completed'
        self.end_time = timezone.now()
        self.result_count = result_count
        self.tickers_scanned = tickers_scanned
        self.save()

    def mark_failed(self, error_message=''):
        """Mark scan as failed with error message."""
        self.status = 'failed'
        self.end_time = timezone.now()
        self.error_message = error_message
        self.save()

    def mark_aborted(self, reason='Manually aborted by staff'):
        """Mark scan as aborted (usually due to manual intervention)."""
        self.status = 'aborted'
        self.end_time = timezone.now()
        self.error_message = reason
        self.save()
