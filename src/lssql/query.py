import re

SORRY = "I'm sorry Dave, I can't run that query."


def parse_query(query: str) -> dict:
    """
    parse a query string into a structured dict.
    supports:
        SELECT * WHERE key = 'value'
        SELECT * WHERE key IS NOT NULL
        SELECT * WHERE key CONTAINS 'value'

    returns a dict with 'predicate' on success.
    returns a dict with 'error' on failure.
    """
    query = query.strip()

    # must start with SELECT *
    if not re.match(r"(?i)^select\s+\*", query):
        return {"error": f"{SORRY}\n  expected: SELECT * WHERE ..."}

    # no WHERE clause -- return everything
    where_match = re.search(r"(?i)\bwhere\b(.+)$", query)
    if not where_match:
        return {"predicate": None}

    clause = where_match.group(1).strip()

    # IS NOT NULL
    m = re.match(r"^([\w:]+)\s+IS\s+NOT\s+NULL$", clause, re.IGNORECASE)
    if m:
        return {"predicate": {"op": "IS NOT NULL", "key": m.group(1)}}

    # = 'value'
    m = re.match(r"^([\w:]+)\s*=\s*'([^']*)'$", clause, re.IGNORECASE)
    if m:
        return {"predicate": {"op": "=", "key": m.group(1), "value": m.group(2)}}

    # CONTAINS 'value'
    m = re.match(r"^([\w:]+)\s+CONTAINS\s+'([^']*)'$", clause, re.IGNORECASE)
    if m:
        return {"predicate": {"op": "CONTAINS", "key": m.group(1), "value": m.group(2)}}

    return {"error": f"{SORRY}\n  unrecognised clause: {clause}"}


def evaluate_predicate(predicate: dict, row: dict) -> bool:
    """
    evaluate a single predicate against a parsed file row.
    row is a dict from parse_filename -- has 'tags', 'original', 'comment', etc.
    """
    if predicate is None:
        return True

    op = predicate["op"]
    key = predicate["key"]
    tags = row.get("tags", {})

    if op == "IS NOT NULL":
        return key in tags

    value = predicate.get("value", "")

    if op == "=":
        return tags.get(key) == value

    if op == "CONTAINS":
        tag_value = tags.get(key, "")
        return value in tag_value

    return False


def run_query(query: str, rows: list[dict]) -> tuple[list[dict], str | None]:
    """
    parse and run a query against a list of parsed file rows.
    returns (matching_rows, error_string).
    error_string is None on success.
    """
    parsed = parse_query(query)

    if "error" in parsed:
        return [], parsed["error"]

    predicate = parsed["predicate"]
    matched = [row for row in rows if evaluate_predicate(predicate, row)]
    return matched, None
