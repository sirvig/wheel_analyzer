from django.contrib import admin

from .models import CuratedStock, OptionsWatch, ValuationHistory


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


# Register your models here.
admin.site.register(OptionsWatch)
