# -*- coding: utf-8 -*-
"""Apply the 2026-09-18 patches to Only_260820.py and master.py.

The edits themselves live in patches.json, one entry per block, so they can be
read and reviewed without reading this file.

  Only_260820.py  the management price guard now repairs provable power-of-ten
                  unit artifacts and blocks only what it cannot prove.
  master.py       the master now BUILDS the three upstream workbooks it used to
                  merely check for, instead of aborting when a separate program
                  had not been run.

Every patch is:

  * exact      - it refuses to run unless the original block is found verbatim;
  * idempotent - each patch carries a marker, so re-running changes nothing;
  * verified   - each file is re-parsed and the protected function hashes for
                 PBROE_All3 and SentimentMomentumV31 are re-checked before
                 anything is saved;
  * atomic     - a file is written only if every patch for it succeeded;
  * reversible - originals go to 2026-09-18/backup/.

Line endings are preserved. Only_260820.py mixes 12373 CRLF lines with 150 bare
LF ones, so the convention is taken from the match site, not from the file.

    python 2026-09-18/apply_patch.py            # apply
    python 2026-09-18/apply_patch.py --check    # report status only
    python 2026-09-18/apply_patch.py --revert   # restore newest backups
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BACKUP = HERE / "backup"
HASHES = ROOT / "protected_strategy_hashes.json"
PATCHES = HERE / "patches.json"


def _read(path: Path) -> str:
    """Read without newline translation, so CRLF survives a round trip."""
    with path.open(encoding="utf-8", newline="") as handle:
        return handle.read()


def _write(path: Path, text: str) -> None:
    """Write verbatim: the newlines already in `text` are the ones stored."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text)


def _locate(text: str, original):
    """Find the block and the newline convention used AT THE MATCH.

    A file-wide heuristic picks CRLF for Only_260820.py and then fails on the
    blocks that happen to be LF. Trying both and requiring exactly one hit keeps
    the replacement byte-identical to its surroundings.
    """
    for newline in ("\r\n", "\n"):
        needle = newline.join(original)
        if text.count(needle) == 1:
            return needle, newline
    return None, None


def protected_hashes(text: str):
    expected = json.loads(HASHES.read_text(encoding="utf-8"))
    actual, lines = {}, text.splitlines()
    for node in ast.parse(text).body:
        if isinstance(node, ast.FunctionDef) and node.name in expected:
            body = "\n".join(lines[node.lineno - 1:node.end_lineno])
            actual[node.name] = hashlib.sha256(body.encode()).hexdigest()
    return expected, actual


def load_patches():
    patches = json.loads(PATCHES.read_text(encoding="utf-8"))
    grouped = {}
    for patch in patches:
        grouped.setdefault(patch["file"], []).append(patch)
    return grouped


def plan(text: str, patches):
    """Classify each patch against the current text without changing anything."""
    states = []
    for patch in patches:
        if patch["marker"] in text:
            states.append((patch, "applied"))
            continue
        needle, _ = _locate(text, patch["original"])
        states.append((patch, "ready" if needle else "unknown"))
    return states


def apply_file(filename: str, patches, check_only: bool) -> int:
    target = ROOT / filename
    if not target.exists():
        print(f"  ERROR: {filename} not found.")
        return 1
    text = _read(target)
    states = plan(text, patches)

    for patch, state in states:
        print(f"  [{state:>7}] {patch['name']}")
    if any(state == "unknown" for _, state in states):
        print(f"  ERROR: one or more original blocks were not found verbatim in "
              f"{filename}. It differs from the version these patches were written "
              f"against; refusing to edit it. Nothing was changed.")
        return 1
    todo = [patch for patch, state in states if state == "ready"]
    if not todo:
        print(f"  {filename}: already up to date.")
        return 0
    if check_only:
        print(f"  {filename}: {len(todo)} patch(es) ready to apply.")
        return 0

    patched = text
    for patch in todo:
        needle, newline = _locate(patched, patch["original"])
        if needle is None:
            print(f"  ERROR: {patch['name']} stopped matching mid-run. Nothing saved.")
            return 1
        patched = patched.replace(needle, newline.join(patch["replacement"]), 1)

    try:
        ast.parse(patched)
    except SyntaxError as exc:
        print(f"  ERROR: patched {filename} does not parse ({exc}). Nothing saved.")
        return 1

    expected, actual = protected_hashes(patched)
    for name, digest in expected.items():
        if name in actual and actual[name] != digest:
            print(f"  ERROR: protected function {name} changed. Nothing saved.")
            return 1

    BACKUP.mkdir(exist_ok=True)
    backup = BACKUP / f"{filename}.bak-{datetime.now():%Y%m%d_%H%M%S}"
    _write(backup, text)
    _write(target, patched)
    print(f"  Applied {len(todo)} patch(es). Backup: backup/{backup.name}")
    if expected and any(n in actual for n in expected):
        print(f"  Protected hashes verified unchanged: "
              f"{', '.join(sorted(n for n in expected if n in actual))}")
    return 0


def revert() -> int:
    if not BACKUP.is_dir():
        print("No backup directory.")
        return 1
    newest = {}
    for path in sorted(BACKUP.glob("*.bak-*")):
        newest[path.name.split(".bak-")[0]] = path
    if not newest:
        print("No backups found.")
        return 1
    for filename, backup in newest.items():
        _write(ROOT / filename, _read(backup))
        print(f"Reverted {filename} from backup/{backup.name}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="report status, change nothing")
    parser.add_argument("--revert", action="store_true", help="restore the newest backups")
    args = parser.parse_args(argv)
    if args.revert:
        return revert()
    failures = 0
    for filename, patches in load_patches().items():
        print(f"{filename}")
        failures += apply_file(filename, patches, args.check)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
