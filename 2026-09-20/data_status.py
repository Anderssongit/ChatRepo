# -*- coding: utf-8 -*-
"""Per strategi: kom dataene ned, og er de ferske nok til å handles på?

HVORFOR DENNE FINNES
--------------------
I kjøringen 2026-09-18 sto Sentiment Momentum v3.1 oppført som `OK`. Den hadde
ikke hentet noe som helst: den kjørte backtesten på nytt over kurser som sluttet
2026-08-19, tretti dager før rapporten. `OK` betydde «leste gamle data uten å
feile», ikke «dette er ferskt».

Denne modulen gjør forskjellen synlig, øverst i mailen, for hver av de fire
strategiene — og den avgjør hvem som får være med i den samlede porteføljen.

TO LAG
------
`klassifiser` og `bygg` er rene funksjoner uten pandas, nett eller filsystem.
`hent` er IO-laget: det leser eksportene via portfolio_blend.load_production_curves.

STATUSVERDIER
-------------
  OK         eksporten finnes, er gyldig og siste observasjon er fersk nok
  FORELDET   eksporten finnes, men siste observasjon er for gammel (eller
             datert i fremtiden, som er en merkelapp og ikke en observert kurs)
  MANGLER    ingen brukbare observasjoner
  FEIL       eksporten kunne ikke leses, eller er erklært ugyldig

Bare OK går inn i den samlede porteføljen. Resten utelates, og mailen sier
hvem, hvorfor og hva det betyr for fellestallene.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence

OK = "OK"
FORELDET = "FORELDET"
MANGLER = "MANGLER"
FEIL = "FEIL"

# Rekkefølgen strategiene vises i, og navnene portfolio_blend bruker.
STRATEGIER = ("PB-ROE-Momentum", "NLP Sentiment — ledelse",
              "Sentiment Momentum v3.1", "Innsidehandel — Oslo Børs")

# Hvor gammel siste observasjon får være. PB-ROE eksporterer månedlige verdier,
# så en måned pluss slingringsmonn er riktig grense der; de tre andre er
# daglige og skal være innenfor en uke.
MAKSALDER_DAGER = {"PB-ROE-Momentum": 45,
                   "NLP Sentiment — ledelse": 7,
                   "Sentiment Momentum v3.1": 7,
                   "Innsidehandel — Oslo Børs": 7}

# Hva hver strategi faktisk leser, i klartekst for mailen.
DATAKILDE = {
    "PB-ROE-Momentum":
        "TradingView-nøkkeltall (Playwright) + Data_BT/AllTickers_OSEBX_TW_260428.xlsx",
    "NLP Sentiment — ledelse":
        "Euronext-artikler + FinBERT-score + Yahoo-kurser",
    "Sentiment Momentum v3.1":
        "DataNLP/Step4_Sentiment_Changes_*.xlsx + Data_BT1/FinancialData/Stock_Prices_*.xlsx",
    "Innsidehandel — Oslo Børs":
        "Euronext/NewsWeb-meldinger + Yahoo-kurser",
}

# Hvilken strategi en hentet grunnlagsfil tilhører.
KILDE_TIL_STRATEGI = {
    "Aksjeliste": ("PB-ROE-Momentum", "NLP Sentiment — ledelse",
                   "Sentiment Momentum v3.1", "Innsidehandel — Oslo Børs"),
    "PB-ROE tickerliste": ("PB-ROE-Momentum", "NLP Sentiment — ledelse"),
    "Kursdata": ("Sentiment Momentum v3.1",),
    "Sentimentendringer": ("Sentiment Momentum v3.1",),
}

# Navnene kjøringsloggen bruker, oversatt til strateginavnene over.
ANALYSE_TIL_STRATEGI = {
    "PB-ROE-Momentum": "PB-ROE-Momentum",
    "NLP-artikler — skraping": "NLP Sentiment — ledelse",
    "NLP Sentiment — ledelse": "NLP Sentiment — ledelse",
    "Sentimentendringer — Step4": "Sentiment Momentum v3.1",
    "Sentiment Momentum v3.1": "Sentiment Momentum v3.1",
    "Innsidehandel Oslo Børs": "Innsidehandel — Oslo Børs",
    "Innsidehandel — Oslo Børs": "Innsidehandel — Oslo Børs",
}

# Handlinger fra data_acquisition som ikke er et problem i seg selv.
GREIE_HANDLINGER = ("SKREVET", "GJENBRUKT", "OK")


def to_date(value) -> Optional[date]:
    """Tolerant datotolkning: str, date, datetime og pandas Timestamp."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    for attribute in ("to_pydatetime", "date"):
        handler = getattr(value, attribute, None)
        if callable(handler):
            try:
                result = handler()
                return result.date() if isinstance(result, datetime) else result
            except Exception:                          # noqa: BLE001
                pass
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def observation_span(observations: Iterable) -> Dict[str, Any]:
    """(antall, første, siste) for [(dato, verdi), ...] — ugyldige rader hoppes over."""
    days = []
    for row in observations or ():
        try:
            raw = row[0]
        except (TypeError, IndexError):
            continue
        day = to_date(raw)
        if day is not None:
            days.append(day)
    if not days:
        return {"antall": 0, "forste": None, "siste": None}
    return {"antall": len(days), "forste": min(days), "siste": max(days)}


def klassifiser(name: str, *, errors: Sequence[str] = (), observations: Iterable = (),
                as_of: Optional[date] = None, max_age_days: Optional[int] = None,
                analysis_errors: Sequence[str] = (),
                input_problems: Sequence[str] = ()) -> Dict[str, Any]:
    """Én strategis datastatus. Ren funksjon — ingen IO, ingen pandas.

    Rekkefølgen er bevisst: en eksport som ikke kan leses er FEIL uansett hvor
    fersk den ser ut, og en fremtidsdatert siste observasjon er FORELDET fordi
    den er en merkelapp og ikke en observert kurs.
    """
    as_of = as_of or date.today()
    if max_age_days is None:
        max_age_days = MAKSALDER_DAGER.get(name, 7)
    span = observation_span(observations)
    problems = [str(e) for e in errors if e] + [str(e) for e in analysis_errors if e]

    if problems:
        status = FEIL
        begrunnelse = "; ".join(problems)
    elif span["antall"] == 0:
        status = MANGLER
        begrunnelse = "eksporten har ingen brukbare observasjoner"
    else:
        alder = (as_of - span["siste"]).days
        if alder < 0:
            status = FORELDET
            begrunnelse = (f"siste observasjon {span['siste']} ligger ETTER rapportdatoen "
                           f"{as_of}; en fremtidsdatert rad er en merkelapp, ikke en kurs")
        elif alder > max_age_days:
            status = FORELDET
            begrunnelse = (f"siste observasjon {span['siste']} er {alder} dager gammel "
                           f"(grense {max_age_days}). Å kjøre modellen på nytt gjør ikke "
                           "kildekursene ferskere")
        else:
            status = OK
            begrunnelse = f"ferske data til og med {span['siste']} ({alder} dager gamle)"

    alder = None if span["siste"] is None else (as_of - span["siste"]).days
    return {
        "Strategi": name,
        "Datakilde": DATAKILDE.get(name, ""),
        "Status": status,
        "Nedlasting": list(input_problems),
        "Observasjoner": span["antall"],
        "Forste": None if span["forste"] is None else str(span["forste"]),
        "Siste": None if span["siste"] is None else str(span["siste"]),
        "Alder_Dager": alder,
        "Maksalder_Dager": max_age_days,
        "Begrunnelse": begrunnelse,
        "I_Portefolje": status == OK,
        "Konsekvens": ("Inngår i samlet portefølje" if status == OK else
                       "Utelatt fra samlet portefølje"),
    }


def input_problems(acquisition: Iterable[Dict[str, Any]]) -> Dict[str, List[str]]:
    """Hentestatus per strategi: bare det som faktisk er et problem."""
    per_strategy: Dict[str, List[str]] = {}
    for row in acquisition or ():
        handling = str(row.get("Handling") or "").upper()
        if handling in GREIE_HANDLINGER:
            continue
        kilde = str(row.get("Kilde") or "")
        melding = f"{kilde}: {handling.lower()} — {row.get('Merknad') or ''}".strip(" —")
        for name in KILDE_TIL_STRATEGI.get(kilde, ()):
            per_strategy.setdefault(name, []).append(melding)
    return per_strategy


def analysis_problems(run_status: Iterable[Dict[str, Any]]) -> Dict[str, List[str]]:
    """Analysesteg som feilet, oversatt til strateginavn."""
    per_strategy: Dict[str, List[str]] = {}
    for row in run_status or ():
        if str(row.get("Status") or "").upper() == "OK":
            continue
        analyse = str(row.get("Analyse") or "")
        name = ANALYSE_TIL_STRATEGI.get(analyse)
        if name is None:
            continue
        per_strategy.setdefault(name, []).append(
            f"{analyse} feilet: {row.get('Feil') or 'ukjent årsak'}")
    return per_strategy


def bygg(components: Sequence[Dict[str, Any]], *,
         acquisition: Iterable[Dict[str, Any]] = (),
         run_status: Iterable[Dict[str, Any]] = (),
         component_errors: Optional[Dict[str, Sequence[str]]] = None,
         as_of: Optional[date] = None) -> Dict[str, Any]:
    """Datastatus for alle fire strategiene. Ren funksjon.

    `components` er radene fra portfolio_blend.load_production_curves.
    `component_errors` er ekstra feil per strategi (f.eks. «eksporten ble ikke
    oppdatert av denne kjøringen» fra validate_sources).
    """
    as_of = as_of or date.today()
    component_errors = component_errors or {}
    innganger = input_problems(acquisition)
    analyser = analysis_problems(run_status)
    by_name = {str(c.get("name")): c for c in components}

    rows: List[Dict[str, Any]] = []
    for name in STRATEGIER:
        component = by_name.get(name)
        if component is None:
            rows.append(klassifiser(
                name, errors=["eksporten ble ikke funnet av portfolio_blend"],
                as_of=as_of, analysis_errors=analyser.get(name, ()),
                input_problems=innganger.get(name, ())))
            continue
        errors = list(component.get("errors") or []) + list(component_errors.get(name, ()))
        if component.get("valid") is False and not errors:
            errors.append(str(component.get("error") or "kilden er erklært ugyldig"))
        row = klassifiser(name, errors=errors,
                          observations=component.get("observations") or (),
                          as_of=as_of, analysis_errors=analyser.get(name, ()),
                          input_problems=innganger.get(name, ()))
        source = component.get("source") or {}
        row["Fil"] = source.get("path") or ""
        row["Variant"] = component.get("variant") or ""
        rows.append(row)

    # Andre kilder enn de fire strategiene — aksjelista hører ikke til én av dem.
    included = [r["Strategi"] for r in rows if r["I_Portefolje"]]
    excluded = [r["Strategi"] for r in rows if not r["I_Portefolje"]]
    alle_ok = not excluded
    return {
        "rows": rows,
        "included": included,
        "excluded": excluded,
        "all_ok": alle_ok,
        "as_of": str(as_of),
        "acquisition": list(acquisition or ()),
        "summary": _summary(rows, alle_ok),
    }


def _summary(rows: Sequence[Dict[str, Any]], alle_ok: bool) -> str:
    if alle_ok:
        return (f"Alle {len(rows)} strategiene har ferske data. "
                "Samlet portefølje bruker alle fire.")
    daarlige = [r for r in rows if not r["I_Portefolje"]]
    navn = ", ".join(f"{r['Strategi']} ({r['Status'].lower()})" for r in daarlige)
    antall = len(rows) - len(daarlige)
    if antall < 2:
        return (f"{len(daarlige)} av {len(rows)} strategier mangler ferske data: {navn}. "
                "Færre enn to strategier har brukbare data, så ingen samlet "
                "portefølje kan beregnes.")
    return (f"{len(daarlige)} av {len(rows)} strategier mangler ferske data: {navn}. "
            f"Samlet portefølje beregnes på de {antall} som har det, med "
            f"{100.0 / antall:.0f} % kapital til hver.")


def hent(excel_dir, insider_dir, *, acquisition: Iterable[Dict[str, Any]] = (),
         run_status: Iterable[Dict[str, Any]] = (),
         component_errors: Optional[Dict[str, Sequence[str]]] = None,
         as_of: Optional[date] = None,
         curves: Optional[Sequence[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """IO-laget: les eksportene én gang og klassifiser dem.

    `curves` kan sendes inn når de allerede er lest, så ingen arbeidsbok
    åpnes to ganger i samme kjøring.
    """
    if curves is None:
        try:
            from portfolio_blend import load_production_curves
            curves = load_production_curves(excel_dir, insider_dir)
        except Exception as exc:                       # noqa: BLE001
            # Uten pandas, eller uten ExcelData i det hele tatt, skal dette gi en
            # lesbar status - ikke et unntak midt i en mail som ellers kunne
            # blitt sendt.
            curves = [{"name": name, "observations": [], "valid": False,
                       "errors": [f"eksportene kunne ikke leses: "
                                  f"{type(exc).__name__}: {exc}"]}
                      for name in STRATEGIER]
    result = bygg(curves, acquisition=acquisition, run_status=run_status,
                  component_errors=component_errors, as_of=as_of)
    result["curves"] = list(curves)
    return result


def included_curves(status: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Kurvene som skal inn i den samlede porteføljen, i fast rekkefølge."""
    wanted = set(status.get("included") or ())
    return [c for c in status.get("curves") or () if str(c.get("name")) in wanted]
