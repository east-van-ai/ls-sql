# ==============================================
# East Van AI -- AI for the rest of us!
# https://github.com/east-van-ai
# contact: east-van-ai@proton.me
# ==============================================
#
# lssql.cli_util - shared plumbing for the cli_<command> modules.
#
# Target dispatch and the rename-preview printer. Everything here is
# used by more than one command; anything used by exactly one lives
# with that command.
#
# License: MIT
# ==============================================

import os

from lssql.parser import should_skip

# rename-preview status column, as wide as the longest status word ("restored")
STATUS_WIDTH = 8


def resolve(target: str, on_file, on_directory) -> list:
    """
    dispatch a file-or-directory target to the matching operation.
    on_file(directory, filename) is called only when target is a file and
    not should_skip; on_directory(target) handles the directory case.
    """
    if os.path.isfile(target):
        directory = os.path.dirname(target) or "."
        filename = os.path.basename(target) or ""
        return [] if should_skip(filename) else [on_file(directory, filename)]
    return on_directory(target)


def print_rename_results(
    results: list,
    recursive: bool = False,
    verbose: bool = False,
    commit: bool = False,
) -> None:
    """
    print the shared rename-preview block for harvest, set, and reset.

    One line per actioned file, an arrow line carrying the new name, and a
    skipped line under --verbose. Then the summary tail and, unless --commit
    was passed, the reminder that nothing on disk moved.

    The status word is right-aligned in a STATUS_WIDTH field so the ` : `
    column lines up down the whole block and across every mode.

    Anything that is not "skipped" counts as actioned. The rename modes emit
    renamed, restored, updated, dry-run, and skipped; ok and changed belong to
    verify, which prints its own shape.

    See DESIGN.md, "Rename previews".
    """
    for r in results:
        status = r["status"]
        directory = f"{r['directory']}/" if recursive else ""
        if status == "skipped":
            if verbose:
                print(
                    f"  {'skipped':>{STATUS_WIDTH}} : "
                    f"{directory}{r['file']}  ({r['reason']})"
                )
            continue
        print(f"  {status:>{STATUS_WIDTH}} : {directory}{r['file']}")
        print(f"  {'->':>{STATUS_WIDTH}} : {directory}{r['new_name']}")

    actioned = sum(1 for r in results if r["status"] != "skipped")
    skipped = sum(1 for r in results if r["status"] == "skipped")

    mode_label = "committed" if commit else "dry-run"
    print(f"\n{actioned} file(s) {mode_label}, {skipped} skipped")

    if not commit:
        print("  (no files changed -- pass --commit to execute)")
