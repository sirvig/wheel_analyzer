from django.urls import path

from scanner import views

urlpatterns = [
    path("", views.index, name="scanner_index"),
    path("scan/", views.scan_view, name="scan"),
    path("scan-status/", views.scan_status, name="scan_status"),
    path("options/<str:ticker>", views.options_list, name="options_list"),
]
