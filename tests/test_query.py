# ==============================================
# ls-sql -- filesystem query engine
# East Van AI -- AI for the rest of us!
# https://github.com/east-van-ai
# ==============================================

"""
tests for lssql.query -- parse_query, evaluate_predicate, run_query.
"""

from lssql.query import evaluate_predicate, parse_query, run_query

SORRY = "I'm sorry Dave, I can't run that query."


# -- parse_query --


def test_parse_query_select_star_no_where():
    result = parse_query("SELECT *")
    assert "predicate" in result
    assert result["predicate"] is None


def test_parse_query_is_not_null():
    result = parse_query("SELECT * WHERE ls:hd IS NOT NULL")
    assert result["predicate"]["op"] == "IS NOT NULL"
    assert result["predicate"]["key"] == "ls:hd"


def test_parse_query_equals():
    result = parse_query("SELECT * WHERE sd:mn='sdxl'")
    assert result["predicate"]["op"] == "="
    assert result["predicate"]["key"] == "sd:mn"
    assert result["predicate"]["value"] == "sdxl"


def test_parse_query_contains():
    result = parse_query("SELECT * WHERE ud:ingredients CONTAINS 'beef'")
    assert result["predicate"]["op"] == "CONTAINS"
    assert result["predicate"]["key"] == "ud:ingredients"
    assert result["predicate"]["value"] == "beef"


def test_parse_query_case_insensitive():
    result = parse_query("select * where ls:hd is not null")
    assert result["predicate"]["op"] == "IS NOT NULL"


def test_parse_query_missing_select_star():
    result = parse_query("SELECT filename WHERE ls:hd IS NOT NULL")
    assert "error" in result
    assert "Dave" in result["error"]


def test_parse_query_unrecognised_clause():
    result = parse_query("SELECT * WHERE ls:hd LIKE '%2024%'")
    assert "error" in result
    assert "Dave" in result["error"]


def test_parse_query_empty_string():
    result = parse_query("")
    assert "error" in result


# -- evaluate_predicate --


def make_row(tags: dict) -> dict:
    return {"tags": tags, "path": "", "filename": "photo.jpg"}


def test_evaluate_is_not_null_present():
    row = make_row({"ls:hd": "20260424"})
    assert evaluate_predicate({"op": "IS NOT NULL", "key": "ls:hd"}, row) is True


def test_evaluate_is_not_null_absent():
    row = make_row({})
    assert evaluate_predicate({"op": "IS NOT NULL", "key": "ls:hd"}, row) is False


def test_evaluate_equals_match():
    row = make_row({"sd:mn": "sdxl"})
    assert evaluate_predicate({"op": "=", "key": "sd:mn", "value": "sdxl"}, row) is True


def test_evaluate_equals_no_match():
    row = make_row({"sd:mn": "flux"})
    assert (
        evaluate_predicate({"op": "=", "key": "sd:mn", "value": "sdxl"}, row) is False
    )


def test_evaluate_contains_match():
    row = make_row({"ud:ingredients": "beef,garlic,carrot"})
    assert (
        evaluate_predicate(
            {"op": "CONTAINS", "key": "ud:ingredients", "value": "beef"}, row
        )
        is True
    )


def test_evaluate_contains_no_match():
    row = make_row({"ud:ingredients": "pork,garlic,pepper"})
    assert (
        evaluate_predicate(
            {"op": "CONTAINS", "key": "ud:ingredients", "value": "beef"}, row
        )
        is False
    )


def test_evaluate_none_predicate_always_true():
    row = make_row({})
    assert evaluate_predicate(None, row) is True  # type: ignore


# -- run_query --


def test_run_query_filters_correctly():
    rows = [
        {"tags": {"sd:mn": "sdxl"}, "path": ".", "filename": "a.png"},
        {"tags": {"sd:mn": "flux"}, "path": ".", "filename": "b.png"},
    ]
    matched, error = run_query("SELECT * WHERE sd:mn='sdxl'", rows)
    assert error is None
    assert len(matched) == 1
    assert matched[0]["filename"] == "a.png"


def test_run_query_returns_all_on_no_where():
    rows = [
        {"tags": {}, "path": ".", "filename": "a.png"},
        {"tags": {}, "path": ".", "filename": "b.png"},
    ]
    matched, error = run_query("SELECT *", rows)
    assert error is None
    assert len(matched) == 2


def test_run_query_returns_error_on_bad_query():
    matched, error = run_query("GET * FROM files", [])
    assert error is not None
    assert "Dave" in error
    assert matched == []
