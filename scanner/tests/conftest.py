import sys

import django
import pytest
from django.core.cache import cache
from django.core.management.base import OutputWrapper

from scanner.factories import OptionsWatchFactory
from scanner.models import CuratedStock
from tracker.factories import UserFactory


@pytest.fixture
def user():
    """Create a test user."""
    return UserFactory()


@pytest.fixture
def options_watch():
    return OptionsWatchFactory.create_batch(20)


@pytest.fixture
def clean_curated_stocks():
    """Remove all curated stocks for isolated testing."""
    CuratedStock.objects.all().delete()
    yield
    # Cleanup after test
    CuratedStock.objects.all().delete()


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before each test."""
    cache.clear()
    yield
    cache.clear()


if django.VERSION < (5, 2):
    orig_unraisablehook = sys.unraisablehook

    def unraisablehook(unraisable):
        if (
            unraisable.exc_type is ValueError
            and unraisable.exc_value is not None
            and unraisable.exc_value.args == ("I/O operation on closed file.",)
            and isinstance(unraisable.object, OutputWrapper)
        ):
            return
        orig_unraisablehook(unraisable)

    sys.unraisablehook = unraisablehook
