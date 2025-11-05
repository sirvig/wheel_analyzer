from django.contrib import admin

from .models import CuratedStock, OptionsWatch


@admin.register(CuratedStock)
class CuratedStockAdmin(admin.ModelAdmin):
    list_display = [
        "symbol",
        "active",
        "intrinsic_value",
        "last_calculation_date",
        "created_at",
    ]
    list_filter = ["active", "created_at"]
    search_fields = ["symbol", "notes"]
    ordering = ["symbol"]
    readonly_fields = [
        "intrinsic_value",
        "last_calculation_date",
        "created_at",
        "updated_at",
    ]
    fieldsets = (
        ("Stock Information", {"fields": ("symbol", "active", "notes")}),
        (
            "Intrinsic Value Calculation",
            {
                "fields": ("intrinsic_value", "last_calculation_date"),
                "description": "Calculated values updated by weekly valuation job",
            },
        ),
        (
            "DCF Assumptions",
            {
                "fields": (
                    "current_eps",
                    "eps_growth_rate",
                    "eps_multiple",
                    "desired_return",
                    "projection_years",
                ),
                "description": "Customize DCF model assumptions for this stock",
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


# Register your models here.
admin.site.register(OptionsWatch)
