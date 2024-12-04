import django_filters

from scanner.models import OptionsWatch


class OptionsWatchFilter(django_filters.FilterSet):
    class Meta:
        model = OptionsWatch
        fields = ["active"]
