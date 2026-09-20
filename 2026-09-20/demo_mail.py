# -*- coding: utf-8 -*-
"""Rendre en DEMONSTRASJONSMAIL av oppdiktede tall, for å se på utformingen.

Hele poenget er å kunne se hvordan mailen ser ut — særlig datastatusblokken
øverst — uten å vente på en kjøring på halvannen time og uten å sende noe.

    python 2026-09-20/demo_mail.py                 tre av fire har ferske data
    python 2026-09-20/demo_mail.py --alle-ok       alle fire har ferske data
    python 2026-09-20/demo_mail.py --ut demo.html  skriv til en bestemt fil

ALLE TALL I DENNE FILA ER OPPDIKTET. Den leser ingen ExcelData, henter
ingenting og sender ingenting. Mailen den lager er merket som demonstrasjon i
selve HTML-en, slik at den ikke kan forveksles med et resultat.
"""
from __future__ import annotations

import argparse
import calendar
import sys
import types
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for _sti in (str(HERE), str(ROOT)):
    if _sti not in sys.path:
        sys.path.insert(0, _sti)

import patched_import                                               # noqa: E402

MERKE = ('<div style="background:#c62828;color:#fff;padding:12px 16px;'
         'font-weight:700;letter-spacing:.3px">DEMONSTRASJON — alle tall i '
         'denne mailen er oppdiktet. Ingen data er hentet, og ingen strategi '
         'er kjørt.</div>')


class DemoMaster:
    """Akkurat de feltene capital_mail rører."""

    excel_dir = Path("ExcelData")
    innside_dir = Path("data")
    startkapital = 1_000_000.0

    def oppsett(self):
        return types.SimpleNamespace(risikofri_pst=3.0)

    def insider_oppsett(self):
        return self.oppsett()


def manedsslutter(antall, slutt: date, start_verdi=100.0, vekst=1.012):
    """`antall` fortløpende månedsslutter som ender i måneden til `slutt`.

    Slik PB-ROE eksporterer: én verdi per fullført måned.
    """
    punkter, verdi = [], start_verdi
    year, month = slutt.year, slutt.month
    for n in range(antall - 1, -1, -1):
        y, m = divmod((month - 1) - n, 12)
        y, m = year + y, m + 1
        punkter.append((f"{y:04d}-{m:02d}-{calendar.monthrange(y, m)[1]:02d}", verdi))
        verdi *= vekst
    return punkter


def borsdager(fra: date, til: date, start_verdi=100.0, vekst=1.0006):
    """Daglig NAV på børsdager, slik de tre daglige strategiene eksporterer."""
    punkter, verdi, dag = [], start_verdi, fra
    while dag <= til:
        if dag.weekday() < 5:
            punkter.append((str(dag), verdi))
            verdi *= vekst
        dag += timedelta(days=1)
    return punkter


def demodata(i_dag: date, alle_ok: bool):
    import data_status as ds

    i_gar = i_dag - timedelta(days=1)
    forrige_manedsslutt = date(i_dag.year, i_dag.month, 1) - timedelta(days=1)
    fra = date(i_dag.year - 1, i_dag.month, 1)

    # PB-ROE eksporterer månedlig, de tre andre daglig. Det er nettopp derfor
    # fellesperioden er månedlig og ferskhetsgrensene er ulike.
    kurver = [{"name": "PB-ROE-Momentum", "frequency": "monthly",
               "observations": manedsslutter(14, forrige_manedsslutt, vekst=1.019)},
              {"name": "NLP Sentiment — ledelse", "frequency": "daily",
               "observations": borsdager(fra, i_gar, vekst=1.0004)},
              {"name": "Sentiment Momentum v3.1", "frequency": "daily",
               "observations": borsdager(fra, i_gar, vekst=1.0006)},
              {"name": "Innsidehandel — Oslo Børs", "frequency": "daily",
               "observations": borsdager(fra, i_gar, vekst=1.0009)}]
    if not alle_ok:
        # Nøyaktig feilen fra 2026-09-18: kursene stopper en måned for tidlig,
        # strategien kjører likevel uten å feile, og august faller ut i stillhet.
        stopp = i_gar - timedelta(days=32)
        kurver[2]["observations"] = borsdager(fra, stopp, vekst=1.0006)
    for kurve in kurver:
        kurve.update(valid=True, errors=[],
                     source={"path": f"ExcelData/DEMO/{kurve['name']}.xlsx",
                             "sheet": None, "mtime_ns": 1, "size": 1})

    siste_kurs = str(i_gar) if alle_ok else str(i_gar - timedelta(days=32))
    henting = [
        {"Kilde": "Aksjeliste", "Handling": "OK", "Merknad": "231 selskaper",
         "Rader": 231, "Siste": None},
        {"Kilde": "PB-ROE tickerliste", "Handling": "SKREVET",
         "Merknad": "231 tickere; skrevet som AllTickers_OSEBX_TW_260428.xlsx, "
                    "navnet PBROE_All3 og SentimentManagement leser",
         "Rader": 231, "Siste": None},
        {"Kilde": "Kursdata", "Handling": "SKREVET" if alle_ok else "DEGRADERT",
         "Merknad": (f"412 903 rader, siste kurs {i_gar}" if alle_ok else
                     "beholdt eksisterende fil: 41 210 rader mot 412 903 tidligere "
                     "(under 80 %) — ser ut som en halvferdig nedlasting"),
         "Rader": 412903 if alle_ok else 41210, "Siste": siste_kurs},
        {"Kilde": "Sentimentendringer", "Handling": "SKREVET",
         "Merknad": "5 118 artikler", "Rader": 5118, "Siste": str(i_gar)},
    ]
    return kurver, henting


def bygg(i_dag: date, alle_ok: bool) -> str:
    import data_status as ds
    import mail_status
    from capital_mail import render_capital_mail
    from portfolio_blend import build_capital_portfolio

    kurver, henting = demodata(i_dag, alle_ok)
    status = ds.hent("ExcelData", "data", acquisition=henting, as_of=i_dag,
                     curves=kurver)
    valgte = ds.included_curves(status)
    portefolje = build_capital_portfolio(valgte, as_of=i_dag,
                                         start_capital=1_000_000.0,
                                         risk_free_pct=3.0)
    portefolje["metrics"]["Utelatte_Strategier"] = list(status["excluded"])
    kjoring = [{"Analyse": r["Kilde"], "Status": "OK", "Minutter": 0.4,
                "Feil": r["Merknad"]} for r in henting]
    kjoring += [{"Analyse": n, "Status": "OK", "Minutter": m, "Feil": ""}
                for n, m in (("PB-ROE-Momentum", 106.2),
                             ("NLP Sentiment — ledelse", 12.8),
                             ("Sentiment Momentum v3.1", 3.1),
                             ("Innsidehandel Oslo Børs", 43.0))]
    html = render_capital_mail(DemoMaster(), kjoring, portefolje,
                               {"kort": {}, "stil": "", "strategier": []}, {}, [],
                               data_status_html=mail_status.render(status))
    return html.replace("<body>", "<body>" + MERKE, 1)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="demo_mail", description=__doc__)
    parser.add_argument("--alle-ok", action="store_true",
                        help="vis mailen når alle fire har ferske data")
    parser.add_argument("--ut", metavar="FIL", default="demo_mail.html")
    parser.add_argument("--dato", metavar="YYYY-MM-DD",
                        help="rapportdato (standard: i dag)")
    args = parser.parse_args(list(argv) if argv is not None else None)

    patched_import.install()
    i_dag = date.fromisoformat(args.dato) if args.dato else date.today()
    ut = Path(args.ut)
    ut.write_text(bygg(i_dag, args.alle_ok), encoding="utf-8")
    print(f"Skrev demonstrasjonsmail til {ut.resolve()}")
    print("Alle tall i den er oppdiktet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
