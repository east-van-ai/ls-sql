import pytest
from unittest.mock import patch


@pytest.fixture
def freeze_date():
    """freeze harvest_date() to a known value for deterministic tests."""
    with patch("lssql.harvester.harvest_date", return_value="20260503"):
        yield
