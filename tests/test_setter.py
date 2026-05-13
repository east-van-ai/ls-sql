"""
tests for setter.py

covers:
    parse_set_string    -- validation and parsing
    is_protected_namespace
    apply_operations    -- all operators and no-ops
    rebuild_filename    -- reconstruction
    set_file            -- file operations, harvest-first, dry-run, commit
    set_tags_directory  -- directory walk, recursive
"""

import os
import pytest

from lssql.setter import (
    apply_operations,
    is_protected_namespace,
    parse_set_string,
    rebuild_filename,
    set_file,
    set_tags_directory,
)

# -- is_protected_namespace -----------------------------------------------


def test_protected_ls():
    assert is_protected_namespace("ls:fh") is True


def test_protected_ex():
    assert is_protected_namespace("ex:cam") is True


def test_protected_au():
    assert is_protected_namespace("au:ar") is True


def test_protected_zi():
    assert is_protected_namespace("zi:ext") is True


def test_not_protected_ud():
    assert is_protected_namespace("ud:album") is False


def test_not_protected_three_letter():
    assert is_protected_namespace("myapp:key") is False


def test_not_protected_one_letter():
    assert is_protected_namespace("x:key") is False


# -- parse_set_string -- valid --------------------------------------------


def test_parse_overwrite():
    ops, error = parse_set_string("ud:fruit=banana")
    assert error is None
    assert ops == [{"op": "=", "key": "ud:fruit", "values": {"banana"}}]


def test_parse_append():
    ops, error = parse_set_string("ud:weather+=rainy")
    assert error is None
    assert ops == [{"op": "+=", "key": "ud:weather", "values": {"rainy"}}]


def test_parse_append_multiple_values():
    ops, error = parse_set_string("ud:weather+=rainy;sunny")  # SEMICOLON
    assert error is None
    assert ops == [
        {"op": "+=", "key": "ud:weather", "values": {"rainy", "sunny"}},
    ]


def test_parse_remove_value():
    ops, error = parse_set_string("ud:weather-=rainy")
    assert error is None
    assert ops == [{"op": "-=", "key": "ud:weather", "values": {"rainy"}}]


def test_parse_delete():
    ops, error = parse_set_string("ud:weather==")
    assert error is None
    assert ops == [{"op": "==", "key": "ud:weather", "values": {""}}]


def test_parse_multiple_ops():
    ops, error = parse_set_string("ud:fruit=banana^ud:weather+=rainy^ud:old==")
    assert error is None
    assert len(ops) == 3
    assert ops[0] == {"op": "=", "key": "ud:fruit", "values": {"banana"}}
    assert ops[1] == {"op": "+=", "key": "ud:weather", "values": {"rainy"}}
    assert ops[2] == {"op": "==", "key": "ud:old", "values": {""}}


# -- parse_set_string -- no-ops (valid, but will be skipped by apply) -----


def test_parse_overwrite_empty_value():
    ops, error = parse_set_string("ud:fruit=")
    assert error is None
    assert ops == [{"op": "=", "key": "ud:fruit", "values": {""}}]


def test_parse_append_empty_value():
    ops, error = parse_set_string("ud:weather+=")
    assert error is None
    assert ops == [{"op": "+=", "key": "ud:weather", "values": {""}}]


def test_parse_remove_empty_value():
    ops, error = parse_set_string("ud:weather-=")
    assert error is None
    assert ops == [{"op": "-=", "key": "ud:weather", "values": {""}}]


def test_parse_delete_with_value_is_noop():
    ops, error = parse_set_string("ud:weather==banana")
    assert error is None
    assert ops == [{"op": "==", "key": "ud:weather", "values": {"banana"}}]


# -- parse_set_string -- errors -------------------------------------------


def test_parse_empty_string():
    ops, error = parse_set_string("")
    assert error is not None
    assert ops == []


def test_parse_no_operator():
    ops, error = parse_set_string("ud:fruit")
    assert error is not None
    assert ops == []


def test_parse_missing_namespace():
    ops, error = parse_set_string("fruit=banana")
    assert error is not None
    assert "namespace" in error


def test_parse_protected_ls():
    ops, error = parse_set_string("ls:fh=abc")
    assert error is not None
    assert "reserved" in error
    assert ops == []


def test_parse_protected_ex():
    ops, error = parse_set_string("ex:cam=fuji")
    assert error is not None
    assert "reserved" in error


def test_parse_protected_stops_all():
    # even if first op is valid, protected tag stops everything
    ops, error = parse_set_string("ud:fruit=banana^ls:fh=abc")
    assert error is not None
    assert ops == []


# -- apply_operations -----------------------------------------------------


def test_apply_overwrite_new_tag():
    tags = {}
    ops = [{"op": "=", "key": "ud:fruit", "values": {"banana"}}]
    result = apply_operations(tags, ops)
    assert result == {"ud:fruit": "banana"}


def test_apply_overwrite_existing_tag():
    tags = {"ud:fruit": "apple"}
    ops = [{"op": "=", "key": "ud:fruit", "values": {"banana"}}]
    result = apply_operations(tags, ops)
    assert result == {"ud:fruit": "banana"}


def test_apply_overwrite_empty_value_is_noop():
    tags = {"ud:fruit": "apple"}
    ops = [{"op": "=", "key": "ud:fruit", "values": {""}}]
    result = apply_operations(tags, ops)
    assert result == {"ud:fruit": "apple"}


def test_apply_append_to_existing():
    tags = {"ud:weather": "sunny"}
    ops = [{"op": "+=", "key": "ud:weather", "values": {"rainy"}}]
    result = apply_operations(tags, ops)
    assert result == {"ud:weather": "rainy;sunny"}


def test_apply_append_to_empty():
    tags = {}
    ops = [{"op": "+=", "key": "ud:weather", "values": {"rainy"}}]
    result = apply_operations(tags, ops)
    assert result == {"ud:weather": "rainy"}


def test_apply_append_empty_value_is_noop():
    tags = {"ud:weather": "sunny"}
    ops = [{"op": "+=", "key": "ud:weather", "values": {""}}]
    result = apply_operations(tags, ops)
    assert result == {"ud:weather": "sunny"}


def test_apply_remove_value():
    tags = {"ud:weather": "sunny;rainy"}
    ops = [{"op": "-=", "key": "ud:weather", "values": {"rainy"}}]
    result = apply_operations(tags, ops)
    assert result == {"ud:weather": "sunny"}


def test_apply_remove_last_value_deletes_tag():
    tags = {"ud:weather": "sunny"}
    ops = [{"op": "-=", "key": "ud:weather", "values": {"sunny"}}]
    result = apply_operations(tags, ops)
    assert "ud:weather" not in result


def test_apply_remove_missing_value_is_noop():
    tags = {"ud:weather": "sunny"}
    ops = [{"op": "-=", "key": "ud:weather", "values": {"rainy"}}]
    result = apply_operations(tags, ops)
    assert result == {"ud:weather": "sunny"}


def test_apply_remove_empty_value_is_noop():
    tags = {"ud:weather": "sunny"}
    ops = [{"op": "-=", "key": "ud:weather", "values": {""}}]
    result = apply_operations(tags, ops)
    assert result == {"ud:weather": "sunny"}


def test_apply_delete():
    tags = {"ud:weather": "sunny", "ud:fruit": "apple"}
    ops = [{"op": "==", "key": "ud:weather", "values": {""}}]
    result = apply_operations(tags, ops)
    assert "ud:weather" not in result
    assert result == {"ud:fruit": "apple"}


def test_apply_delete_missing_tag_is_noop():
    tags = {"ud:fruit": "apple"}
    ops = [{"op": "==", "key": "ud:weather", "values": {""}}]
    result = apply_operations(tags, ops)
    assert result == {"ud:fruit": "apple"}


def test_apply_delete_with_value_is_noop():
    tags = {"ud:weather": "sunny"}
    ops = [{"op": "==", "key": "ud:weather", "values": {"banana"}}]
    result = apply_operations(tags, ops)
    assert result == {"ud:weather": "sunny"}


def test_apply_preserves_other_tags():
    tags = {"ls:hd": "20260504", "ls:fh": "ab2c3d4e5f", "ud:fruit": "apple"}
    ops = [{"op": "=", "key": "ud:fruit", "values": {"banana"}}]
    result = apply_operations(tags, ops)
    assert result["ls:hd"] == "20260504"
    assert result["ls:fh"] == "ab2c3d4e5f"
    assert result["ud:fruit"] == "banana"


# -- rebuild_filename -----------------------------------------------------


def test_rebuild_with_comment():
    parsed = {
        "original": "photo",
        "comment": "london",
        "ext": ".jpg",
        "tags": {},
    }
    tags = {"ls:hd": "20260504", "ud:fruit": "banana"}
    result = rebuild_filename(parsed, tags)
    assert result == "photo^^^ls:hd=20260504^ud:fruit=banana^^^london.jpg"


def test_rebuild_without_comment():
    parsed = {
        "original": "photo",
        "comment": "",
        "ext": ".jpg",
        "tags": {},
    }
    tags = {"ls:hd": "20260504"}
    result = rebuild_filename(parsed, tags)
    assert result == "photo^^^ls:hd=20260504^^^.jpg"


def test_rebuild_empty_tags():
    parsed = {
        "original": "photo",
        "comment": "",
        "ext": ".jpg",
        "tags": {},
    }
    result = rebuild_filename(parsed, {})
    assert result == "photo.jpg"


# -- set_file -------------------------------------------------------------


def test_set_file_dry_run(tmp_path, freeze_date):
    f = tmp_path / "photo^^^ls:hd=20260503^ls:fh=ab2c3d4e5f^^^.jpg"
    f.write_bytes(b"x")

    ops, _ = parse_set_string("ud:album=london")
    result = set_file(str(tmp_path), f.name, ops, commit=False)

    assert result["status"] == "dry-run"
    assert "ud:album=london" in result["new_name"]
    assert f.exists()  # file not touched


def test_set_file_commit(tmp_path, freeze_date):
    f = tmp_path / "photo^^^ls:hd=20260503^ls:fh=ab2c3d4e5f^^^.jpg"
    f.write_bytes(b"x")

    ops, _ = parse_set_string("ud:album=london")
    result = set_file(str(tmp_path), f.name, ops, commit=True)

    assert result["status"] == "updated"
    assert "ud:album=london" in result["new_name"]
    assert not f.exists()  # renamed
    assert (tmp_path / result["new_name"]).exists()


def test_set_file_harvest_first_dry_run(tmp_path, freeze_date):
    f = tmp_path / "photo.jpg"
    f.write_bytes(b"x")

    ops, _ = parse_set_string("ud:album=london")
    result = set_file(str(tmp_path), f.name, ops, commit=False)

    assert result["status"] == "dry-run"
    assert "ud:album=london" in result["new_name"]
    assert f.exists()  # not touched in dry-run


def test_set_file_harvest_first_commit(tmp_path, freeze_date):
    f = tmp_path / "photo.jpg"
    f.write_bytes(b"x")

    ops, _ = parse_set_string("ud:album=london")
    result = set_file(str(tmp_path), f.name, ops, commit=True)

    assert result["status"] == "updated"
    assert "ud:album=london" in result["new_name"]
    assert not f.exists()


def test_set_file_no_change_is_skipped(tmp_path, freeze_date):
    f = tmp_path / "photo^^^ls:hd=20260503^ls:fh=ab2c3d4e5f^ud:fruit=apple^^^.jpg"
    f.write_bytes(b"x")

    # overwrite with same value -- no change
    ops, _ = parse_set_string("ud:fruit=apple")
    result = set_file(str(tmp_path), f.name, ops, commit=False)

    assert result["status"] == "skipped"
    assert result["reason"] == "no change"


def test_set_file_append(tmp_path, freeze_date):
    f = tmp_path / "photo^^^ls:hd=20260503^ls:fh=ab2c3d4e5f^ud:weather=sunny^^^.jpg"
    f.write_bytes(b"x")

    ops, _ = parse_set_string("ud:weather+=rainy")
    result = set_file(str(tmp_path), f.name, ops, commit=False)

    assert result["status"] == "dry-run"
    assert "ud:weather=rainy;sunny" in result["new_name"]


def test_set_file_delete(tmp_path, freeze_date):
    f = tmp_path / "photo^^^ls:hd=20260503^ls:fh=ab2c3d4e5f^ud:weather=sunny^^^.jpg"
    f.write_bytes(b"x")

    ops, _ = parse_set_string("ud:weather==")
    result = set_file(str(tmp_path), f.name, ops, commit=False)

    assert result["status"] == "dry-run"
    assert "ud:weather" not in result["new_name"]


# -- set_tags_directory ---------------------------------------------------


def test_set_tags_directory_dry_run(tmp_path, freeze_date):
    (tmp_path / "a^^^ls:hd=20260503^ls:fh=ab2c3d4e5f^^^.jpg").write_bytes(b"x")
    (tmp_path / "b^^^ls:hd=20260503^ls:fh=cd4e5f6g7h^^^.jpg").write_bytes(b"x")

    ops, _ = parse_set_string("ud:trip=london")
    results = set_tags_directory(str(tmp_path), ops, commit=False)

    assert len(results) == 2
    assert all(r["status"] == "dry-run" for r in results)
    assert all("ud:trip=london" in r["new_name"] for r in results)


def test_set_tags_directory_recursive(tmp_path, freeze_date):
    sub = tmp_path / "sub"
    sub.mkdir()
    (tmp_path / "a^^^ls:hd=20260503^ls:fh=ab2c3d4e5f^^^.jpg").write_bytes(b"x")
    (sub / "b^^^ls:hd=20260503^ls:fh=cd4e5f6g7h^^^.jpg").write_bytes(b"x")

    ops, _ = parse_set_string("ud:trip=london")
    results = set_tags_directory(str(tmp_path), ops, commit=False, recursive=True)

    assert len(results) == 2


def test_set_tags_directory_skips_hidden(tmp_path, freeze_date):
    (tmp_path / ".hidden^^^ls:hd=20260503^ls:fh=ab2c3d4e5f^^^.jpg").write_bytes(b"x")
    (tmp_path / "visible^^^ls:hd=20260503^ls:fh=cd4e5f6g7h^^^.jpg").write_bytes(b"x")

    ops, _ = parse_set_string("ud:trip=london")
    results = set_tags_directory(str(tmp_path), ops, commit=False)

    assert len(results) == 1
    assert results[0]["file"].startswith("visible")
