"""
tests for lssql.harvester with pytest.
* 'tmp_path' -- a built-in pytest fixture. fresh temporary directory per test, cleans up automatically.
* 'freeze_date' -- a custom pytest fixture defined in 'conftest.py'
"""

import lssql.harvester as harvester
from lssql.harvester import content_hash

# -- harvest_date --


def test_harvest_date(freeze_date):
    """harvest_date() must be called via the module, not imported directly, while freeze_date is active."""
    assert len(harvester.harvest_date()) == 8
    assert harvester.harvest_date().isdigit()
    assert harvester.harvest_date() == "20260421"


# -- content_hash --


def test_content_hash_length(tmp_path):
    f = tmp_path / "photo.jpg"
    f.write_text("fake image content")
    result = content_hash(str(f))
    assert len(result) == 10


def test_content_hash_is_hex(tmp_path):
    f = tmp_path / "photo.jpg"
    f.write_text("fake image content")
    result = content_hash(str(f))
    assert all(c in "0123456789abcdef" for c in result)


def test_content_hash_same_content_same_hash(tmp_path):
    a = tmp_path / "a.jpg"
    b = tmp_path / "b.jpg"
    a.write_text("same content")
    b.write_text("same content")
    assert content_hash(str(a)) == content_hash(str(b))


def test_content_hash_different_content_different_hash(tmp_path):
    a = tmp_path / "a.jpg"
    b = tmp_path / "b.jpg"
    a.write_text("content a")
    b.write_text("content b")
    assert content_hash(str(a)) != content_hash(str(b))
