from django.contrib import admin

from .models import CuratedStock, OptionsWatch, SavedSearch, ScanStatus, ScanUsage, UserQuota, ValuationHistory


@admin.register(CuratedStock)
class CuratedStockAdmin(admin.ModelAdmin):
    list_display = [
        "symbol",
        "active",
        "intrinsic_value",
        "intrinsic_value_fcf",
        "preferred_valuation_method",
        "last_calculation_date",
        "created_at",
    ]
    list_filter = ["active", "preferred_valuation_method", "created_at"]
    search_fields = ["symbol", "notes"]
    ordering = ["symbol"]
    readonly_fields = [
        "intrinsic_value",
        "intrinsic_value_fcf",
        "current_fcf_per_share",
        "last_calculation_date",
        "created_at",
        "updated_at",
    ]
    fieldsets = (
        ("Stock Information", {"fields": ("symbol", "active", "notes")}),
        (
            "Intrinsic Value Calculation",
            {
                "fields": (
                    "intrinsic_value",
                    "intrinsic_value_fcf",
                    "preferred_valuation_method",
                    "last_calculation_date",
                ),
                "description": "Calculated values updated by weekly valuation job",
            },
        ),
        (
            "EPS-based DCF Assumptions",
            {
                "fields": (
                    "current_eps",
                    "eps_growth_rate",
                    "eps_multiple",
                ),
                "description": "Customize EPS-based DCF model assumptions for this stock",
            },
        ),
        (
            "FCF-based DCF Assumptions",
            {
                "fields": (
                    "current_fcf_per_share",
                    "fcf_growth_rate",
                    "fcf_multiple",
                ),
                "description": "Customize FCF-based DCF model assumptions for this stock",
            },
        ),
        (
            "Shared DCF Assumptions",
            {
                "fields": (
                    "desired_return",
                    "projection_years",
                ),
                "description": "Used by both EPS and FCF valuation methods",
            },
        ),
        (
            "Metadata",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(ValuationHistory)
class ValuationHistoryAdmin(admin.ModelAdmin):
    list_display = [
        "stock",
        "quarter_label",
        "snapshot_date",
        "intrinsic_value",
        "intrinsic_value_fcf",
        "preferred_valuation_method",
        "calculated_at",
    ]
    list_filter = ["snapshot_date", "preferred_valuation_method", "stock"]
    search_fields = ["stock__symbol", "notes"]
    ordering = ["-snapshot_date", "stock__symbol"]
    readonly_fields = ["calculated_at"]
    date_hierarchy = "snapshot_date"

    fieldsets = (
        (
            "Snapshot Information",
            {
                "fields": ("stock", "snapshot_date", "calculated_at", "notes")
            },
        ),
        (
            "EPS Valuation Results",
            {
                "fields": (
                    "intrinsic_value",
                    "current_eps",
                    "eps_growth_rate",
                    "eps_multiple",
                )
            },
        ),
        (
            "FCF Valuation Results",
            {
                "fields": (
                    "intrinsic_value_fcf",
                    "current_fcf_per_share",
                    "fcf_growth_rate",
                    "fcf_multiple",
                )
            },
        ),
        (
            "Shared DCF Assumptions",
            {
                "fields": (
                    "desired_return",
                    "projection_years",
                    "preferred_valuation_method",
                )
            },
        ),
    )


@admin.register(SavedSearch)
class SavedSearchAdmin(admin.ModelAdmin):
    list_display = ['ticker', 'option_type', 'user', 'scan_count', 'last_scanned_at', 'created_at', 'is_deleted']
    list_filter = ['option_type', 'is_deleted', 'created_at']
    search_fields = ['ticker', 'user__username', 'notes']
    readonly_fields = ['scan_count', 'last_scanned_at', 'created_at']
    ordering = ['-created_at']


@admin.register(ScanUsage)
class ScanUsageAdmin(admin.ModelAdmin):
    list_display = ['user', 'scan_type', 'ticker', 'timestamp']
    list_filter = ['scan_type', 'timestamp']
    search_fields = ['user__username', 'ticker']
    readonly_fields = ['timestamp']
    ordering = ['-timestamp']
    date_hierarchy = 'timestamp'


@admin.register(UserQuota)
class UserQuotaAdmin(admin.ModelAdmin):
    list_display = ['user', 'daily_limit', 'created_at', 'updated_at']
    search_fields = ['user__username']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['user__username']


@admin.register(ScanStatus)
class ScanStatusAdmin(admin.ModelAdmin):
    list_display = ['scan_type', 'status', 'start_time', 'end_time', 'tickers_scanned', 'result_count']
    list_filter = ['status', 'scan_type', 'start_time']
    search_fields = ['error_message']
    readonly_fields = ['start_time', 'duration']
    ordering = ['-start_time']
    date_hierarchy = 'start_time'

    fieldsets = (
        ('Scan Information', {
            'fields': ('scan_type', 'status', 'start_time', 'end_time', 'duration')
        }),
        ('Results', {
            'fields': ('tickers_scanned', 'result_count')
        }),
        ('Error Details', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
    )

    def duration(self, obj):
        """Display scan duration in human-readable format."""
        if obj.duration is not None:
            minutes, seconds = divmod(int(obj.duration), 60)
            if minutes > 0:
                return f"{minutes}m {seconds}s"
            return f"{seconds}s"
        return "N/A"
    duration.short_description = 'Duration'


# Register your models here.
admin.site.register(OptionsWatch)
