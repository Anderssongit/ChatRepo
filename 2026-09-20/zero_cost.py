# -*- coding: utf-8 -*-
"""Variantvalg uten handelskostnader — og uten å se på fremtiden.

HVA SOM ER ENDRET, OG HVORFOR
-----------------------------
De fire strategiene handlet allerede uten kostnader: innsidemotoren har
`spread_pst = 0.00` og `kurtasje_pst = 0.00` som standard, og de tre andre sier
«Kostnad er satt til 0 %» i sine egne regler. Kostnadene levde bare ett sted
igjen — i VALGET av innsidevariant:

    krav:   positiv trenings-CAGR etter 0,15 % kostnad per handelsside
    mål:    høyest CAGR i den svakeste treningshalvdelen etter 0,80 % per side

Det valget optimaliserte altså for et kostnadsregime som ikke gjelder. Her er
regelen i stedet:

    krav:   minst 252 treningsdager, 20 nye innganger og 5 forskjellige aksjer,
            og positiv trenings-CAGR uten kostnader
    mål:    høyest trenings-CAGR uten kostnader
    likhet: best svakeste treningshalvdel, så lavest omsetning, så fast
            variantrekkefølge

DET SOM IKKE ER ENDRET: HORISONTEN
----------------------------------
Valget leser fortsatt BARE data til og med treningsslutt (standard 2025-06-30).
Full historikk og senere testresultater påvirker ikke hvilken variant som
velges. Å velge varianten med høyest CAGR over hele historikken ville gitt et
penere tall og vært verdiløst: varianten ville da være valgt med data den
etterpå rapporterer avkastning på.

Minstekravene står igjen av samme grunn. Uten dem vinner en variant med tre
heldige handler over en med tre hundre, og «høyest CAGR» blir en måling av
flaks i stedet for av regelen.

Ren stdlib. Ingen IO, ingen pandas, ingen nett.
"""
from __future__ import annotations

import math
from typing import Any, Dict, Optional, Sequence, Tuple

POLICY_VERSION = "insider-zero-cost-v1"

MIN_TRAIN_DAYS = 252
MIN_ENTRIES = 20
MIN_TICKERS = 5

OBJECTIVE = ("Høyest trenings-CAGR uten handelskostnader. Ved likhet vinner "
             "best svakeste treningshalvdel, deretter lavere treningsomsetning, "
             "deretter fast variantrekkefølge.")
ELIGIBILITY = (f"Minst {MIN_TRAIN_DAYS} treningsdager, {MIN_ENTRIES} nye innganger "
               f"og {MIN_TICKERS} forskjellige aksjer, og positiv trenings-CAGR "
               "uten kostnader.")


def _number(value) -> Optional[float]:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def meets_minimums(row: Dict[str, Any]) -> bool:
    """Bredde- og lengdekravene. De hindrer at flaks vinner over regel."""
    return (_int(row.get("Train_Days")) >= MIN_TRAIN_DAYS
            and _int(row.get("Train_Entries")) >= MIN_ENTRIES
            and _int(row.get("Train_Tickers")) >= MIN_TICKERS)


def is_eligible(row: Dict[str, Any]) -> bool:
    """Kvalifisert til å bli valgt: minstekrav møtt og positiv trening uten kostnad."""
    train = _number(row.get("Train_CAGR_Pst"))
    return meets_minimums(row) and train is not None and train > 0


def _sort_key(row: Dict[str, Any], order: Dict[str, int]):
    worst = _number(row.get("Train_Worst_Half_CAGR_Pst"))
    turnover = _number(row.get("Train_Turnover_Per_Year_Pst"))
    return (
        -float(_number(row.get("Train_CAGR_Pst")) or 0.0),
        # Manglende halvdelstall skal ikke vinne en likhet det ikke kan bevise.
        -(worst if worst is not None else -math.inf),
        turnover if turnover is not None else math.inf,
        order.get(str(row.get("Variant")), 1_000_000),
    )


def select_variant(rows: Sequence[Dict[str, Any]], baseline: str = "daglig"
                   ) -> Tuple[Dict[str, Any], str]:
    """Ren velger. Verken fullhistorikk- eller testkolonner leses her."""
    rows = list(rows)
    base = next((r for r in rows if r.get("Variant") == baseline), None)
    if base is None:
        raise ValueError("Innsidebaselinen mangler; kan ikke velge trygt.")
    eligible = [r for r in rows if is_eligible(r)]
    if not eligible:
        return base, (
            "Daglig baseline beholdes: ingen variant har både tilstrekkelig "
            "treningshistorikk/bredde og positiv trenings-CAGR uten "
            f"handelskostnader (krav: {MIN_TRAIN_DAYS} treningsdager, "
            f"{MIN_ENTRIES} innganger, {MIN_TICKERS} aksjer). "
            "Dette dokumenterer ingen varig fordel.")

    order = {str(r.get("Variant")): n for n, r in enumerate(rows)}
    selected = min(eligible, key=lambda row: _sort_key(row, order))
    reason = (
        "Valgt på treningsdata alene: høyest CAGR uten handelskostnader, blant "
        f"varianter med minst {MIN_TRAIN_DAYS} treningsdager, {MIN_ENTRIES} nye "
        f"innganger og {MIN_TICKERS} forskjellige aksjer. Ved likhet vinner best "
        "svakeste treningshalvdel, deretter lavere treningsomsetning, deretter "
        "fast variantrekkefølge. Handelskostnader er satt til null i hele "
        "kjøringen, også her. Fullhistorikk og senere testresultater påvirker "
        "ikke valget.")
    worst = _number(selected.get("Train_Worst_Half_CAGR_Pst"))
    if worst is not None and worst <= 0:
        reason += (" Den valgte varianten taper i minst én av de to "
                   "treningshalvdelene; resultatet er ujevnt fordelt over "
                   "treningsperioden.")
    return selected, reason


def policy(cutoff: str) -> Dict[str, Any]:
    """Det som skrives til selected_variant.json, så regelen kan leses etterpå."""
    return {
        "minimum_training_days": MIN_TRAIN_DAYS,
        "minimum_new_entries": MIN_ENTRIES,
        "minimum_tickers": MIN_TICKERS,
        "cost_per_side_pct": 0.0,
        "objective": OBJECTIVE,
        "eligibility": ELIGIBILITY,
        "selection_cutoff": str(cutoff),
        "annualization": ("Fulltabellen beholder motorens konvensjon med 252 "
                          "handelsdager per år. Trening/test bruker faktiske "
                          "kalenderdatoer (365,25 dager per år)."),
        "lookahead": ("Ingen. Bare observasjoner til og med treningsslutt inngår "
                      "i valget."),
    }


LIMITATIONS = [
    "Null handelskostnad er en forutsetning, ikke en observasjon. Faktisk "
    "spread, kurtasje og markedspåvirkning finnes og er ikke modellert her.",
    "En forhåndsdefinert valgregel er ikke bevis for varig fordel eller "
    "fremtidig meravkastning.",
    "Senere testdata er holdt utenfor valget, men variantene ble opprinnelig "
    "utviklet på deler av den samme historikken; dette er ikke uberørt forskning.",
    "Fullhistorisk kurve for den valgte varianten er tilbakeberegnet; et "
    "historisk porteføljeresultat basert på dette valget må begynne etter "
    "treningsslutt.",
]
