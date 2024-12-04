import pytest

from scanner.factories import OptionsWatchFactory


@pytest.fixture
def options_watch():
    return OptionsWatchFactory.create_batch(20)
