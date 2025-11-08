from django.urls import path

from scanner import views

app_name = "scanner"

urlpatterns = [
    path("", views.index, name="index"),
    path("valuations/", views.valuation_list_view, name="valuations"),
    path("scan/", views.scan_view, name="scan"),
    path("scan-status/", views.scan_status, name="scan_status"),
    path("options/<str:ticker>", views.options_list, name="options_list"),
]
