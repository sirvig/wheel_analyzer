import pytest

from scanner.models import OptionsWatch


@pytest.mark.django_db
def test_queryset_get_active_method(options_watch):
    qs = OptionsWatch.objects.get_active()
    assert qs.count() > 0
    assert all([watch.active for watch in qs])


@pytest.mark.django_db
def test_queryset_get_inactive_method(options_watch):
    qs = OptionsWatch.objects.get_inactive()
    assert qs.count() > 0
    assert all([not watch.active for watch in qs])
