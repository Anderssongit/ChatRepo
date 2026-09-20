# -*- coding: utf-8 -*-
"""Svar på sekunder: hva blokkerer en publiserbar samlet portefølje akkurat nå?

Kjøringen 2026-09-18 brukte 106 minutter på PB-ROE og 43 på innsidepipelinen før
den meldte at den samlede porteføljen ikke kunne bygges. Begge grunnene var
kjente på forhånd:

  * ledelseseksporten manglet allerede accounting_version=2, og
  * Sentiment Momentums kurser sluttet allerede 2026-08-19.

Denne bruker NØYAKTIG samme vurdering som datastatusblokken i mailen — samme
`data_status.hent` — så preflight og mail kan ikke være uenige om hva som er
ferskt. Den laster ikke ned noe, sender ingenting og skriver ingen filer.

    python 2026-09-20/preflight_data.py
    python 2026-09-20/preflight_data.py --excel-dir "D:\\Data\\ExcelData" --json

Sluttkoder: 0 alt er ferskt, 2 noe er utelatt eller blokkert.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for _sti in (str(HERE), str(ROOT)):
    if _sti not in sys.path:
        sys.path.insert(0, _sti)

import data_status as ds


def standard_excel_dir() -> Path:
    try:
        from runtime_config import data_root
        return Path(data_root())
    except Exception:                                  # noqa: BLE001
        return ROOT / "ExcelData"


def _line(row) -> str:
    alder = row.get("Alder_Dager")
    alder = "—" if alder is None else f"{int(alder)}d"
    return (f"  {str(row.get('Status')):9} {str(row.get('Strategi')):26} "
            f"siste {str(row.get('Siste') or '—'):12} {alder:>5}   "
            f"{row.get('Begrunnelse')}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="preflight_data",
        description="Sjekk alle fire strategier og grunnlagsfilene deres uten "
                    "å laste ned, beregne eller sende noe.")
    parser.add_argument("--excel-dir", metavar="STI")
    parser.add_argument("--mappe", metavar="STI", help="innsidedatamappen")
    parser.add_argument("--json", action="store_true", help="maskinlesbar utskrift")
    args = parser.parse_args(list(argv) if argv is not None else None)

    excel_dir = Path(args.excel_dir).expanduser() if args.excel_dir else standard_excel_dir()
    insider_dir = Path(args.mappe).expanduser() if args.mappe else ROOT / "data"

    status = ds.hent(excel_dir, insider_dir, as_of=date.today())
    if args.json:
        print(json.dumps({k: v for k, v in status.items() if k != "curves"},
                         ensure_ascii=False, indent=2, default=str))
        return 0 if status.get("all_ok") else 2

    print(f"ExcelData   : {excel_dir}")
    print(f"Innsidedata : {insider_dir}")
    print(f"Rapportdato : {status.get('as_of')}\n")
    for row in status.get("rows", ()):
        print(_line(row))
    print("\n" + (status.get("summary") or ""))
    if not status.get("all_ok"):
        print("\nSlik retter du det:")
        print("  • foreldede kurser/tickerliste : RUN.cmd --tving-datahent")
        print("  • manglende Step4              : kjør uten --ingen-nlp-hent, "
              "slik at artikkelskrapingen kjører først")
        print("  • ledelseseksport avvist       : se "
              "ExcelData/StrategyResults_v5_Sentiment_Exit/"
              "management_price_issues.csv")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
