import pytest
from django.core.cache import cache

from scanner.factories import OptionsWatchFactory
from scanner.models import CuratedStock


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
