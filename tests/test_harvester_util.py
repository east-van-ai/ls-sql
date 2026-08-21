from collections.abc import Generator

import pytest

from src.lssql.harvester_util import (
    is_already_harvested,
    is_troublesome_name,
    parse_ext_filter,
    sanitize_tag_value,
)

# -- is_troublesome_name --


def test_is_troublesome_name():
    assert is_troublesome_name("photo^^^hello^^^hey^^^you.jpg") is True
    assert is_troublesome_name("photo^^^hello^^^hey^^^you^^^.jpg") is True


# -- is_already_harvested --


def test_already_harvested_plain_filename():
    assert is_already_harvested("photo.jpg") is False


def _caret_filenames(max_carets: int = 15, prefix: str = "") -> Generator[str]:
    """
    Yield filenames of the form ``<prefix><caret-string>.jpg``.

    * ``max_carets`` - maximum number of ^ characters (inclusive).
    * ``prefix``     - optional string that appears before the carets.
    """
    for n in range(1, max_carets + 1):
        yield f"{prefix}{'^' * n}.jpg"


@pytest.mark.parametrize("filename", list(_caret_filenames(prefix="")))
def test_carets_only_without_prefix_without_postfix(filename):
    """A caret-only filename must be reported as *not* harvested."""
    assert is_already_harvested("^^^.jpg") is False
    assert not is_already_harvested(filename)


@pytest.mark.parametrize("filename", list(_caret_filenames(prefix="img_")))
def test_carets_only_with_prefix_without_postfix(filename):
    """A prefixed caret-only filename must be reported as *not* harvested."""
    assert is_already_harvested("img_^^^.jpg") is False
    assert not is_already_harvested(filename)


def test_already_harvested_with_separator():
    assert is_already_harvested("photo^^^ls:hd=20260503.jpg") is True
    assert is_already_harvested("photo^^^ls:hd=20260503^^^.jpg") is True
    assert is_already_harvested("photo^^^ls:hd=20260503^^^london.jpg") is True


# -- parse_ext_filter --


def test_parse_ext_filter_single():
    assert parse_ext_filter("jpg") == {".jpg"}


def test_parse_ext_filter_multiple():
    assert parse_ext_filter("jpg,png") == {".jpg", ".png"}


def test_parse_ext_filter_empty():
    assert parse_ext_filter("") == set()


def test_parse_ext_filter_normalizes_case():
    assert parse_ext_filter("JPG,PNG") == {".jpg", ".png"}


def test_parse_ext_filter_handles_dot_prefix():
    assert parse_ext_filter(".jpg,.png") == {".jpg", ".png"}


# -- sanitize_tag_value --


def test_sanitize_tag_value_replaces_carets():

    assert sanitize_tag_value("AC^DC") == "AC-DC"
    assert sanitize_tag_value("Live^^^Unplugged") == "Live---Unplugged"
    assert sanitize_tag_value("normal value") == "normal value"


# -- malformed stems --


def test_is_troublesome_name_catches_stray_caret_runs():
    """A caret run that is not a multiple of three is not a Hatfile stem."""
    assert is_troublesome_name("0001-01234^^^^it-is-blue.jpg") is True
    assert is_troublesome_name("0001-01234^^^^^it-is-blue.jpg") is True
    assert is_troublesome_name("0001-01234^^^^^^^it-is-blue.jpg") is True


def test_is_troublesome_name_allows_well_formed_stems():
    """An empty tag section is six carets, and stays valid."""
    assert is_troublesome_name("0001-01234^^^^^^it-is-blue.jpg") is False
    assert is_troublesome_name("photo^^^ls:hd=20260503^ls:dw=8^^^london.jpg") is False
    assert is_troublesome_name("plain-photo.jpg") is False


def test_malformed_stem_is_never_already_harvested():
    """
    the tag slot of a malformed stem holds a stray caret run, not tags.
    reading it as tags is what let set overwrite the section.
    """
    assert is_already_harvested("0001-01234^^^^it-is-blue.jpg") is False
    assert is_already_harvested("0001-01234^^^^^^^it-is-blue.jpg") is False
