# -*- coding: utf-8 -*-
"""Apply the 2026-09-18 management price-repair patch to Only_260820.py.

The patch replaces the all-or-nothing abort in `hent_kurser` (inside
SentimentHendelseLab) with a classified repair step. It is:

  * exact      - it refuses to run unless the original block is found verbatim;
  * idempotent - a second run reports "already applied" and changes nothing;
  * verified   - it re-parses the file and re-checks the protected function
                 hashes for PBROE_All3 and SentimentMomentumV31 before saving;
  * reversible - the original is kept as Only_260820.py.bak-<timestamp>.

Line endings are preserved: Only_260820.py is predominantly CRLF.

    python 2026-09-18/apply_patch.py            # apply
    python 2026-09-18/apply_patch.py --check    # report status only
    python 2026-09-18/apply_patch.py --revert   # restore newest backup
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "Only_260820.py"
HASHES = ROOT / "protected_strategy_hashes.json"
MARKER = "price_repair import repair_price_frames"

ORIGINAL = [
    '        issues = kontroller_priser(close)',
    '        issues.to_csv(config.ut_dir / "management_price_issues.csv", index=False)',
    '        if not issues.empty:',
    '            examples = ", ".join(issues["ticker"].drop_duplicates().head(8))',
    '            raise RuntimeError(',
    '                "Management prices require verification after provider repair: "',
    '                + examples + ". See management_price_issues.csv. No backtest or variant "',
    '                "is published from these prices; prices were not clipped or guessed.")',
]

REPLACEMENT = [
    '        # 2026-09-18 correction. kontroller_priser flags every 4x step between two',
    '        # observations and this call used to abort the entire management run on any',
    '        # of them. A step that is an exact power of ten (BSP.OL: 0.101440 ->',
    '        # 10.144007, ratio 100.000) is a provider denomination artifact, provable',
    '        # from the data alone. Those are rescaled BACKWARDS - the most recent',
    '        # prices, which live positions are marked against, are never modified -',
    '        # and every change is written to management_price_issues.csv. Every other',
    '        # flagged observation still blocks publication. Nothing is clipped,',
    '        # interpolated or guessed. Logic and tests: 2026-09-18/price_repair.py.',
    '        import sys as _sys',
    '        from pathlib import Path as _Path',
    '        _fix_dir = _Path(__file__).resolve().parent / "2026-09-18"',
    '        if _fix_dir.is_dir() and str(_fix_dir) not in _sys.path:',
    '            _sys.path.insert(0, str(_fix_dir))',
    '        from price_repair import repair_price_frames, blocked_tickers, summary',
    '        close, high, low, _repair_results, _issue_rows = repair_price_frames(',
    '            close, high, low, logger=log)',
    '        issues = pd.DataFrame(_issue_rows, columns=[',
    '            "ticker", "date", "issue", "previous_date", "previous_price",',
    '            "price", "ratio", "applied_factor", "resolution"])',
    '        issues.to_csv(config.ut_dir / "management_price_issues.csv", index=False)',
    '        log.info("Kurser   : prisrevisjon %s", summary(_repair_results.values()))',
    '        _blocked = blocked_tickers(_repair_results.values())',
    '        if _blocked:',
    '            raise RuntimeError(',
    '                "Management prices require verification after provider repair: "',
    '                + ", ".join(_blocked[:8]) + ". See management_price_issues.csv. "',
    '                "Power-of-ten unit artifacts were repaired and logged; these remaining "',
    '                "discontinuities are not provably unit errors, so no backtest or "',
    '                "variant is published from them. Prices were not clipped or guessed.")',
    '        # The repaired series actually used, kept beside the raw download.',
    '        close.to_csv(config.ut_dir / "management_prices_close_repaired.csv",',
    '                     index_label="Date")',
]


def _read(path: Path) -> str:
    """Read without newline translation, so CRLF survives a round trip."""
    with path.open(encoding="utf-8", newline="") as handle:
        return handle.read()


def _write(path: Path, text: str) -> None:
    """Write verbatim: the newlines already in `text` are the ones stored."""
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text)


def _locate(text: str):
    """Find the original block and the newline convention used AT THE MATCH.

    Only_260820.py has mixed line endings - 12373 CRLF lines and 150 bare LF,
    and this particular block is one of the LF regions. A file-wide heuristic
    picks CRLF and then fails to match. Trying both separators and requiring
    exactly one hit keeps the replacement byte-identical to its surroundings.
    """
    for newline in ("\r\n", "\n"):
        needle = newline.join(ORIGINAL)
        if text.count(needle) == 1:
            return needle, newline
    return None, None


def protected_hashes(text: str) -> dict:
    expected = json.loads(HASHES.read_text(encoding="utf-8"))
    actual = {}
    lines = text.splitlines()
    for node in ast.parse(text).body:
        if isinstance(node, ast.FunctionDef) and node.name in expected:
            body = "\n".join(lines[node.lineno - 1:node.end_lineno])
            actual[node.name] = hashlib.sha256(body.encode()).hexdigest()
    return expected, actual


def status(text: str) -> str:
    if MARKER in text:
        return "applied"
    needle, _ = _locate(text)
    return "unpatched" if needle else "unknown"


def apply(check_only: bool = False) -> int:
    if not TARGET.exists():
        print(f"ERROR: {TARGET} not found.")
        return 1
    # newline="" keeps CRLF intact; read_text() would translate it away and
    # rewrite every line ending in the file on save. Path.read_text() only
    # accepts newline= on Python 3.13+, so open() is used instead (target: 3.12).
    text = _read(TARGET)
    state = status(text)
    if state == "applied":
        print("Already applied - no change made.")
        return 0
    if state == "unknown":
        print("ERROR: the original guard block was not found verbatim in "
              f"{TARGET.name}. The file differs from the version this patch was "
              "written against; refusing to edit it. Nothing was changed.")
        return 1
    if check_only:
        print("Not yet applied. The original block was found exactly once.")
        return 0

    needle, newline = _locate(text)
    patched = text.replace(needle, newline.join(REPLACEMENT), 1)

    try:
        ast.parse(patched)
    except SyntaxError as exc:
        print(f"ERROR: patched file does not parse ({exc}). Nothing was changed.")
        return 1

    expected, actual = protected_hashes(patched)
    for name, digest in expected.items():
        if actual.get(name) != digest:
            print(f"ERROR: protected function {name} changed. Nothing was changed.")
            return 1

    backup_dir = Path(__file__).resolve().parent / "backup"
    backup_dir.mkdir(exist_ok=True)
    backup = backup_dir / f"Only_260820.py.bak-{datetime.now():%Y%m%d_%H%M%S}"
    _write(backup, text)
    _write(TARGET, patched)
    print(f"Applied. Backup: {backup.name}")
    print(f"Protected hashes verified unchanged: {', '.join(sorted(expected))}")
    return 0


def revert() -> int:
    backups = sorted((Path(__file__).resolve().parent / "backup")
                     .glob("Only_260820.py.bak-*"))
    if not backups:
        print("No backup found.")
        return 1
    newest = backups[-1]
    _write(TARGET, _read(newest))
    print(f"Reverted from {newest.name}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="report status, change nothing")
    parser.add_argument("--revert", action="store_true", help="restore the newest backup")
    args = parser.parse_args(argv)
    if args.revert:
        return revert()
    return apply(check_only=args.check)


if __name__ == "__main__":
    sys.exit(main())
