from django.urls import path

from scanner import views

urlpatterns = [
    path("", views.index, name="scanner_index"),
    path("options/<str:ticker>", views.options_list, name="options_list"),
]
