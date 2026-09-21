# -*- coding: utf-8 -*-
"""Answer, in seconds, whether a run can produce a publishable joint portfolio.

The 2026-09-18 run spent 106 minutes on PB-ROE and 43 on the insider pipeline
before reporting that the joint portfolio could not be built. Both reasons were
knowable up front:

  * the management export was already missing accounting_version=2, and
  * Sentiment Momentum's prices already stopped at 2026-08-19.

This checks all four legs plus their upstream inputs, names the component that
caps the joint window, and says what to re-run. It downloads nothing, sends
nothing and writes nothing.

    python preflight_data.py
    python preflight_data.py --excel-dir "D:\\Data\\ExcelData" --json

Exit codes: 0 publishable, 2 blocked.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date, datetime
from pathlib import Path

import freshness as fr

# Daily strategies must be current; PB-ROE only publishes month-end NAVs, so a
# 35-day tail is normal for it right after a month turns.
MAX_AGE_DAYS = {"PB-ROE-Momentum": 40, "NLP Sentiment - ledelse": 40,
                "Sentiment Momentum v3.1": 7, "Innsidehandel - Oslo Bors": 7}


def _latest(folder: Path, pattern: str):
    paths = [p for p in folder.glob(pattern)
             if not p.name.startswith("~$") and "BEFORE_FIX" not in p.name]
    return max(paths, key=lambda p: (p.stat().st_mtime_ns, p.name)) if paths else None


def _last_excel_date(path: Path, sheet, column: str):
    try:
        import pandas as pd
    except ImportError:
        return None, "pandas not installed; date not read"
    try:
        frame = pd.read_excel(path, sheet_name=sheet)
        if column not in frame.columns:
            return None, f"missing value column {column!r}"
        values = pd.to_numeric(frame[column], errors="coerce")
        dates = pd.to_datetime(frame.loc[values.gt(0) & values.lt(float("inf")), "Date"], errors="coerce").dropna()
        if dates.empty:
            return None, "no dated, finite positive portfolio values"
        return dates.max().date(), ""
    except Exception as exc:  # noqa: BLE001 - reported, never raised
        return None, f"{type(exc).__name__}: {exc}"


def _insider_last_date(insider_dir: Path):
    folder = insider_dir if insider_dir.name == "6_backtest" else insider_dir / "6_backtest"
    selection = folder / "selected_variant.json"
    equity = folder / "strategi_equity.csv"
    if not selection.exists():
        return None, None, f"missing {selection}"
    if not equity.exists():
        return None, None, f"missing {equity}"
    try:
        variant = json.loads(selection.read_text(encoding="utf-8"))["Variant"]
        with equity.open(encoding="utf-8-sig", newline="") as handle:
            rows = [r["Dato"] for r in csv.DictReader(handle) if r["Strategi"] == variant]
        if not rows:
            return variant, None, f"no equity rows for variant {variant}"
        return variant, fr.to_date(max(rows)), ""
    except Exception as exc:  # noqa: BLE001
        return None, None, f"{type(exc).__name__}: {exc}"


def _management_gates(path):
    """Read the two publication gates without failing when pandas is absent."""
    if path is None:
        return ["management export not found"]
    try:
        import pandas as pd
    except ImportError:
        return ["pandas not installed; accounting_version/data_valid not read"]
    try:
        metrics = pd.read_excel(path, sheet_name="Metrics").iloc[0].to_dict()
    except Exception as exc:  # noqa: BLE001
        return [f"Metrics sheet unreadable: {type(exc).__name__}: {exc}"]
    problems = []
    version = metrics.get("accounting_version", 0)
    if pd.isna(version) or float(version) < 2:
        problems.append("accounting_version < 2 (export predates the valuation fix)")
    valid = str(metrics.get("data_valid", "")).strip().lower()
    if valid not in ("true", "1", "1.0", "ja", "yes", "ok"):
        problems.append("data_valid not set (price-quality issues unresolved)")
    return problems


def _price_issue_summary(folder: Path):
    """Report unresolved prices; a power-of-ten ratio is not proof of error."""
    path = folder / "management_price_issues.csv"
    if not path.exists():
        return None
    repaired, blocked = set(), set()
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            ticker = row.get("ticker", "")
            resolution = row.get("resolution", "")
            # Automatic rescaling is not independently verified. Only a
            # verified source correction is accepted as resolved.
            (repaired if resolution == "verified_source_correction" else blocked).add(ticker)
    return {"path": str(path), "repairable": sorted(repaired), "blocked": sorted(blocked)}


def collect(excel_dir: Path, insider_dir: Path, as_of: date):
    legs, notes = [], []

    specs = [("PB-ROE-Momentum", excel_dir / "DataPB_ROE" / "Backtest",
              "BT_v3_Enhanced_*.xlsx", "Equity_Curve", "Strategy_v3"),
             ("NLP Sentiment - ledelse", excel_dir / "StrategyResults_v4_Sentiment",
              "Sentiment_v6_Hendelse_SMA*.xlsx", "Equity_Curve", "Strategy"),
             ("Sentiment Momentum v3.1", excel_dir / "DataNLP" / "BacktestResults",
              "S5_SentMom31_Portfolio_*.xlsx", 0, "Portfolio_Value")]
    management_path = None
    for name, folder, pattern, sheet, column in specs:
        path = _latest(folder, pattern) if folder.is_dir() else None
        if name.startswith("NLP"):
            management_path = path
        if path is None:
            legs.append({"name": name, "last": None, "file": None,
                         "problems": [f"no {pattern} in {folder}"]})
            continue
        last, problem = _last_excel_date(path, sheet, column)
        legs.append({"name": name, "last": last, "file": str(path),
                     "problems": [problem] if problem else []})

    variant, last, problem = _insider_last_date(insider_dir)
    legs.append({"name": "Innsidehandel - Oslo Bors", "last": last,
                 "file": str(insider_dir), "variant": variant,
                 "problems": [problem] if problem else []})

    for leg in legs:
        if leg["name"].startswith("NLP"):
            leg["problems"].extend(_management_gates(management_path))

    # Upstream inputs produced by data_acquisition.py.
    for label, folder, pattern in [
            ("OSEBX ticker workbook", excel_dir / "Data_BT", "AllTickers_OSEBX_TW_*.xlsx"),
            ("Shared sentiment changes", excel_dir / "DataNLP", "Step4_Sentiment_Changes_*.xlsx"),
            ("Upstream stock prices", excel_dir / "Data_BT1" / "FinancialData", "Stock_Prices_*.xlsx")]:
        path = _latest(folder, pattern) if folder.is_dir() else None
        if path is None:
            notes.append(f"{label}: MISSING - no {pattern} in {folder}")
            continue
        age = (as_of - datetime.fromtimestamp(path.stat().st_mtime).date()).days
        notes.append(f"{label}: {path.name}, file written {age} days ago"
                     + (" - refresh this before expecting a current result." if age > 7 else ""))
    return legs, notes


def evaluate(legs, as_of: date):
    checks, coverages, blocking = [], [], []
    for leg in legs:
        name = leg["name"]
        for problem in leg["problems"]:
            blocking.append(f"{name}: {problem}")
        check = fr.assess(name, leg["last"], as_of, max_age_days=MAX_AGE_DAYS.get(name, 7))
        checks.append(check)
        if not check.ok:
            blocking.append(check.message)
        if check.last_observation is not None and check.last_observation <= as_of:
            coverages.append(fr.month_end_coverage(name, check.last_observation, as_of))
    return checks, coverages, blocking


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--excel-dir")
    parser.add_argument("--insider-dir")
    parser.add_argument("--as-of")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    from runtime_config import data_root
    excel_dir = Path(args.excel_dir).expanduser() if args.excel_dir else data_root()
    insider_dir = (Path(args.insider_dir).expanduser() if args.insider_dir
                   else Path(__file__).resolve().parent / "data")
    as_of = fr.to_date(args.as_of) if args.as_of else date.today()

    legs, notes = collect(excel_dir, insider_dir, as_of)
    checks, coverages, blocking = evaluate(legs, as_of)
    window = fr.joint_window(coverages)
    issues = _price_issue_summary(excel_dir / "StrategyResults_v5_Sentiment_Exit")
    if issues and issues["blocked"]:
        blocking.append("Unresolved management price anomalies: " + ", ".join(issues["blocked"]))
    if len(coverages) != 4:
        blocking.append("All four strategies must have a valid observed date.")

    payload = {"as_of": str(as_of), "excel_dir": str(excel_dir),
               "insider_dir": str(insider_dir),
               "legs": [{"name": c.name, "last_observation": str(c.last_observation),
                         "age_days": c.age_days, "status": c.status} for c in checks],
               "coverage": [c.message for c in coverages],
               "blocking": blocking, "upstream": notes,
               "price_issues": issues, **{k: str(v) for k, v in window.items()}}

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 2 if blocking else 0

    print(f"Preflight - {as_of}")
    print(f"  ExcelData : {excel_dir}")
    print(f"  Insider   : {insider_dir}\n")
    print("Legs")
    for check in checks:
        mark = "ok  " if check.ok else "STOP"
        # check.message already starts with the leg name.
        print(f"  [{mark}] {check.message}")
    print("\nMonth-end coverage")
    for coverage in coverages:
        print(f"  {coverage.message}")
    print(f"\n  {window['explanation']}")
    if issues:
        print(f"\nManagement price issues ({issues['path']})")
        print(f"  verified corrections        : {', '.join(issues['repairable']) or 'none'}")
        print(f"  need manual verification    : {', '.join(issues['blocked']) or 'none'}")
    print("\nUpstream inputs (produced by data_acquisition.py)")
    for note in notes:
        print(f"  {note}")
    if blocking:
        print("\nBLOCKED - a joint portfolio cannot be published:")
        for item in blocking:
            print(f"  - {item}")
        print("\nNext steps:")
        print("  1. Refresh any upstream file flagged above, then re-run its strategy.")
        print("  2. Management: python run_strategy.py --strategy management")
        print("     Verify unresolved source-price anomalies before publishing.")
        print("  3. Re-run preflight. Only when it reports OK will master.py reach")
        print("     exit code 0.")
        return 2
    print("\nOK - all four legs are current and a joint portfolio can be built.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
