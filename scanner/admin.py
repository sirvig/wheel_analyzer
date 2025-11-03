from django.contrib import admin

from .models import CuratedStock, OptionsWatch


@admin.register(CuratedStock)
class CuratedStockAdmin(admin.ModelAdmin):
    list_display = ["symbol", "active", "created_at", "updated_at"]
    list_filter = ["active", "created_at"]
    search_fields = ["symbol", "notes"]
    ordering = ["symbol"]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = (
        (None, {"fields": ("symbol", "active")}),
        ("Additional Information", {"fields": ("notes",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


# Register your models here.
admin.site.register(OptionsWatch)
