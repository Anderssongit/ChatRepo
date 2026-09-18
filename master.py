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

def _fikspakke() -> bool:
    """Put the dated fix package on sys.path without importing it eagerly."""
    folder = SKRIPTMAPPE / "2026-09-18"
    if folder.is_dir() and str(folder) not in sys.path:
        sys.path.insert(0, str(folder))
    return folder.is_dir()


def hent_grunnlagsdata(m: Master, logger, *, steg, force: bool = False) -> List[Rad]:
    """Bygg grunnlagsfilene masteren tidligere bare KONTROLLERTE at fantes.

    AllTickers_OSEBX_TW_*.xlsx, Stock_Prices_*.xlsx og
    Step4_Sentiment_Changes_*.xlsx kom fra et annet program. Ingen hadde kjort
    det siden 2026-08-19, og det er hele grunnen til at Sentiment Momentum
    backtestet maned gamle kurser og likevel ble rapportert som OK.

    Alt som trengs for a bygge dem lastes allerede ned av denne pakken:
    aksjelista og kursene av innsidepipelinen, artikkelscorene av FinBERT-
    skrapingen. Masteren bygger dem derfor selv. De hash-beskyttede
    strategiene rores ikke - dette skriver filene de leser, i det formatet de
    allerede forventer.
    """
    start = time.time()
    if not _fikspakke():
        return [{"Analyse": "Datahenting", "Status": "FEIL", "Minutter": 0.0,
                 "Feil": "Fant ikke mappen 2026-09-18 ved siden av master.py"}]
    try:
        from data_acquisition import build_all
        rader = build_all(m.excel_dir, m.oppsett(), logger, steps=steg, force=force)
    except KeyboardInterrupt:
        raise
    except Exception as e:
        logger.exception("Datahenting feilet")
        return [{"Analyse": "Datahenting", "Status": "OK", "Handling": "FEIL",
                 "Minutter": round((time.time() - start) / 60.0, 1),
                 "Feil": "feil - " + IP.feiltekst(e)[:180]}]
    minutter = round((time.time() - start) / 60.0, 1)
    ut: List[Rad] = []
    for rad in rader:
        logger.info("   %-9s %-22s %s", rad["Handling"], rad["Kilde"], rad["Merknad"])
        # Status er alltid OK: henting som feiler skal ikke velte en kjoring
        # der filene allerede ligger der og er ferske. Handling baerer utfallet,
        # og bygg_sentimentendringer leser den.
        ut.append({"Analyse": "Data: " + str(rad["Kilde"]), "Status": "OK",
                   "Handling": rad["Handling"], "Minutter": minutter,
                   "Feil": f'{rad["Handling"].lower()} - {rad["Merknad"]}'})
        minutter = 0.0
    return ut


# Hvor gamle grunnlagsfilene faar vaere for de ikke lenger dokumenterer noe
# ferskt. Tickerlista endrer seg langsomt; kursene gjor ikke det.
DATA_MAKSALDER = {"Data_BT/AllTickers_OSEBX_TW_*.xlsx": 90,
                  "Data_BT1/FinancialData/Stock_Prices_*.xlsx": 7,
                  "DataNLP/Step4_Sentiment_Changes_*.xlsx": 14}


def foreldede_grunnlagsdata(m: Master) -> List[str]:
    """Filer som FINNES, men er for gamle til aa baere et ferskt resultat.

    Dette er porten som manglet 2026-09-18: kursfila laa der, SentMom leste
    den uten aa feile, og ingen sa at den stoppet 2026-08-19. En fil som
    mangler fanges av protected_input_errors; denne fanger den som er gammel.
    Henting som feilet er ikke i seg selv en feil - resultatet av den er det.
    """
    if not _fikspakke():
        return []
    from data_acquisition import latest, needs_refresh
    from datetime import date as _date
    feil = []
    for monster, maksalder in DATA_MAKSALDER.items():
        mappe, mal = monster.rsplit("/", 1)
        funnet = latest(m.excel_dir / mappe, mal)
        if funnet is None:
            continue                      # manglende fil: protected_input_errors
        gammel, hvorfor = needs_refresh(funnet, _date.today(), maksalder)
        if gammel:
            feil.append(f"Grunnlagsdata for gamle: {funnet.name} er {hvorfor}. "
                        f"Resultatene bygget paa denne fila er ikke ferske. "
                        f"Kjor uten --ingen-datahent, eller med --tving-datahent.")
    return feil


def bygg_sentimentendringer(m: Master, logger) -> int:
    """Step4-endringene, bygget av FinBERT-scorene skrapingen nettopp skrev.

    Ma kjore ETTER skrapingen og FOR SentimentMomentumV31, som leser fila.
    """
    rader = hent_grunnlagsdata(m, logger, steg=("step4",))
    feil = [r["Feil"] for r in rader if r.get("Handling") == "FEIL"]
    if feil:
        # Her ER det fatalt: uten en fersk Step4-fil leser SentimentMomentumV31
        # den forrige, og da er vi tilbake i 2026-09-18.
        raise RuntimeError("; ".join(feil))
    return 0



def kjor_alle(m: Master, logger) -> List[Rad]:
    """Kjører de fire analysene. Én rad per analyse med status og tid."""
    ut: List[Rad] = []

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
        import Only_260820 as O
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
        # Step4 bygges av scorene skrapingen nettopp skrev, og maa ligge der
        # foer SentimentMomentumV31 leser den. Derfor akkurat her.
        analyser.append(("Sentimentendringer — Step4",
                         lambda: bygg_sentimentendringer(m, logger)))
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
    mappe = SKRIPTMAPPE / "mail"
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
    errors, files = [], []
    from portfolio_blend import load_production_curves
    for component in load_production_curves(m.excel_dir, m.innside_dir):
        name = component['name']
        errors.extend(name + ': ' + str(e) for e in component.get('errors', []))
        source = component.get('source')
        if source:
            files.append({'source': name, **source})
            if since_ns is not None and source['mtime_ns'] < since_ns:
                errors.append(f"{name}: output was not refreshed by this run")
    opp = m.oppsett()
    for path in (opp.strategier_csv, opp.strategi_equity_csv,
                 opp.beholdning_csv, opp.strategi_handler_csv,
                 opp.s6_dir / "selected_variant.json"):
        try:
            stat = path.stat()
            files.append({"source": "Insider report", "path": str(path.resolve()),
                          "mtime_ns": stat.st_mtime_ns, "size": stat.st_size})
            if since_ns is not None and stat.st_mtime_ns < since_ns:
                errors.append(f"Insider report was not refreshed: {path.name}")
        except OSError:
            errors.append(f"Insider report missing: {path.name}")
    return errors, files


def failure_report(errors):
    return ('<html><meta charset="utf-8"><body><h1>Analysis incomplete</h1>'
            '<p>No current performance report was issued. Correct these errors and rerun.</p><ul>'
            + ''.join('<li>' + IP.trygg(e) + '</li>' for e in errors) + '</ul></body></html>')


def calculate_capital_portfolio(m, rebalance="monthly"):
    """Blend exported strategy NAVs; raw scores are not allocations."""
    from portfolio_blend import build_from_files
    return build_from_files(m.excel_dir, m.innside_dir, rebalance=rebalance,
                            as_of=date.today(), start_capital=m.startkapital,
                            risk_free_pct=m.oppsett().risikofri_pst)


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
    p.add_argument("--ingen-datahent", action="store_true",
                   help="ikke bygg tickerliste, kursfil og sentimentendringer; "
                        "bruk filene som allerede ligger i ExcelData")
    p.add_argument("--tving-datahent", action="store_true",
                   help="bygg grunnlagsfilene paa nytt selv om de er ferske")
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
    errors = []
    kjoring = []
    if not a.ikke_kjor:
        # Tickerliste og kurser foerst: PB-ROE og SentMom leser dem. Step4
        # bygges inne i kjor_alle, rett etter artikkelskrapingen.
        if not a.ingen_datahent:
            kjoring.extend(hent_grunnlagsdata(m, logger, steg=("tickers", "prices"),
                                              force=a.tving_datahent))
        missing = protected_input_errors(m.excel_dir)
        if missing:
            errors.extend("Required upstream data missing: " + f for f in missing)
        else:
            kjoring.extend(kjor_alle(m, logger))
        errors.extend(r["Analyse"] + ": " + r["Feil"]
                      for r in kjoring if r["Status"] != "OK")
        errors.extend(foreldede_grunnlagsdata(m))
    # Old saved selection must be upgraded before it enters a capital sleeve.
    if a.ikke_kjor and not a.bare_mail:
        try:
            ensure_robust_insider_selection(m, logger)
        except Exception as exc:
            logger.exception("Insider selection failed")
            errors.append(str(exc))
    source_errors, source_files = validate_sources(m, None if a.ikke_kjor else started)
    errors.extend(source_errors)
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
                portfolio = calculate_capital_portfolio(m, rebalance=a.rebalance)
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
    if portfolio and (len(sections.get("strategier", [])) != 3
                      or any(x.get("mangler") for x in sections["strategier"])):
        errors.append("One or more strategy report sections are missing or invalid")
    if portfolio and not insider:
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
        if sections.get("kort") or insider:
            from capital_mail import render_capital_mail
            html = render_capital_mail(m, kjoring, portfolio, sections, insider, errors)
        else:
            html = failure_report(errors or ["No strategy reports are available"])
    except Exception as exc:
        logger.exception("Email rendering failed")
        errors.append("Email rendering failed: " + str(exc))
        html = failure_report(errors)
    if errors:
        subject = "Analysis incomplete — ufullstendig beregning"
    else:
        subject = "Samlet aksjeanalyse — 25 % i hver strategi"
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
