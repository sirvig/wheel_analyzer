from django.urls import path

from scanner import views

app_name = "scanner"

urlpatterns = [
    path("", views.index, name="index"),
    path("valuations/", views.valuation_list_view, name="valuations"),
    path("valuations/analytics/", views.analytics_view, name="analytics"),
    path("valuations/history/<str:symbol>/", views.stock_history_view, name="stock_history"),
    path("valuations/comparison/", views.valuation_comparison_view, name="valuation_comparison"),
    path("valuations/export/", views.export_valuation_history_csv, name="export_all_history"),
    path("valuations/export/<str:symbol>/", views.export_valuation_history_csv, name="export_stock_history"),
    path("scan/", views.scan_view, name="scan"),
    path("scan-status/", views.scan_status, name="scan_status"),
    path("options/<str:ticker>", views.options_list, name="options_list"),
]
