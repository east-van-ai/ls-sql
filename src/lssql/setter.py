# ==============================================
# ls-sql -- filesystem query engine
# East Van AI -- AI for the rest of us!
# https://github.com/east-van-ai
# ==============================================

"""
--set mode -- write user-defined tags directly into filenames.

operators:
    ud:key=value     overwrite -- replaces existing value
    ud:key=          no-op -- empty value, skip
    ud:key+=value    append -- adds value, semicolon-separated
    ud:key+=         no-op -- empty value, skip
    ud:key-=value    remove -- removes value from existing if present
    ud:key-=         no-op -- empty value, skip
    ud:key==         delete -- removes tag entirely
    ud:key==value    no-op -- value present after ==, skip

protected:
    any 2-letter namespace except ud: is rejected -- stop and error.
    ls:fh and friends are managed by harvesters, not by hand.
"""

import os

from lssql.harvester import harvest_file
from lssql.harvester_util import SEPARATOR, is_already_harvested
from lssql.parser import parse_filename, should_skip

# -- validation -----------------------------------------------------------


def is_protected_namespace(key: str) -> bool:
    """
    2-letter namespaces are reserved for ls-sql built-in harvesters.
    ud: is the one 2-letter namespace users are allowed to write.
    """
    namespace = key.split(":")[0]
    return len(namespace) == 2 and namespace != "ud"


def parse_set_string(tag_string: str) -> tuple[list[dict], str | None]:
    """
    parse and validate a caret-separated operator string.
    returns (operations, error) -- error is None on success.

    each operation is a dict:
        {'op': '=',     'key': 'ud:fruit',      'values': {'banana'}}
        {'op': '+=',    'key': 'ud:weather',    'values': {'rainy'}}
        {'op': '-=',    'key': 'ud:weather',    'values': {'rainy']}
        {'op': '==',    'key': 'ud:old',        'values': {''}}
    """
    if not tag_string or not tag_string.strip():
        return [], "error: empty --set string"

    ops = []

    for part in tag_string.split("^"):
        part = part.strip()
        if not part:
            continue

        # detect operator -- order matters: check == before =
        if "==" in part:
            key, value = part.split("==", 1)
            op = "=="
        elif "+=" in part:
            key, value = part.split("+=", 1)
            op = "+="
        elif "-=" in part:
            key, value = part.split("-=", 1)
            op = "-="
        elif "=" in part:
            key, value = part.split("=", 1)
            op = "="
        else:
            return [], f"error: malformed --set expression: '{part}'"

        key = key.strip()
        value = value.strip()

        if not key:
            return [], f"error: malformed --set expression: '{part}'"

        if ":" not in key:
            return [], f"error: missing namespace in key: '{key}' -- use ud:key=value"

        if is_protected_namespace(key):
            namespace = key.split(":")[0]
            return [], (
                f"error: '{key}' -- '{namespace}:' is a reserved namespace. "
                f"use ud: or 3-letter+ namespaces."
            )

        values = {v.strip() for v in value.split(";")}  # SEMICOLON
        ops.append({"op": op, "key": key, "values": values})

    if not ops:
        return [], "error: no valid operations in --set string"

    return ops, None


# -- tag manipulation -----------------------------------------------------


def apply_operations(tags: dict, ops: list[dict]) -> dict:
    """
    apply a list of operations to an existing tags dict.
    returns updated tags dict.

    no-ops are silently skipped:
        =   with empty value
        +=  with empty value
        -=  with empty value
        ==  with non-empty value
    """
    result = dict(tags)

    for op_dict in ops:
        op = op_dict["op"]
        key = op_dict["key"]
        values = op_dict["values"]

        if op == "=":
            if not values or values == {""}:
                continue  # no-op
            result[key] = ";".join(sorted(values))

        elif op == "+=":
            if not values or values == {""}:
                continue  # no-op
            existing = result.get(key, "")
            existing_set = set(existing.split(";")) if existing else set()
            existing_set.update(values)
            result[key] = ";".join(sorted(existing_set))

        elif op == "-=":
            if not values or values == {""}:
                continue  # no-op
            existing = result.get(key, "")
            if not existing:
                continue
            existing_set = set(existing.split(";"))
            existing_set.difference_update(values)
            if existing_set:
                result[key] = ";".join(sorted(existing_set))
            else:
                del result[key]  # last value removed -- delete tag

        elif op == "==":
            if values and values != {""}:
                continue  # no-op -- value present after ==
            if key in result:
                del result[key]

    return result


def rebuild_filename(parsed: dict, updated_tags: dict) -> str:
    """
    reconstruct filename from parsed components and updated tags dict.
    """
    original = parsed["original"]
    comment = parsed["comment"]
    ext = parsed["ext"]

    tag_parts = [f"{k}={v}" for k, v in updated_tags.items()]
    tags_str = "^".join(tag_parts)

    if comment:
        return f"{original}{SEPARATOR}{tags_str}{SEPARATOR}{comment}{ext}"
    elif tags_str:
        return f"{original}{SEPARATOR}{tags_str}{SEPARATOR}{ext}"
    return f"{original}{ext}"


# -- file operations ------------------------------------------------------


def set_file(
    directory: str,
    filename: str,
    ops: list[dict],
    commit: bool,
) -> dict:
    """
    apply tag operations to a single file.
    harvest-first if not yet harvested.
    returns a result dict -- same shape as harvest_file results.
    """
    # harvest-first -- silent and automatic
    if not is_already_harvested(filename):
        harvest_result = harvest_file(directory, filename, commit=commit)
        if harvest_result["status"] == "skipped":
            return {
                "directory": directory,
                "file": filename,
                "status": "skipped",
                "reason": harvest_result["reason"],
            }
        filename = harvest_result["new_name"]

    parsed = parse_filename(filename)
    parsed["path"] = directory

    updated_tags = apply_operations(parsed["tags"], ops)

    new_filename = rebuild_filename(parsed, updated_tags)

    if new_filename == filename:
        return {
            "directory": directory,
            "file": filename,
            "status": "skipped",
            "reason": "no change",
        }

    old_path = os.path.join(directory, filename)
    new_path = os.path.join(directory, new_filename)

    if commit:
        os.rename(old_path, new_path)
        return {
            "directory": directory,
            "file": filename,
            "status": "updated",
            "new_name": new_filename,
        }
    else:
        return {
            "directory": directory,
            "file": filename,
            "status": "dry-run",
            "new_name": new_filename,
        }


def set_tags_directory(
    path: str,
    ops: list[dict],
    commit: bool,
    recursive: bool = False,
) -> list[dict]:
    """
    apply tag operations to all files in a directory.
    harvest-first per file if not yet harvested.
    """
    results = []

    with os.scandir(path) as entries:
        for entry in entries:
            if entry.is_dir(follow_symlinks=False):
                if recursive:
                    results.extend(
                        set_tags_directory(entry.path, ops, commit, recursive)
                    )
                continue

            if not entry.is_file():
                continue

            filename = entry.name

            if should_skip(filename):
                continue

            results.append(set_file(path, filename, ops, commit))

    results.sort(key=lambda d: (d["directory"], d["file"]))
    return results
