# -*- coding: utf-8 -*-
"""
MASTER — FIRE STRATEGIER, 25 % KAPITAL TIL HVER, ÉN MAIL

python master.py                 oppdater analysene, beregn og send mail
python master.py --mail-kladd    oppdater og beregn, men lagre bare mailen
python master.py --ikke-kjor     beregn fra gyldige lagrede resultater
python master.py --bare-mail     gjenbruk siste fullførte kapitalberegning

PB-ROE, ledelsessentiment, Sentiment Momentum og valgt innsidevariant
beholder egne handelsregler. Verdikurvene kombineres med 25 % kapital hver
og månedlig rebalansering over felles fullførte måneder, etter variantvalg.
portfolio_blend.py beregner kapitalen; capital_mail.py bygger rapporten.
De eldre scoreverktøyene beholdes for kompatibilitet og regresjonstester,
men brukes ikke av standardkjøringen. Se README.md for krav og metode.

RETTELSER I DENNE UTGAVEN — ALT LIGGER I DENNE FILA
---------------------------------------------------
Denne master.py er eneste fil du trenger å bytte. Ingen egen mappe, ingen
importkrok, ingenting som stilltiende gjør ingenting hvis det ligger feil sted.

1. LEDELSESSENTIMENT KJØRER IGJEN. Prisvakten i Only_260820.py stanset hele
   strategien når én ticker hadde en kurs den ikke kunne kontrollere — åtte av
   rundt to hundre selskaper kostet alle fire tallene. Nå utelates de tickerne
   fra universet, navngis i loggen og i management_price_issues.csv, og resten
   handles. Ingen kurs klippes, interpoleres eller gjettes. Forsvinner mer enn
   halve universet, stopper den fortsatt — da er det nedlastingen som feiler.
   Vakten ligger som en nestet funksjon og kan ikke byttes utenfra, så kilden
   endres i MINNET ved import. Fila på disk åpnes aldri for skriving, og
   PBROE_All3 og SentimentMomentumV31 er byte-identiske etterpå.

2. ET STEG SOM HENTET NOE STANSER IKKE DE NESTE. Innsidepipelinen kastet hele
   strategien når steg 1, 4 eller 5 meldte noe annet enn OK — og steg 1 melder
   OK bare når NULL av 294 selskaper feilet. En kjøring som hadde hentet 3879
   artikler på 2,2 timer ble derfor forkastet i sin helhet. Delvis behandles nå
   som delvis: kjøringen fortsetter på det som faktisk ble hentet, og at det var
   delvis står i steglista og i mailen.

3. INGEN HANDELSKOSTNADER, HELLER IKKE I VALGET. Motoren handler allerede uten
   kostnader. Valget mellom de fem innsidevariantene brukte likevel en
   kostnadsregel, og optimaliserte dermed for et regime som ikke gjelder.
   Kriteriet er nå høyest trenings-CAGR uten kostnader. Horisonten er uendret:
   bare data til og med treningsslutt inngår, så valget ser ikke fremover.

4. MAILEN BEGYNNER MED DATASTATUS. Én linje per strategi: kom dataene ned, hvor
   ferske er de, teller strategien i fellestallene. En strategi uten ferske data
   utelates og navngis i stedet for å velte hele mailen, og de øvrige blandes
   med lik vekt — fire gir 25 % hver, tre gir 33 %. En utelatt strategi
   erstattes ikke med null avkastning, og forrige verdi videreføres ikke som om
   den var dagens.

Tester: test_master_standalone.py (kjører uten pandas, numpy og nett).
"""

from __future__ import annotations

import argparse
import json
from runtime_config import data_root, configure_paths, protected_input_errors
import bisect
import os
import sys
import time
import traceback
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

SKRIPTMAPPE = Path(__file__).resolve().parent
sys.path.insert(0, str(SKRIPTMAPPE))

import innsidehandel_pipeline as IP          # noqa: E402  (stien må settes først)

Rad = Dict[str, Any]


# ══════════════════════════════════════════════════════════════════════════
# RETTELSER — ALT LIGGER I DENNE FILA
# ══════════════════════════════════════════════════════════════════════════
#
# master.py er eneste fil du trenger å bytte. Ingen egen mappe, ingen
# importkrok, ingenting som stilltiende gjør ingenting hvis det ligger feil
# sted. Fire rettelser:
#
#   1. Ledelsessentiment: en ticker med ukontrollerbare kurser utelates, i
#      stedet for å stanse hele strategien. Det var denne som gjorde 3 av 4.
#   2. Innsidepipelinen: et steg som hentet NOE stanser ikke de neste.
#   3. Innsidevalget bruker ingen handelskostnader — motoren gjør det heller
#      ikke.
#   4. Mailen begynner med datastatus per strategi, og en strategi uten
#      ferske data utelates fra fellestallene i stedet for å velte mailen.
#
# Rettelse 1 må endre kildekoden til Only_260820.py, fordi vakten ligger som
# en nestet funksjon inne i SentimentHendelseLab og ikke kan byttes utenfra.
# Endringen gjøres i MINNET. Fila på disk åpnes aldri for skriving. Treffer
# den ikke, sies det høyt i loggen og i mailen — den later aldri som.

FIKS_VERSJON = "standalone-2026-09-20"


# ── 1. Prisvakten: utelat tickeren, ikke hele strategien ──────────────────

_PRISVAKT_GAMMEL = '''        issues = kontroller_priser(close)
        issues.to_csv(config.ut_dir / "management_price_issues.csv", index=False)
        if not issues.empty:
            examples = ", ".join(issues["ticker"].drop_duplicates().head(8))
            raise RuntimeError(
                "Management prices require verification after provider repair: "
                + examples + ". See management_price_issues.csv. No backtest or variant "
                "is published from these prices; prices were not clipped or guessed.")'''

_PRISVAKT_NY = '''        issues = kontroller_priser(close)
        issues.to_csv(config.ut_dir / "management_price_issues.csv", index=False)
        if not issues.empty:
            # En ticker med ukontrollerbare kurser skal koste DEN tickeren,
            # ikke hele strategien. For aatte av rundt to hundre selskaper
            # stanset dette foer alt: ingen backtest, ingen variant, ingen tall
            # i mailen. Tickerne utelates naa fra universet og navngis i
            # loggen og i management_price_issues.csv. Ingen kurs klippes,
            # interpoleres eller gjettes - de utelatte selskapene handles bare
            # ikke.
            _uten_kurs = sorted({str(t) for t in issues["ticker"]})
            _alle = [str(c) for c in close.columns]
            _beholdt = [c for c in close.columns if str(c) not in _uten_kurs]
            log.warning("Kurser   : utelater %d av %d tickere med "
                        "ukontrollerbare kurser: %s", len(_uten_kurs),
                        len(_alle), ", ".join(_uten_kurs[:12])
                        + (" ..." if len(_uten_kurs) > 12 else ""))
            if len(_beholdt) < max(10, 0.5 * len(_alle)):
                # Naar halve universet er borte er det ikke enkelttickere som
                # er problemet, det er nedlastingen. Da skal den stoppe.
                raise RuntimeError(
                    "For faa tickere igjen etter prisvalidering: "
                    + str(len(_beholdt)) + " av " + str(len(_alle)) + ". "
                    "Se management_price_issues.csv. Ingen kurs ble klippet "
                    "eller gjettet.")
            close = close[_beholdt].copy()
            high = high.reindex(index=close.index, columns=_beholdt)
            low = low.reindex(index=close.index, columns=_beholdt)'''


def _les_tekst(sti: Path) -> str:
    with Path(sti).open(encoding="utf-8", newline="") as fil:
        return fil.read()


def _bytt_blokk(kilde: str, gammel: str, ny: str) -> Tuple[str, str]:
    """Bytt blokken uansett linjeskiftkonvensjon. (ny kilde, melding)."""
    for skift in ("\r\n", "\n"):
        behov = gammel.replace("\n", skift)
        if kilde.count(behov) == 1:
            return kilde.replace(behov, ny.replace("\n", skift), 1), ""
        if kilde.count(behov) > 1:
            return kilde, "blokken finnes flere steder i fila"
    return kilde, "blokken ble ikke funnet — fila er en annen utgave"


def last_only_med_rettelser(logger) -> Tuple[Any, str]:
    """Importer Only_260820 med prisvakten rettet. Skriver aldri til disk.

    Returnerer (modul, merknad). Merknaden er tom naar rettelsen traff.
    Treffer den ikke, importeres fila som den er og merknaden sier hvorfor —
    da er du tilbake til at aatte tickere stanser ledelsessentimentet, og det
    skal staa i mailen og ikke oppdages tre maaneder senere.
    """
    import importlib
    import linecache

    if "Only_260820" in sys.modules:
        return sys.modules["Only_260820"], ""
    sti = SKRIPTMAPPE / "Only_260820.py"
    if not sti.is_file():
        raise ImportError(f"Fant ikke {sti}")
    try:
        kilde = _les_tekst(sti)
    except OSError as e:
        raise ImportError(f"Kunne ikke lese {sti}: {e}") from e

    if "_uten_kurs = sorted(" in kilde:
        merknad = ""                         # rettelsen ligger allerede i fila
    else:
        kilde, feil = _bytt_blokk(kilde, _PRISVAKT_GAMMEL, _PRISVAKT_NY)
        merknad = ("Prisvakten i Only_260820.py kunne ikke rettes: " + feil
                   + ". Ledelsessentimentet stanser da fortsatt paa tickere "
                     "med ukontrollerbare kurser." if feil else "")
        if feil:
            logger.error("❌ %s", merknad)

    modul = importlib.util.module_from_spec(
        importlib.util.spec_from_loader("Only_260820", loader=None))
    modul.__file__ = str(sti)
    # Uten dette viser tracebacks linjer fra fila paa disk, som ikke er de
    # som kjoerer.
    linecache.cache[str(sti)] = (len(kilde), None, kilde.splitlines(True), str(sti))
    sys.modules["Only_260820"] = modul
    try:
        exec(compile(kilde, str(sti), "exec"), modul.__dict__)
    except BaseException:
        sys.modules.pop("Only_260820", None)
        raise
    if not merknad:
        logger.info("   ✓ Prisvakten rettet i minnet — Only_260820.py er urørt "
                    "på disk.")
    return modul, merknad


# ── 2. Et steg som hentet noe stanser ikke de neste ───────────────────────

def tillat_delvise_steg(logger) -> None:
    """Delvis er ikke mislykket.

    Innsidepipelinen stanser steg 2-6 naar steg 1, 4 eller 5 melder noe annet
    enn OK — og steg 1 melder OK bare naar NULL av 294 selskaper feilet. Et
    nettskrap av 294 selskaper er aldri feilfritt, saa en kjoering som hentet
    3879 artikler kunne bli kastet i sin helhet.

    Stegfunksjonene ligger som modulglobaler og kalles av lambdaer i main(),
    saa de kan byttes her — ingen kildekode roeres. Delvis blir OK, og at det
    var delvis staar i detaljteksten, i steglista og i mailen.
    """
    for navn in ("steg1_nedlasting", "steg4_kurser", "steg5_merge"):
        original = getattr(IP, navn, None)
        if original is None or getattr(original, "_delvis_tillatt", False):
            continue

        def lag(_orig=original, _navn=navn):
            def kall(*args, **kwargs):
                svar = _orig(*args, **kwargs)
                if isinstance(svar, dict) and svar.get("status") == "DELVIS":
                    svar = dict(svar, status="OK", delvis=True,
                                detaljer="DELVIS, kjøringen fortsetter — "
                                         + str(svar.get("detaljer") or ""))
                    logger.warning("   ⚠️  %s er delvis. Kjøringen fortsetter på "
                                   "det som faktisk ble hentet.", _navn)
                return svar
            kall._delvis_tillatt = True
            kall.__name__ = _navn
            return kall

        setattr(IP, navn, lag())


# ── 3. Variantvalg uten handelskostnader ──────────────────────────────────

MIN_TRENINGSDAGER, MIN_INNGANGER, MIN_TICKERE = 252, 20, 5


def _tall(verdi):
    try:
        verdi = float(verdi)
    except (TypeError, ValueError):
        return None
    return verdi if verdi == verdi and abs(verdi) != float("inf") else None


def velg_uten_kostnader(rader, baseline="daglig"):
    """Hoeyest trenings-CAGR uten kostnader, blant varianter med nok historikk.

    Motoren handler allerede uten kostnader (spread_pst = kurtasje_pst = 0).
    Kostnadene levde bare i VALGET, som dermed optimaliserte for et regime
    som ikke gjelder. Horisonten er uendret: bare data til og med
    treningsslutt inngaar, saa valget ser fortsatt ikke fremover.
    """
    rader = list(rader)
    base = next((r for r in rader if r.get("Variant") == baseline), None)
    if base is None:
        raise ValueError("Innsidebaselinen mangler; kan ikke velge trygt.")

    def nok_historikk(rad):
        try:
            return (int(rad.get("Train_Days", 0)) >= MIN_TRENINGSDAGER
                    and int(rad.get("Train_Entries", 0)) >= MIN_INNGANGER
                    and int(rad.get("Train_Tickers", 0)) >= MIN_TICKERE)
        except (TypeError, ValueError):
            return False

    kvalifiserte = [r for r in rader if nok_historikk(r)
                    and (_tall(r.get("Train_CAGR_Pst")) or 0) > 0]
    if not kvalifiserte:
        return base, ("Daglig baseline beholdes: ingen variant har baade nok "
                      "treningshistorikk og positiv trenings-CAGR uten "
                      "handelskostnader. Dette dokumenterer ingen varig fordel.")
    rekkefolge = {str(r.get("Variant")): n for n, r in enumerate(rader)}
    valgt = min(kvalifiserte, key=lambda r: (
        -(_tall(r.get("Train_CAGR_Pst")) or 0.0),
        _tall(r.get("Train_Turnover_Per_Year_Pst")) or float("inf"),
        rekkefolge.get(str(r.get("Variant")), 10 ** 6)))
    return valgt, ("Valgt paa treningsdata alene: hoeyest CAGR uten "
                   "handelskostnader, blant varianter med minst "
                   f"{MIN_TRENINGSDAGER} treningsdager, {MIN_INNGANGER} nye "
                   f"innganger og {MIN_TICKERE} forskjellige aksjer. Ved likhet "
                   "vinner lavere treningsomsetning. Handelskostnader er null i "
                   "hele kjoeringen. Fullhistorikk og senere testresultater "
                   "paavirker ikke valget.")


def bruk_nullkostnadsvalg(logger) -> None:
    """Bytt ut den kostnadsbaserte velgeren. Ren monkey-patch, ingen kildekode."""
    try:
        import insider_selection
    except Exception as e:                                   # noqa: BLE001
        logger.warning("   ⚠️  Fant ikke insider_selection: %s", IP.feiltekst(e))
        return
    if getattr(insider_selection.select_robust_variant, "_nullkostnad", False):
        return
    velg_uten_kostnader._nullkostnad = True
    insider_selection.select_robust_variant = velg_uten_kostnader
    insider_selection.POLICY_VERSION = "insider-zero-cost-v1"


# ── 4. Datastatus per strategi ────────────────────────────────────────────

STRATEGIER = ("PB-ROE-Momentum", "NLP Sentiment — ledelse",
              "Sentiment Momentum v3.1", "Innsidehandel — Oslo Børs")

# PB-ROE eksporterer bare maanedsverdier, saa en hale paa et par uker er
# normal der. De tre andre er daglige og skal vaere innenfor en uke.
MAKSALDER_DAGER = {"PB-ROE-Momentum": 45, "NLP Sentiment — ledelse": 7,
                   "Sentiment Momentum v3.1": 7, "Innsidehandel — Oslo Børs": 7}

ANALYSE_TIL_STRATEGI = {
    "PB-ROE-Momentum": "PB-ROE-Momentum",
    "NLP-artikler — skraping": "NLP Sentiment — ledelse",
    "NLP Sentiment — ledelse": "NLP Sentiment — ledelse",
    "Sentiment Momentum v3.1": "Sentiment Momentum v3.1",
    "Innsidehandel Oslo Børs": "Innsidehandel — Oslo Børs",
}


def _som_dato(verdi) -> Optional[date]:
    """Tolerant datotolkning: str, date, datetime og pandas Timestamp."""
    if verdi is None or verdi == "":
        return None
    if isinstance(verdi, datetime):
        return verdi.date()
    if isinstance(verdi, date):
        return verdi
    for navn in ("to_pydatetime", "date"):
        handler = getattr(verdi, navn, None)
        if callable(handler):
            try:
                svar = handler()
                return svar.date() if isinstance(svar, datetime) else svar
            except Exception:                                # noqa: BLE001
                pass
    try:
        return date.fromisoformat(str(verdi)[:10])
    except (TypeError, ValueError):
        return None


def _siste_observasjon(observasjoner) -> Tuple[int, Optional[date]]:
    dager = []
    for rad in observasjoner or ():
        try:
            dag = _som_dato(rad[0])
        except (TypeError, IndexError):
            continue
        if dag is not None:
            dager.append(dag)
    return len(dager), (max(dager) if dager else None)


def vurder_strategi(navn, feil=(), observasjoner=(), as_of=None):
    """Én strategis datastatus. Ren funksjon — ingen IO.

    OK bare naar eksporten kan leses, er gyldig og siste observasjon er fersk
    nok. En fremtidsdatert rad er en merkelapp, ikke en observert kurs.
    """
    as_of = as_of or date.today()
    grense = MAKSALDER_DAGER.get(navn, 7)
    antall, siste = _siste_observasjon(observasjoner)
    problemer = [str(f) for f in feil if f]
    if problemer:
        status, hvorfor = "FEIL", "; ".join(problemer)
    elif antall == 0:
        status, hvorfor = "MANGLER", "eksporten har ingen brukbare observasjoner"
    else:
        alder = (as_of - siste).days
        if alder < 0:
            status = "FORELDET"
            hvorfor = (f"siste observasjon {siste} ligger ETTER rapportdatoen "
                       f"{as_of}; en fremtidsdatert rad er en merkelapp, ikke "
                       "en kurs")
        elif alder > grense:
            status = "FORELDET"
            hvorfor = (f"siste observasjon {siste} er {alder} dager gammel "
                       f"(grense {grense}). Å kjøre modellen på nytt gjør ikke "
                       "kildekursene ferskere")
        else:
            status, hvorfor = "OK", f"ferske data til og med {siste} ({alder} dager)"
    return {"Strategi": navn, "Status": status, "Begrunnelse": hvorfor,
            "Observasjoner": antall, "Siste": None if siste is None else str(siste),
            "Alder_Dager": None if siste is None else (as_of - siste).days,
            "Maksalder_Dager": grense, "I_Portefolje": status == "OK",
            "Konsekvens": ("Inngår i samlet portefølje" if status == "OK"
                           else "Utelatt fra samlet portefølje")}


def bygg_datastatus(kurver, kjoring=(), per_komponent=None, as_of=None,
                    merknader=()):
    """Status for alle fire strategiene, og hvem som blir med i fellestallene."""
    as_of = as_of or date.today()
    per_komponent = dict(per_komponent or {})
    for rad in kjoring or ():
        if str(rad.get("Status") or "").upper() == "OK":
            continue
        navn = ANALYSE_TIL_STRATEGI.get(str(rad.get("Analyse") or ""))
        if navn:
            per_komponent.setdefault(navn, []).append(
                f"{rad.get('Analyse')} feilet: {rad.get('Feil') or 'ukjent årsak'}")

    etter_navn = {str(k.get("name")): k for k in (kurver or ())}
    rader = []
    for navn in STRATEGIER:
        komponent = etter_navn.get(navn)
        if komponent is None:
            rader.append(vurder_strategi(
                navn, feil=["eksporten ble ikke funnet"] + per_komponent.get(navn, []),
                as_of=as_of))
            continue
        feil = list(komponent.get("errors") or []) + per_komponent.get(navn, [])
        if komponent.get("valid") is False and not feil:
            feil.append(str(komponent.get("error") or "kilden er erklært ugyldig"))
        rad = vurder_strategi(navn, feil=feil,
                              observasjoner=komponent.get("observations") or (),
                              as_of=as_of)
        kilde = komponent.get("source") or {}
        rad["Fil"] = kilde.get("path") or ""
        rader.append(rad)

    med = [r["Strategi"] for r in rader if r["I_Portefolje"]]
    uten = [r["Strategi"] for r in rader if not r["I_Portefolje"]]
    if not uten:
        sammendrag = (f"Alle {len(rader)} strategiene har ferske data. "
                      "Samlet portefølje bruker alle fire.")
    elif len(med) < 2:
        sammendrag = (f"{len(uten)} av {len(rader)} strategier mangler ferske "
                      f"data: {', '.join(uten)}. Færre enn to strategier har "
                      "brukbare data, så ingen samlet portefølje kan beregnes.")
    else:
        sammendrag = (f"{len(uten)} av {len(rader)} strategier mangler ferske "
                      f"data: {', '.join(uten)}. Samlet portefølje beregnes på "
                      f"de {len(med)} som har det, med {100.0 / len(med):.0f} % "
                      "kapital til hver.")
    return {"rows": rader, "included": med, "excluded": uten,
            "all_ok": not uten, "as_of": str(as_of), "summary": sammendrag,
            "curves": list(kurver or ()),
            "notes": [str(n) for n in merknader if n]}


_FARGE = {"OK": "#2e7d32", "FORELDET": "#ef6c00",
          "MANGLER": "#c62828", "FEIL": "#c62828"}


def statusblokk_html(status) -> str:
    """Datastatusblokken som legges ØVERST i mailen."""
    import html as _html

    def t(v):
        return "" if v is None else _html.escape(str(v), quote=True)

    if not status or not status.get("rows"):
        return ('<div class="kort"><h2>Datastatus</h2><p>Datastatus kunne ikke '
                'bygges for denne kjøringen.</p></div>')
    rader = status["rows"]
    alle_ok = bool(status.get("all_ok"))
    hode = ("Datastatus: alle fire strategier har ferske data" if alle_ok
            else "Datastatus: ikke alle strategier har ferske data")
    linjer = "".join(
        "<tr>"
        f"<td style='font-weight:600'>{t(r['Strategi'])}</td>"
        f"<td>{t(r.get('Siste') or '—')}</td>"
        f"<td>{'—' if r.get('Alder_Dager') is None else t(str(r['Alder_Dager']) + ' dager')}</td>"
        f"<td style='color:{_FARGE.get(r['Status'], '')};font-weight:600'>{t(r['Status'])}</td>"
        f"<td>{t(r['Konsekvens'])}</td></tr>" for r in rader)
    darlige = [r for r in rader if not r["I_Portefolje"]]
    punkter = ""
    if darlige:
        punkter = ("<h3>Hva som mangler, og hva det betyr</h3><ul>" + "".join(
            f"<li><b>{t(r['Strategi'])}</b> — {t(r['Status'])}: "
            f"{t(r['Begrunnelse'])}.</li>" for r in darlige)
            + "</ul><p>En strategi uten ferske data utelates fra den samlede "
              "porteføljen. Den erstattes ikke med null avkastning, og den "
              "gamle verdien videreføres ikke som om den var dagens.</p>")
    notater = ""
    if status.get("notes"):
        notater = ("<h3>Merknader om kjøringen</h3><ul>"
                   + "".join(f"<li>{t(n)}</li>" for n in status["notes"]) + "</ul>")
    return (
        '<div class="kort">'
        f"<h2 style='color:{'#2e7d32' if alle_ok else '#c62828'}'>{t(hode)}</h2>"
        f"<p style='font-weight:600'>{t(status.get('summary'))}</p>"
        f"<p>Vurdert mot rapportdato {t(status.get('as_of'))}. En strategi er OK "
        "bare når eksporten kan leses, er gyldig og siste observasjon er innenfor "
        "grensen for den strategien — 45 dager for den månedlige PB-ROE-kurven, "
        "7 dager for de tre daglige.</p>"
        "<table><tr><th>Strategi</th><th>Siste observasjon</th><th>Alder</th>"
        f"<th>Status</th><th>Følge for fellestallene</th></tr>{linjer}</table>"
        + punkter + notater + "</div>")


# ── 5. Lik vekt til de strategiene som faktisk har ferske data ────────────
#
# portfolio_blend.build_capital_portfolio krever noeyaktig fire kurver og
# stanser ellers. Det betyr at én foreldet kursfil koster deg ALLE fellestall.
# Denne gjoer det samme regnestykket, men med lik vekt til de N som er igjen:
# fire gir 25 % hver, tre gir 33 %. Reglene er de samme - fullfoerte
# maanedsslutter, felles datoer, ingen maaned funnet paa.

import calendar as _kalender
import math as _matte
import statistics as _statistikk

MAKS_HULL_BORSDAGER = 5


def _manedsslutt(dag: date) -> date:
    return dag.replace(day=_kalender.monthrange(dag.year, dag.month)[1])


def _borsdager_etter(start: date, slutt: date) -> int:
    if slutt <= start:
        return 0
    return sum((start + timedelta(days=i)).weekday() < 5
               for i in range(1, (slutt - start).days + 1))


def _klargjor(komponent, as_of: date):
    """(dato -> NAV) for én kurve. Fremtidsdaterte rader utelates."""
    navn = komponent["name"]
    rader, fremtid = {}, 0
    for ra_dato, ra_verdi in komponent.get("observations", ()):
        dag = _som_dato(ra_dato)
        try:
            verdi = float(ra_verdi)
        except (TypeError, ValueError):
            raise ValueError(f"{navn}: ugyldig NAV {ra_verdi!r}")
        if dag is None:
            raise ValueError(f"{navn}: ugyldig dato {ra_dato!r}")
        if dag > as_of:
            fremtid += 1
            continue
        if not _matte.isfinite(verdi) or verdi <= 0:
            raise ValueError(f"{navn}: NAV er null eller negativ {dag}")
        rader[dag] = verdi
    if len(rader) < 2:
        raise ValueError(f"{navn}: færre enn to brukbare observasjoner")
    return dict(sorted(rader.items())), fremtid


def _manedspunkter(rader, as_of: date):
    """Siste observasjon i hver fullfoerte maaned, naar hullet er lite nok."""
    maaneder = {}
    for dag, verdi in rader.items():
        slutt = _manedsslutt(dag)
        if slutt <= as_of:
            maaneder[slutt] = (dag, verdi)
    brukbare, forkastet = {}, []
    for slutt, (dag, verdi) in maaneder.items():
        hull = _borsdager_etter(dag, slutt)
        if hull <= MAKS_HULL_BORSDAGER:
            brukbare[slutt] = (dag, verdi)
        else:
            forkastet.append((slutt, dag, hull))
    return brukbare, sorted(forkastet)


def _nokkeltall(verdier, datoer, risikofri_pst):
    avkastninger = [b / a - 1 for a, b in zip(verdier, verdier[1:])]
    dager = (datoer[-1] - datoer[0]).days
    total = verdier[-1] / verdier[0] - 1
    cagr = ((verdier[-1] / verdier[0]) ** (365.25 / dager) - 1
            if dager >= 180 else None)
    topp, fall = verdier[0], 0.0
    for verdi in verdier:
        topp = max(topp, verdi)
        fall = min(fall, verdi / topp - 1)
    vol = (_statistikk.stdev(avkastninger) * _matte.sqrt(12)
           if len(avkastninger) >= 2 else 0.0)
    rf = (1 + risikofri_pst / 100) ** (1 / 12) - 1
    sharpe = ((_statistikk.mean(avkastninger) - rf) * 12 / vol) if vol else None
    return {"CAGR_Pst": None if cagr is None else cagr * 100,
            "MaxDD_Pst": fall * 100, "Sharpe": sharpe,
            "Periode": f"{datoer[0]} → {datoer[-1]}",
            "Startkapital": verdier[0], "Sluttverdi": verdier[-1],
            "Total_Pst": total * 100, "Volatilitet_Pst": vol * 100,
            "frequency": "monthly", "Observasjoner": len(verdier),
            "drawdown_basis": "fullførte månedsslutter; fall inne i måneden "
                              "er ikke observerbare"}


def bland_likevektet(kurver, as_of=None, startkapital=1_000_000.0,
                     risikofri_pst=3.0, utelatte=()):
    """Samlet portefølje med lik vekt til hver kurve som sendes inn."""
    kurver = list(kurver)
    antall = len(kurver)
    if antall < 2:
        raise RuntimeError(
            "Færre enn to strategier har ferske data — ingen samlet portefølje "
            "kan beregnes. Se datastatus øverst i mailen.")
    navn_liste = [k["name"] for k in kurver]
    if len(set(navn_liste)) != antall:
        raise RuntimeError("To kurver har samme navn.")
    as_of = _som_dato(as_of) or date.today()
    andel = 100.0 / antall

    klargjort, manedlig, advarsler = {}, {}, []
    for komponent in kurver:
        navn = komponent["name"]
        klargjort[navn], fremtid = _klargjor(komponent, as_of)
        if fremtid:
            advarsler.append(f"{navn}: {fremtid} observasjoner etter {as_of} "
                             "er utelatt.")
        manedlig[navn], forkastet = _manedspunkter(klargjort[navn], as_of)
        for slutt, dag, hull in forkastet:
            advarsler.append(
                f"{navn}: {slutt} forkastet — siste observasjon {dag} er {hull} "
                f"børsdager før månedsslutt (grense {MAKS_HULL_BORSDAGER}).")
        if not manedlig[navn]:
            raise RuntimeError(f"{navn}: ingen fullført månedsslutt kan belegges.")

    dekning = {n: max(p) for n, p in manedlig.items()}
    bindende = min(dekning, key=dekning.get)
    advarsler.append(f"Felles periode slutter {dekning[bindende]} fordi "
                     f"{bindende} ikke har noen senere brukbar månedsslutt.")

    datoer = sorted(set.intersection(*(set(p) for p in manedlig.values())))
    grenser = []
    for komponent in kurver:
        metadata = komponent.get("metadata") or {}
        valg = komponent.get("selection") or {}
        grense = metadata.get("selection_cutoff") or valg.get("Selection_Cutoff")
        if grense and _som_dato(grense):
            grenser.append(_som_dato(grense))
    valggrense = max(grenser) if grenser else None
    if valggrense:
        datoer = [d for d in datoer if d >= valggrense]
        advarsler.append(
            f"Porteføljen starter ved første felles månedsslutt på eller etter "
            f"{valggrense}, siste dato brukt til variantvalg.")
    if len(datoer) < 2:
        raise RuntimeError(
            "Færre enn to felles fullførte månedsslutter — ingen samlet "
            f"avkastning kan beregnes. {bindende} rekker bare til "
            f"{dekning[bindende]}.")
    for a, b in zip(datoer, datoer[1:]):
        if b != _manedsslutt(a + timedelta(days=1)):
            raise RuntimeError(
                f"Felles månedsslutt mangler mellom {a} og {b}; nekter å finne "
                "opp en månedlig rebalansering.")

    andeler = {n: startkapital / antall / manedlig[n][datoer[0]][1]
               for n in navn_liste}
    equity, overforinger = [], []
    for nr, dag in enumerate(datoer):
        for_rebalansering = {n: andeler[n] * manedlig[n][dag][1] for n in navn_liste}
        total = sum(for_rebalansering.values())
        mal = total / antall
        equity.append({"Dato": str(dag), "Verdi_NOK": total,
                       "Antall_Strategier": antall})
        for n in navn_liste:
            flytt = mal if nr == 0 else mal - for_rebalansering[n]
            if abs(flytt) > 1e-8:
                overforinger.append({
                    "Dato": str(dag), "Strategi": n,
                    "Type": ("INITIAL_ALLOCATION" if nr == 0
                             else ("ALLOCATE" if flytt > 0 else "WITHDRAW")),
                    "Verdi_NOK": abs(flytt), "Transfer_NOK": flytt,
                    "Kostnad_NOK": 0.0, "Level": "strategy capital allocation"})
            andeler[n] = mal / manedlig[n][dag][1]

    siste = datoer[-1]
    beholdning = [{"Strategi": n, "Dato": str(siste),
                   "Verdi_NOK": equity[-1]["Verdi_NOK"] / antall,
                   "Andel_Pst": andel, "Target_Pst": andel,
                   "Antall": andeler[n], "NAV": manedlig[n][siste][1],
                   "Observation_Date": str(manedlig[n][siste][0]),
                   "Type": "strategy sleeve"} for n in navn_liste]
    komponenter = []
    for kilde in kurver:
        n = kilde["name"]
        ra = [manedlig[n][d][1] for d in datoer]
        normalisert = [startkapital / antall * v / ra[0] for v in ra]
        komponenter.append({"Strategi": n,
                            **_nokkeltall(normalisert, datoer, risikofri_pst),
                            "source": kilde.get("source"),
                            "source_frequency": kilde.get("frequency"),
                            "variant": kilde.get("variant"), "valid": True})

    advarsler += [
        f"Alle {antall} strategiene måles over den samme felles perioden av "
        "fullførte månedsslutter. Ingen daglig PB-ROE-verdi blir funnet på.",
        "Ingen handelskostnader er modellert noe sted i denne kjøringen. Det er "
        "en forutsetning, ikke en observasjon.",
        "Risiko er målt på månedspunkter og kan overse fall inne i måneden.",
        f"Den samlede perioden slutter {siste}; dette er et historisk "
        "øyeblikksbilde, ikke dagens beholdning.",
    ]
    if antall != 4:
        advarsler.append(
            f"Kapitalen er delt likt på {antall} strategier ({andel:.0f} % hver), "
            f"ikke fire. Utelatt: {', '.join(utelatte) or 'ukjent'}. "
            "Se datastatus øverst i mailen.")

    nokkeltall = _nokkeltall([r["Verdi_NOK"] for r in equity], datoer, risikofri_pst)
    nokkeltall.update({
        "Rebalance": "monthly", "Andel_Per_Strategi_Pst": andel,
        "N_Strategier": antall, "As_Of": str(as_of),
        "Utelatte_Strategier": list(utelatte),
        "Selection_Cutoff": str(valggrense) if valggrense else None,
        "Cost_Basis": "eksporterte strategikurver, modellert uten "
                      "handelskostnader; kapitaloverføringer koster 0"})
    return {"equity": equity, "holdings": beholdning, "trades": overforinger,
            "metrics": nokkeltall, "components": komponenter,
            "warnings": advarsler,
            "sources": [k.get("source") for k in kurver],
            "binding_component": bindende,
            "strategies": sorted(navn_liste),
            "common_period": {"start": str(datoer[0]), "end": str(siste),
                              "frequency": "monthly", "observations": len(datoer),
                              "return_periods": len(datoer) - 1}}


# ══════════════════════════════════════════════════════════════════════════
# INNSTILLINGER
# ══════════════════════════════════════════════════════════════════════════

@dataclass
class Master:
    """Alt som er verdt å justere, ett sted."""

    # ── hvor filene ligger ───────────────────────────────────────────────
    excel_dir: Path = field(default_factory=data_root)
    # Samme standard som innsidehandel_pipeline: mappen «data» ved siden av
    # scriptet. Overstyres med --mappe.
    innside_dir: Path = IP.SKRIPTMAPPE / "data"
    ut_dir: Path = field(default_factory=Path)

    # ── eldre scoremodell, ikke brukt av standardkjøringen ───────────────
    # Likevekt. En kilde uten mening om et selskap teller 50 (nøytral), så
    # enighet mellom flere kilder er det som løfter en aksje.
    vekt_pbroe: float = 0.25
    vekt_nlp: float = 0.25
    vekt_sentmom: float = 0.25
    vekt_innside: float = 0.25
    # Hvor lenge en score fra hver kilde regnes som gyldig. PB-ROE rebalanserer
    # månedlig, så scoren lever lenger enn et innsidekjøp, som er en hendelse på
    # én dag. NLP-ledelse er også en hendelse — én rapport, én dag — men den
    # rapporten er selskapets siste ord om egen drift til neste kvartal kommer,
    # så 45 dager er omtrent halve livslengden på informasjonen, ikke en
    # rebalanseringssyklus.
    gyldig_pbroe_dager: int = 45
    gyldig_nlp_dager: int = 45
    gyldig_sentmom_dager: int = 21
    gyldig_innside_dager: int = 30
    # Hvor mange selskaper per dag som får en signalrad til backtesten.
    # Hele universet hver dag ville gitt to millioner rader uten å endre
    # hvilke aksjer som velges.
    topp_per_dag: int = 30
    min_kilder: int = 1            # hvor mange kilder som må ha en mening

    # ── backtesten ───────────────────────────────────────────────────────
    min_score: float = 55.0
    maks_navn: int = 20
    min_navn: int = 5
    signal_vindu_dager: int = 5
    startkapital: float = 1_000_000.0
    spread_pst: float = 0.0
    kurtasje_pst: float = 0.0
    min_omsetning_nok: float = 500_000.0
    inn_utvalg_slutt: str = "2025-06-30"

    # ── mail ─────────────────────────────────────────────────────────────
    # Passordet leses fra AKSJE_MAIL_APP_PASSWORD eller mail_passord.txt ved
    # siden av dataene. Det skal ikke stå i en kildefil som ligger i git.
    epost_fra: str = "andyxcx@gmail.com"
    epost_til: str = "andyxcx@gmail.com"

    def __post_init__(self) -> None:
        self.excel_dir = Path(self.excel_dir)
        self.innside_dir = Path(self.innside_dir)
        self.ut_dir = (Path(self.ut_dir) if str(self.ut_dir) not in ("", ".")
                       else self.innside_dir / "7_master")
        self.epost_fra = os.environ.get("AKSJE_MAIL_USER", self.epost_fra)
        self.epost_til = os.environ.get("AKSJE_MAIL_TO", self.epost_til)

    # ── avledede stier ───────────────────────────────────────────────────
    @property
    def pbroe_bt(self) -> Path:
        return self.excel_dir / "DataPB_ROE" / "Backtest"

    @property
    def nlp_dir(self) -> Path:
        return self.excel_dir / "StrategyResults_v4_Sentiment"

    @property
    def sentmom_dir(self) -> Path:
        return self.excel_dir / "DataNLP" / "BacktestResults"

    def oppsett(self) -> "IP.Oppsett":
        """Innsidehandel-pipelinens eget oppsett, med masterens verdier."""
        o = IP.Oppsett(base_dir=self.innside_dir)
        o.maks_navn = self.maks_navn
        o.min_navn_portefolje = self.min_navn
        o.min_score_portefolje = self.min_score
        o.signal_vindu_dager = self.signal_vindu_dager
        o.startkapital = self.startkapital
        o.spread_pst = self.spread_pst
        o.kurtasje_pst = self.kurtasje_pst
        o.min_omsetning_nok = self.min_omsetning_nok
        o.inn_utvalg_slutt = self.inn_utvalg_slutt
        o.epost_fra = self.epost_fra
        o.epost_til = self.epost_til
        return o

    def insider_oppsett(self):
        """Match the standalone pipeline; legacy score-blend settings differ."""
        o = IP.Oppsett(base_dir=self.innside_dir)
        o.min_navn_portefolje = self.min_navn
        o.inn_utvalg_slutt = self.inn_utvalg_slutt
        o.epost_fra, o.epost_til = self.epost_fra, self.epost_til
        return o


# ══════════════════════════════════════════════════════════════════════════
# SMÅVERKTØY
# ══════════════════════════════════════════════════════════════════════════

def nyeste(mappe: Path, monster: str) -> Optional[Path]:
    """Ferskeste fil som passer mønsteret. Hopper over Excel sine låsefiler."""
    try:
        treff = [p for p in Path(mappe).glob(monster)
                 if not p.name.startswith("~$") and "BEFORE_FIX" not in p.name]
        return max(treff, key=lambda p: p.stat().st_mtime) if treff else None
    except OSError:
        return None


def bar(ticker: Any) -> str:
    """«EQNR.OL» og «EQNR» er samme selskap. Internt bruker vi det bare."""
    t = IP.rens(ticker).upper()
    return t[:-3] if t.endswith(".OL") else t


def oslo(ticker: Any) -> str:
    """Symbolet Yahoo kjenner."""
    t = bar(ticker)
    return f"{t}.OL" if t else ""


def filalder(sti: Optional[Path]) -> str:
    if sti is None or not Path(sti).exists():
        return "mangler"
    m = datetime.fromtimestamp(Path(sti).stat().st_mtime)
    timer = (datetime.now() - m).total_seconds() / 3600.0
    if timer < 1:
        return f"{m:%Y-%m-%d %H:%M} ({int(timer * 60)} min siden)"
    if timer < 48:
        return f"{m:%Y-%m-%d %H:%M} ({int(timer)} t siden)"
    return f"{m:%Y-%m-%d %H:%M} ({int(timer / 24)} dager siden)"


# ══════════════════════════════════════════════════════════════════════════
# DEL 1 — KJØR ALLE FIRE
# ══════════════════════════════════════════════════════════════════════════
#
# Hver analyse kjøres i sin egen try/except. Én som feiler skal ikke ta de tre
# andre med seg — da hadde en manglende Excel-fil i PB-ROE stoppet mailen om
# innsidehandel også, og det er ingen tjent med.

def kjor_alle(m: Master, logger, notater: Optional[List[str]] = None) -> List[Rad]:
    """Kjører de fire analysene. Én rad per analyse med status og tid."""
    ut: List[Rad] = []
    notater = notater if notater is not None else []

    def kjor(navn: str, handling) -> None:
        logger.info(f"\n{'━' * 74}\n{navn.upper()}\n{'━' * 74}")
        start = time.time()
        try:
            code = handling()
            if isinstance(code, int) and not isinstance(code, bool) and code not in (0, 2):
                raise RuntimeError(f"Analysis returned failure code {code}")
            status, feil = "OK", ("Parsing partly classified; see insider stage status"
                                   if code == 2 else "")
        except KeyboardInterrupt:
            raise
        except Exception as e:
            status, feil = "FEIL", IP.feiltekst(e)[:200]
            logger.error(f"❌ {navn} feilet: {feil}")
            logger.debug(traceback.format_exc())
        ut.append({"Analyse": navn, "Status": status,
                   "Minutter": round((time.time() - start) / 60.0, 1), "Feil": feil})

    def de_tre() -> None:
        # Importeres først her: Only-filen krever pandas, numpy og matplotlib,
        # og masteren skal kunne lese og sende mail uten dem.
        O, _merknad = last_only_med_rettelser(logger)
        if _merknad:
            notater.append(_merknad)
        configure_paths(O.__dict__, m.excel_dir)

        # Ledelses-sentiment kommer fra hendelseslaben, ikke fra den månedlige
        # utgaven. Den månedlige gikk gjennom alle selskaper hver månedsslutt og
        # regnet bedringen fra forrige rapport på nytt — men forrige rapport
        # endrer seg ikke mellom rapportene, så samme nyhet ga samme signal
        # måned etter måned. Én rapport ble tretten kjøp, og det første kom 23
        # dager etter at nyheten var ute.
        #
        # Skrapingen ligger fortsatt i SentimentManagement(), og den er det
        # eneste den kjøres for her: laben leser artiklene som ligger i DataNLP
        # og henter ingenting selv. Derfor er skrapesteget betinget av
        # --hent-nlp, mens laben kjøres hver gang.
        analyser = [("PB-ROE-Momentum", O.PBROE_All3)]
        if O._miljo_paa("AKSJE_NLP_HENT"):
            analyser.append(("NLP-artikler — skraping", O.SentimentManagement))
        analyser += [("NLP Sentiment — ledelse", O.SentimentHendelseLab),
                     ("Sentiment Momentum v3.1", O.SentimentMomentumV31)]
        for navn, funksjon in analyser:
            kjor(navn, funksjon)

    try:
        de_tre()
    except ImportError as e:
        logger.error(f"❌ Fant ikke Only_260820 eller pakkene den trenger: "
                     f"{IP.feiltekst(e)}")
        for navn in ("PB-ROE-Momentum", "NLP Sentiment — ledelse",
                     "Sentiment Momentum v3.1"):
            ut.append({"Analyse": navn, "Status": "FEIL", "Minutter": 0.0,
                       "Feil": "Only_260820 kunne ikke importeres"})

    # Et steg som hentet NOE skal ikke stanse de neste, og variantvalget
    # skal ikke bruke en kostnadsregel når motoren handler uten kostnader.
    tillat_delvise_steg(logger)
    bruk_nullkostnadsvalg(logger)
    kjor("Innsidehandel Oslo Børs",
         lambda: IP.main(["--steg", "1-6", "--ingen-mail",
                          "--mappe", str(m.innside_dir),
                          "--min-navn", str(m.min_navn), "--stopp-ved-feil"]))
    return ut


# ══════════════════════════════════════════════════════════════════════════
# DEL 2 — SCOREHISTORIKKEN FRA HVER KILDE
# ══════════════════════════════════════════════════════════════════════════
#
# Alle fire leses til det samme formatet: (Kilde, Dato, Ticker, Rå_Score).
# Det er hele grensesnittet. Vil du legge til en femte modell senere, er det
# én leser til som skal skrive de fire feltene — ingenting annet endres.

KILDER = ("PB-ROE", "NLP", "SentMom", "Innside")


# Arket hver modell skal legge scoreloggen sin i. Samme navn i alle tre,
# så en ny modell ikke trenger en ny regel.
SCORE_ARK = "Score_Log"


def _rader(kilde: str, poster: Sequence[Tuple[Any, Any, Any]],
           tapt: Optional[Dict[str, int]] = None) -> List[Rad]:
    """
    (dato, ticker, score) → scorerader. Teller hva som ble forkastet, og hvorfor.

    Tellingen er ikke pynt. En leser som stilltiende forkaster alt ser ut
    som en modell uten mening om noe som helst, og masteren gir da alle
    selskaper 50 og går videre. Da forsvinner en fjerdedel av grunnlaget
    uten at noen får vite det — som SentMom gjorde: hver eneste rad hadde
    en dato Excel lagret som tallet 45900, og fra_iso() sa nei til alle.
    """
    ut: List[Rad] = []
    for dato, ticker, score in poster:
        d = IP.fra_dato_celle(dato)
        if d is None:
            if tapt is not None:
                tapt["dato"] = tapt.get("dato", 0) + 1
            continue
        if not bar(ticker):
            if tapt is not None:
                tapt["ticker"] = tapt.get("ticker", 0) + 1
            continue
        v = IP.tolk_maskin(score)
        if v is None:
            if tapt is not None:
                tapt["score"] = tapt.get("score", 0) + 1
            continue
        ut.append({"Kilde": kilde, "Dato": IP.iso(d), "Ticker": bar(ticker),
                   "Ra_Score": v})
    return ut


def _hvorfor_tomt(fil: Optional[Path], lest: int, tapt: Dict[str, int]) -> str:
    """Én setning som sier hva som faktisk sto i filen, når ingenting overlevde."""
    if not lest:
        return (f"{fil.name if fil else 'filen'} ble lest, men arket er tomt — "
                f"modellen skrev ingen rader.")
    verst = max(tapt.items(), key=lambda x: x[1], default=("", 0))[0]
    forklaring = {
        "dato": "datoen kunne ikke tolkes (verken ÅÅÅÅ-MM-DD, ekte datocelle "
                "eller Excel-serienummer)",
        "ticker": "tickerkolonnen er tom",
        "score": "scorekolonnen er tom eller ikke et tall",
    }.get(verst, "kolonnene heter ikke det leseren venter")
    deler = ", ".join(f"{n}: {a}" for n, a in sorted(tapt.items()))
    return (f"{lest} rader lest fra {fil.name if fil else 'filen'}, men ingen "
            f"kunne brukes — {forklaring}. Forkastet ({deler}).")


def _felt(rad: Rad, *navn: str) -> Any:
    """
    Verdien fra den første kolonnen som finnes, uten hensyn til store bokstaver.

    «Date», «date» og «DATE» er samme kolonne. Modellene skriver dem ulikt,
    og en leser som krever én skrivemåte er en leser som knekker neste gang
    noen rører en overskrift.
    """
    if not rad:
        return None
    små = {str(k).strip().lower(): v for k, v in rad.items()}
    for n in navn:
        v = små.get(n.strip().lower())
        if v not in (None, ""):
            return v
    return None


def nyeste_med_ark(mappe: Path, monster: str, ark: str
                   ) -> Tuple[Optional[Path], List[Path]]:
    """
    (ferskeste fil som HAR arket, de ferskere filene som ikke hadde det).

    Å velge fil på alder alene var feilen som gjorde NLP-kilden tom: samme
    modell finnes i to utgaver, begge skriver et filnavn som passer
    søkemønsteret, og bare den ene skriver scoreloggen. Er den andre nyest,
    leser masteren en fil som aldri kan inneholde det den leter etter — og
    å kjøre modellen på nytt hjelper ikke.
    """
    def alder(p: Path) -> float:
        # En fil kan forsvinne mellom listingen og sorteringen — OneDrive,
        # antivirus, en annen kjøring. Da skal vi ikke krasje, bare rangere
        # den sist.
        try:
            return p.stat().st_mtime
        except OSError:
            return -1.0

    try:
        treff = [p for p in Path(mappe).glob(monster)
                 if not p.name.startswith("~$") and "BEFORE_FIX" not in p.name]
    except OSError:
        return None, []
    treff.sort(key=alder, reverse=True)
    forbigått: List[Path] = []
    for p in treff:
        if IP.har_xlsx_ark(p, ark):
            return p, forbigått
        forbigått.append(p)
    return None, forbigått


def _les_scorelogg(kilde: str, mappe: Path, monstre, kjor_paa_nytt: str
                   ) -> Tuple[List[Rad], Optional[Path], str, str]:
    """
    Felles leser for modellene som logger til arket «Score_Log».

    (rader, fil, feil, notat). `feil` er rødt i mailen og betyr at kilden er
    borte; `notat` er grått og betyr «dette bør du vite, men scoren står».

    `monstre` er enten ett filmønster eller en PRIORITERT liste av
    (mønster, motornavn). Rekkefølgen er med vilje ikke alder: to ulike motorer
    kan skrive en scorelogg om det samme selskapet, og da er det ikke den
    ferskeste filen som skal vinne — det er den motoren som er kilden nå.
    Faller vi tilbake på en eldre motor, sier notatet hvilken, for to motorer
    gir to svar om samme aksje, og et tall uten avsender er ikke etterprøvbart.
    """
    if isinstance(monstre, str):
        monstre = ((monstre, ""),)
    monstre = tuple((m, "") if isinstance(m, str) else m for m in monstre)

    fil = None
    forbigått: List[Path] = []
    motor = ""
    reserve = False
    for nr, (monster, motornavn) in enumerate(monstre):
        treff, hoppet = nyeste_med_ark(mappe, monster, SCORE_ARK)
        forbigått.extend(hoppet)
        if treff is not None:
            fil, motor, reserve = treff, motornavn, nr > 0
            break

    if fil is None and not forbigått:
        navn = " eller ".join(m for m, _ in monstre)
        return [], None, f"Fant ingen {navn} i {mappe}", ""
    if fil is None:
        nyeste_navn = ", ".join(p.name for p in forbigått[:3])
        return [], forbigått[0], (
            f"Ingen av de {len(forbigått)} filene har arket «{SCORE_ARK}» "
            f"({nyeste_navn}). {kjor_paa_nytt}"), ""
    deler = []
    if reserve:
        # «Fant ingen» og «fant en uten scoreloggen» er ikke samme sak: i det
        # andre tilfellet KJØRTE motoren, den skrev bare ikke arket, og da er
        # rådet et annet. Setningen skal si hvilket av de to som skjedde.
        primær = monstre[0][0]
        deler.append((f"Ingen brukbar {primær}" if forbigått
                      else f"Fant ingen {primær}")
                     + f" — leser {fil.name}"
                     + (f" ({motor})" if motor else "")
                     + ". Det er en ANNEN motor enn den som er kilden nå, så "
                       "tallene er ikke de samme.")
    elif motor:
        deler.append(f"Motor: {motor}.")
    if forbigått:
        deler.append(f"{len(forbigått)} fil(er) mangler «{SCORE_ARK}» og ble "
                     f"hoppet over: {', '.join(p.name for p in forbigått[:3])}.")
    notat = " ".join(deler)
    rader = IP.les_xlsx(fil, ("date", "ticker"), ark_navn=SCORE_ARK)
    tapt: Dict[str, int] = {}
    ut = _rader(kilde, [(_felt(r, "date", "dato"), _felt(r, "ticker", "Ticker"),
                         _felt(r, "score", "Score", "Sentiment_Score",
                               "Combined_score"))
                        for r in rader], tapt)
    if not ut:
        return [], fil, _hvorfor_tomt(fil, len(rader), tapt), notat
    return ut, fil, "", notat


def les_pbroe(m: Master) -> Tuple[List[Rad], Optional[Path], str, str]:
    return _les_scorelogg(
        "PB-ROE", m.pbroe_bt, "BT_v3_Enhanced_*.xlsx",
        "Kjør PBROE_All3() på nytt med den oppdaterte Only_260820.py — den "
        "eldre versjonen lagret aldri score per måned.")


# Ledelses-sentiment har to motorer som begge kan skrive en scorelogg, og de
# måler ikke det samme:
#
#   v6  SentimentHendelseLab()   én rapport = én hendelse = ett kjøp, på første
#                                handledag etter artikkelen. Dette er kilden.
#   v4  SentimentManagement()    månedlig rebalansering. Den gikk gjennom alle
#                                selskaper hver månedsslutt og regnet bedringen
#                                på nytt — men «forrige rapport» endrer seg ikke
#                                mellom rapportene, så den SAMME nyheten ga det
#                                samme signalet måned etter måned. Én rapport
#                                ble tretten kjøp, det første 23 dager for sent.
#
# Rekkefølgen er derfor ikke alder, men hvilken motor som er kilden. Den
# månedlige beholdes som reserve fordi den fortsatt er den som skraper
# artiklene, og fordi en tom NLP-kilde koster en fjerdedel av samlet score.
NLP_MOTORER = (
    ("Sentiment_v6_Hendelse_SMA*.xlsx",
     "v6 hendelsesdrevet — SentimentHendelseLab()"),
    ("Sentiment_v4*_SMA*.xlsx",
     "v4 månedlig rebalansering — SentimentManagement()"),
)


def les_nlp(m: Master) -> Tuple[List[Rad], Optional[Path], str, str]:
    return _les_scorelogg(
        "NLP", m.nlp_dir, NLP_MOTORER,
        "Kjør SentimentHendelseLab() med den oppdaterte Only_260820.py.")


def les_sentmom(m: Master) -> Tuple[List[Rad], Optional[Path], str, str]:
    """
    SentMom, med to lesemåter og én advarsel.

    Helst arket «Score_Log»: én rad per dag per kandidat, altså også de
    dagene modellen IKKE kjøpte noe. Finnes ikke det arket, faller vi
    tilbake på signalloggen i første ark — men den inneholder bare navn som
    faktisk ble kjøpt. Som grunnlag for en persentil er det skjevt: en
    kilde som bare rapporterer sine egne vinnere vil alltid ligge på topp,
    og masteren tror den ser enighet der den ser en utvalgsfeil. Derfor sier
    notatet fra.
    """
    f = nyeste(m.sentmom_dir, "S5_SentMom31_Signals_*.xlsx")
    if f is None:
        return [], None, (f"Fant ingen S5_SentMom31_Signals_*.xlsx i "
                          f"{m.sentmom_dir}. Kjør SentimentMomentumV31() med "
                          f"DIAGNOSE_ONLY = False."), ""
    notat = ""
    if IP.har_xlsx_ark(f, SCORE_ARK):
        rader = IP.les_xlsx(f, ("date", "ticker"), ark_navn=SCORE_ARK)
    else:
        rader = IP.les_xlsx(f, ("date", "ticker"))
        notat = (f"{f.name} har ikke arket «{SCORE_ARK}» — leser signalloggen, "
                 f"som bare inneholder navn modellen KJØPTE. Persentilen blir "
                 f"da for høy. Kjør SentimentMomentumV31() på nytt for en "
                 f"kandidatlogg.")
    tapt: Dict[str, int] = {}
    ut = _rader("SentMom", [(_felt(r, "Date", "dato"), _felt(r, "Ticker"),
                             _felt(r, "Composite", "Composite_Score", "score"))
                            for r in rader], tapt)
    if not ut:
        return [], f, _hvorfor_tomt(f, len(rader), tapt), notat
    return ut, f, "", notat


def les_innside(m: Master) -> Tuple[List[Rad], Optional[Path], str, str]:
    """
    Innsidekjøpene, datert til dagen de FAKTISK kunne handles.

    Ikke meldingsdatoen: en melding etter stengetid er først handlebar dagen
    etter, og `Handelsdag_0` er den dagen. Uten det ville den samlede scoren
    kjøpt på informasjon den ikke hadde.
    """
    f = m.oppsett().merget_csv
    if not f.exists():
        return [], None, f"Fant ingen {f.name} — kjør innsidehandel-pipelinen.", ""
    alle = IP.les_csv(f)
    poster = [(r.get("Handelsdag_0"), r.get("Ticker"), r.get("Bullish_Score"))
              for r in alle
              if r.get("Klasse") == "KJOP" and r.get("Handelsdag_0")]
    tapt: Dict[str, int] = {}
    ut = _rader("Innside", poster, tapt)
    if not ut:
        return [], f, _hvorfor_tomt(f, len(poster), tapt), ""
    return ut, f, "", ""


def les_alle_scorer(m: Master, logger) -> Tuple[List[Rad], List[Rad]]:
    """
    (alle scorerader, én statusrad per kilde).

    Regelen som gjelder alle fire: NULL RADER ER ALDRI EN HAKE. En kilde
    uten rader teller 50 for hvert eneste selskap, og da er den samlede
    scoren et gjennomsnitt av færre meninger enn navnet lover. Det skal stå
    i loggen og i mailen, ikke oppdages tre måneder senere.
    """
    alle: List[Rad] = []
    status: List[Rad] = []
    for navn, leser in (("PB-ROE", les_pbroe), ("NLP", les_nlp),
                        ("SentMom", les_sentmom), ("Innside", les_innside)):
        rader, fil, feil, notat = leser(m)
        if not rader and not feil:
            feil = (f"0 scorer lest{f' fra {fil.name}' if fil else ''} — kilden "
                    f"teller som nøytral 50 for alle selskaper.")
        alle.extend(rader)
        datoer = sorted({r["Dato"] for r in rader})
        status.append({
            "Kilde": navn, "Rader": len(rader),
            "Selskaper": len({r["Ticker"] for r in rader}),
            "Fra": datoer[0] if datoer else "", "Til": datoer[-1] if datoer else "",
            "Fil": fil.name if fil else "", "Alder": filalder(fil),
            "Merknad": feil, "Notat": notat})
        if feil:
            logger.warning(f"   ⚠️  {navn}: {feil}")
        else:
            logger.info(f"   ✓ {navn}: {len(rader)} scorer, "
                        f"{len({r['Ticker'] for r in rader})} selskaper, "
                        f"{datoer[0] if datoer else '—'} → "
                        f"{datoer[-1] if datoer else '—'}")
        if notat:
            logger.warning(f"   ⓘ  {navn}: {notat}")
    return alle, status


# ══════════════════════════════════════════════════════════════════════════
# DEL 3 — DEN SAMLEDE SCOREN
# ══════════════════════════════════════════════════════════════════════════

def persentiler(rader: List[Rad]) -> None:
    """
    Gjør hver kildes råscore om til en persentil 0–100, uten look-ahead.

    Persentilen regnes mot alt kilden har sett TIL OG MED denne datoen, aldri
    mot hele historikken. Forskjellen er ikke akademisk: en persentil regnet
    mot alle årene ville visst i 2019 hvordan 2025 ble, og backtesten hadde
    målt sin egen fasit i stedet for en prediksjon.

    De første observasjonene fra en kilde havner derfor nær midten uansett
    hvor gode de er — vi har ikke noe å sammenlikne dem med ennå, og det er
    riktig svar.
    """
    for kilde in KILDER:
        egne = sorted((r for r in rader if r["Kilde"] == kilde),
                      key=lambda r: (r["Dato"], r["Ticker"]))
        sett: List[float] = []
        i = 0
        while i < len(egne):
            # Alle radene fra samme dato skal rangeres mot det samme
            # grunnlaget, ellers avhenger scoren av rekkefølgen i filen.
            j = i
            while j < len(egne) and egne[j]["Dato"] == egne[i]["Dato"]:
                j += 1
            for r in egne[i:j]:
                v = float(r["Ra_Score"])
                if not sett:
                    r["Score"] = 50.0
                else:
                    under = bisect.bisect_left(sett, v)
                    like = bisect.bisect_right(sett, v) - under
                    r["Score"] = round(100.0 * (under + like / 2.0) / len(sett), 2)
            for r in egne[i:j]:
                bisect.insort(sett, float(r["Ra_Score"]))
            i = j


SAMLET_KOLONNER = ["Dato", "Ticker", "Samlet_Score", "Kilder",
                   "PB_ROE", "NLP", "SentMom", "Innside"]


def bygg_samlet(m: Master, rader: List[Rad], kalender: Sequence[date],
                logger) -> List[Rad]:
    """
    Én rad per (dag, selskap) for de best rangerte hver dag.

    En kilde som ikke har sagt noe om selskapet innenfor gyldighetsvinduet
    teller som 50 — nøytral, ikke null. Det er forskjellen på «modellen
    misliker selskapet» og «modellen kjenner det ikke», og de to skal ikke
    behandles likt: uten dette ville et selskap bare innsidemodellen kjenner
    fått samme samlede score som ett alle fire misliker.
    """
    vekt = {"PB-ROE": m.vekt_pbroe, "NLP": m.vekt_nlp,
            "SentMom": m.vekt_sentmom, "Innside": m.vekt_innside}
    gyldig = {"PB-ROE": m.gyldig_pbroe_dager, "NLP": m.gyldig_nlp_dager,
              "SentMom": m.gyldig_sentmom_dager, "Innside": m.gyldig_innside_dager}
    sum_vekt = sum(vekt.values()) or 1.0

    # (ticker, kilde) → sorterte (dato, score). Slås opp med bisect per dag.
    per: Dict[Tuple[str, str], List[Tuple[date, float]]] = {}
    for r in rader:
        d = IP.fra_iso(r["Dato"])
        if d is None or "Score" not in r:
            continue
        per.setdefault((r["Ticker"], r["Kilde"]), []).append((d, float(r["Score"])))
    for v in per.values():
        v.sort()

    tickere = sorted({t for t, _ in per})
    logger.info(f"🧮 Bygger samlet score for {len(tickere)} selskaper over "
                f"{len(kalender)} handledager …")

    ut: List[Rad] = []
    for dag in kalender:
        dagens: List[Rad] = []
        for t in tickere:
            deler: Dict[str, float] = {}
            for kilde in KILDER:
                serie = per.get((t, kilde))
                if not serie:
                    continue
                i = bisect.bisect_left(serie, (dag, float("-inf"))) - 1
                if i < 0:
                    continue
                d0, s0 = serie[i]
                if (dag - d0).days > gyldig[kilde]:
                    continue
                deler[kilde] = s0
            if len(deler) < m.min_kilder:
                continue
            samlet = sum(vekt[k] * deler.get(k, 50.0) for k in KILDER) / sum_vekt
            dagens.append({
                "Dato": IP.iso(dag), "Ticker": t,
                "Samlet_Score": round(samlet, 2), "Kilder": len(deler),
                "PB_ROE": round(deler["PB-ROE"], 1) if "PB-ROE" in deler else "",
                "NLP": round(deler["NLP"], 1) if "NLP" in deler else "",
                "SentMom": round(deler["SentMom"], 1) if "SentMom" in deler else "",
                "Innside": round(deler["Innside"], 1) if "Innside" in deler else "",
            })
        dagens.sort(key=lambda r: (-r["Samlet_Score"], r["Ticker"]))
        ut.extend(dagens[:m.topp_per_dag])
    logger.info(f"   {len(ut)} rader (topp {m.topp_per_dag} per dag)")
    return ut


# ══════════════════════════════════════════════════════════════════════════
# DEL 4 — KURSER FOR HELE UNIVERSET
# ══════════════════════════════════════════════════════════════════════════

def sikre_kurser(m: Master, tickere: Sequence[str], logger,
                 offline: bool = False) -> int:
    """
    Henter kurser for hvert selskap noen av de fire har en mening om.

    Uten dette kan den samlede porteføljen bare eie selskaper som tilfeldigvis
    har hatt en innsidemelding — og da er PB-ROE og de andre med i scoren, men
    ikke i porteføljen.
    """
    opp = m.oppsett()
    opp.lag_mapper()
    ønsket = sorted({oslo(t) for t in tickere if bar(t)})
    bok = IP.Kursbok(opp.s4_dir).last()
    mangler = ([t for t in ønsket if t not in bok.serier] if offline else ønsket)
    if not mangler:
        logger.info(f"📈 Alle {len(ønsket)} selskapene har kurser fra før.")
        return 0
    if offline:
        logger.warning(f"   ⚠️  {len(mangler)} selskaper mangler kurser, og "
                       f"--ikke-kjor er satt. De blir usynlige i backtesten.")
        return 0

    logger.info(f"📈 Kontrollerer og oppdaterer kurser for {len(mangler)} selskaper.")
    vm = IP.Vannmerke(opp.vannmerke_json, logger)
    IP._hent_alle_kurser(opp, logger, bok, vm, mangler,
                         opp.eldste_kurs(), date.today())
    vm.lagre()
    return len(mangler)


# ══════════════════════════════════════════════════════════════════════════
# DEL 5 — BACKTEST AV DEN SAMLEDE SCOREN
# ══════════════════════════════════════════════════════════════════════════
#
# Den samlede scoren mates inn i den SAMME motoren som innsidehandel-
# pipelinen bruker. Det er et bevisst valg: motoren er allerede prøvd mot ren
# støy og krever minst fem posisjoner, tak per posisjon og ingen look-ahead.
# En ny backtest skrevet fra bunnen ville måttet bevise alt det på nytt.

SAMLET_STRATEGI = IP.Strategi(
    "samlet", "alle fire modellene, likevektet, handlet daglig", takt="dag")


def _omsetning(bok: "IP.Kursbok", kalender: Sequence[date],
               tickere: Sequence[str], vindu: int = 20) -> Dict[Tuple[str, str], float]:
    """Snittomsetning i kronene FØR hver dag — aldri på dagen selv."""
    ut: Dict[Tuple[str, str], float] = {}
    for t in tickere:
        kurs = bok.justert_serie(t, kalender, "close", 5)
        vol = bok.volumserie(t, kalender, 5)
        for i in range(len(kalender)):
            fra = max(0, i - vindu)
            k = [x for x in kurs[fra:i] if x]
            v = [x for x in vol[fra:i] if x]
            if k and v:
                ut[(t, IP.iso(kalender[i]))] = (sum(k) / len(k)) * (sum(v) / len(v))
    return ut


def backtest_samlet(m: Master, samlet: Sequence[Rad], logger
                    ) -> Tuple[List[Rad], List[Rad], List[Rad], Rad]:
    """(equity, handler, beholdning, nøkkeltall). Tomme lister uten data."""
    opp = m.oppsett()
    bok = IP.Kursbok(opp.s4_dir).last()
    kalender = IP.les_kalenderfil(opp.kalender_csv)
    if not samlet or not bok.serier or not kalender:
        logger.warning("   Mangler score, kurser eller kalender — ingen backtest.")
        return [], [], [], {}

    tickere = sorted({oslo(r["Ticker"]) for r in samlet
                      if oslo(r["Ticker"]) in bok.serier})
    oms = _omsetning(bok, kalender, tickere)

    # Scoren gjøres om til «hendelser» motoren allerede forstår. Da arver den
    # samlede strategien alle reglene i motoren i stedet for å kopiere dem.
    hendelser: List[Rad] = []
    for r in samlet:
        t = oslo(r["Ticker"])
        if t not in bok.serier:
            continue
        hendelser.append({
            "Melding_ID": f"S-{r['Dato']}-{r['Ticker']}", "Dato": r["Dato"],
            "Klokkeslett": "09:00", "Selskap": r["Ticker"], "Ticker": t,
            "Klasse": "KJOP", "Tillit": "HOY", "Primaer_I_Klynge": "JA",
            "Bullish_Score": r["Samlet_Score"], "Handelsdag_0": r["Dato"],
            "Kurs_Status": "OK", "Rolle": "SAMLET",
            "Omsetning_Snitt_NOK": round(oms.get((t, r["Dato"]), 0.0), 0),
            "Verdi_NOK": "",
        })
    if not hendelser:
        logger.warning("   Ingen av selskapene i scoren har kurser.")
        return [], [], [], {}

    marked = IP.Marked(hendelser, opp)
    if not marked:
        logger.warning("   For kort periode til å simulere.")
        return [], [], [], {}
    equity, handler, nedskrevet, beholdning = IP.kjor_strategi(
        marked, SAMLET_STRATEGI, opp)
    if len(equity) < 40:
        return [], [], [], {}

    verdier = [float(r["Verdi_NOK"]) for r in equity]
    n = IP.nokkeltall(verdier, opp.risikofri_pst)
    inn = [float(r["Verdi_NOK"]) for r in equity
           if str(r["Dato"]) <= opp.inn_utvalg_slutt]
    ute = [float(r["Verdi_NOK"]) for r in equity
           if str(r["Dato"]) > opp.inn_utvalg_slutt]
    ute = inn[-1:] + ute
    navn = [int(r["Antall_Navn"] or 0) for r in equity]
    med = sorted(x for x in navn if x > 0)

    def pst(x: Any) -> Any:
        return round(x * 100, 2) if x is not None and x == x else ""

    maal: Rad = {
        "Strategi": "samlet", "Hvorfor": SAMLET_STRATEGI.hvorfor,
        "Periode": f"{equity[0]['Dato']} → {equity[-1]['Dato']}",
        "CAGR_Pst": pst(n.get("CAGR")),
        "Sharpe": round(n["Sharpe"], 2) if n["Sharpe"] == n["Sharpe"] else "",
        "MaxDD_Pst": pst(n.get("MaxDD")),
        "Ut_Sharpe": "", "Inn_Sharpe": "",
        "Andel_Kapital_Pst": round(100.0 * sum(
            float(r.get("Andel_Kapital") or 0.0) for r in equity) / len(equity), 1),
        "Median_Navn": round(IP.median(med), 1) if med else 0.0,
        "Maks_Vekt_Pst": round(100.0 * max(
            (float(r.get("Storste_Vekt") or 0.0) for r in equity), default=0.0), 1),
        "Omsetning_Per_Ar_Pst": "", "Drag_Ved_15_Pst": "",
        "Nedskrevet": nedskrevet, "Handler": len(handler),
    }
    for felt, verdier_ in (("Inn_Sharpe", inn), ("Ut_Sharpe", ute)):
        if len(verdier_) > 40:
            s = IP.nokkeltall(verdier_, opp.risikofri_pst).get("Sharpe")
            maal[felt] = round(s, 2) if s == s else ""
    omsatt = sum(IP.tolk_maskin(h.get("Verdi_NOK")) or 0.0 for h in handler)
    ar = max(0.5, len(equity) / 252.0)
    snitt_kap = sum(verdier) / len(verdier)
    maal["Omsetning_Per_Ar_Pst"] = round(100.0 * omsatt / ar / max(1.0, snitt_kap), 0)
    maal["Drag_Ved_15_Pst"] = round(
        float(maal["Omsetning_Per_Ar_Pst"]) * IP.DEFAULT_FRIKSJON, 1)

    logger.info(f"🎯 Samlet strategi: CAGR {maal['CAGR_Pst']} %, "
                f"Sharpe {maal['Sharpe']}, median {maal['Median_Navn']} navn, "
                f"{maal['Andel_Kapital_Pst']} % kapital ute")
    return equity, handler, beholdning, maal


# ══════════════════════════════════════════════════════════════════════════
# DEL 6 — MAILEN
# ══════════════════════════════════════════════════════════════════════════

def _tabell(hoder: Sequence[str], rader: Sequence[Sequence[str]]) -> str:
    if not rader:
        return '<p class="sub"><em>(ingen rader)</em></p>'
    h = "".join(f"<th>{IP.trygg(x)}</th>" for x in hoder)
    kropp = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>"
                    for r in rader)
    return f"<table><tr>{h}</tr>{kropp}</table>"


def strategisammendrag(m: Master, logger) -> Dict[str, Any]:
    """
    De tre enkeltstrategiene fra mail/mail_strategier.py, som data og HTML.

    Nøklene: «stil» (scopet CSS), «html» (alle kortene samlet, som reserve),
    «kort» ({navn: kort}) og «strategier» (rådata). Master bygger sitt eget
    sammendrag på tvers av FIRE strategier — innsidehandelen kommer fra
    pipelinen — og en ferdig tabell kan ikke slås sammen med en annen tabell.

    Denne seksjonen gikk før ut som sin EGEN mail, sendt av sitt eget script
    med sitt eget passord. To mailer per kjøring, to sett tall om de samme
    filene, og bare den ene av dem kom fram. Nå er master eneste avsender, og
    sammendraget er en seksjon her.

    Feiler aldri kjøringen. mail_strategier trenger pandas og numpy, som
    masteren ellers klarer seg uten, og en manglende pakke skal koste deg én
    seksjon — ikke hele mailen.
    """
    tomt: Dict[str, Any] = {"stil": "", "html": "", "kort": {},
                            "strategier": [], "ekstra": ""}
    # mail_strategier.py ligger flatt i roten her, ikke i en mail/-undermappe.
    # Før falt de tre enkeltstrategiene ut av mailen av den grunnen alene.
    mappe = SKRIPTMAPPE / "mail"
    if not (mappe / "mail_strategier.py").exists() and (
            SKRIPTMAPPE / "mail_strategier.py").exists():
        mappe = SKRIPTMAPPE
    if not (mappe / "mail_strategier.py").exists():
        logger.warning(f"   ⚠️  Fant ikke mail/mail_strategier.py i {mappe} — "
                       f"de tre enkeltstrategiene blir utelatt fra mailen.")
        return {**tomt, "html": (
            '<div class="kort"><h2>De tre enkeltstrategiene</h2>'
            '<p class="sub">Fant ikke <code>mail/mail_strategier.py</code> '
            f'ved siden av master.py ({mappe}). Legg mappen <code>mail/</code> '
            'der master.py ligger.</p></div>')}
    try:
        if str(mappe) not in sys.path:
            sys.path.insert(0, str(mappe))
        from mail_strategier import MailAlleStrategier  # type: ignore
        svar = MailAlleStrategier(send=False, returner_html=True,
                                  base_dir=m.excel_dir)
    except Exception as e:
        logger.warning(f"   ⚠️  Strategisammendraget feilet: {IP.feiltekst(e)}")
        return {**tomt, "html": (
            '<div class="kort"><h2>De tre enkeltstrategiene</h2>'
            f'<p class="sub">Kunne ikke bygges: {IP.trygg(IP.feiltekst(e))}. '
            'Resten av mailen er upåvirket.</p></div>')}
    if not isinstance(svar, dict):
        logger.info("   ℹ️  Ingen av de tre enkeltstrategiene har skrevet "
                    "resultatfiler — seksjonen er utelatt.")
        return tomt
    logger.info(f"   ✓ Strategisammendrag: {svar['n_aktive']}/"
                f"{svar['n_strategier']} strategier, "
                f"{svar['n_posisjoner']} posisjoner")
    ekstra = "".join(f'<div class="strategier">{svar.get(n, "")}</div>'
                     for n in ("overlapp_html", "datagrunnlag_html")
                     if svar.get(n))
    return {"stil": svar["stil"],
            "html": f'<div class="strategier">{svar["seksjoner"]}</div>',
            "kort": svar.get("kort", {}),
            "strategier": svar.get("strategier", []),
            "ekstra": ekstra}


def _dagens_samlede(samlet: Sequence[Rad], antall: int = 20) -> Tuple[str, str]:
    """(dato, HTML-tabell) for de best rangerte på siste dag i scoren."""
    if not samlet:
        return "", ""
    dag = max(r["Dato"] for r in samlet)
    dagens = sorted((r for r in samlet if r["Dato"] == dag),
                    key=lambda r: -float(r["Samlet_Score"]))[:antall]
    rader = [[f'<strong>{IP.trygg(r["Ticker"])}</strong>',
              f'<span class="opp">{float(r["Samlet_Score"]):.1f}</span>',
              str(r["Kilder"]),
              IP._e_tall(r.get("PB_ROE"), 0), IP._e_tall(r.get("NLP"), 0),
              IP._e_tall(r.get("SentMom"), 0), IP._e_tall(r.get("Innside"), 0)]
             for r in dagens]
    return dag, _tabell(["Ticker", "Samlet", "Kilder", "PB-ROE", "NLP",
                         "SentMom", "Innside"], rader)


# Hvor mange handler som vises per strategi. Samme tall som i
# mail_strategier.py — to ulike tall i samme mail er en unødvendig gåte.
ANTALL_HANDLER = 20

# Innsidehandelen kjører fem varianter av samme signal. Denne er hovedsaken;
# de fire andre står som en følsomhetstabell i vedlegget.
INNSIDE_HOVEDVARIANT = "daglig"

# Hvordan hver av de fire faktisk handler. De tre første kommer fra
# mail_strategier.py; innsidehandelen bor her, fordi den kommer fra pipelinen.
INNSIDE_HVORDAN = [
    ("Signal", "Innsidemeldinger fra Euronext. Teksten leses, og "
               "transaksjonens art hentes ut av MAR-skjemaet — et innsideSALG "
               "er ikke et svakt kjøp, det er motsatt fortegn."),
    ("Score", "0–100 per melding: rollen til den som handlet 30 %, hvor mye "
              "personen økte sin egen beholdning 28 %, om flere innsidere "
              "kjøpte i samme vindu 25 %, og beløpet 17 %. En helt ny posisjon "
              "gir 10 % påslag, og hele scoren skaleres med hvor sikkert "
              "uttrekket av teksten var."),
    ("Timing", "Datert til dagen meldingen faktisk kunne handles, ikke "
               "meldingsdatoen. En melding etter stengetid er først handlebar "
               "dagen etter — ellers ville backtesten kjøpt på informasjon den "
               "ikke hadde."),
    ("Exit", "Signalet varer et gitt antall dager, så selges posisjonen. "
             "Porteføljen er hel eller tom: minst 5 navn, ellers kontanter, "
             "med tak på hver enkelt posisjon."),
]


def innside_data(opp) -> Dict[str, Any]:
    """
    Innsidehandelen som én strategi, i samme form som de tre andre.

    Pipelinen skriver fem varianter av samme signal. Mailen viste dem før bare
    som en tabell med fem CAGR-er nederst — ingen beholdning, ingen handler.
    Da var den den eneste av de fire modellene du ikke kunne se hva faktisk
    gjorde. Her plukkes hovedvarianten ut og får samme behandling som resten.
    """
    alle = IP.les_csv(opp.strategier_csv)
    if not alle:
        return {}
    selection_file = opp.s6_dir / "selected_variant.json"
    selection = json.loads(selection_file.read_text(encoding="utf-8")) if selection_file.exists() else {}
    selected_name = selection.get("Variant", INNSIDE_HOVEDVARIANT)
    hoved = next((r for r in alle if str(r.get("Strategi")) == selected_name), alle[0])
    curve = [r for r in IP.les_csv(opp.strategi_equity_csv)
             if r.get("Strategi") == hoved.get("Strategi")]
    if curve:
        hoved["Periode"] = f"{curve[0]['Dato']} → {curve[-1]['Dato']}"
    hoved["Selection"] = selection
    navn = str(hoved.get("Strategi"))
    beholdning = [b for b in IP.les_csv(opp.beholdning_csv)
                  if str(b.get("Strategi")) == navn
                  and b.get("Ticker") != "(kontanter)"]
    handler = sorted((h for h in IP.les_csv(opp.strategi_handler_csv)
                      if str(h.get("Strategi")) == navn),
                     key=lambda h: str(h.get("Dato")))
    return {"maal": hoved, "varianter": alle,
            "beholdning": beholdning, "handler": handler}


def _hvordan_html(rader: Sequence[Tuple[str, str]]) -> str:
    """«Slik handler den» — signal, filtre, timing, exit."""
    if not rader:
        return ""
    celler = "".join(
        f'<tr><td style="width:96px;vertical-align:top;padding:5px 10px 5px 0;'
        f'font-weight:600;color:#1a237e;white-space:nowrap;">{lab}</td>'
        f'<td style="padding:5px 0;color:#444;line-height:1.55;">{tekst}</td></tr>'
        for lab, tekst in rader)
    return (f'<h3>Slik handler den</h3>'
            f'<table style="font-size:12.5px;margin-top:4px;">{celler}</table>')


def bygg_mail(m: Master, kjoring: Sequence[Rad], kilder: Sequence[Rad],
              samlet: Sequence[Rad], maal: Rad, beholdning: Sequence[Rad],
              handler: Sequence[Rad], strategi_stil: str = "",
              strategi_html: str = "",
              strategier: Optional[Sequence[Dict[str, Any]]] = None,
              kort: Optional[Dict[str, str]] = None,
              ekstra_html: str = "") -> str:
    opp = m.oppsett()
    dag, dagens_html = _dagens_samlede(samlet)

    kjoring_html = _tabell(
        ["Analyse", "Status", "Minutter", "Merknad"],
        [[IP.trygg(r["Analyse"]),
          f'<span class="{"opp" if r["Status"] == "OK" else "ned"}">{r["Status"]}</span>',
          f'{r["Minutter"]:.1f}', IP.trygg(r.get("Feil"))[:90]] for r in kjoring])

    def _merknad(r: Rad) -> str:
        deler = []
        if r.get("Merknad"):
            deler.append(f'<span style="color:#c62828;font-size:11px;">'
                         f'{IP.trygg(r["Merknad"])[:160]}</span>')
        if r.get("Notat"):
            deler.append(f'<span style="color:#8a6d3b;font-size:11px;">ⓘ '
                         f'{IP.trygg(r["Notat"])[:160]}</span>')
        return "<br>".join(deler) or "<span class='opp'>ok</span>"

    kilder_html = _tabell(
        ["Kilde", "Scorer", "Selskaper", "Fra", "Til", "Fil", "Merknad"],
        [[IP.trygg(r["Kilde"]), str(r["Rader"]), str(r["Selskaper"]),
          IP.trygg(r["Fra"]), IP.trygg(r["Til"]),
          f'<span style="font-size:11px;">{IP.trygg(r["Alder"])}</span>',
          _merknad(r)] for r in kilder])

    if maal:
        ruter = "".join([
            IP._e_rute("CAGR", IP._e_tall(maal.get("CAGR_Pst"), 1, " %", True),
                       "#2e7d32" if (IP.tolk_maskin(maal.get("CAGR_Pst")) or 0) > 0
                       else "#c62828"),
            IP._e_rute("Sharpe", IP._e_tall(maal.get("Sharpe"))),
            IP._e_rute("Sharpe ut-utvalg", IP._e_tall(maal.get("Ut_Sharpe"))),
            IP._e_rute("Max drawdown", IP._e_tall(maal.get("MaxDD_Pst"), 1, " %"),
                       "#c62828"),
            IP._e_rute("Kapital ute", IP._e_tall(maal.get("Andel_Kapital_Pst"), 0, " %")),
            IP._e_rute("Navn (median)", IP._e_tall(maal.get("Median_Navn"), 1)),
            IP._e_rute("Største posisjon", IP._e_tall(maal.get("Maks_Vekt_Pst"), 0, " %")),
            IP._e_rute("Drag ved 1,5 %", IP._e_tall(maal.get("Drag_Ved_15_Pst"), 1, " %"),
                       "#c62828"),
        ])
        aksjer = [b for b in beholdning if b.get("Ticker") != "(kontanter)"]
        beholdning_html = _tabell(
            ["Ticker", "Antall", "Kjøpt", "Inngang", "Siste", "Verdi", "Vekt", "Avk."],
            [[f'<strong>{IP.trygg(b["Ticker"])}</strong>',
              IP._e_tall(b.get("Antall"), 0), IP.trygg(b.get("Inn_Dato")),
              IP._e_tall(b.get("Inn_Kurs")), IP._e_tall(b.get("Siste_Kurs")),
              IP._e_tall(b.get("Verdi_NOK"), 0),
              IP._e_tall(b.get("Andel_Pst"), 1, " %"),
              IP._e_farge(b.get("Avk_Pst"))] for b in beholdning])
        dato_tekst = (f' per {IP.trygg(aksjer[0].get("Dato"))}' if aksjer else "")
        siste = sorted(handler, key=lambda h: str(h.get("Dato")))[-ANTALL_HANDLER:][::-1]
        handler_html = _tabell(
            ["Dato", "Type", "Ticker", "Beløp"],
            [[IP.trygg(h.get("Dato")),
              f'<span class="{"opp" if str(h.get("Type")) == "KJØP" else "ned"}">'
              f'{IP.trygg(h.get("Type"))}</span>',
              f'<strong>{IP.trygg(h.get("Ticker"))}</strong>',
              IP._e_tall(h.get("Verdi_NOK"), 0)] for h in siste])
        samlet_kort = f"""
<div class="kort">
    <h2>Den samlede strategien</h2>
    <p class="sub">Alle fire modellene, likevektet, handlet daglig — kjørt med
       den samme motoren som innsidehandel-pipelinen: minst
       {m.min_navn} posisjoner eller ingen, tak på hver posisjon, ingen
       look-ahead.</p>
    <div class="rute">{ruter}</div>
    {_hvordan_html([
        ("Signal", "Hver modell gjøres om til en persentil innenfor sin egen "
                   "historikk fram til i dag, og de fire vektes likt. En kilde "
                   "uten mening om et selskap teller 50, ikke null — det er "
                   "forskjellen på «modellen misliker selskapet» og «modellen "
                   "kjenner det ikke»."),
        ("Filtre", f"Minst {m.min_kilder} kilde må ha en mening, og den samlede "
                   f"scoren må over {m.min_score:.0f}. Topp "
                   f"{m.topp_per_dag} selskaper per dag går videre til "
                   f"backtesten."),
        ("Vekting", f"Likevektet, maksimalt {m.maks_navn} navn, og aldri færre "
                    f"enn {m.min_navn} — er det for få kvalifiserte, står "
                    f"resten i kontanter i stedet for å konsentrere risikoen."),
        ("Exit", "Rebalanserer når lista endrer seg, ikke hver dag. En score "
                 "har begrenset levetid per kilde (45 dager for de månedlige, "
                 "21–30 for de raskere), så en gammel mening faller ut av seg "
                 "selv."),
    ])}
    <h3>Alle valgte aksjer{dato_tekst}</h3>
    {beholdning_html}
    <h3>Siste {ANTALL_HANDLER} handler</h3>
    {handler_html}
</div>"""
    else:
        samlet_kort = """
<div class="kort">
    <h2>Den samlede strategien</h2>
    <div class="advarsel">Backtesten kunne ikke kjøres. Se «Kildene» over —
       som regel mangler én av de fire scoreloggene, eller kursene er ikke
       hentet for selskapene i scoren.</div>
</div>"""

    # ── Innsidehandelen som strategi nummer fire ─────────────────────────
    inn = innside_data(opp)
    egne = inn.get("varianter", [])
    egne_html = _tabell(
        ["Strategi", "CAGR", "Sharpe", "Sharpe ut", "Kapital ute", "Navn",
         "Største pos."],
        [[IP.trygg(r["Strategi"]), IP._e_farge(r.get("CAGR_Pst")),
          IP._e_tall(r.get("Sharpe")), IP._e_tall(r.get("Ut_Sharpe")),
          IP._e_tall(r.get("Andel_Kapital_Pst"), 0, " %"),
          IP._e_tall(r.get("Median_Navn"), 1),
          IP._e_tall(r.get("Maks_Vekt_Pst"), 0, " %")] for r in egne])

    if inn:
        i_maal = inn["maal"]
        i_ruter = "".join([
            IP._e_rute("CAGR", IP._e_tall(i_maal.get("CAGR_Pst"), 1, " %", True),
                       "#2e7d32" if (IP.tolk_maskin(i_maal.get("CAGR_Pst")) or 0) > 0
                       else "#c62828"),
            IP._e_rute("Sharpe", IP._e_tall(i_maal.get("Sharpe"))),
            IP._e_rute("Sharpe ut-utvalg", IP._e_tall(i_maal.get("Ut_Sharpe"))),
            IP._e_rute("Max drawdown", IP._e_tall(i_maal.get("MaxDD_Pst"), 1, " %"),
                       "#c62828"),
            IP._e_rute("Kapital ute",
                       IP._e_tall(i_maal.get("Andel_Kapital_Pst"), 0, " %")),
            IP._e_rute("Navn (median)", IP._e_tall(i_maal.get("Snitt_Navn"), 1)),
            IP._e_rute("Drag ved 1,5 %",
                       IP._e_tall(i_maal.get("Drag_Ved_15_Pst"), 1, " %"), "#c62828"),
        ])
        i_beholdning = _tabell(
            ["Ticker", "Antall", "Kjøpt", "Inngang", "Siste", "Verdi", "Vekt", "Avk."],
            [[f'<strong>{IP.trygg(b["Ticker"])}</strong>',
              IP._e_tall(b.get("Antall"), 0), IP.trygg(b.get("Inn_Dato")),
              IP._e_tall(b.get("Inn_Kurs")), IP._e_tall(b.get("Siste_Kurs")),
              IP._e_tall(b.get("Verdi_NOK"), 0),
              IP._e_tall(b.get("Andel_Pst"), 1, " %"),
              IP._e_farge(b.get("Avk_Pst"))] for b in inn["beholdning"]])
        i_siste = inn["handler"][-ANTALL_HANDLER:][::-1]
        i_handler = _tabell(
            ["Dato", "Type", "Ticker", "Beløp", "Kostnad"],
            [[IP.trygg(h.get("Dato")),
              f'<span class="{"opp" if str(h.get("Type")) == "KJØP" else "ned"}">'
              f'{IP.trygg(h.get("Type"))}</span>',
              f'<strong>{IP.trygg(h.get("Ticker"))}</strong>',
              IP._e_tall(h.get("Verdi_NOK"), 0),
              IP._e_tall(h.get("Kostnad_NOK"), 0)] for h in i_siste])
        innside_kort = f"""
<div class="kort">
    <h2>Innsidehandel — Oslo Børs</h2>
    <p class="sub">Meldepliktige innsidekjøp fra Euronext, lest ut av
       MAR-skjemaet og scoret 0–100.
       <span style="color:#aaa;">· innsidehandel_pipeline.py, variant
       «{IP.trygg(i_maal.get("Strategi"))}»</span></p>
    <div class="rute">{i_ruter}</div>
    {_hvordan_html(INNSIDE_HVORDAN)}
    <p>Variantvalg: {IP.trygg(i_maal.get("Selection", {}).get("Reason", "daglig baseline"))}
    Trening til {IP.trygg(i_maal.get("Selection", {}).get("Selection_Cutoff", "—"))}:
    {IP._e_tall(i_maal.get("Selection", {}).get("Train_CAGR_Pst"), 1, " % CAGR")}.
    Separat testperiode: {IP._e_tall(i_maal.get("Selection", {}).get("Test_CAGR_Pst"), 1, " % CAGR")}.
    Sammenligningen med baseline er lagret i variant_comparison.csv.</p>
    <h3>Alle valgte aksjer</h3>
    {i_beholdning}
    <h3>Siste {ANTALL_HANDLER} handler</h3>
    {i_handler}
    <h3>De fem variantene</h3>
    <p class="sub">Samme signal, ulik takt og konsentrasjon. Spennet mellom
       dem sier mer om hvor mye tilfeldighetene betyr enn den beste raden
       gjør alene.</p>
    {egne_html}
</div>"""
    else:
        innside_kort = """
<div class="kort">
    <h2>Innsidehandel — Oslo Børs</h2>
    <div class="advarsel">Pipelinen har ikke skrevet resultatfiler ennå.
       Kjør <code>innsidehandel.py</code>, eller se «Kjøringen» i vedlegget.</div>
</div>"""

    # ── Executive summary ────────────────────────────────────────────────
    def _tall(rad: Rad, *navn: str):
        for n in navn:
            v = IP.tolk_maskin(rad.get(n)) if rad else None
            if v is not None:
                return v
        return None

    sam_rader: List[List[str]] = []
    posisjons_rader: List[List[str]] = []
    forklaringer: List[str] = []

    def _legg_til(navn: str, kort_om: str, cagr, bench, sharpe, mdd,
                  periode: str, n_handler, tickere: Sequence[str],
                  advarsel: str = "") -> None:
        merav = (cagr - bench) if (cagr is not None and bench is not None) else None
        sam_rader.append([
            f'<strong>{IP.trygg(navn)}</strong>'
            + (f'<br><span class="ned" style="font-size:11px;">⚠ {IP.trygg(advarsel)}</span>'
               if advarsel else ""),
            IP._e_farge(cagr, 1), IP._e_tall(bench, 1, " %"),
            IP._e_farge(merav, 1), IP._e_tall(sharpe),
            IP._e_tall(mdd, 1, " %"),
            f'<span style="font-size:11px;">{IP.trygg(periode)}</span>',
            IP._e_tall(n_handler, 0), str(len(tickere)),
        ])
        posisjons_rader.append([
            f'<strong>{IP.trygg(navn)}</strong>', str(len(tickere)),
            (", ".join(IP.trygg(t) for t in tickere) if tickere
             else '<em style="color:#888;">kontanter</em>')])
        forklaringer.append(
            f'<tr><td style="width:190px;vertical-align:top;padding:6px 12px 6px 0;'
            f'font-weight:600;color:#1a237e;">{IP.trygg(navn)}</td>'
            f'<td style="padding:6px 0;color:#444;line-height:1.55;">{kort_om}</td></tr>')

    if maal:
        _legg_til("Den samlede strategien",
                  "De fire modellene under, vektet likt og handlet som én "
                  "portefølje. Det er denne som er produktet — de fire andre "
                  "er ingrediensene.",
                  _tall(maal, "CAGR_Pst"), None, _tall(maal, "Sharpe"),
                  _tall(maal, "MaxDD_Pst"),
                  str(maal.get("Periode") or "—"),
                  len(handler),
                  [str(b.get("Ticker")) for b in beholdning
                   if b.get("Ticker") != "(kontanter)"])

    for s in (strategier or []):
        if s.get("mangler"):
            sam_rader.append([f'<strong>{IP.trygg(s["navn"])}</strong>',
                              '<span class="ned">ikke kjørt</span>',
                              "—", "—", "—", "—", "—", "—", "—"])
            posisjons_rader.append([f'<strong>{IP.trygg(s["navn"])}</strong>',
                                    "—", '<em style="color:#888;">ikke kjørt</em>'])
            forklaringer.append(
                f'<tr><td style="padding:6px 12px 6px 0;font-weight:600;'
                f'color:#1a237e;">{IP.trygg(s["navn"])}</td>'
                f'<td style="padding:6px 0;color:#888;">{IP.trygg(s["mangler"])}</td></tr>')
            continue
        n = s["n"]
        tynt = ""
        if not n.get("cagr_meningsfull", True):
            tynt = f"bare {n.get('n_ar') or 0:.1f} år — bruk Total, ikke CAGR"
        elif (n.get("n_lukket") or 0) < 20:
            tynt = f"{n.get('n_lukket')} lukkede handler — tallene er støy"
        _legg_til(s["navn"], s["beskrivelse"], n.get("cagr"),
                  n.get("benchmark_cagr"), n.get("sharpe"), n.get("mdd"),
                  n.get("periode") or "—", n.get("n_handler"),
                  [str(p.get("ticker")) for p in s["posisjoner"]
                   if p.get("ticker")], tynt)

    if inn:
        _legg_til("Innsidehandel — Oslo Børs",
                  "Meldepliktige innsidekjøp på Oslo Børs, scoret på hvem som "
                  "kjøpte, hvor mye de økte sin egen beholdning, og om flere "
                  "innsidere kjøpte samtidig.",
                  _tall(i_maal, "CAGR_Pst"), None, _tall(i_maal, "Sharpe"),
                  _tall(i_maal, "MaxDD_Pst"),
                  IP.trygg(i_maal.get("Periode") or "—"), None,
                  [str(b.get("Ticker")) for b in inn["beholdning"]])

    # ── Rekkefølgen i detaljdelen ────────────────────────────────────────
    # Fundamentalt først, så de tre signalbaserte i økende «mykhet»:
    # innsidere handler med egne penger, ledelsen skriver om egen drift,
    # offentligheten skriver om alt. Innsidehandelen kommer fra pipelinen og
    # limes inn mellom de to andre.
    #
    # Kortene fra mail_strategier bruker klassen .card, som bare gjelder inne
    # i <div class="strategier"> — derfor pakkes hvert av dem for seg.
    def _pakk(navn: str) -> str:
        html = (kort or {}).get(navn, "")
        return f'<div class="strategier">{html}</div>' if html else ""

    if kort:
        kort_html = (_pakk("PB-ROE-Momentum") + innside_kort
                     + _pakk("NLP Sentiment — ledelse")
                     + _pakk("Sentiment Momentum v3.1"))
    else:
        # Ingen rådata fra mail_strategier (pandas mangler, eller ingen av de
        # tre har kjørt). Da står innsidehandelen alene, med sin egen merknad.
        kort_html = (strategi_html or "") + innside_kort

    sammendrag = f"""
<div class="kort">
    <h2>Executive summary</h2>
    <p class="sub">Alle strategiene side om side. Kolonnen «Periode» er den
       viktigste: en CAGR fra åtte måneder og en fra fire år hører ikke hjemme
       i samme sammenligning, uansett hvor like de ser ut.</p>
    {_tabell(["Strategi", "CAGR", "Benchmark", "Meravk.", "Sharpe",
              "Max DD", "Periode", "Handler", "Posisjoner"], sam_rader)}

    <h3>Posisjoner nå</h3>
    {_tabell(["Strategi", "Antall", "Aksjer"], posisjons_rader)}

    <h3>Strategiene kort</h3>
    <table style="font-size:12.5px;">{"".join(forklaringer)}</table>

    <div class="advarsel">
        <strong>Alt dette er backtester.</strong> Ingen av dem trekker fra
        transaksjonskostnader, og modellene er utviklet på de samme årene de
        måles på.{f' Den samlede strategien taper {IP._e_tall(maal.get("Drag_Ved_15_Pst"), 1, " %")} i året ved 1,5 % spread — les det tallet før du leser CAGR-en.' if maal and maal.get("Drag_Ved_15_Pst") not in (None, "") else ""}
    </div>
</div>"""

    return f"""<html><head><meta charset="utf-8"><style>{IP.EPOST_STIL}
{strategi_stil}</style></head>
<body><div class="beholder">

<div class="topp">
    <h1>Samlet aksjeanalyse</h1>
    <p>Fire modeller · én score · bygget {datetime.now():%Y-%m-%d %H:%M}</p>
</div>

{sammendrag}

<div class="kort" style="background:#1a237e;color:#fff;padding:14px 25px;">
    <h2 style="color:#fff;margin:0;">Strategiene i detalj</h2>
    <p class="sub" style="color:#c5cae9;margin:4px 0 0;">Hvordan hver av dem
       handler, hvilke aksjer den står i nå, og de siste
       {ANTALL_HANDLER} handlene.</p>
</div>

{samlet_kort}

{kort_html}

<div class="kort" style="background:#455a64;color:#fff;padding:14px 25px;">
    <h2 style="color:#fff;margin:0;">Vedlegg</h2>
    <p class="sub" style="color:#cfd8dc;margin:4px 0 0;">Dagens signalliste og
       kontrollene bak tallene over.</p>
</div>

<div class="kort">
    <h2>Dagens samlede liste{f" — {IP.trygg(dag)}" if dag else ""}</h2>
    <p class="sub">Rangert på den samlede scoren. Kolonnene bak viser hva hver
       modell mente; tomt felt betyr at modellen ikke har en mening om
       selskapet, og da teller den som 50.</p>
    {dagens_html}
    <div class="advarsel">
        <strong>Dette er en signalliste, ikke et resultat.</strong>
        Scorene er persentiler regnet mot hver modells egen historikk fram til
        i dag — ingen av dem er etterprøvd for akkurat denne dagen.
    </div>
</div>

<div class="kort">
    <h2>Kjøringen</h2>
    {kjoring_html}
</div>

<div class="kort">
    <h2>Kildene</h2>
    <p class="sub">Hva hver modell faktisk leverte av score per dato og selskap.
       Uten historikk fra en kilde teller den som nøytral, ikke som null.</p>
    {kilder_html}
</div>

{ekstra_html}

<div class="fot">
    <p>Alt over er backtester på historiske data, ikke en live portefølje.</p>
    <p>master.py · {datetime.now():%Y-%m-%d %H:%M:%S}</p>
</div>

</div></body></html>"""


# ══════════════════════════════════════════════════════════════════════════
# HOVEDLØP
# ══════════════════════════════════════════════════════════════════════════

def validate_sources(m, since_ns=None):
    """(errors, files, per_strategi, kurver).

    Feil som kan tilskrives ÉN strategi havner i per_strategi, ikke i errors.
    Da kan den strategien utelates fra fellestallene i stedet for å velte hele
    mailen. Kurvene gis videre slik at eksportene ikke leses to ganger.
    """
    errors, files, per_strategi = [], [], {}
    from portfolio_blend import load_production_curves
    try:
        kurver = load_production_curves(m.excel_dir, m.innside_dir)
    except Exception as exc:                                 # noqa: BLE001
        kurver = [{"name": n, "observations": [], "valid": False,
                   "errors": [f"eksportene kunne ikke leses: {IP.feiltekst(exc)}"]}
                  for n in STRATEGIER]

    def _per(navn, tekst):
        per_strategi.setdefault(navn, []).append(str(tekst))

    for component in kurver:
        name = component['name']
        for e in component.get('errors', []):
            _per(name, e)
        source = component.get('source')
        if source:
            files.append({'source': name, **source})
            if since_ns is not None and source['mtime_ns'] < since_ns:
                _per(name, "eksporten ble ikke oppdatert av denne kjøringen")
    opp = m.oppsett()
    _innside = "Innsidehandel — Oslo Børs"
    for path in (opp.strategier_csv, opp.strategi_equity_csv,
                 opp.beholdning_csv, opp.strategi_handler_csv,
                 opp.s6_dir / "selected_variant.json"):
        try:
            stat = path.stat()
            files.append({"source": "Insider report", "path": str(path.resolve()),
                          "mtime_ns": stat.st_mtime_ns, "size": stat.st_size})
            if since_ns is not None and stat.st_mtime_ns < since_ns:
                _per(_innside, f"innsiderapporten ble ikke oppdatert: {path.name}")
        except OSError:
            _per(_innside, f"innsiderapporten mangler: {path.name}")
    return errors, files, per_strategi, kurver


def failure_report(errors, statusblokk=""):
    """Selv en mislykket kjøring skal lede med hva som kom ned og hva som ikke."""
    return ('<html><meta charset="utf-8"><body><h1>Analysis incomplete</h1>'
            + (statusblokk or '')
            + '<p>No current performance report was issued. Correct these errors and rerun.</p><ul>'
            + ''.join('<li>' + IP.trygg(e) + '</li>' for e in errors) + '</ul></body></html>')


def calculate_capital_portfolio(m, datastatus, rebalance="monthly"):
    """Bland de eksporterte strategikurvene med lik vekt til hver som er fersk.

    Fire gir 25 % hver, tre gir 33 %. En strategi uten ferske data erstattes
    ikke med null avkastning, og forrige verdi videreføres ikke som om den var
    dagens — den utelates, og datastatusen øverst i mailen sier hvem og hvorfor.
    """
    if rebalance != "monthly":
        raise RuntimeError("Bare månedlig rebalansering kan belegges av den "
                           "månedlige PB-ROE-kurven.")
    med = set(datastatus.get("included") or ())
    kurver = [k for k in datastatus.get("curves") or ()
              if str(k.get("name")) in med]
    return bland_likevektet(kurver, as_of=date.today(),
                            startkapital=m.startkapital,
                            risikofri_pst=m.oppsett().risikofri_pst,
                            utelatte=datastatus.get("excluded") or ())


def ensure_robust_insider_selection(m, logger):
    path = m.oppsett().s6_dir / "selected_variant.json"
    if not m.oppsett().strategier_csv.exists():
        return
    saved = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    from insider_selection import POLICY_VERSION
    manual = os.environ.get("AKSJE_INNSIDE_VALG", "").strip()
    same_override = (saved.get("Variant") == manual and saved.get("Manual_Override") is True
                     if manual else not saved.get("Manual_Override", False))
    if (saved.get("Policy_Version") == POLICY_VERSION
            and saved.get("Selection_Cutoff") == m.inn_utvalg_slutt and same_override):
        return
    from insider_selection import build_insider_selection
    build_insider_selection(m.insider_oppsett(), logger)


def kjor(argv: Optional[Sequence[str]] = None) -> int:
    from runtime_config import configure_console
    configure_console()
    p = argparse.ArgumentParser(
        prog="master",
        description="Kjører fire aksjeanalyser, fordeler 25 % kapital til hver, "
                    "beregner felles portefølje og sender én mail.")
    p.add_argument("--ikke-kjor", action="store_true",
                   help="ikke kjør analysene, bruk resultatfilene som ligger der")
    p.add_argument("--bare-mail", action="store_true",
                   help="hopp over backtesten, send det som allerede er regnet ut")
    p.add_argument("--mail-kladd", action="store_true",
                   help="bygg mailen og lagre kopien, men ikke send den")
    p.add_argument("--mappe", metavar="STI", help="datamappen til innsidehandel")
    p.add_argument("--excel-dir", metavar="STI", help="ExcelData-mappen")
    p.add_argument("--mail-til", metavar="ADRESSE", help="mottaker(e), kommaskilt")
    p.add_argument("--hent-nlp", action="store_true",
                   help="hent NLP-artikler på nytt før backtesten (dyp "
                        "skraping av Euronext — tar timer, og utvider "
                        "historikken ledelses-sentimentet kan måles på). Henting "
                        "er standard; --ingen-nlp-hent bruker lagrede artikler")
    p.add_argument("--nlp-skraper", metavar="UTGAVE", choices=("v4", "v4.1"),
                   help="hvilken skraper --hent-nlp bruker: v4 = 10 artikler "
                        "per selskap, v4.1 = 100 med paginering (standard)")
    p.add_argument("--nlp-motor", metavar="UTGAVE", choices=("v4", "v4.1"),
                   help="bare for den MÅNEDLIGE reservemotoren som kjører "
                        "sammen med --hent-nlp. Kilden er hendelseslaben, og "
                        "hvilken kombinasjon den velger styres med "
                        "AKSJE_SENT_VALG (f.eks. S1|F08)")
    p.add_argument("--sent-valg", metavar="INNGANG|EXIT",
                   help="lås hvilken av de 384 kombinasjonene ledelses-"
                        "sentimentet skal handles med, f.eks. «S1|TP10». "
                        "Uten denne velges høyeste CAGR i treningsperioden")
    p.add_argument("--feilsok", action="store_true", help="full sporing i loggen")
    p.add_argument("--ingen-nlp-hent", action="store_true", help="use existing management article data")
    p.add_argument("--selection-cutoff", default="2025-06-30", help="last date used for variant selection")
    p.add_argument("--innside-valg", help="optional fixed insider variant, e.g. daglig")
    p.add_argument("--preflight", action="store_true", help="check inputs and packages without downloading or sending")
    p.add_argument("--rebalance", choices=("monthly",), default="monthly",
                   help="25 percent to each strategy at completed month-end; PB-ROE supplies monthly NAV")
    a = p.parse_args(list(argv) if argv is not None else None)

    m = Master()
    if a.mappe:
        m.innside_dir = Path(a.mappe).expanduser()
        m.ut_dir = m.innside_dir / "7_master"
    if a.excel_dir:
        m.excel_dir = Path(a.excel_dir).expanduser()
    if a.mail_til:
        m.epost_til = a.mail_til
    # Bryterne til NLP-strategien går gjennom miljøet. Only_260820.py leser
    # dem selv, så masteren slipper å importere en 8000-linjers fil bare for
    # å sette et flagg — og du slipper å redigere den for å skru på en
    # skraping.
    os.environ["AKSJE_BASE_DIR"] = str(m.excel_dir.resolve())
    os.environ["AKSJE_SELECTION_CUTOFF"] = a.selection_cutoff
    date.fromisoformat(a.selection_cutoff)  # Validate before a long download starts.
    m.inn_utvalg_slutt = a.selection_cutoff
    if a.innside_valg:
        os.environ["AKSJE_INNSIDE_VALG"] = a.innside_valg
    if a.bare_mail:
        a.ikke_kjor = True
    os.environ["AKSJE_NLP_ONLY_DOWNLOAD"] = "1"
    os.environ["AKSJE_NLP_HENT"] = "1" if (a.hent_nlp or not a.ingen_nlp_hent) else "0"
    if a.preflight:
        from run_strategy import preflight
        return preflight(m.excel_dir)
    if a.nlp_skraper:
        os.environ["AKSJE_NLP_SKRAPER"] = a.nlp_skraper
    if a.nlp_motor:
        os.environ["AKSJE_NLP_MOTOR"] = a.nlp_motor
    if a.sent_valg:
        os.environ["AKSJE_SENT_VALG"] = a.sent_valg
    m.ut_dir.mkdir(parents=True, exist_ok=True)

    logger = IP.lag_logger(m.ut_dir / "master.log", feilsok=bool(a.feilsok))
    logger.info(f"\n{'═' * 74}\nMASTER — FIRE STRATEGIER, 25 % KAPITAL TIL HVER\n{'═' * 74}")
    logger.info(f"   Innsidedata : {m.innside_dir}")
    logger.info(f"   ExcelData   : {m.excel_dir}")

    started = time.time_ns()
    errors: List[str] = []
    notater: List[str] = []
    kjoring: List[Rad] = []
    if not a.ikke_kjor:
        missing = protected_input_errors(m.excel_dir)
        if missing:
            # Ikke lenger fatalt for HELE kjøringen. En manglende grunnlagsfil
            # rammer de strategiene som leser den; de øvrige skal fortsatt
            # kjøre, og datastatusen sier hvem som mangler hva.
            logger.warning("   ⚠️  Grunnlagsdata mangler: %s", "; ".join(missing))
            notater.append("Grunnlagsdata mangler: " + "; ".join(missing))
        kjoring = kjor_alle(m, logger, notater)
    # Old saved selection must be upgraded before it enters a capital sleeve.
    if a.ikke_kjor and not a.bare_mail:
        try:
            ensure_robust_insider_selection(m, logger)
        except Exception as exc:
            logger.exception("Insider selection failed")
            errors.append(str(exc))
    source_errors, source_files, per_strategi, kurver = validate_sources(
        m, None if a.ikke_kjor else started)
    errors.extend(source_errors)
    # Hver strategi vurderes for seg. En uten ferske data utelates fra
    # fellestallene og navngis øverst i mailen — den stopper ikke de andre.
    datastatus = bygg_datastatus(kurver, kjoring, per_strategi,
                                 as_of=date.today(), merknader=notater)
    for _rad in datastatus["rows"]:
        logger.info("   Datastatus  %-26s %-9s %s", _rad["Strategi"],
                    _rad["Status"], _rad["Begrunnelse"])
    portfolio = None
    manifest_path = m.ut_dir / "completed_run.json"
    if not errors:
        try:
            if a.bare_mail:
                saved = json.loads(manifest_path.read_text(encoding="utf-8"))
                if saved.get("format_version") != 2 or saved.get("method") != "capital_25_each":
                    raise RuntimeError("Saved report used the old score blend; recalculate the capital portfolio first")
                if saved.get("sources") != source_files:
                    raise RuntimeError("Saved results refer to different source files; rerun calculation")
                portfolio = saved["portfolio"]
            else:
                portfolio = calculate_capital_portfolio(
                    m, datastatus, rebalance=a.rebalance)
                if not portfolio.get("equity") or not portfolio.get("metrics"):
                    raise RuntimeError("Capital portfolio did not produce a usable result")
                IP.skriv_csv(m.ut_dir / "samlet_equity.csv", portfolio["equity"])
                IP.skriv_csv(m.ut_dir / "samlet_handler.csv", portfolio["trades"],
                             ["Dato", "Strategi", "Type", "Verdi_NOK", "Transfer_NOK", "Kostnad_NOK"])
                IP.skriv_csv(m.ut_dir / "samlet_beholdning.csv", portfolio["holdings"])
                IP.skriv_csv(m.ut_dir / "samlet_sammenligning.csv", portfolio["components"])
        except Exception as exc:
            logger.exception("Capital calculation failed")
            errors.append(str(exc))

    # Valid individual results can still explain an incomplete combined run.
    sections = strategisammendrag(m, logger)
    try:
        insider = innside_data(m.oppsett())
    except Exception as exc:
        insider = {}
        errors.append("Insider report: " + str(exc))
    # Datastatusen sier allerede hvilke strategier som mangler data, og de er
    # da utelatt fra fellestallene. Da skal en manglende seksjon ikke i tillegg
    # gjøre hele kjøringen ufullstendig.
    alle_med = bool(datastatus.get("all_ok"))
    if portfolio and alle_med and (len(sections.get("strategier", [])) != 3
                                   or any(x.get("mangler") for x in sections["strategier"])):
        errors.append("One or more strategy report sections are missing or invalid")
    if portfolio and alle_med and not insider:
        errors.append("Insider results missing")
    if portfolio and not errors:
        payload = {"format_version": 2, "method": "capital_25_each",
                   "completed": datetime.now().isoformat(), "sources": source_files,
                   "portfolio": portfolio}
        try:
            IP.skriv_atomisk(manifest_path, lambda tmp: tmp.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8"))
        except Exception as exc:
            logger.exception("Could not save completed portfolio")
            errors.append("Could not save completed portfolio: " + str(exc))
    try:
        statusblokk = statusblokk_html(datastatus)
    except Exception as exc:                                 # noqa: BLE001
        logger.warning("Datastatusblokken kunne ikke bygges: %s", exc)
        statusblokk = ""
    try:
        if sections.get("kort") or insider:
            from capital_mail import render_capital_mail
            html = render_capital_mail(m, kjoring, portfolio, sections, insider, errors)
            # capital_mail er urørt; blokken settes inn rett etter <body>, så
            # datastatus står først uansett hvordan resten av mailen ser ut.
            if statusblokk and "<body>" in html:
                html = html.replace("<body>", "<body>" + statusblokk, 1)
            elif statusblokk:
                html = statusblokk + html
        else:
            html = failure_report(errors or ["No strategy reports are available"],
                                  statusblokk)
    except Exception as exc:
        logger.exception("Email rendering failed")
        errors.append("Email rendering failed: " + str(exc))
        html = failure_report(errors, statusblokk)
    if errors:
        subject = "Analysis incomplete — ufullstendig beregning"
    else:
        _antall = int(((portfolio or {}).get("metrics") or {}).get("N_Strategier", 4) or 4)
        subject = ("Samlet aksjeanalyse — 25 % i hver strategi" if _antall == 4
                   else f"Samlet aksjeanalyse — {100.0 / _antall:.0f} % i hver "
                        f"av {_antall} strategier")
        if not datastatus.get("all_ok"):
            subject += f" · {len(datastatus.get('excluded') or ())} uten ferske data"
        cagr = (portfolio or {}).get("metrics", {}).get("CAGR_Pst")
        if cagr not in (None, ""):
            subject += f" · samlet CAGR {float(cagr):.2f} %"
        if a.ikke_kjor:
            subject += " · lagrede data"
    subject += f" — {datetime.now():%Y-%m-%d}"
    copy_path = m.ut_dir / f"master_mail_{datetime.now():%Y%m%d_%H%M%S}.html"
    copy_path.write_text(html, encoding="utf-8")
    logger.info("Email copy: %s", copy_path)
    if errors:
        for error in errors:
            logger.error(error)
    if not a.mail_kladd and not IP.send_epost(m.oppsett(), html, subject, logger):
        logger.error("Email delivery failed; local HTML copy is available")
        for handler in list(logger.handlers):
            handler.close()
            logger.removeHandler(handler)
        return 3
    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)
    return 2 if errors else 0


if __name__ == "__main__":
    sys.exit(kjor())
