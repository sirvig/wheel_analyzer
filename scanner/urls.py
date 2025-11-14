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
    # Individual stock search
    path("search/", views.individual_search_view, name="search"),
    path("search/scan/", views.individual_scan_view, name="individual_scan"),
    path("search/status/", views.individual_scan_status_view, name="individual_scan_status"),
    # Saved searches (Phase 7.1)
    path("searches/", views.saved_searches_view, name="saved_searches"),
    path("searches/save/", views.save_search_view, name="save_search"),
    path("searches/delete/<int:pk>/", views.delete_search_view, name="delete_search"),
    path("searches/scan/<int:pk>/", views.quick_scan_view, name="quick_scan"),
    path("searches/edit/<int:pk>/", views.edit_search_notes_view, name="edit_search_notes"),
    # API Usage Dashboard (Phase 7.2)
    path("usage/", views.usage_dashboard_view, name="usage_dashboard"),
    # Staff Monitoring (Ad-hoc)
    path("admin/monitor/", views.scan_monitor_view, name="scan_monitor"),
    path("admin/clear-lock/", views.clear_scan_lock_view, name="clear_scan_lock"),
]
