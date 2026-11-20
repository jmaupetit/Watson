"""Provide fixtures for pytest-based unit tests."""

import pytest
from click.testing import CliRunner

from watson import Watson


@pytest.fixture
def config_dir(tmpdir):
    """Temporary Watson configuration directory."""
    return str(tmpdir.mkdir("config"))


@pytest.fixture
def watson(config_dir):
    """Watson instance using a temporary configuration directory."""
    return Watson(config_dir=config_dir)


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def watson_df(datafiles):
    """Creates a Watson object with datafiles in config directory."""
    return Watson(config_dir=str(datafiles))
