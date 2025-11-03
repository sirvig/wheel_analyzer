import pytest

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
