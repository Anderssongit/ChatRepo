# -*- coding: utf-8 -*-
"""Bygg patches.json av de urørte rotfilene.

Hver redigering oppgir et LINJEINTERVALL i den originale fila, ikke en avskrift
av den. Originalblokken hentes derfor ut av fila selv og kan ikke skrives feil.
Skriptet kontrollerer at hver blokk finnes nøyaktig én gang, at markøren ikke
allerede står i fila, og at resultatet fortsatt parser som Python.

    python 2026-09-20/build_patches.py            # skriv patches.json
    python 2026-09-20/build_patches.py --sjekk    # bare kontroller

Rotfilene åpnes aldri for skriving.
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FOLDER = HERE.name


ANCHOR_FILE = HERE / "anchors.json"


def load_anchors() -> Dict[str, str]:
    if not ANCHOR_FILE.is_file():
        return {}
    return json.loads(ANCHOR_FILE.read_text(encoding="utf-8"))


ANCHORS: Dict[str, str] = load_anchors()


def read(name: str) -> str:
    with (ROOT / name).open(encoding="utf-8", newline="") as handle:
        return handle.read()


def lines_of(text: str) -> List[str]:
    """Del paa \\n alene, slik awk/sed/grep teller linjer.

    En CR som avslutter linja blir staaende i innholdet. Split og join paa
    \\n er dermed tapsfritt: en blokk hentet ut slik er byte for byte den
    samme som i fila, ogsaa naar fila blander CRLF og LF - og
    insider_selection.py gjoer nettopp det, 269 mot 37 linjer.
    """
    return text.split("\n")


def block_of(text: str, first: int, last: int) -> str:
    """Den eksakte teksten paa linje first..last, med opprinnelige linjeskift."""
    return "\n".join(lines_of(text)[first - 1:last])


def dominant_newline(block: str) -> str:
    """\\r\\n hvis flertallet av linjene i blokken slutter slik, ellers \\n."""
    rows = block.split("\n")
    return "\r\n" if sum(r.endswith("\r") for r in rows) * 2 >= len(rows) else "\n"


def with_newline(replacement: str, newline: str) -> str:
    """Skriv erstatningen med blokkens egen linjeskiftkonvensjon."""
    rows = replacement.split("\n")
    return "\n".join(r + "\r" for r in rows) if newline == "\r\n" else "\n".join(rows)


# ---------------------------------------------------------------------------
# Redigeringene. (fil, navn, markør, førstelinje, sistelinje, erstatning)
# Linjenumrene er 1-baserte og inklusive, og peker inn i den URØRTE fila.
# ---------------------------------------------------------------------------

EDITS: List[Tuple[str, str, str, int, int, str]] = []


def edit(file: str, name: str, marker: str, first: int, last: int, replacement: str) -> None:
    EDITS.append((file, name, marker, first, last, replacement))


# ══════════════════════════════════════════════════════════════════════════
# master.py
# ══════════════════════════════════════════════════════════════════════════

edit("master.py", "master.py :: hente- og statushjelpere", "def hent_grunnlagsdata", 223, 223, f'''
def _fikspakke() -> bool:
    """Legg rettelsesmappen på sys.path uten å importere noe med det samme."""
    folder = SKRIPTMAPPE / "{FOLDER}"
    if folder.is_dir() and str(folder) not in sys.path:
        sys.path.insert(0, str(folder))
    return folder.is_dir()


def hent_grunnlagsdata(m: Master, logger, *, steg, force: bool = False) -> List[Rad]:
    """Bygg grunnlagsfilene masteren tidligere bare KONTROLLERTE at fantes.

    AllTickers_OSEBX_TW_260428.xlsx, Stock_Prices_*.xlsx og
    Step4_Sentiment_Changes_*.xlsx kom fra et annet program. Ingen hadde kjørt
    det siden 2026-08-19, og det er hele grunnen til at Sentiment Momentum
    backtestet måned gamle kurser og likevel ble rapportert som OK.

    Alt som trengs for å bygge dem lastes allerede ned av denne pakken:
    aksjelista og kursene av innsidepipelinen, artikkelscorene av FinBERT-
    skrapingen. Masteren bygger dem derfor selv. De hash-beskyttede strategiene
    røres ikke — dette skriver filene de leser, i formatet de forventer.

    Statusradene bærer Kilde, Handling, Rader og Siste videre, slik at
    datastatusblokken i mailen kan si hva som faktisk kom ned.
    """
    start = time.time()
    if not _fikspakke():
        return [{{"Analyse": "Datahenting", "Status": "FEIL", "Minutter": 0.0,
                 "Feil": "Fant ikke mappen {FOLDER} ved siden av master.py"}}]
    try:
        from data_acquisition import build_all
        rader = build_all(m.excel_dir, m.oppsett(), logger, steps=steg, force=force)
    except KeyboardInterrupt:
        raise
    except Exception as e:
        logger.exception("Datahenting feilet")
        return [{{"Analyse": "Datahenting", "Status": "OK", "Handling": "FEIL",
                 "Kilde": "Datahenting", "Merknad": IP.feiltekst(e)[:180],
                 "Minutter": round((time.time() - start) / 60.0, 1),
                 "Feil": "feil — " + IP.feiltekst(e)[:180]}}]
    minutter = round((time.time() - start) / 60.0, 1)
    ut: List[Rad] = []
    for rad in rader:
        logger.info("   %-11s %-22s %s", rad["Handling"], rad["Kilde"], rad["Merknad"])
        # Status er alltid OK: henting som feiler skal ikke velte en kjøring der
        # filene allerede ligger der og er ferske. Handling bærer utfallet, og
        # både bygg_sentimentendringer og datastatusblokken leser den.
        ut.append({{"Analyse": "Data: " + str(rad["Kilde"]), "Status": "OK",
                   "Handling": rad["Handling"], "Kilde": rad["Kilde"],
                   "Merknad": rad["Merknad"], "Rader": rad.get("Rader"),
                   "Siste": rad.get("Siste"), "Minutter": minutter,
                   "Feil": f'{{rad["Handling"].lower()}} — {{rad["Merknad"]}}'}})
        minutter = 0.0
    return ut


def bygg_sentimentendringer(m: Master, logger) -> int:
    """Step4-endringene, bygget av FinBERT-scorene skrapingen nettopp skrev.

    Må kjøre ETTER skrapingen og FØR SentimentMomentumV31, som leser fila.
    """
    rader = hent_grunnlagsdata(m, logger, steg=("step4",))
    feil = [r["Feil"] for r in rader if r.get("Handling") == "FEIL"]
    if feil:
        # Her ER det fatalt for SentMom: uten en fersk Step4-fil leser den den
        # forrige, og da er vi tilbake i 2026-09-18.
        raise RuntimeError("; ".join(feil))
    return 0


def bygg_datastatus(m: Master, kjoring: Sequence[Rad],
                    per_component=None, curves=None) -> Dict[str, Any]:
    """Kom dataene ned, per strategi — og hvem får være med i fellestallene?

    Feiler aldri kjøringen. Uten datastatus faller masteren tilbake til den
    gamle oppførselen der alle fire må være gyldige.
    """
    if not _fikspakke():
        return {{}}
    try:
        import data_status
        return data_status.hent(
            m.excel_dir, m.innside_dir,
            acquisition=[r for r in kjoring if r.get("Kilde")],
            run_status=kjoring, component_errors=per_component or {{}},
            as_of=date.today(), curves=curves)
    except Exception as e:
        logger.exception("Datastatus kunne ikke bygges: %s", IP.feiltekst(e))
        return {{}}


def kjor_alle(m: Master, logger) -> List[Rad]:'''.lstrip("\n"))

edit("master.py", "master.py :: Step4 mellom skraping og SentMom",
     "Sentimentendringer — Step4", 264, 268, '''
        analyser = [("PB-ROE-Momentum", O.PBROE_All3)]
        if O._miljo_paa("AKSJE_NLP_HENT"):
            analyser.append(("NLP-artikler — skraping", O.SentimentManagement))
        # Step4 bygges av scorene skrapingen nettopp skrev, og må ligge der før
        # SentimentMomentumV31 leser den. Derfor akkurat her.
        analyser.append(("Sentimentendringer — Step4",
                         lambda: bygg_sentimentendringer(m, logger)))
        analyser += [("NLP Sentiment — ledelse", O.SentimentHendelseLab),
                     ("Sentiment Momentum v3.1", O.SentimentMomentumV31)]'''.lstrip("\n"))

# «finn mail_strategier i flat mappe» er rettet i selve master.py (2026-09-22)
# og patches ikke lenger.

edit("master.py", "master.py :: validate_sources per strategi",
     "per_component.setdefault", 1477, 1500, '''
def validate_sources(m, since_ns=None):
    """Feil per strategi i stedet for én felles liste.

    Returnerer (errors, files, per_component, curves). `errors` er bare det som
    ikke kan tilskrives én strategi; resten ligger i per_component, slik at en
    strategi med dårlige data kan utelates fra fellestallene i stedet for å
    velte hele mailen. `curves` gis videre så eksportene ikke leses to ganger.
    """
    errors, files, per_component = [], [], {}
    from portfolio_blend import load_production_curves
    curves = load_production_curves(m.excel_dir, m.innside_dir)

    def _per(name, text):
        per_component.setdefault(name, []).append(str(text))

    for component in curves:
        name = component['name']
        for e in component.get('errors', []):
            _per(name, e)
        source = component.get('source')
        if source:
            files.append({'source': name, **source})
            if since_ns is not None and source['mtime_ns'] < since_ns:
                _per(name, "output was not refreshed by this run")
    opp = m.oppsett()
    innside = "Innsidehandel — Oslo Børs"
    for path in (opp.strategier_csv, opp.strategi_equity_csv,
                 opp.beholdning_csv, opp.strategi_handler_csv,
                 opp.s6_dir / "selected_variant.json"):
        try:
            stat = path.stat()
            files.append({"source": "Insider report", "path": str(path.resolve()),
                          "mtime_ns": stat.st_mtime_ns, "size": stat.st_size})
            if since_ns is not None and stat.st_mtime_ns < since_ns:
                _per(innside, f"Insider report was not refreshed: {path.name}")
        except OSError:
            _per(innside, f"Insider report missing: {path.name}")
    return errors, files, per_component, curves'''.lstrip("\n"))

edit("master.py", "master.py :: datastatus også i feilrapporten",
     "data_status_html or ''", 1536, 1539, '''
def failure_report(errors, data_status_html=""):
    """Selv en mislykket kjøring skal lede med hva som kom ned og hva som ikke."""
    return ('<html><meta charset="utf-8"><body><h1>Analysis incomplete</h1>'
            + (data_status_html or '')
            + '<p>No current performance report was issued. Correct these errors and rerun.</p><ul>'
            + ''.join('<li>' + IP.trygg(e) + '</li>' for e in errors) + '</ul></body></html>')'''.lstrip("\n"))

edit("master.py", "master.py :: bland bare strategier med ferske data",
     "included_curves(datastatus)", 1542, 1547, '''
def calculate_capital_portfolio(m, rebalance="monthly", datastatus=None):
    """Bland de eksporterte strategikurvene; rå scorer er ikke kapitalvekter.

    Med datastatus blandes bare strategiene som faktisk har ferske data, med
    lik vekt til hver: fire gir 25 % hver, tre gir 33 %. En strategi uten
    ferske data erstattes ikke med null avkastning, og forrige verdi
    videreføres ikke som om den var dagens.
    """
    from portfolio_blend import build_capital_portfolio, build_from_files
    felles = dict(rebalance=rebalance, as_of=date.today(),
                  start_capital=m.startkapital,
                  risk_free_pct=m.oppsett().risikofri_pst)
    if datastatus and datastatus.get("curves"):
        import data_status
        valgte = data_status.included_curves(datastatus)
        if len(valgte) < 2:
            raise RuntimeError(
                "Færre enn to strategier har ferske data ("
                + (", ".join(datastatus.get("excluded") or ()) or "ingen kilder")
                + " er utelatt). Ingen samlet portefølje kan beregnes av dette.")
        result = build_capital_portfolio(valgte, **felles)
        result.setdefault("metrics", {})["Utelatte_Strategier"] = list(
            datastatus.get("excluded") or ())
        return result
    return build_from_files(m.excel_dir, m.innside_dir, **felles)'''.lstrip("\n"))

edit("master.py", "master.py :: hente- og kostnadsbrytere", "--tving-datahent", 1600, 1600, '''
    p.add_argument("--ingen-nlp-hent", action="store_true", help="use existing management article data")
    p.add_argument("--ingen-datahent", action="store_true",
                   help="ikke bygg tickerliste, kursfil og sentimentendringer; "
                        "bruk filene som allerede ligger i ExcelData")
    p.add_argument("--tving-datahent", action="store_true",
                   help="bygg grunnlagsfilene på nytt selv om de er ferske")
    p.add_argument("--kostnadstest", action="store_true",
                   help="kjør innsidevariantene på nytt med 0,15 %% og 0,80 %% "
                        "kostnad per side som ren opplysning. Kjøringen handler "
                        "uten kostnader uansett, og valget bruker dem ikke")'''.lstrip("\n"))

edit("master.py", "master.py :: hent data, og la én strategi feile alene",
     "datastatus = bygg_datastatus", 1656, 1674, '''
    started = time.time_ns()
    errors = []
    kjoring = []
    if not a.ikke_kjor:
        # Tickerliste og kurser først: PB-ROE og SentMom leser dem. Step4 bygges
        # inne i kjor_alle, rett etter artikkelskrapingen.
        if not a.ingen_datahent:
            kjoring.extend(hent_grunnlagsdata(m, logger, steg=("tickers", "prices"),
                                              force=a.tving_datahent))
        missing = protected_input_errors(m.excel_dir)
        if missing:
            # Ikke lenger fatalt for HELE kjøringen. En manglende grunnlagsfil
            # rammer de strategiene som leser den; de øvrige skal fortsatt
            # kjøre, og datastatusblokken sier hvem som mangler hva.
            logger.warning("   ⚠️  Grunnlagsdata mangler: %s", "; ".join(missing))
            kjoring.append({"Analyse": "Grunnlagsdata", "Status": "FEIL",
                            "Minutter": 0.0,
                            "Feil": "mangler: " + "; ".join(missing)})
        kjoring.extend(kjor_alle(m, logger))
    # Old saved selection must be upgraded before it enters a capital sleeve.
    if a.ikke_kjor and not a.bare_mail:
        try:
            ensure_robust_insider_selection(m, logger)
        except Exception as exc:
            logger.exception("Insider selection failed")
            errors.append(str(exc))
    source_errors, source_files, per_component, curves = validate_sources(
        m, None if a.ikke_kjor else started)
    errors.extend(source_errors)
    # Hver strategi vurderes for seg. En strategi uten ferske data utelates fra
    # fellestallene og navngis øverst i mailen — den stopper ikke de tre andre.
    datastatus = bygg_datastatus(m, kjoring, per_component, curves)
    for _rad in datastatus.get("rows", ()):
        logger.info("   Datastatus  %-26s %-9s %s", _rad.get("Strategi"),
                    _rad.get("Status"), _rad.get("Begrunnelse"))'''.lstrip("\n"))

edit("master.py", "master.py :: send datastatus inn i kapitalberegningen",
     "rebalance=a.rebalance, datastatus=datastatus", 1687, 1687, '''
                portfolio = calculate_capital_portfolio(
                    m, rebalance=a.rebalance, datastatus=datastatus)'''.lstrip("\n"))

edit("master.py", "master.py :: manglende seksjon roper ikke over datastatusen",
     "alle_strategier_med", 1706, 1710, '''
    # Datastatusen sier allerede hvilke strategier som mangler data, og de er da
    # utelatt fra fellestallene. Da skal en manglende seksjon ikke i tillegg
    # gjøre hele kjøringen ufullstendig — det ville skjult et svar med et rop.
    alle_strategier_med = bool(datastatus.get("all_ok")) if datastatus else True
    if portfolio and alle_strategier_med and (
            len(sections.get("strategier", [])) != 3
            or any(x.get("mangler") for x in sections["strategier"])):
        errors.append("One or more strategy report sections are missing or invalid")
    if portfolio and alle_strategier_med and not insider:
        errors.append("Insider results missing")'''.lstrip("\n"))

edit("master.py", "master.py :: datastatusblokken øverst i mailen",
     "statusblokk = mail_status.render", 1724, 1729, '''
    statusblokk = ""
    try:
        _fikspakke()
        import mail_status
        statusblokk = mail_status.render(datastatus)
    except Exception as exc:
        logger.warning("Datastatusblokken kunne ikke bygges: %s", exc)
    try:
        if sections.get("kort") or insider:
            from capital_mail import render_capital_mail
            html = render_capital_mail(m, kjoring, portfolio, sections, insider,
                                       errors, data_status_html=statusblokk)
        else:
            html = failure_report(errors or ["No strategy reports are available"],
                                  data_status_html=statusblokk)'''.lstrip("\n"))

edit("master.py", "master.py :: emnefelt som teller strategiene",
     "uten ferske data", 1736, 1737, '''
    else:
        _antall = int(((portfolio or {}).get("metrics", {}) or {}).get("N_Strategier", 4) or 4)
        subject = ("Samlet aksjeanalyse — 25 % i hver strategi" if _antall == 4 else
                   f"Samlet aksjeanalyse — {100.0 / _antall:.0f} % i hver av {_antall} strategier")
        if datastatus and not datastatus.get("all_ok"):
            subject += f" · {len(datastatus.get('excluded') or ())} uten ferske data"'''.lstrip("\n"))


# ══════════════════════════════════════════════════════════════════════════
# capital_mail.py
# ══════════════════════════════════════════════════════════════════════════

edit("capital_mail.py", "capital_mail.py :: kostnadstabellen er opplysning, ikke regel",
     "zero_table = _table(", 55, 63, '''
    def _har(key):
        return any(compared.get(r.get('Strategi'), {}).get(key) is not None
                   for r in displayed)
    # Kjøringen handler uten kostnader, så tabellen som faktisk beskriver den er
    # trening og treningshalvdeler uten kostnader. Kostnadsreplayene er ren
    # opplysning og kjøres bare med --kostnadstest / AKSJE_KOSTNADSTEST=1.
    zero_table = _table(
        ['Variant','Trening, 0 % kostnad','Senere, 0 % kostnad',
         'Første treningshalvdel','Andre treningshalvdel','Svakeste halvdel'],
        [[ip.trygg(r.get('Strategi')),
          _number(compared.get(r.get('Strategi'),{}).get('Train_CAGR_Pst'),1,' %'),
          _number(compared.get(r.get('Strategi'),{}).get('Test_CAGR_Pst'),1,' %'),
          _number(compared.get(r.get('Strategi'),{}).get('Train_First_Half_CAGR_Pst'),1,' %'),
          _number(compared.get(r.get('Strategi'),{}).get('Train_Second_Half_CAGR_Pst'),1,' %'),
          _number(compared.get(r.get('Strategi'),{}).get('Train_Worst_Half_CAGR_Pst'),1,' %')]
         for r in displayed])
    if _har('Train_Moderate_CAGR_Pst') or _har('Train_Stress_CAGR_Pst'):
        cost_table = ('<h3>Kostnadstest: CAGR etter modellerte kostnader</h3>'
            '<p>Variantene er kjørt på nytt med 0,15 % og 0,80 % kostnad per kjøp '
            'eller salg. Dette er ren opplysning — kjøringen selv handler uten '
            'kostnader, og variantvalget bruker ikke disse tallene.</p>' + _table(
            ['Variant','Trening: 0,15 % per side','Senere: 0,15 % per side',
             'Trening: 0,80 % per side','Svakeste treningshalvdel: 0,80 %'],
            [[ip.trygg(r.get('Strategi')),
              _number(compared.get(r.get('Strategi'),{}).get('Train_Moderate_CAGR_Pst'),1,' %'),
              _number(compared.get(r.get('Strategi'),{}).get('Test_Moderate_CAGR_Pst'),1,' %'),
              _number(compared.get(r.get('Strategi'),{}).get('Train_Stress_CAGR_Pst'),1,' %'),
              _number(compared.get(r.get('Strategi'),{}).get('Train_Stress_Worst_Half_CAGR_Pst'),1,' %')]
             for r in displayed]))
    else:
        cost_table = ('<p>Kostnadstesten er ikke kjørt. Hele kjøringen forutsetter '
                      'null handelskostnad, og valget bruker ingen kostnadsregel. '
                      'Kjør med <code>--kostnadstest</code> for å få den med som '
                      'opplysning.</p>')'''.lstrip("\n"))

edit("capital_mail.py", "capital_mail.py :: innsideseksjonen uten kostnadsregel",
     "Uten handelskostnader: trening", 83, 91, '''
    return f\'\'\'<div class="kort"><h2>Innsidehandel: topp tre og valgt variant</h2>
<p>Rangeringen viser høyest historisk CAGR over hele historikken.
Valget videre bruker bare treningsperioden, og handler uten kostnader.
En høy plassering er ikke dokumentasjon på en varig konkurransefordel («MOAT»).</p>
{headline}<h3>Uten handelskostnader: trening, senere periode og de to treningshalvdelene</h3>
<p>Dette er tallene kjøringen faktisk bygger på. Varianten velges på høyest
trenings-CAGR uten kostnader; halvdelene bryter likhet og viser hvor jevnt
resultatet er fordelt. Tallene annualiseres etter kalendertid; hovedtabellen
beholder innsidermotorens 252 handelsdager per år.</p>{zero_table}{cost_table}
<h3>Valgt til innsidedelen av samlet portefølje: {ip.trygg(selected)}</h3>'''.lstrip("\n"))

edit("capital_mail.py", "capital_mail.py :: overskrift og tekst teller strategiene",
     "antall_strategier = int(metrics.get", 130, 139, '''
        antall_strategier = int(metrics.get('N_Strategier', 4) or 4)
        andel = float(metrics.get('Andel_Per_Strategi_Pst',
                                  100.0 / max(1, antall_strategier)))
        utelatt = list(metrics.get('Utelatte_Strategier') or [])
        mangler = ('<p style="color:#c62828;font-weight:600">Utelatt fra fellestallene '
                   'fordi dataene ikke var ferske: ' + ip.trygg(', '.join(utelatt))
                   + '. Se datastatus øverst i mailen.</p>') if utelatt else ''
        main = f\'\'\'<div class="kort"><h2>Samlet portefølje: {andel:.0f} % i hver av {antall_strategier} strategier</h2>{summary}{mangler}
<p>Hver strategi får like stor del av kapitalen. Vi kombinerer verdiene til de
{antall_strategier} faktiske delporteføljene over samme observerte periode. Ingen ny
aksjeliste lages av scorene.</p>
{_rules([
('Kjøp og salg','Hver delportefølje følger sine egne kjøps- og salgsregler, forklart nedenfor.'),
('Handelskostnader','Null. Hele kjøringen modellerer handel uten spread, kurtasje eller markedspåvirkning. Det er en forutsetning, ikke en observasjon: faktisk handel koster noe.'),
('Kapitalfordeling',f'Kapitalen fordeles likt ved start og justeres {frequency}. Ved månedlig justering får hver del {andel:.0f} % ved månedsslutt; mellom disse tidspunktene kan vektene drive.'),
('Kontanter','Når en strategi går i kontanter, blir pengene i den strategiens del. De flyttes ikke automatisk til de andre.'),
('Avkastning',f'Ved månedlig justering er hver måneds samlede avkastning gjennomsnittet av de {antall_strategier} månedsavkastningene. Månedene forrentes deretter etter hverandre. CAGR er beregnet fra denne samlede kurven.'),
('Sammenligning',f'Bare fullførte måneder med observerte verdier for alle {antall_strategier} brukes. Daglige PB-ROE-verdier blir ikke funnet på. Risiko er derfor målt på månedspunkter og kan undervurdere fall innenfor måneden.'),
('Innsidevalg','Innsidedelen følger den dokumenterte valgregelen nedenfor: høyest trenings-CAGR uten kostnader, ikke et gjennomsnitt av alle innsidevariantene.')])}'''.lstrip("\n"))

edit("capital_mail.py", "capital_mail.py :: deltabellen teller strategiene",
     "De {antall_strategier} delene", 140, 140, """
<h3>De {antall_strategier} delene, målt over samme periode</h3>{comparison}""".lstrip("\n"))

edit("capital_mail.py", "capital_mail.py :: datastatus først i mailen",
     "data_status_html=''", 99, 100, '''
def render_capital_mail(m, run_status, portfolio, sections, insider, errors=(),
                        data_status_html=''):
    """Portfolio is the calculation result; sections contain individual model cards.

    data_status_html legges ØVERST i mailen: om dataene kom ned, per strategi,
    før ett eneste avkastningstall.
    """'''.lstrip("\n"))

edit("capital_mail.py", "capital_mail.py :: statusblokken inn i kroppen",
     "{data_status_html}{status}{main}", 160, 161, '''
<body><div class="beholder"><div class="topp"><h1>{_overskrift(portfolio)}</h1>
<p>Bygget {datetime.now():%Y-%m-%d %H:%M}</p></div>{data_status_html}{status}{main}'''.lstrip("\n"))

edit("capital_mail.py", "capital_mail.py :: overskriftshjelper", "def _overskrift(", 25, 25, '''
def _overskrift(portfolio):
    """Tittelen må telle strategiene som faktisk er med, ikke alltid fire."""
    metrics = (portfolio or {}).get('metrics') or {}
    antall = int(metrics.get('N_Strategier', 4) or 4)
    andel = float(metrics.get('Andel_Per_Strategi_Pst', 100.0 / max(1, antall)))
    if antall == 4:
        return 'Fire strategier med 25 % kapital hver'
    return f'{antall} strategier med {andel:.0f} % kapital hver'


def _rules(rows):'''.lstrip("\n"))


# ══════════════════════════════════════════════════════════════════════════
# portfolio_blend.py
# ══════════════════════════════════════════════════════════════════════════

edit("portfolio_blend.py", "portfolio_blend.py :: dekningsdiagnostikk 1/7",
     "2026-09-18 correction", 4, 5, '''
source curves limit the portfolio to completed month-end observations.

2026-09-18 correction
---------------------
`_monthly_observations` used to drop a month-end silently when a component's
last observation was too far before it. On 2026-09-18 that hid the fact that
Sentiment Momentum's prices stop at 2026-08-19 - eight business days before
2026-08-31 - so the joint window could not pass 2026-07-31 no matter what was
done about the management leg. Drops are now returned, reported as warnings,
and named in the error when too few common month-ends remain.

2026-09-20 correction
---------------------
The blend no longer requires exactly four curves. A strategy whose data is
missing or stale is excluded upstream and the remaining ones are weighted
equally, with the count carried in the metrics so the mail cannot print "25 %
each" over three sleeves.
"""'''.lstrip("\n"))

edit("portfolio_blend.py", "portfolio_blend.py :: lik vekt til N strategier",
     "share = 100.0 / count", 118, 127, '''
    """Return a monthly portfolio with capital split equally between the curves.

    Four curves give 25% each, three give 33%. Each component supplies name,
    observations [(date, NAV)], source, frequency, and optionally
    valid/errors/warnings/variant. The first common completed month end is the
    initial allocation; every following common month end marks the sleeves to
    market, then rebalances to an equal share for the following month.
    """
    curves = list(curves)
    count = len(curves)
    share = 100.0 / count if count else 0.0
    if count < 2 or len({c['name'] for c in curves}) != count:
        raise PortfolioDataError(
            'At least two distinct strategy NAV curves are required; '
            f'received {count}.')'''.lstrip("\n"))

edit("portfolio_blend.py", "portfolio_blend.py :: dekningsdiagnostikk 2/7",
     'usable_month_ends, dropped', 83, 84, '''
    """Return (usable_month_ends, dropped).

    Never carry a missing month's value from a previous month. The month must
    be complete as of the report date; near-end holiday gaps are bounded.
    `dropped` records every month-end rejected for gap, so the caller can say
    which component capped the joint window and why.
    """'''.lstrip("\n"))

edit("portfolio_blend.py", "portfolio_blend.py :: dekningsdiagnostikk 3/7",
     "usable, dropped = {}, []", 90, 91, '''
    usable, dropped = {}, []
    for end, item in months.items():
        gap = _business_days_after(item[0], end)
        if gap <= max_gap_business_days:
            usable[end] = item
        else:
            dropped.append({'month_end': end, 'last_observation': item[0],
                            'gap_business_days': gap,
                            'limit_business_days': max_gap_business_days})
    return usable, sorted(dropped, key=lambda d: d['month_end'])'''.lstrip("\n"))

edit("portfolio_blend.py", "portfolio_blend.py :: dekningsdiagnostikk 4/7",
     "prepared, monthly, warnings, coverage", 133, 133, '''
    prepared, monthly, warnings, coverage = {}, {}, [], {}'''.lstrip("\n"))

edit("portfolio_blend.py", "portfolio_blend.py :: dekningsdiagnostikk 5/7",
     "the binding constraint on the shared period", 138, 138, '''
        monthly[name], dropped = _monthly_observations(prepared[name], as_of)
        last_observation = max(prepared[name])
        coverage[name] = {
            'last_observation': last_observation,
            'last_usable_month_end': max(monthly[name]) if monthly[name] else None,
            'dropped_month_ends': dropped,
            'age_days': (as_of - last_observation).days,
        }
        for drop in dropped:
            warnings.append(
                f"{name}: {drop['month_end']} excluded - last observation "
                f"{drop['last_observation']} is {drop['gap_business_days']} business days "
                f"before it (limit {drop['limit_business_days']}). Refreshing the other "
                "strategies cannot recover this month.")
    # Name the component that caps the joint window before any date math fails.
    covered = {n: c['last_usable_month_end'] for n, c in coverage.items()
               if c['last_usable_month_end'] is not None}
    uncovered = [n for n, c in coverage.items() if c['last_usable_month_end'] is None]
    if uncovered:
        raise PortfolioDataError(
            'No completed month-end can be substantiated for: ' + ', '.join(sorted(uncovered))
            + '. Every component must supply at least one month-end NAV.')
    binding = min(covered, key=covered.get)
    warnings.append(
        f"The joint window ends at {covered[binding]} because {binding} has no later "
        "usable month-end. This is the binding constraint on the shared period.")'''.lstrip("\n"))

edit("portfolio_blend.py", "portfolio_blend.py :: dekningsdiagnostikk 6/7",
     "Binding component:", 159, 159, '''
        detail = '; '.join(f"{n} reaches {covered[n]}" for n in sorted(covered, key=covered.get))
        raise PortfolioDataError(
            f'Fewer than two common completed month-end observations{reason}; '
            f'no portfolio return can be calculated. Binding component: {binding} '
            f'(last usable month-end {covered[binding]}). Coverage: {detail}.')'''.lstrip("\n"))

edit("portfolio_blend.py", "portfolio_blend.py :: lik vekt i kurve og overføringer",
     "start_capital / count / monthly", 164, 172, '''
    names = [c['name'] for c in curves]
    units = {n: start_capital / count / monthly[n][dates[0]][1] for n in names}
    equity, trades = [], []
    for index, day in enumerate(dates):
        before = {n: units[n] * monthly[n][day][1] for n in names}
        total = sum(before.values())
        target = total / count
        equity.append({'Dato': str(day), 'Verdi_NOK': total,
                       'Antall_Strategier': count,'''.lstrip("\n"))

edit("portfolio_blend.py", "portfolio_blend.py :: lik vekt i beholdningen",
     "'Andel_Pst': share, 'Target_Pst': share", 184, 185, '''
    holdings = [{'Strategi': n, 'Dato': str(last), 'Verdi_NOK': equity[-1]['Verdi_NOK'] / count,
                 'Andel_Pst': share, 'Target_Pst': share, 'Antall': units[n],'''.lstrip("\n"))

edit("portfolio_blend.py", "portfolio_blend.py :: lik vekt i sammenligningen",
     "start_capital / count * v", 192, 192, '''
        normalized = [start_capital / count * v / raw[0] for v in raw]'''.lstrip("\n"))

edit("portfolio_blend.py", "portfolio_blend.py :: forbehold teller strategiene",
     "Only these strategies are in the blend", 197, 202, """
    warnings.extend([
        f'Returns use the same completed month-end window for all {count} strategies. No daily PB-ROE NAV is interpolated.',
        f'Only these strategies are in the blend: {", ".join(sorted(names))}. An excluded strategy is not replaced by zero return, and its last value is not carried forward.',
        'Drawdown and volatility are measured monthly and can miss losses within a month.',
        'No trading costs are modelled anywhere in this run: not in the strategy curves and not in the capital transfers. That is an assumption, not an observation.',
        f'The shared portfolio ends on {last}; this is a historical allocation snapshot, not current stock holdings.',
    ])
    if count != 4:
        warnings.append(
            f'Capital is split equally between {count} strategies ({share:.0f}% each), not four. '
            'The missing strategies had no fresh data; see the data status at the top of the mail.')""".lstrip("\n"))

edit("portfolio_blend.py", "portfolio_blend.py :: nøkkeltall teller strategiene",
     "'N_Strategier': count", 208, 209, '''
    metrics.update({'Rebalance': 'monthly', 'Andel_Per_Strategi_Pst': share,
                    'N_Strategier': count, 'As_Of': str(as_of),
                    'Cost_Basis': 'exported strategy NAVs, modelled without trading costs; capital transfers cost 0'})'''.lstrip("\n"))

edit("portfolio_blend.py", "portfolio_blend.py :: dekningsdiagnostikk 7/7",
     "'binding_component': binding", 213, 214, '''
            'sources': [c.get('source') for c in curves],
            'coverage': {n: {'last_observation': str(c['last_observation']),
                             'last_usable_month_end': str(c['last_usable_month_end']),
                             'age_days': c['age_days'],
                             'dropped_month_ends': [
                                 {'month_end': str(d['month_end']),
                                  'last_observation': str(d['last_observation']),
                                  'gap_business_days': d['gap_business_days']}
                                 for d in c['dropped_month_ends']]}
                         for n, c in coverage.items()},
            'binding_component': binding,
            'strategies': sorted(names),
            'common_period': {'start': str(dates[0]), 'end': str(last),'''.lstrip("\n"))


# ══════════════════════════════════════════════════════════════════════════
# insider_selection.py
# ══════════════════════════════════════════════════════════════════════════

edit("insider_selection.py", "insider_selection.py :: nullkostnad som politikk",
     "insider-zero-cost-v1", 16, 22, f'''
# 2026-09-20: valget bruker ikke lenger en kostnadsregel. Motoren handler uten
# kostnader (spread_pst = kurtasje_pst = 0), og da kan ikke varianten velges av
# hvordan den ville klart seg ved 0,80 % per side. Reglene ligger i
# {FOLDER}/zero_cost.py. Ny versjonsstreng tvinger et lagret valg fra den
# gamle regelen til å bygges på nytt i stedet for å bli gjenbrukt i stillhet.
POLICY_VERSION = "insider-zero-cost-v1"
BASELINE = "daglig"
MODERATE_ONE_WAY_PCT = 0.15
STRESS_ONE_WAY_PCT = 0.80
MIN_TRAIN_DAYS = 252
MIN_ENTRIES = 20
MIN_TICKERS = 5


def _zero_cost():
    """Den kostnadsfrie velgeren.

    Mangler den, skal det smelle. Å falle stille tilbake til kostnadsregelen
    ville gitt en mail som sier «valgt uten kostnader» over et valg som ikke er
    det.
    """
    import sys as _sys
    _folder = Path(__file__).resolve().parent / "{FOLDER}"
    if _folder.is_dir() and str(_folder) not in _sys.path:
        _sys.path.insert(0, str(_folder))
    import zero_cost
    return zero_cost


def _kostnadsnivaaer():
    """Kostnadsreplayene er ren opplysning nå — valget bruker dem ikke.

    De koster to ekstra fulle backtester per variant, så de er av som standard
    og slås på med --kostnadstest (AKSJE_KOSTNADSTEST=1).
    """
    if str(os.environ.get("AKSJE_KOSTNADSTEST", "")).strip().lower() in (
            "1", "ja", "true", "on", "yes"):
        return (("Moderate", MODERATE_ONE_WAY_PCT), ("Stress", STRESS_ONE_WAY_PCT))
    return ()'''.lstrip("\n"))

edit("insider_selection.py", "insider_selection.py :: velg uten kostnader",
     "return _zero_cost().select_variant", 70, 103, '''
def select_robust_variant(rows, baseline=BASELINE):
    """Ren velger. Verken fullhistorikk- eller testkolonner leses her.

    2026-09-20: handelskostnader er null i hele kjøringen, så valget kan ikke
    lenger gå på en kostnadsregel. Kriteriet er høyest trenings-CAGR uten
    kostnader, blant varianter som møter minstekravene til historikk og bredde
    (252 treningsdager, 20 nye innganger, 5 forskjellige aksjer). Horisonten er
    uendret: bare data til og med treningsslutt inngår i valget.
    """
    return _zero_cost().select_variant(rows, baseline=baseline)'''.lstrip("\n"))

edit("insider_selection.py", "insider_selection.py :: manuelt valg uten kostnadsspråk",
     "_worst = _number(", 115, 121, '''
    reason = (f"Manuelt valg: {manual}. Den automatiske regelen anbefalte "
              f"{recommended['Variant']}; det manuelle valget er ikke resultat av "
              "denne regelen og dokumenterer ingen MOAT. "
              "Sammenligningen vises fortsatt uendret.")
    _worst = _number(selected.get("Train_Worst_Half_CAGR_Pst"))
    if _worst is None or _worst <= 0:
        reason += (" Den manuelt valgte varianten er ikke positiv uten kostnader "
                   "i begge treningshalvdeler.")'''.lstrip("\n"))

edit("insider_selection.py", "insider_selection.py :: treningshalvdeler uten kostnad",
     "Treningshalvdelene UTEN kostnader", 239, 241, '''
               "Train_Turnover_Per_Year_Pst": 100 * turnover / mean_capital / years
               if mean_capital > 0 and years > 0 else None}
        # Treningshalvdelene UTEN kostnader. Motoren handler kostnadsfritt, så
        # det er disse to halvdelene som faktisk beskriver kjøringen. De bryter
        # likhet i valget og vises i mailen.
        _halves = [_cagr(first), _cagr(second)]
        row["Train_First_Half_CAGR_Pst"], row["Train_Second_Half_CAGR_Pst"] = _halves
        row["Train_Worst_Half_CAGR_Pst"] = (
            min(_halves) if all(v is not None for v in _halves) else None)
        for label, cost in _kostnadsnivaaer():'''.lstrip("\n"))

edit("insider_selection.py", "insider_selection.py :: politikk uten kostnadsregel",
     "cost_test_enabled", 275, 282, '''
        "policy": dict(_zero_cost().policy(cutoff),
                       cost_test_enabled=bool(_kostnadsnivaaer()),
                       cost_test_note=("Kostnadsreplayene er ren opplysning og "
                                       "påvirker ikke valget."),
                       moderate_cost_per_side_pct=MODERATE_ONE_WAY_PCT,
                       stress_cost_per_side_pct=STRESS_ONE_WAY_PCT),'''.lstrip("\n"))

edit("insider_selection.py", "insider_selection.py :: forbehold uten kostnadsstress",
     "LIMITATIONS)", 284, 289, '''
        "limitations": list(_zero_cost().LIMITATIONS),'''.lstrip("\n"))


# ══════════════════════════════════════════════════════════════════════════
# Only_260820.py  —  ingen patch lenger
# ══════════════════════════════════════════════════════════════════════════
#
# Prisvakten er rettet direkte i rotfila (2026-09-22): tierpotenser skaleres
# bakover som her, og en ticker med et sprang ingen kan forklare holdes utenfor
# universet i stedet for å stanse hele ledelsesanalysen. Å patche over den ville
# ha satt tilbake den strengere regelen. price_repair.py og testene står igjen
# som dokumentasjon av logikken.


# ══════════════════════════════════════════════════════════════════════════
# Bygging og kontroll
# ══════════════════════════════════════════════════════════════════════════

def build() -> Tuple[List[Dict[str, object]], List[str]]:
    """Hent hver originalblokk ut av fila selv, og kontroller alt underveis."""
    patches: List[Dict[str, object]] = []
    pristine: Dict[str, str] = {}
    working: Dict[str, str] = {}
    problems: List[str] = []

    for file, name, marker, first, last, replacement in EDITS:
        if file not in pristine:
            pristine[file] = working[file] = read(file)
        raw = pristine[file]
        total = len(lines_of(raw))
        if not 1 <= first <= last <= total:
            problems.append(f"{name}: linjeintervallet {first}-{last} finnes ikke "
                            f"i {file} ({total} linjer)")
            continue
        original = block_of(raw, first, last)
        # Frosne ankerlinjer. Uniktest og parsekontroll fanger ikke en blokk som
        # traff FEIL sted men likevel gir gyldig Python - Step4-patchen landet
        # slik paa kommentaren over `analyser`, og den opprinnelige tilordningen
        # overskrev den. Foerste linje i hver blokk staar derfor i anchors.json.
        forventet = ANCHORS.get(name)
        faktisk = original.split("\n")[0].rstrip("\r").strip()
        if forventet is None:
            problems.append(f"{name}: mangler ankerlinje i anchors.json; "
                            "kjoer med --frys naar blokken er kontrollert")
        elif forventet != faktisk:
            problems.append(
                f"{name}: linje {first} er {faktisk!r}, men ankeret sier "
                f"{forventet!r}. Rotfila har flyttet seg - rett linjenumrene.")
        if raw.count(original) != 1:
            problems.append(
                f"{name}: blokken paa linje {first}-{last} finnes "
                f"{raw.count(original)} ganger i fila; den kan ikke brukes som "
                "ankerpunkt")
            continue
        if marker in raw:
            problems.append(
                f"{name}: markoeren {marker!r} finnes allerede i {file}; "
                "patchen ville blitt regnet som allerede paafoert")
        if marker not in replacement:
            problems.append(f"{name}: markoeren {marker!r} staar ikke i erstatningen")
        # Et feilrettet ankerpunkt endrer nesten alltid innrykket paa foerste
        # linje. Det er akkurat slik en blokk som traff feil sted avsloerte seg.
        def _indent(line):
            return len(line) - len(line.lstrip(" "))
        if _indent(original.split("\n")[0]) != _indent(replacement.split("\n")[0]):
            problems.append(
                f"{name}: erstatningen starter paa et annet innrykk enn blokken "
                f"paa linje {first} ({_indent(original.split(chr(10))[0])} mot "
                f"{_indent(replacement.split(chr(10))[0])} mellomrom). Det tyder "
                "paa at linjenumrene peker feil sted.")
        if working[file].count(original) != 1:
            problems.append(f"{name}: blokken overlapper en tidligere patch i samme fil")
            continue
        newline = dominant_newline(original)
        replacement_text = with_newline(replacement, newline)
        working[file] = working[file].replace(original, replacement_text, 1)
        patches.append({"file": file, "name": name, "marker": marker,
                        "lines": [first, last],
                        "original_text": original,
                        "replacement_text": replacement_text})

    for file, text in working.items():
        try:
            ast.parse(text)
        except SyntaxError as exc:
            problems.append(f"{file}: den patchede kilden parser ikke: {exc}")
    return patches, problems


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--frys" in argv:
        frozen = {}
        cache: Dict[str, str] = {}
        for file, name, _marker, first, _last, _repl in EDITS:
            raw = cache.setdefault(file, read(file))
            frozen[name] = lines_of(raw)[first - 1].rstrip("\r").strip()
        ANCHOR_FILE.write_text(
            json.dumps(frozen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Froes {len(frozen)} ankerlinjer til {ANCHOR_FILE}")
        ANCHORS.clear()
        ANCHORS.update(frozen)
    patches, problems = build()
    for problem in problems:
        print("FEIL: " + problem)
    if problems:
        print("\nIngenting ble skrevet.")
        return 1
    per_file: Dict[str, int] = {}
    for patch in patches:
        per_file[patch["file"]] = per_file.get(patch["file"], 0) + 1
    for file in sorted(per_file):
        print(f"  {file:24} {per_file[file]} blokk(er)")
    print(f"  {len(patches)} patcher totalt")
    if "--sjekk" in argv:
        print("\nBare kontroll: patches.json er ikke skrevet.")
        return 0
    target = HERE / "patches.json"
    target.write_text(json.dumps(patches, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    print(f"\nSkrevet {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
