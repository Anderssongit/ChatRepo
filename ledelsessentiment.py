# -*- coding: utf-8 -*-
"""
LEDELSESSENTIMENT (NLP) — frittstående utgave med to funksjoner.

    last_ned_data(opp)   DEL 1: henter artikler fra Euronext, scorer dem med
                         FinBERT og laster ned kurser. Dellagrer hele veien.

    kjor_backtest(opp)   DEL 2: kjører hendelses-laben på de nedlastede dataene.
                         12 inngangsstrategier x 32 exit-strategier = 384
                         backtester, og velger én variant på treningsdata.

Alt ligger i én mappe som bygges fra bunnen (standard: ./LedelseData). Filen
er uavhengig av master.py, Only_260820.py og ExcelData-strukturen.

    python ledelsessentiment.py --hent            # bare del 1
    python ledelsessentiment.py --backtest        # bare del 2
    python ledelsessentiment.py --alt             # begge
    python ledelsessentiment.py --hent --full     # ignorer checkpoint, hent alt

STRATEGIEN
----------
Kjøp den første handelsdagen etter en rapport, hvis tonen har bedret seg nok
siden selskapets FORRIGE rapport. Seks terskler for bedring (20/50/85/135/200/
300 %), og de samme seks igjen med krav om kurs over SMA50 = 12 innganger.
Hver av dem testes mot 32 salgsmetoder: faste hold, alpha-plateau, neste
rapport, sentimentreversering, SMA/EMA, stop-loss, ATR-stop, trailing, profit
target, break-even, relativ underprestasjon, erstatning og to hybrider.

HVA SOM ER GJORT MER ROBUST ENN ORIGINALEN
------------------------------------------
Originalen kastet unntak ved den minste delfeil. Ett selskap som ikke lot seg
skrape veltet hele artikkeljobben; én ticker uten kurs veltet hele kursjobben;
ett mistenkelig kurshopp veltet hele publiseringen. Her gjelder i stedet:

  * Ingen enkeltfeil stopper kjøringen. Selskaper, artikler, tickere og
    backtest-varianter som feiler blir hoppet over, talt opp og rapportert.
  * Alt delLAGRES fortløpende. Artikler skrives til artikler.jsonl etter HVERT
    selskap (flush + fsync), kurser etter hver bolk, backtest-rader hver 25.
    Et avbrudd midt i en 6-timers kjøring koster deg siste selskap, ikke alt.
  * Kjøringen kan gjenopptas. Selskaper som alt er hentet hoppes over; bruk
    --full for å hente dem likevel.
  * Semantiske selectorer først, absolutt XPath sist. Originalen brukte
    /html/body/div[2]/div[1]/... som førstevalg — det brekker ved minste
    endring på nettstedet.
  * Nettverkskall har retry med backoff.

TO STEDER DER ROBUSTHET KOSTER NOE — LES DETTE
----------------------------------------------
  1. Mistenkelige kurser. Originalen NEKTET å publisere hvis en serie hadde et
     sprang paa 4x eller mer mellom to observasjoner. Her droppes den enkelte
     tickeren i stedet, og resten kjøres videre (opp.dropp_mistenkelige_kurser).
     Et ekte firedobling over seks år forsvinner da fra grunnlaget. Sett
     flagget til False for å beholde alt — men les kurs_problemer.csv først,
     for et udetektert splitt-feilhopp blir til falsk avkastning i backtesten.
  2. Artikler uten FinBERT-score. Faller modellen ut, lagres teksten likevel og
     raden får Final_Score = None. Backtesten ser bort fra slike rader. Kjør
     last_ned_data() på nytt senere for å score dem uten å skrape om igjen.

Ingen av delene sender e-post, og ingen av dem legger inn meglerordre.
Handlene er simulerte, og standard er null kurtasje, spread og slippage.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import math
import os
import re
import sys
import time
import warnings
from dataclasses import dataclass
from datetime import date, datetime
from math import exp
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

log = logging.getLogger("ledelsessentiment")


# ═══════════════════════════════════════════════════════════════════════════
# OPPSETT — alt som kan justeres, ett sted
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class Oppsett:
    # ── Mapper ────────────────────────────────────────────────────────────
    mappe: Path = Path("LedelseData")

    # ── Del 1: skraping ───────────────────────────────────────────────────
    euronext_base: str = "https://live.euronext.com"
    start_url: str = "https://live.euronext.com/nb/product/equities/NO0010161896-XOSL"
    aksjeliste_url: str = "https://live.euronext.com/nb/markets/oslo/equities/list"
    headless: bool = True
    slow_mo_ms: int = 40
    steg_pause_ms: int = 400
    side_timeout_ms: int = 25_000
    modal_pause_ms: int = 1_800
    artikkel_pause_s: float = 0.8
    maks_sider: int = 40           # paginering per selskap
    maks_artikler: int = 400       # per selskap
    forsok_per_selskap: int = 3
    # "minimal" = halvår + årsrapport · "quarterly" = + kvartal (anbefalt)
    # "all_financial" = + foreløpig regnskap og kapitalmarkedsdager
    # "everything" = ingen emnefilter (mye støy)
    emnefilter: str = "quarterly"

    # ── Del 1: FinBERT ────────────────────────────────────────────────────
    finbert_modell: str = "yiyanghkust/finbert-tone"
    maks_setninger: int = 100
    min_tekstlengde: int = 50

    # ── Del 1: kurser ─────────────────────────────────────────────────────
    kurs_start: str = "2019-01-01"
    kurs_bolk: int = 40
    oslo_suffix: str = ".OL"
    dropp_mistenkelige_kurser: bool = True
    mistenkelig_forhold: float = 4.0

    # ── Del 2: innganger ──────────────────────────────────────────────────
    terskler: Tuple[float, ...] = (20.0, 50.0, 85.0, 135.0, 200.0, 300.0)
    gulv: float = 0.05             # minste nevner i bedringsprosenten
    min_historikk_dager: int = 120  # kursobservasjoner før inngang
    sma_dager: int = 50

    # ── Del 2: portefølje ─────────────────────────────────────────────────
    startkapital: float = 1_000_000.0
    maks_posisjoner: int = 10
    hold_dager: int = 21
    dynamisk_maks_hold: int = 63

    # ── Del 2: exits ──────────────────────────────────────────────────────
    alpha_horisonter: Tuple[int, ...] = (3, 5, 8, 10, 15, 21, 30, 42, 63)
    alpha_plateau_andel: float = 0.95
    atr_dager: int = 20
    min_dager_for_trend_exit: int = 2
    min_dager_for_relative_exit: int = 3
    sentiment_reversering: float = -0.10
    relativ_stop: float = -0.03
    erstatt_min_alder: int = 5
    erstatt_styrkekrav: float = 1.50
    erstatt_halveringstid: float = 10.0

    # ── Del 2: variantvalg ────────────────────────────────────────────────
    # Varianten velges KUN på data til og med denne datoen. Senere resultater
    # brukes til visning, aldri til valg.
    trening_slutt: str = "2025-06-30"
    min_handler: int = 30
    min_treningsdager: int = 126
    manuelt_valg: str = ""         # f.eks. "S1|TP10" — merkes som manuelt

    # ── Avledede stier ────────────────────────────────────────────────────
    @property
    def selskapsfil(self) -> Path:
        return self.mappe / "selskaper.csv"

    @property
    def artikkelfil(self) -> Path:
        return self.mappe / "artikler.jsonl"

    @property
    def tekstmappe(self) -> Path:
        return self._lag(self.mappe / "tekster")

    @property
    def fullfortfil(self) -> Path:
        return self.mappe / "fullfort.json"

    @property
    def statusfil(self) -> Path:
        return self.mappe / "nedlasting_status.json"

    @property
    def framdriftsfil(self) -> Path:
        # Skrapingens egen framdrift. Egen fil, slik at den ikke overskriver
        # sluttstatusen — og slik at den overlever et avbrudd som sin egen sak.
        return self.mappe / "skraping_framdrift.json"

    @property
    def kursmappe(self) -> Path:
        return self._lag(self.mappe / "kurser")

    @property
    def resultatmappe(self) -> Path:
        return self._lag(self.mappe / "resultater")

    def _lag(self, p: Path) -> Path:
        p.mkdir(parents=True, exist_ok=True)
        return p

    def klargjor(self) -> None:
        self.mappe = Path(self.mappe)
        self.mappe.mkdir(parents=True, exist_ok=True)
        self.tekstmappe, self.kursmappe, self.resultatmappe


def sett_opp_logging(nivaa: int = logging.INFO) -> None:
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=nivaa,
            format="%(asctime)s  %(levelname)-7s  %(message)s",
            datefmt="%H:%M:%S",
        )


# ═══════════════════════════════════════════════════════════════════════════
# SMÅ HJELPERE
# ═══════════════════════════════════════════════════════════════════════════

def _rens(v) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()


def _tall(v) -> Optional[float]:
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def _filnavn(tekst: str, maks: int = 40) -> str:
    return re.sub(r"[^\w]", "_", str(tekst))[:maks] or "x"


def _les_json(sti: Path, standard):
    """Leser JSON. En ødelagt fil skal aldri stoppe en kjøring."""
    try:
        if sti.exists():
            return json.loads(sti.read_text(encoding="utf-8"))
    except Exception as e:
        log.warning("Kunne ikke lese %s (%s) — starter tomt.", sti.name, e)
    return standard


def _skriv_json(sti: Path, data) -> None:
    """Skriver via temp + replace, slik at et avbrudd ikke gir halv fil."""
    try:
        temp = sti.with_suffix(sti.suffix + ".tmp")
        temp.write_text(json.dumps(data, ensure_ascii=False, indent=2,
                                   default=str), encoding="utf-8")
        temp.replace(sti)
    except Exception as e:
        log.error("Kunne ikke skrive %s: %s", sti.name, e)


def _med_retry(kall, forsok: int = 4, pause: float = 2.0, hva: str = "kall"):
    """Kjører kall() med eksponentiell backoff. Returnerer (verdi, feil)."""
    siste = None
    for n in range(forsok):
        try:
            return kall(), None
        except Exception as e:
            siste = e
            if n < forsok - 1:
                ventetid = pause * (2 ** n)
                log.warning("%s feilet (%s) — nytt forsøk om %.0fs [%d/%d]",
                            hva, e, ventetid, n + 1, forsok)
                time.sleep(ventetid)
    return None, siste


# ═══════════════════════════════════════════════════════════════════════════
#
#   DEL 1 — NEDLASTING
#
# ═══════════════════════════════════════════════════════════════════════════

# Semantiske selectorer først. Absolutt XPath står sist, som nødløsning:
# originalen hadde dem FØRST, og da brekker alt av en liten layoutendring.
SEL_COOKIE = [
    "#onetrust-reject-all-handler",
    "#onetrust-accept-btn-handler",
    "button:has-text('Reject All')",
    "button:has-text('Accept All')",
    "button:has-text('Avvis alle')",
    "button:has-text('Godta alle')",
    "//*[@id='onetrust-reject-all-handler']",
]
SEL_SOKEFELT = [
    "input[name='search_symbol']",
    "header form input[type='text']",
    "nav input[type='text']",
    "input[placeholder*='øk' i]",
    "/html/body/div[2]/div[1]/div/div/header/nav[1]/div/div[2]/div[1]/form/div[2]/input",
]
SEL_DROPDOWN = [
    "ul.ui-autocomplete li:first-child a",
    ".ui-autocomplete li:first-child a",
    "ul[role='listbox'] li:first-child a",
    "ul.ui-autocomplete li:first-child",
    "/html/body/ul[1]/li[1]/a/span[1]/a",
]
SEL_SELSKAPSINFO = [
    "a[href*='company-information']",
    "a:has-text('SELSKAPSINFORMASJON')",
    "a:has-text('Company information')",
]
SEL_SE_ALLE = [
    "a[href*='listview/company-press-release']",
    "a[href*='company-press-release']",
    "a:has-text('Se alle')",
    "a:has-text('See all')",
]
SEL_FILTER = [
    "button:has-text('Filters')",
    "button:has-text('Filter')",
    "button.filter-toggle",
]
SEL_EMNE = [
    "button:has-text('Topic')",
    "button:has-text('Emne')",
    "details summary:has-text('Topic')",
]
SEL_BRUK = [
    "input[type='submit'][value*='Apply' i]",
    "input[type='submit'][value*='Bruk' i]",
    "button:has-text('Apply')",
    "button:has-text('Bruk')",
    ".views-exposed-form input[type='submit']",
]
SEL_NESTE_SIDE = [
    "li.pager__item--next a",
    "li.pager-next a",
    "a.pager__item--next",
    "a[rel='next']",
    "a[title='Go to next page']",
    "a[aria-label='Next page']",
    ".pagination a:has-text('›')",
    ".pager a:has-text('Next')",
    ".pager a:has-text('Neste')",
]

# Emnene som hukes av, per modus.
EMNER = {
    "halvaar": ["label:has-text('Halvårsdata')", "label:has-text('Half year')",
                "label:has-text('Half Year')"],
    "aarsrapport": ["label:has-text('Årsrapporter og revisjonsberetninger')",
                    "label:has-text('Annual reports')",
                    "label:has-text('Annual financial report')",
                    "label[for*='1070']"],
    "kvartal": ["label:has-text('Kvartalsdata')", "label:has-text('Quarterly')",
                "label:has-text('Quarterly report')"],
    "forelopig": ["label:has-text('Foreløpig regnskap')",
                  "label:has-text('Preliminary financial')"],
    "kapitalmarked": ["label:has-text('Kapitalmarkedsdager')",
                      "label:has-text('Capital markets day')"],
}

# Rader ut av pressemeldingstabellen. data-node-nid først, generisk tabell som
# reserve, slik at en klassenavnendring ikke tømmer resultatet.
JS_ARTIKKELRADER = """
() => {
    const ut = [];
    const lenker = document.querySelectorAll('a.standardRightCompanyPressRelease[data-node-nid]');
    for (const a of lenker) {
        const nid = a.getAttribute('data-node-nid') || '';
        const tittel = a.innerText.trim();
        if (!nid || !tittel) continue;
        let dato = '';
        const tr = a.closest('tr');
        if (tr) {
            const d = tr.querySelector('td:first-child span, td:first-child');
            if (d) dato = d.innerText.trim();
        }
        ut.push({nid: nid, tittel: tittel, dato: dato, href: ''});
    }
    if (ut.length === 0) {
        for (const tr of document.querySelectorAll('table tbody tr')) {
            const tds = tr.querySelectorAll('td');
            if (tds.length < 2) continue;
            const ds = tds[0] && tds[0].querySelector('span');
            const dato = ds ? ds.innerText.trim() : (tds[0] ? tds[0].innerText.trim() : '');
            let tittel = '', href = '', nid = '';
            for (const td of tds) {
                const a = td.querySelector('a');
                if (a && a.innerText.trim().length > 5) {
                    tittel = a.innerText.trim();
                    href = a.getAttribute('href') || '';
                    nid = a.getAttribute('data-node-nid') || '';
                    break;
                }
            }
            if (tittel && (href || nid)) ut.push({dato: dato, tittel: tittel, href: href, nid: nid});
        }
    }
    return ut;
}
"""

JS_LUKK_MODALER = """
() => {
    for (const m of document.querySelectorAll('.modal, [role=\"dialog\"]')) {
        m.classList.remove('show', 'in');
        m.style.display = 'none';
        m.setAttribute('aria-hidden', 'true');
    }
    for (const b of document.querySelectorAll('.modal-backdrop')) b.remove();
    document.body.classList.remove('modal-open');
    document.body.style.overflow = '';
    document.body.style.paddingRight = '';
}
"""

JS_MODALTEKST = """
(nid) => {
    let beste = '';
    const merket = document.querySelector(
        '#CompanyPressRelease-' + nid + ', [id*=\"CompanyPressRelease\"][id*=\"' + nid + '\"]');
    if (merket) {
        const b = merket.querySelector('.modal-body');
        if (b) beste = b.innerText.trim();
    }
    if (beste.length < 100) {
        const apne = document.querySelectorAll(
            '.modal.show, .modal.in, .modal[style*=\"display: block\"], ' +
            '.modal[aria-modal=\"true\"], [role=\"dialog\"]:not([style*=\"display: none\"])');
        for (const m of apne) {
            for (const sel of ['.modal-body', '.modal-content']) {
                const el = m.querySelector(sel);
                if (el) {
                    const t = el.innerText.trim();
                    if (t.length > beste.length) beste = t;
                }
            }
        }
    }
    return beste;
}
"""

JS_ARTIKKELTEKST = """
() => {
    const seler = [
        '.field--name-field-press-release-body',
        '.field--name-body',
        '.node__content .field--type-text-with-summary',
        '.node__content .field--type-text-long',
        'article .field--name-body',
        '.press-release-content',
        '.article-body',
        '[class*=\"press-release\"]',
        '[class*=\"article-content\"]',
    ];
    for (const sel of seler) {
        const el = document.querySelector(sel);
        if (el && el.innerText.trim().length > 100) return el.innerText.trim();
    }
    const m = document.querySelector('#main-content, main, [role=\"main\"]');
    return m ? m.innerText.trim() : document.body.innerText.trim();
}
"""

JS_PDF_LENKE = """
() => {
    for (const a of document.querySelectorAll('a[href]')) {
        const h = (a.href || '').toLowerCase();
        if (h.endsWith('.pdf') || h.includes('/pdf') ||
            (a.innerText && a.innerText.toLowerCase().includes('pdf'))) return a.href;
    }
    return null;
}
"""

SOPPEL = (
    "skip to main content", "toggle navigation", "euronext websites",
    "my profile", "my subscriptions", "watchlists", "quote alerts",
    "create account", "sign in", "close menu", "© 20", "privacy statement",
    "terms of use", "cookie policy", "to subscribe to press releases",
    "reject all", "accept all", "cookie settings",
)


def _vask_tekst(raa: str) -> str:
    """Fjerner meny- og bunntekst som ellers havner i sentimentscoren."""
    if not raa:
        return ""
    linjer = []
    for linje in raa.split("\n"):
        lav = linje.strip().lower()
        if any(s in lav for s in SOPPEL) or not linje.strip():
            continue
        linjer.append(linje.strip())
    return re.sub(r"\n{3,}", "\n\n", "\n".join(linjer)).strip()


def _sokevarianter(symbol: str, navn: str) -> List[str]:
    """Symbolet først, så navnet, så navnet uten selskapsform."""
    ut: List[str] = []
    for kandidat in (symbol, navn):
        k = _rens(kandidat)
        if k and k not in ut:
            ut.append(k)
    n = _rens(navn)
    if n:
        kort = re.sub(r"\s+(ASA|AS|A/S|Holding|Group|Gruppen)\s*$", "", n,
                      flags=re.IGNORECASE).strip()
        if kort and kort not in ut:
            ut.append(kort)
        ord_ = n.split()
        if len(ord_) >= 2 and " ".join(ord_[:2]) not in ut:
            ut.append(" ".join(ord_[:2]))
    return ut


# ─────────────────────────────────────────────────────────────────────────
# Artikkellageret — append-only, tåler avbrudd
# ─────────────────────────────────────────────────────────────────────────

ARTIKKELFELT = ["Company", "Article_Date", "Article_Title", "Article_URL",
                "Final_Score", "Positive_Score", "Neutral_Score",
                "Negative_Score", "Text_Length", "Tekst_Fil", "PDF_Used",
                "Scrape_Date"]


class Artikkellager:
    """
    Én JSON-linje per artikkel, skrevet med flush + fsync etter hvert selskap.

    Hvorfor ikke bare en Excel-fil: et avbrudd midt i en skriving av xlsx gir
    en korrupt fil og du mister alt. En append-only tekstfil mister på det
    verste siste linje, og resten er fortsatt lesbar.
    """

    def __init__(self, opp: Oppsett):
        self.opp = opp
        self.sti = opp.artikkelfil
        self.rader: List[dict] = []
        self._nokler: Set[Tuple[str, str, str]] = set()
        self._les_eksisterende()

    def _nokkel(self, rad: dict) -> Tuple[str, str, str]:
        return (_rens(rad.get("Company")), str(rad.get("Article_Date"))[:10],
                _rens(rad.get("Article_Title"))[:90])

    def _les_eksisterende(self) -> None:
        if not self.sti.exists():
            return
        skadet = 0
        for linje in self.sti.read_text(encoding="utf-8", errors="replace").splitlines():
            linje = linje.strip()
            if not linje:
                continue
            try:
                rad = json.loads(linje)
            except Exception:
                skadet += 1
                continue
            self.rader.append(rad)
            self._nokler.add(self._nokkel(rad))
        log.info("Lager   : %d artikler fra før%s", len(self.rader),
                 f" ({skadet} ulesbare linjer hoppet over)" if skadet else "")

    def har(self, rad: dict) -> bool:
        return self._nokkel(rad) in self._nokler

    def legg_til(self, nye: Sequence[dict]) -> int:
        """Skriver nye rader til disk med en gang. Returnerer antall lagret."""
        ferske = [r for r in nye if not self.har(r)]
        if not ferske:
            return 0
        try:
            with self.sti.open("a", encoding="utf-8") as fh:
                for rad in ferske:
                    fh.write(json.dumps(rad, ensure_ascii=False, default=str) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
        except Exception as e:
            log.error("Kunne ikke skrive artikler til disk: %s", e)
            return 0
        for rad in ferske:
            self.rader.append(rad)
            self._nokler.add(self._nokkel(rad))
        return len(ferske)

    def uten_score(self) -> List[dict]:
        return [r for r in self.rader if _tall(r.get("Final_Score")) is None
                and int(r.get("Text_Length") or 0) >= self.opp.min_tekstlengde]

    def skriv_om(self) -> None:
        """Skriver hele lageret på nytt — brukes etter etterskåring."""
        try:
            temp = self.sti.with_suffix(".jsonl.tmp")
            with temp.open("w", encoding="utf-8") as fh:
                for rad in self.rader:
                    fh.write(json.dumps(rad, ensure_ascii=False, default=str) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
            temp.replace(self.sti)
        except Exception as e:
            log.error("Kunne ikke skrive om artikkellageret: %s", e)

    def lagre_tabell(self) -> None:
        """Bekvemmelighetskopi som CSV og (hvis mulig) Excel."""
        if not self.rader:
            return
        try:
            import pandas as pd
            df = pd.DataFrame(self.rader)
            for kol in ARTIKKELFELT:
                if kol not in df.columns:
                    df[kol] = None
            df = df[ARTIKKELFELT]
            df.to_csv(self.opp.mappe / "artikler.csv", index=False)
            try:
                df.to_excel(self.opp.mappe / "artikler.xlsx", index=False)
            except Exception as e:
                log.debug("Excel-kopi hoppet over (%s)", e)
        except Exception as e:
            log.warning("Kunne ikke lagre artikkeltabellen: %s", e)


# ─────────────────────────────────────────────────────────────────────────
# FinBERT
# ─────────────────────────────────────────────────────────────────────────

class Sentiment:
    """
    FinBERT-scoring som ikke velter kjøringen når modellen ikke er der.

    analyser() returnerer None i stedet for å kaste. Kalleren lagrer da
    artikkelen uten score, og en senere kjøring kan score den uten å skrape
    på nytt. Det er nøyaktig det motsatte av å finne på en nøytral score:
    en manglende score er merket som manglende hele veien.
    """

    def __init__(self, opp: Oppsett):
        self.opp = opp
        self.pipe = None
        self.feil = ""
        self._last()

    def _last(self) -> None:
        try:
            import torch
            from transformers import (BertForSequenceClassification,
                                      BertTokenizer, pipeline)
            log.info("FinBERT : laster %s …", self.opp.finbert_modell)
            tok = BertTokenizer.from_pretrained(self.opp.finbert_modell)
            mod = BertForSequenceClassification.from_pretrained(self.opp.finbert_modell)
            enhet = "cuda" if torch.cuda.is_available() else "cpu"
            self.pipe = pipeline("sentiment-analysis", model=mod,
                                 tokenizer=tok, device=enhet)
            log.info("FinBERT : klar på %s", enhet)
        except Exception as e:
            self.feil = str(e)
            log.error("FinBERT utilgjengelig (%s). Artikler lagres uten score "
                      "og kan scores senere uten ny skraping.", e)

    @property
    def klar(self) -> bool:
        return self.pipe is not None

    def _setninger(self, tekst: str) -> List[str]:
        try:
            import nltk
            try:
                from nltk.tokenize import sent_tokenize
                return sent_tokenize(tekst)[:self.opp.maks_setninger]
            except LookupError:
                nltk.download("punkt", quiet=True)
                nltk.download("punkt_tab", quiet=True)
                from nltk.tokenize import sent_tokenize
                return sent_tokenize(tekst)[:self.opp.maks_setninger]
        except Exception:
            # Uten nltk: del på punktum. Dårligere, men ikke stoppende.
            biter = re.split(r"(?<=[.!?])\s+", tekst)
            return [b for b in biter if b.strip()][:self.opp.maks_setninger]

    def analyser(self, tekst: str) -> Optional[dict]:
        if not self.klar or not tekst or len(tekst) < self.opp.min_tekstlengde:
            return None
        try:
            setninger = self._setninger(tekst)
            sum_ = {"positive": 0.0, "neutral": 0.0, "negative": 0.0}
            n = 0
            for i in range(0, len(setninger), 16):
                bolk = setninger[i:i + 16]
                try:
                    svar = self.pipe(bolk, truncation=True, max_length=512)
                except Exception:
                    # Bolken feilet — prøv én og én, hopp over dem som ryker.
                    svar = []
                    for s in bolk:
                        try:
                            svar.extend(self.pipe(s, truncation=True, max_length=512))
                        except Exception:
                            continue
                for r in svar:
                    merke = str(r.get("label", "")).lower()
                    if merke in sum_:
                        sum_[merke] += float(r.get("score", 0.0))
                        n += 1
            if not n:
                return None
            return {k: v / n for k, v in sum_.items()}
        except Exception as e:
            log.warning("Sentimentscoring feilet: %s", e)
            return None


# ─────────────────────────────────────────────────────────────────────────
# Selskapslisten
# ─────────────────────────────────────────────────────────────────────────

def _les_selskapsfil(opp: Oppsett) -> List[dict]:
    if not opp.selskapsfil.exists():
        return []
    try:
        import csv
        with opp.selskapsfil.open(encoding="utf-8-sig", newline="") as fh:
            rader = list(csv.DictReader(fh))
    except Exception as e:
        log.error("Kunne ikke lese %s: %s", opp.selskapsfil.name, e)
        return []
    ut = []
    for r in rader:
        symbol = _rens(r.get("Symbol") or r.get("Company") or r.get("Ticker"))
        symbol = symbol.upper().replace(".OL", "")
        if not symbol or symbol.startswith("^"):
            continue
        ut.append({"Symbol": symbol,
                   "Navn": _rens(r.get("Navn") or r.get("Name")) or symbol,
                   "ISIN": _rens(r.get("ISIN"))})
    return ut


def _skriv_selskapsfil(opp: Oppsett, selskaper: Sequence[dict]) -> None:
    try:
        import csv
        with opp.selskapsfil.open("w", encoding="utf-8", newline="") as fh:
            skriv = csv.DictWriter(fh, fieldnames=["Symbol", "Navn", "ISIN"])
            skriv.writeheader()
            for s in selskaper:
                skriv.writerow({k: s.get(k, "") for k in ("Symbol", "Navn", "ISIN")})
        log.info("Selskaper: skrev %d til %s", len(selskaper), opp.selskapsfil)
    except Exception as e:
        log.error("Kunne ikke skrive selskapsfilen: %s", e)


def _last_ned_aksjeliste(opp: Oppsett) -> List[dict]:
    """
    Henter Euronext-aksjelista med nettleseren: nedlastingsikon, så «Go».

    Feiler den, returneres tom liste og kalleren ber deg lage selskaper.csv
    for hånd. Ingen unntak slipper ut.
    """
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        log.error("Playwright mangler (%s). Lag %s manuelt med kolonnene "
                  "Symbol,Navn,ISIN.", e, opp.selskapsfil)
        return []

    raa: List[dict] = []
    try:
        with sync_playwright() as pw:
            nettleser = pw.chromium.launch(headless=opp.headless,
                                           slow_mo=opp.slow_mo_ms)
            side = nettleser.new_page()
            side.set_default_timeout(opp.side_timeout_ms)
            side.goto(opp.aksjeliste_url, wait_until="domcontentloaded",
                      timeout=60_000)
            side.wait_for_timeout(2_000)
            for sel in SEL_COOKIE:
                try:
                    if side.locator(sel).count():
                        side.locator(sel).first.click(timeout=4_000)
                        break
                except Exception:
                    continue

            # Tabellen ligger på sida; les den direkte i stedet for å gå
            # gjennom nedlastingsdialogen. Færre klikk = færre bruddflater.
            try:
                side.wait_for_selector("table tbody tr", timeout=20_000)
                # Vis så mange rader som mulig før vi leser.
                for sel in ["select[name='per_page']", "select#edit-items-per-page"]:
                    try:
                        if side.locator(sel).count():
                            side.select_option(sel, "100")
                            side.wait_for_timeout(2_000)
                            break
                    except Exception:
                        continue
                for _ in range(60):
                    rader = side.evaluate("""
                    () => {
                        const ut = [];
                        for (const tr of document.querySelectorAll('table tbody tr')) {
                            const tds = [...tr.querySelectorAll('td')].map(td => td.innerText.trim());
                            if (tds.length >= 2) ut.push(tds);
                        }
                        return ut;
                    }
                    """)
                    for tds in rader:
                        isin = next((t for t in tds if re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}\d", t or "")), "")
                        symbol = next((t for t in tds
                                       if re.fullmatch(r"[A-Z][A-Z0-9\-]{1,9}", t or "")
                                       and t != isin), "")
                        navn = tds[0] if tds else ""
                        if symbol:
                            raa.append({"Symbol": symbol, "Navn": navn, "ISIN": isin})
                    klikket = False
                    for sel in SEL_NESTE_SIDE:
                        try:
                            loc = side.locator(sel)
                            if loc.count():
                                loc.first.click(timeout=5_000)
                                side.wait_for_timeout(1_500)
                                klikket = True
                                break
                        except Exception:
                            continue
                    if not klikket:
                        break
            except Exception as e:
                log.error("Kunne ikke lese aksjelistetabellen: %s", e)
            nettleser.close()
    except Exception as e:
        log.error("Nedlasting av aksjelista feilet: %s", e)

    sett, ut = set(), []
    for r in raa:
        s = r["Symbol"].upper()
        if s and s not in sett:
            sett.add(s)
            ut.append(r)
    log.info("Aksjeliste: %d selskaper hentet", len(ut))
    return ut


def hent_selskaper(opp: Oppsett, selskaper: Optional[Sequence] = None) -> List[dict]:
    """Eksplisitt liste > selskaper.csv > nedlasting fra Euronext."""
    if selskaper:
        ut = []
        for s in selskaper:
            if isinstance(s, dict):
                sym = _rens(s.get("Symbol") or s.get("Company")).upper().replace(".OL", "")
                ut.append({"Symbol": sym, "Navn": _rens(s.get("Navn")) or sym,
                           "ISIN": _rens(s.get("ISIN"))})
            else:
                sym = _rens(s).upper().replace(".OL", "")
                ut.append({"Symbol": sym, "Navn": sym, "ISIN": ""})
        ut = [s for s in ut if s["Symbol"]]
        if ut:
            _skriv_selskapsfil(opp, ut)
            return ut

    fra_fil = _les_selskapsfil(opp)
    if fra_fil:
        log.info("Selskaper: %d fra %s", len(fra_fil), opp.selskapsfil.name)
        return fra_fil

    lastet = _last_ned_aksjeliste(opp)
    if lastet:
        _skriv_selskapsfil(opp, lastet)
    else:
        log.error("Ingen selskapsliste. Lag %s med kolonnene Symbol,Navn,ISIN.",
                  opp.selskapsfil)
    return lastet


# ─────────────────────────────────────────────────────────────────────────
# Skraping — én side, mange selskaper
# ─────────────────────────────────────────────────────────────────────────

async def _klikk(side, kandidater: Sequence[str], hva: str,
                 timeout: int = 6_000) -> bool:
    """Prøver selectorene i rekkefølge. Returnerer True ved første treff."""
    for sel in kandidater:
        try:
            loc = (side.locator("xpath=" + sel) if sel.startswith(("/", "("))
                   else side.locator(sel))
            if await loc.count() == 0:
                continue
            el = loc.first
            try:
                await el.scroll_into_view_if_needed(timeout=2_000)
                await side.wait_for_timeout(150)
            except Exception:
                pass
            await el.click(timeout=timeout)
            log.debug("  klikket %s via %s", hva, sel[:50])
            return True
        except Exception:
            continue
    return False


async def _gaa_til(side, url: str, opp: Oppsett, timeout: Optional[int] = None) -> bool:
    try:
        await side.goto(url, wait_until="domcontentloaded",
                        timeout=timeout or opp.side_timeout_ms)
        await side.wait_for_timeout(1_200)
        return True
    except Exception as e:
        log.debug("Navigering til %s feilet: %s", url[:70], e)
        return False


async def _lukk_modaler(side) -> None:
    try:
        await side.evaluate(JS_LUKK_MODALER)
        await side.keyboard.press("Escape")
        await side.wait_for_timeout(200)
    except Exception:
        pass


async def _finn_selskap(side, symbol: str, navn: str, opp: Oppsett) -> bool:
    """Søker opp selskapet. Prøver symbol, så navn, så kortformer."""
    for term in _sokevarianter(symbol, navn):
        felt = None
        for sel in SEL_SOKEFELT:
            try:
                loc = (side.locator("xpath=" + sel) if sel.startswith("/")
                       else side.locator(sel))
                if await loc.count():
                    felt = loc.first
                    break
            except Exception:
                continue
        if felt is None:
            return False
        try:
            await felt.click(timeout=6_000)
            await felt.fill("")
            await felt.type(term, delay=55)
            await side.wait_for_timeout(2_200)
        except Exception:
            continue
        if not await _klikk(side, SEL_DROPDOWN, f"dropdown '{term}'", 7_000):
            try:
                await side.keyboard.press("Escape")
            except Exception:
                pass
            continue
        try:
            await side.wait_for_load_state("networkidle", timeout=12_000)
        except Exception:
            pass
        await side.wait_for_timeout(1_000)
        if "/product/equities/" in side.url:
            return True
        await _gaa_til(side, opp.start_url, opp)
    return False


async def _velg_emner(side, opp: Oppsett) -> None:
    """Huker av emnefilteret. Manglende emner logges, men stopper ingenting."""
    if opp.emnefilter == "everything":
        return
    await _klikk(side, SEL_FILTER, "filterpanel", 8_000)
    await side.wait_for_timeout(1_200)
    await _klikk(side, SEL_EMNE, "emnemeny", 7_000)
    await side.wait_for_timeout(800)

    onsket = ["halvaar", "aarsrapport"]
    if opp.emnefilter in ("quarterly", "all_financial"):
        onsket.append("kvartal")
    if opp.emnefilter == "all_financial":
        onsket += ["forelopig", "kapitalmarked"]

    for navn in onsket:
        if not await _klikk(side, EMNER[navn], f"emne {navn}", 5_000):
            log.debug("  emnet %s ble ikke funnet", navn)
        await side.wait_for_timeout(300)

    if await _klikk(side, SEL_BRUK, "Bruk/Apply", 7_000):
        try:
            await side.wait_for_load_state("networkidle", timeout=10_000)
        except Exception:
            pass
        await side.wait_for_timeout(1_500)


async def _samle_rader(side, opp: Oppsett) -> Tuple[List[dict], bool]:
    """
    Blar gjennom tabellen og samler artikkelrader.

    Returnerer (rader, komplett). Originalen KASTET når en side ikke ga nye
    rader eller sikkerhetsgrensen ble nådd; her stopper vi bare og melder
    komplett=False, slik at det vi faktisk fikk blir brukt.
    """
    rader: List[dict] = []
    sette_nid: Set[str] = set()
    sette_tittel: Set[str] = set()
    komplett = True

    for sidenr in range(1, opp.maks_sider + 1):
        try:
            await side.wait_for_selector("table tbody tr", timeout=10_000)
        except Exception:
            try:
                kropp = (await side.locator("body").inner_text()).lower()
            except Exception:
                kropp = ""
            if any(t in kropp for t in ("no results found", "ingen resultater",
                                        "ingen treff")):
                return [], True          # bekreftet tomt, ikke en feil
            log.warning("  tabellen kom ikke på side %d — bruker det vi har", sidenr)
            return rader, False

        await side.wait_for_timeout(700)
        try:
            nye_rader = await side.evaluate(JS_ARTIKKELRADER)
        except Exception as e:
            log.warning("  kunne ikke lese side %d (%s)", sidenr, e)
            return rader, False

        nye = 0
        for r in nye_rader:
            nid, tittel = r.get("nid", ""), r.get("tittel", "")
            if nid and nid in sette_nid:
                continue
            if not nid and tittel in sette_tittel:
                continue
            if nid:
                sette_nid.add(nid)
            if tittel:
                sette_tittel.add(tittel)
            rader.append(r)
            nye += 1

        log.debug("  side %d: %d rader, %d nye (totalt %d)",
                  sidenr, len(nye_rader), nye, len(rader))

        if len(rader) >= opp.maks_artikler:
            log.info("  nådde grensen på %d artikler — stopper her",
                     opp.maks_artikler)
            return rader[:opp.maks_artikler], False
        if nye == 0:
            return rader, komplett
        if not await _klikk(side, SEL_NESTE_SIDE, "neste side", 7_000):
            return rader, komplett
        try:
            await side.wait_for_load_state("networkidle", timeout=10_000)
        except Exception:
            pass
        await side.wait_for_timeout(1_200)

    return rader, False                  # sidegrensen nådd


def _pdf_tekst(url: str) -> str:
    try:
        import io
        import requests
        import pdfplumber
        svar = requests.get(url, timeout=30, headers={
            "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/124.0 Safari/537.36")})
        svar.raise_for_status()
        with pdfplumber.open(io.BytesIO(svar.content)) as pdf:
            biter = [s.extract_text() for s in pdf.pages if s.extract_text()]
        return _vask_tekst("\n\n".join(biter))
    except Exception as e:
        log.debug("PDF-uttrekk feilet (%s): %s", url[:70], e)
        return ""


async def _hent_tekst(side, rad: dict, liste_url: str, opp: Oppsett) -> Tuple[str, bool]:
    """Returnerer (tekst, pdf_brukt). Kaster aldri."""
    nid, href = rad.get("nid", ""), rad.get("href", "")

    if nid and not href:
        try:
            await _lukk_modaler(side)
            loc = side.locator(
                f"a.standardRightCompanyPressRelease[data-node-nid='{nid}']")
            if await loc.count() == 0:
                return "", False
            try:
                await loc.first.scroll_into_view_if_needed(timeout=4_000)
            except Exception:
                pass
            await loc.first.click(timeout=10_000)
            await side.wait_for_timeout(opp.modal_pause_ms)
            tekst = await side.evaluate(JS_MODALTEKST, nid)
            await _lukk_modaler(side)
            return _vask_tekst(tekst or ""), False
        except Exception as e:
            log.debug("  modal nid=%s feilet: %s", nid, e)
            await _lukk_modaler(side)
            return "", False

    url = href if href.startswith("http") else opp.euronext_base + href
    try:
        if not await _gaa_til(side, url, opp):
            return "", False
        try:
            innholdstype = await side.evaluate("() => document.contentType || ''")
        except Exception:
            innholdstype = ""
        if "pdf" in innholdstype.lower() or url.lower().endswith(".pdf"):
            tekst = _pdf_tekst(url)
            await _gaa_til(side, liste_url, opp)
            return tekst, bool(tekst)

        tekst = _vask_tekst(await side.evaluate(JS_ARTIKKELTEKST) or "")
        pdf_brukt = False
        if len(tekst) < 200:
            try:
                pdf_url = await side.evaluate(JS_PDF_LENKE)
            except Exception:
                pdf_url = None
            if pdf_url:
                fra_pdf = _pdf_tekst(pdf_url)
                if len(fra_pdf) > len(tekst):
                    tekst, pdf_brukt = fra_pdf, True
        await _gaa_til(side, liste_url, opp)
        return tekst, pdf_brukt
    except Exception as e:
        log.debug("  artikkeltekst feilet (%s): %s", url[:70], e)
        await _gaa_til(side, liste_url, opp)
        return "", False


async def _skrap_selskap(side, selskap: dict, forste: bool,
                         opp: Oppsett) -> Tuple[List[dict], str]:
    """
    Alle artiklene for ett selskap. Returnerer (rader, merknad).

    Kaster aldri. En tom liste med merknad betyr «ikke hentet»; en tom liste
    uten merknad betyr «bekreftet ingen artikler».
    """
    symbol, navn = selskap["Symbol"], selskap.get("Navn", "")

    if forste:
        if not await _gaa_til(side, opp.start_url, opp, 60_000):
            return [], "kom ikke inn på Euronext"
        for sel in SEL_COOKIE:
            if await _klikk(side, [sel], "cookie", 5_000):
                break
        await side.wait_for_timeout(opp.steg_pause_ms)
    else:
        if not await _finn_selskap(side, symbol, navn, opp):
            await _gaa_til(side, opp.start_url, opp)
            return [], f"fant ikke '{symbol}' i søket"

    # Selskapsinformasjon-fanen.
    if not await _klikk(side, SEL_SELSKAPSINFO, "selskapsinformasjon", 8_000):
        treff = re.search(r"(/product/equities/[^/?#]+)", side.url)
        if not treff or not await _gaa_til(
                side, opp.euronext_base + treff.group(1) + "/company-information", opp):
            return [], "nådde ikke selskapsinformasjon"
    await side.wait_for_timeout(1_000)

    # Full pressemeldingsliste.
    if not await _klikk(side, SEL_SE_ALLE, "se alle", 8_000):
        log.debug("  'Se alle' ikke funnet — bruker sida som den er")
    else:
        try:
            await side.wait_for_load_state("networkidle", timeout=10_000)
        except Exception:
            pass
    await side.wait_for_timeout(1_200)

    try:
        await _velg_emner(side, opp)
    except Exception as e:
        log.debug("  emnefilter feilet (%s) — fortsetter ufiltrert", e)

    liste_url = side.url
    rader, komplett = await _samle_rader(side, opp)
    if not rader:
        return [], "" if komplett else "ingen artikkelrader lest"

    await _gaa_til(side, liste_url, opp)

    ut: List[dict] = []
    for n, rad in enumerate(rader, 1):
        tekst, pdf_brukt = await _hent_tekst(side, rad, liste_url, opp)
        fil = ""
        if tekst:
            try:
                fil = f"{_filnavn(symbol)}_{_filnavn(rad.get('tittel',''), 30)}_{n}.txt"
                (opp.tekstmappe / fil).write_text(tekst[:60_000], encoding="utf-8")
            except Exception as e:
                log.debug("  kunne ikke lagre tekstfil: %s", e)
                fil = ""
        ut.append({
            "Company": symbol,
            "Article_Date": _rens(rad.get("dato")),
            "Article_Title": _rens(rad.get("tittel"))[:180],
            "Article_URL": rad.get("href") or (f"modal://{rad.get('nid','')}"),
            "Final_Score": None, "Positive_Score": None,
            "Neutral_Score": None, "Negative_Score": None,
            "Text_Length": len(tekst), "Tekst_Fil": fil,
            "PDF_Used": bool(pdf_brukt),
            "Scrape_Date": date.today().isoformat(),
        })
        await side.wait_for_timeout(int(opp.artikkel_pause_s * 1_000))

    merknad = "" if komplett else "delvis liste"
    return ut, merknad


async def _skrap_alle(selskaper: Sequence[dict], lager: Artikkellager,
                      skaarer: Sentiment, fullfort: dict,
                      opp: Oppsett) -> dict:
    """Skraper alle selskapene. Lagrer etter hvert eneste selskap."""
    from playwright.async_api import async_playwright

    status = {"hentet": 0, "hoppet": 0, "feilet": [], "delvis": [],
              "artikler_nye": 0, "uten_score": 0}

    async with async_playwright() as pw:
        nettleser = await pw.chromium.launch(headless=opp.headless,
                                             slow_mo=opp.slow_mo_ms)
        kontekst = await nettleser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"))
        side = await kontekst.new_page()
        side.set_default_timeout(opp.side_timeout_ms)

        forste = True
        for n, selskap in enumerate(selskaper, 1):
            symbol = selskap["Symbol"]
            log.info("[%d/%d] %s", n, len(selskaper), symbol)

            rader, merknad = [], "ikke forsøkt"
            for forsok in range(1, opp.forsok_per_selskap + 1):
                try:
                    rader, merknad = await _skrap_selskap(side, selskap, forste, opp)
                    forste = False
                except Exception as e:
                    rader, merknad = [], f"{type(e).__name__}: {e}"
                    log.warning("  forsøk %d feilet: %s", forsok, merknad)
                if rader or not merknad:
                    break
                if forsok < opp.forsok_per_selskap:
                    await side.wait_for_timeout(2_500 * forsok)
                    await _gaa_til(side, opp.start_url, opp)

            # Score med en gang, mens teksten er fersk.
            for rad in rader:
                if rad["Text_Length"] < opp.min_tekstlengde or not rad["Tekst_Fil"]:
                    continue
                try:
                    tekst = (opp.tekstmappe / rad["Tekst_Fil"]).read_text(encoding="utf-8")
                except Exception:
                    continue
                poeng = skaarer.analyser(tekst)
                if poeng:
                    rad.update({
                        "Positive_Score": round(poeng["positive"], 4),
                        "Neutral_Score": round(poeng["neutral"], 4),
                        "Negative_Score": round(poeng["negative"], 4),
                        "Final_Score": round(poeng["positive"] - poeng["negative"], 4),
                    })
                else:
                    status["uten_score"] += 1

            lagret = lager.legg_til(rader)
            status["artikler_nye"] += lagret

            if rader:
                status["hentet"] += 1
                fullfort[symbol] = date.today().isoformat()
                if merknad:
                    status["delvis"].append(f"{symbol}: {merknad}")
                log.info("  → %d artikler (%d nye)", len(rader), lagret)
            else:
                if merknad:
                    status["feilet"].append(f"{symbol}: {merknad}")
                    log.warning("  → hoppet over: %s", merknad)
                else:
                    status["hentet"] += 1
                    fullfort[symbol] = date.today().isoformat()
                    log.info("  → ingen artikler (bekreftet tomt)")

            # Delllagring etter HVERT selskap.
            _skriv_json(opp.fullfortfil, fullfort)
            _skriv_json(opp.framdriftsfil, status)
            if n % 10 == 0:
                lager.lagre_tabell()

        try:
            await nettleser.close()
        except Exception:
            pass

    return status


# ─────────────────────────────────────────────────────────────────────────
# Kurser
# ─────────────────────────────────────────────────────────────────────────

def _yahoo_bolk(tickere: Sequence[str], start: str):
    """En bolk med yfinance. Returnerer dict felt -> DataFrame."""
    import pandas as pd
    import yfinance as yf
    raa = yf.download(list(tickere), start=start, auto_adjust=True,
                      progress=False, threads=False,
                      end=datetime.now().strftime("%Y-%m-%d"))
    if raa is None or raa.empty:
        raise RuntimeError("tomt svar")
    ut = {}
    for felt in ("Close", "High", "Low"):
        if isinstance(raa.columns, pd.MultiIndex):
            if felt not in raa.columns.get_level_values(0):
                continue
            d = raa[felt].copy()
        else:
            if felt not in raa.columns:
                continue
            d = raa[[felt]].copy()
            d.columns = [tickere[0]]
        ut[felt] = d
    if "Close" not in ut:
        raise RuntimeError("ingen Close-kolonne")
    return ut


def _slaa_sammen(gammel, ny):
    import pandas as pd
    if gammel is None or gammel.empty:
        return ny
    if ny is None or ny.empty:
        return gammel
    samlet = pd.concat([gammel, ny], axis=1)
    # Nyeste kolonne vinner ved duplikat.
    samlet = samlet.loc[:, ~samlet.columns.duplicated(keep="last")]
    return samlet.sort_index()


def _kursproblemer(close, opp: Oppsett):
    """
    Finner ugyldige kurser og usannsynlige sprang.

    Originalen kastet unntak her og nektet å publisere. Vi rapporterer i
    stedet, og kalleren dropper de berørte tickerne hvis flagget er satt.
    """
    import numpy as np
    import pandas as pd
    funn = []
    for ticker in close.columns:
        serie = pd.to_numeric(close[ticker], errors="coerce").dropna()
        for dag, pris in serie[~np.isfinite(serie) | (serie <= 0)].items():
            funn.append({"ticker": ticker, "dato": str(dag.date()),
                         "type": "ugyldig_kurs", "kurs": float(pris),
                         "forhold": None})
        gode = serie[np.isfinite(serie) & (serie > 0)]
        forhold = gode / gode.shift(1)
        grense = opp.mistenkelig_forhold
        for dag in forhold.index[(forhold >= grense) | (forhold <= 1.0 / grense)]:
            funn.append({"ticker": ticker, "dato": str(dag.date()),
                         "type": "ubekreftet_kurssprang",
                         "kurs": float(gode.loc[dag]),
                         "forhold": float(forhold.loc[dag])})
    return pd.DataFrame(funn, columns=["ticker", "dato", "type", "kurs", "forhold"])


def last_ned_kurser(opp: Oppsett, tickere: Sequence[str]) -> dict:
    """
    Laster ned Close/High/Low for tickerne, bolk for bolk.

    En bolk som feiler prøves ticker for ticker. En ticker som fortsatt
    feiler hoppes over og noteres — den stopper ikke resten.
    """
    import pandas as pd

    tickere = sorted({t for t in tickere if t})
    if not tickere:
        return {"status": "TOM", "nedlastet": 0, "manglende": [], "droppet": []}

    felter = {}
    for felt, navn in (("Close", "kurser_close.csv"), ("High", "kurser_high.csv"),
                       ("Low", "kurser_low.csv")):
        sti = opp.kursmappe / navn
        try:
            if sti.exists():
                felter[felt] = pd.read_csv(sti, index_col=0, parse_dates=True)
            else:
                felter[felt] = pd.DataFrame()
        except Exception as e:
            log.warning("Kunne ikke lese %s (%s) — starter tomt.", navn, e)
            felter[felt] = pd.DataFrame()

    def lagre():
        for f, navn in (("Close", "kurser_close.csv"), ("High", "kurser_high.csv"),
                        ("Low", "kurser_low.csv")):
            try:
                if not felter[f].empty:
                    felter[f].sort_index().to_csv(opp.kursmappe / navn,
                                                  index_label="Date")
            except Exception as e:
                log.error("Kunne ikke lagre %s: %s", navn, e)

    manglende: List[str] = []
    bolker = [tickere[i:i + opp.kurs_bolk]
              for i in range(0, len(tickere), opp.kurs_bolk)]

    for n, bolk in enumerate(bolker, 1):
        log.info("Kurser  : bolk %d/%d (%d tickere)", n, len(bolker), len(bolk))
        data, feil = _med_retry(lambda b=bolk: _yahoo_bolk(b, opp.kurs_start),
                                forsok=3, hva=f"kursbolk {n}")
        if data is None:
            log.warning("  bolken feilet (%s) — prøver én og én", feil)
            data = {}
            for t in bolk:
                enkelt, e2 = _med_retry(lambda x=t: _yahoo_bolk([x], opp.kurs_start),
                                        forsok=2, pause=1.5, hva=t)
                if enkelt is None:
                    manglende.append(t)
                    log.warning("  %s: ingen kurser (%s)", t, e2)
                    continue
                for felt, ramme in enkelt.items():
                    data[felt] = _slaa_sammen(data.get(felt), ramme)

        for felt in ("Close", "High", "Low"):
            if felt in data:
                felter[felt] = _slaa_sammen(felter[felt], data[felt])
        lagre()                                   # delLAGRING etter hver bolk

    close = felter["Close"]
    tomme = [t for t in tickere
             if t not in close.columns or close[t].dropna().empty]
    for t in tomme:
        if t not in manglende:
            manglende.append(t)

    problemer = _kursproblemer(close, opp) if not close.empty else None
    droppet: List[str] = []
    if problemer is not None and not problemer.empty:
        try:
            problemer.to_csv(opp.kursmappe / "kurs_problemer.csv", index=False)
        except Exception as e:
            log.error("Kunne ikke skrive kurs_problemer.csv: %s", e)
        berorte = sorted(problemer["ticker"].unique())
        log.warning("Kurser  : %d tickere har ubekreftede sprang eller ugyldige "
                    "kurser — se kurs_problemer.csv", len(berorte))
        if opp.dropp_mistenkelige_kurser:
            droppet = berorte
            for felt in ("Close", "High", "Low"):
                if not felter[felt].empty:
                    felter[felt] = felter[felt].drop(
                        columns=[c for c in berorte if c in felter[felt].columns])
            lagre()
            log.warning("Kurser  : droppet dem fra grunnlaget "
                        "(dropp_mistenkelige_kurser=True)")

    resultat = {
        "status": "OK" if not manglende and not droppet else "DELVIS",
        "bedt_om": len(tickere),
        "nedlastet": int(felter["Close"].shape[1]) if not felter["Close"].empty else 0,
        "manglende": manglende,
        "droppet": droppet,
        "siste_observasjon": (str(felter["Close"].dropna(how="all").index.max().date())
                              if not felter["Close"].empty else None),
    }
    log.info("Kurser  : %d av %d tickere brukbare, %d manglende, %d droppet",
             resultat["nedlastet"], len(tickere), len(manglende), len(droppet))
    return resultat


# ─────────────────────────────────────────────────────────────────────────
# DEL 1 — hovedfunksjonen
# ─────────────────────────────────────────────────────────────────────────

def last_ned_data(opp: Optional[Oppsett] = None,
                  selskaper: Optional[Sequence] = None,
                  full: bool = False,
                  hent_artikler: bool = True,
                  hent_kurser_ogsaa: bool = True) -> dict:
    """
    DEL 1 — henter alt backtesten trenger, og gir seg aldri på én feil.

    Parametre
    ---------
    opp        Oppsett. None gir standardoppsettet i ./LedelseData.
    selskaper  Valgfri liste med symboler eller dicts. None leser selskaper.csv,
               eller henter aksjelista fra Euronext hvis fila mangler.
    full       True henter alle selskaper på nytt. False (standard) hopper over
               dem som allerede er hentet, slik at en avbrutt kjøring kan
               gjenopptas uten å skrape om igjen.

    Returnerer en statusdict som også ligger i nedlasting_status.json.

    Rekkefølgen er med vilje: artiklene FØRST, kursene etterpå, fordi
    tickerlista for kursene kommer ut av hvilke selskaper vi faktisk har
    artikler for. Å laste ned kurser for selskaper uten artikler er bortkastet.
    """
    opp = opp or Oppsett()
    opp.klargjor()
    sett_opp_logging()

    log.info("=" * 70)
    log.info("  LEDELSESSENTIMENT — DEL 1: NEDLASTING")
    log.info("  Mappe: %s", opp.mappe.resolve())
    log.info("=" * 70)

    status = {"startet": datetime.now().isoformat(timespec="seconds"),
              "artikler": {}, "kurser": {}, "merknader": []}
    lager = Artikkellager(opp)

    # ── Artikler ─────────────────────────────────────────────────────────
    if hent_artikler:
        alle = hent_selskaper(opp, selskaper)
        if not alle:
            status["merknader"].append("Ingen selskapsliste — artikler ikke hentet.")
        else:
            fullfort = _les_json(opp.fullfortfil, {})
            igjen = (alle if full else
                     [s for s in alle if s["Symbol"] not in fullfort])
            log.info("Selskaper: %d totalt, %d gjenstår%s",
                     len(alle), len(igjen), "" if full else " (resten er hentet før)")

            if igjen:
                skaarer = Sentiment(opp)
                if not skaarer.klar:
                    status["merknader"].append(
                        "FinBERT utilgjengelig: " + skaarer.feil +
                        " — artikler lagres uten score.")
                try:
                    resultat = asyncio.run(
                        _skrap_alle(igjen, lager, skaarer, fullfort, opp))
                except KeyboardInterrupt:
                    log.warning("Avbrutt av bruker — det som er hentet er lagret.")
                    resultat = _les_json(opp.framdriftsfil, {})
                except Exception as e:
                    log.exception("Skrapingen stoppet uventet")
                    status["merknader"].append(f"Skraping stoppet: {e}")
                    resultat = _les_json(opp.framdriftsfil, {})
                status["artikler"] = resultat
            else:
                status["artikler"] = {"hentet": 0, "hoppet": len(alle),
                                      "merknad": "alt var hentet fra før"}

    # ── Etterskåring av artikler som mangler score ────────────────────────
    mangler = lager.uten_score()
    if mangler:
        log.info("Score   : %d artikler mangler sentimentscore — prøver på nytt",
                 len(mangler))
        skaarer = Sentiment(opp)
        if skaarer.klar:
            fikset = 0
            for rad in mangler:
                fil = rad.get("Tekst_Fil")
                if not fil:
                    continue
                try:
                    tekst = (opp.tekstmappe / fil).read_text(encoding="utf-8")
                except Exception:
                    continue
                poeng = skaarer.analyser(tekst)
                if poeng:
                    rad.update({
                        "Positive_Score": round(poeng["positive"], 4),
                        "Neutral_Score": round(poeng["neutral"], 4),
                        "Negative_Score": round(poeng["negative"], 4),
                        "Final_Score": round(poeng["positive"] - poeng["negative"], 4),
                    })
                    fikset += 1
                if fikset and fikset % 50 == 0:
                    lager.skriv_om()
            lager.skriv_om()
            log.info("Score   : fylte inn %d av %d", fikset, len(mangler))
            status["merknader"].append(
                f"Etterskåret {fikset} av {len(mangler)} artikler.")
        else:
            status["merknader"].append(
                f"{len(mangler)} artikler står fortsatt uten score.")

    lager.lagre_tabell()
    med_score = sum(1 for r in lager.rader if _tall(r.get("Final_Score")) is not None)
    status["artikler"]["totalt_i_lager"] = len(lager.rader)
    status["artikler"]["med_score"] = med_score

    # ── Kurser ───────────────────────────────────────────────────────────
    if hent_kurser_ogsaa:
        symboler = sorted({_rens(r.get("Company")).upper()
                           for r in lager.rader if _rens(r.get("Company"))})
        tickere = [s + opp.oslo_suffix for s in symboler]
        if tickere:
            try:
                status["kurser"] = last_ned_kurser(opp, tickere)
            except Exception as e:
                log.exception("Kursnedlastingen stoppet")
                status["kurser"] = {"status": "FEIL", "feil": str(e)}
        else:
            status["merknader"].append("Ingen selskaper med artikler — "
                                       "ingen kurser å hente.")

    status["ferdig"] = datetime.now().isoformat(timespec="seconds")
    _skriv_json(opp.statusfil, status)

    log.info("-" * 70)
    log.info("Artikler i lager : %d (%d med score)", len(lager.rader), med_score)
    if status.get("kurser"):
        log.info("Kurser brukbare  : %s", status["kurser"].get("nedlastet"))
    for m in status["merknader"]:
        log.info("Merknad          : %s", m)
    log.info("Status lagret    : %s", opp.statusfil)
    return status


# ═══════════════════════════════════════════════════════════════════════════
#
#   DEL 2 — BACKTEST (hendelseslaben)
#
# ═══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Strategi:
    """En inngangsregel: hvor stor bedring, og om SMA50 må være brutt opp."""
    navn: str
    terskel: float
    krev_sma: bool


@dataclass(frozen=True)
class Exit:
    """En salgsregel. Feltene som ikke gjelder for typen står som None."""
    kode: str
    navn: str
    type: str
    beskrivelse: str
    maks_dager: int = 63
    fast_dager: Optional[int] = None
    stop_loss: Optional[float] = None
    profit_target: Optional[float] = None
    atr_mult: Optional[float] = None
    trail_pct: Optional[float] = None
    trail_atr_mult: Optional[float] = None
    sma_exit: Optional[int] = None
    ema_exit: Optional[int] = None
    breakeven: Optional[float] = None
    relativ_stop: Optional[float] = None
    sentiment_rev: Optional[float] = None
    erstatning: bool = False
    alpha_plateau: bool = False


def bygg_strategier(opp: Oppsett) -> List[Strategi]:
    """Seks terskler, så de samme seks med SMA50-krav. S1…S12."""
    uten = [Strategi(f"S{i} ≥{t:.0f}%", t, False)
            for i, t in enumerate(opp.terskler, start=1)]
    med = [Strategi(f"S{i + len(opp.terskler)} ≥{t:.0f}%+SMA", t, True)
           for i, t in enumerate(opp.terskler, start=1)]
    return uten + med


def bygg_exits(opp: Oppsett) -> List[Exit]:
    """Ni faste holdetider + 23 dynamiske regler = 32."""
    ut = [Exit(kode=f"F{d:02d}", navn=f"Fast {d}d", type="FIXED",
               beskrivelse=f"Selg etter nøyaktig {d} handledager.",
               maks_dager=d, fast_dager=d)
          for d in opp.alpha_horisonter]
    maks = opp.dynamisk_maks_hold
    lengst = max(opp.alpha_horisonter)
    ut += [
        Exit("ALPHA", "Alpha-plateau", "ALPHA",
             "Korteste robuste treningshorisont innen 95 % av beste alpha.",
             maks_dager=lengst, alpha_plateau=True),
        Exit("NEXT", "Neste rapport", "NEXT_REPORT",
             "Selg ved første senere rapport; 63d tak.", maks_dager=maks),
        Exit("SREV", "Sent.rev", "SENT_REV",
             f"Selg ved senere sentimentskift ≤ {opp.sentiment_reversering:+.2f}.",
             maks_dager=maks, sentiment_rev=opp.sentiment_reversering),
        Exit("SMA50", "Under SMA50", "SMA",
             "Selg ved close under SMA50 etter minst 2 dager.",
             maks_dager=maks, sma_exit=50),
        Exit("SMA10", "Under SMA10", "SMA",
             "Selg ved close under SMA10 etter minst 2 dager.",
             maks_dager=maks, sma_exit=10),
        Exit("EMA20", "Under EMA20", "EMA",
             "Selg ved close under EMA20 etter minst 2 dager.",
             maks_dager=maks, ema_exit=20),
        Exit("SL05", "Stop -5%", "STOP", "Close-basert stop-loss på -5 %.",
             maks_dager=maks, stop_loss=-0.05),
        Exit("SL08", "Stop -8%", "STOP", "Close-basert stop-loss på -8 %.",
             maks_dager=maks, stop_loss=-0.08),
        Exit("SL10", "Stop -10%", "STOP", "Close-basert stop-loss på -10 %.",
             maks_dager=maks, stop_loss=-0.10),
        Exit("ATR20", "ATR stop 2.0x", "ATR_STOP",
             "Selg under entry minus 2.0x ATR20 målt ved entry.",
             maks_dager=maks, atr_mult=2.0),
        Exit("ATR25", "ATR stop 2.5x", "ATR_STOP",
             "Selg under entry minus 2.5x ATR20 målt ved entry.",
             maks_dager=maks, atr_mult=2.5),
        Exit("ATR30", "ATR stop 3.0x", "ATR_STOP",
             "Selg under entry minus 3.0x ATR20 målt ved entry.",
             maks_dager=maks, atr_mult=3.0),
        Exit("TR10", "Trail 10%", "TRAIL_PCT",
             "Selg 10 % under høyeste close siden entry.",
             maks_dager=maks, trail_pct=0.10),
        Exit("TRATR", "Trail ATR2.5", "TRAIL_ATR",
             "Selg 2.5x aktuell ATR20 under høyeste close siden entry.",
             maks_dager=maks, trail_atr_mult=2.5),
        Exit("TP05", "Target +5%", "TARGET", "Ta gevinst ved +5 % close.",
             maks_dager=maks, profit_target=0.05),
        Exit("TP10", "Target +10%", "TARGET", "Ta gevinst ved +10 % close.",
             maks_dager=maks, profit_target=0.10),
        Exit("TP15", "Target +15%", "TARGET", "Ta gevinst ved +15 % close.",
             maks_dager=maks, profit_target=0.15),
        Exit("TPSL", "+10/-7", "TARGET_STOP",
             "Ta gevinst ved +10 % eller stopp ved -7 %.",
             maks_dager=maks, profit_target=0.10, stop_loss=-0.07),
        Exit("BE05", "BE etter +5", "BREAKEVEN",
             "Etter at handelen har vært +5 %, selg ved close ≤ entry.",
             maks_dager=maks, breakeven=0.05),
        Exit("REL03", "Relativ -3pp", "RELATIVE",
             "Selg når aksjen ligger minst 3pp bak likevektet marked.",
             maks_dager=maks, relativ_stop=opp.relativ_stop),
        Exit("REPL", "Erstatt svak", "REPLACE",
             "Baseline 21d, men sterkt ferskt signal kan erstatte svak posisjon.",
             maks_dager=opp.hold_dager, fast_dager=opp.hold_dager, erstatning=True),
        Exit("HYB", "Hybrid", "HYBRID",
             "Alpha-horisont + sentimentreversering + erstatning.",
             maks_dager=lengst, sentiment_rev=opp.sentiment_reversering,
             erstatning=True, alpha_plateau=True),
        Exit("HYBATR", "Hybrid+ATR3", "HYBRID_ATR",
             "Hybrid + katastrofestopp på 3.0x ATR20.",
             maks_dager=lengst, atr_mult=3.0,
             sentiment_rev=opp.sentiment_reversering,
             erstatning=True, alpha_plateau=True),
    ]
    return ut


@dataclass
class Marked:
    """Kursmatrisene og indikatorene backtesten trenger. Rader = handledager."""
    close: "object"
    high: "object"
    low: "object"
    atr20: "object"
    sma10: "object"
    sma50: "object"
    ema20: "object"
    indeks: "object"          # likevektet daglig markedsindeks


# ─────────────────────────────────────────────────────────────────────────
# Innlesing av det del 1 lagret
# ─────────────────────────────────────────────────────────────────────────

def les_artikler(opp: Oppsett):
    """Artikler med gyldig dato og score, én rad per rapport, sortert."""
    import pandas as pd

    if not opp.artikkelfil.exists():
        raise FileNotFoundError(
            f"Fant ingen artikler i {opp.artikkelfil}. Kjør last_ned_data() først.")

    rader = []
    for linje in opp.artikkelfil.read_text(encoding="utf-8",
                                           errors="replace").splitlines():
        linje = linje.strip()
        if not linje:
            continue
        try:
            rader.append(json.loads(linje))
        except Exception:
            continue
    if not rader:
        raise ValueError(f"{opp.artikkelfil} inneholdt ingen lesbare rader.")

    df = pd.DataFrame(rader)
    for kol in ("Company", "Article_Date", "Final_Score"):
        if kol not in df.columns:
            raise KeyError(f"Artikkellageret mangler kolonnen {kol}.")

    # Datoformatet fra Euronext er «12 Feb 2026». Faller det, prøver vi fritt.
    tekst = (df["Article_Date"].astype(str)
             .str.replace(r"\n.*$", "", regex=True).str.strip())
    forsok = pd.to_datetime(tekst, format="%d %b %Y", errors="coerce")
    df["Article_Date"] = forsok.fillna(
        pd.to_datetime(tekst, format="mixed", errors="coerce"))

    for_dato = len(df)
    df = df.dropna(subset=["Article_Date"])
    df["Final_Score"] = pd.to_numeric(df["Final_Score"], errors="coerce")
    for_score = len(df)
    df = df.dropna(subset=["Final_Score"])
    if "Text_Length" in df.columns:
        df = df[pd.to_numeric(df["Text_Length"], errors="coerce").fillna(0) > 0]
    if "Article_Title" not in df.columns:
        df["Article_Title"] = ""

    df = (df.drop_duplicates(subset=["Company", "Article_Date", "Article_Title"],
                             keep="last")
            .sort_values(["Company", "Article_Date"]).reset_index(drop=True))

    if for_dato - for_score:
        log.info("Artikler : %d uten gyldig dato hoppet over", for_dato - for_score)
    if for_score - len(df):
        log.info("Artikler : %d uten score hoppet over", for_score - len(df))
    if df.empty:
        raise ValueError("Ingen artikler med både dato og sentimentscore.")
    log.info("Artikler : %d fra %d selskaper, %s → %s", len(df),
             df["Company"].nunique(), df["Article_Date"].min().date(),
             df["Article_Date"].max().date())
    return df


def bygg_marked(opp: Oppsett) -> Marked:
    """Leser kurs-CSV-ene og regner ut ATR20, SMA10/50, EMA20 og indeksen."""
    import numpy as np
    import pandas as pd

    def les(navn: str):
        sti = opp.kursmappe / navn
        if not sti.exists():
            return pd.DataFrame()
        try:
            return pd.read_csv(sti, index_col=0, parse_dates=True).sort_index()
        except Exception as e:
            log.error("Kunne ikke lese %s: %s", navn, e)
            return pd.DataFrame()

    close = les("kurser_close.csv")
    if close.empty:
        raise FileNotFoundError(
            f"Ingen kurser i {opp.kursmappe}. Kjør last_ned_data() først.")
    close = close.apply(pd.to_numeric, errors="coerce")
    close = close.loc[:, close.notna().any()]

    high = les("kurser_high.csv").reindex(index=close.index, columns=close.columns)
    low = les("kurser_low.csv").reindex(index=close.index, columns=close.columns)
    high = high.apply(pd.to_numeric, errors="coerce")
    low = low.apply(pd.to_numeric, errors="coerce")
    # Uten High/Low degenererer True Range til |close - forrige close|.
    high = high.fillna(close)
    low = low.fillna(close)

    forrige = close.shift(1)
    # Første rad og dager uten kurs gir bare NaN å velge mellom. NaN er da
    # riktig svar — ATR skal ikke finnes der — så advarselen dempes bevisst.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        tr = np.nanmax(np.stack([(high - low).abs().to_numpy(),
                                 (high - forrige).abs().to_numpy(),
                                 (low - forrige).abs().to_numpy()]), axis=0)
    tr = pd.DataFrame(tr, index=close.index, columns=close.columns)
    atr20 = tr.rolling(opp.atr_dager,
                       min_periods=max(5, opp.atr_dager // 2)).mean()

    daglig = close.pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan)
    indeks = (1.0 + daglig.mean(axis=1).fillna(0.0)).cumprod()

    log.info("Kurser   : %d tickere, %s → %s", close.shape[1],
             close.index[0].date(), close.index[-1].date())
    return Marked(close=close, high=high, low=low, atr20=atr20,
                  sma10=close.rolling(10).mean(),
                  sma50=close.rolling(opp.sma_dager).mean(),
                  ema20=close.ewm(span=20, adjust=False, min_periods=20).mean(),
                  indeks=indeks)


# ─────────────────────────────────────────────────────────────────────────
# Hendelsene
# ─────────────────────────────────────────────────────────────────────────

def bygg_signaler(artikler, md: Marked, opp: Oppsett):
    """
    Én rad per rapport som har en forrige rapport å måles mot.

    Bedring i prosent = (ny - forrige) / max(|forrige|, gulv) * 100. Gulvet
    hindrer at en forrige score nær null gir uendelig bedring; når det binder,
    merkes raden, og porten nedenfor avviser varianter der det binder ofte.

    Inngangsdagen er første handledag ETTER artikkeldatoen. Vi vet ikke om
    meldingen kom før eller etter børsslutt, så samme dag ville vært
    look-ahead.
    """
    import numpy as np
    import pandas as pd

    kurs = md.close
    kart = {c: str(c).strip() + opp.oslo_suffix
            for c in artikler["Company"].dropna().unique()
            if str(c).strip() and str(c).strip().lower() != "nan"}
    kart = {c: t for c, t in kart.items() if t in kurs.columns}
    log.info("Kobling  : %d av %d selskaper har kurser",
             len(kart), artikler["Company"].nunique())
    if not kart:
        return pd.DataFrame()

    over_sma = kurs > md.sma50
    n_dager = len(kurs.index)
    rader: List[dict] = []
    lopenr = 0

    for selskap, d in artikler.groupby("Company"):
        if selskap not in kart:
            continue
        ticker = kart[selskap]
        d = d.sort_values("Article_Date")
        scorer = d["Final_Score"].to_numpy(dtype=float)
        datoer = list(d["Article_Date"])
        titler = list(d["Article_Title"])

        for i in range(1, len(scorer)):
            ny, forrige = float(scorer[i]), float(scorer[i - 1])
            raa = abs(forrige)
            gulv_bandt = raa < opp.gulv
            bedring = (ny - forrige) / max(raa, opp.gulv) * 100.0
            if not np.isfinite(bedring):
                continue

            inn = int(kurs.index.searchsorted(
                pd.Timestamp(datoer[i]).normalize(), side="right"))
            if inn <= 0 or inn >= n_dager:
                continue
            k0 = kurs[ticker].iloc[inn]
            if kurs[ticker].iloc[:inn].notna().sum() < opp.min_historikk_dager:
                continue
            if not np.isfinite(k0) or k0 <= 0:
                continue

            lopenr += 1
            rader.append({
                "signal_id": lopenr,
                "dato": kurs.index[inn],
                "artikkeldato": datoer[i],
                "nyhets_exit_i": inn,
                "selskap": selskap,
                "ticker": ticker,
                "tittel": str(titler[i])[:90],
                "forrige_score": round(forrige, 4),
                "ny_score": round(ny, 4),
                "endring": round(ny - forrige, 4),
                "bedring_pst": round(bedring, 1),
                "gulv_bandt": gulv_bandt,
                "over_sma": bool(over_sma[ticker].iloc[max(0, inn - 1)]),
                "inn_i": inn,
            })

    if not rader:
        log.warning("Signaler : 0 hendelser — ingen selskaper har to rapporter "
                    "innenfor kursperioden.")
        return pd.DataFrame()

    s = pd.DataFrame(rader).sort_values(["inn_i", "signal_id"]).reset_index(drop=True)
    log.info("Signaler : %d hendelser", len(s))
    log.info("Gulvet band på %.0f %% av hendelsene", s["gulv_bandt"].mean() * 100)
    return s


def lag_nyhetskart(signaler) -> Dict[Tuple[str, int], List[dict]]:
    """(ticker, dag) -> senere rapporter, uansett inngangsterskel."""
    kart: Dict[Tuple[str, int], List[dict]] = {}
    for r in signaler.itertuples(index=False):
        kart.setdefault((r.ticker, int(r.nyhets_exit_i)), []).append(
            {"artikkeldato": r.artikkeldato, "endring": float(r.endring)})
    return kart


def _senere_rapport(kart, pos: dict, dag_i: int) -> bool:
    return any(e["artikkeldato"] > pos["artikkeldato"]
               for e in kart.get((pos["ticker"], dag_i), []))


def _reversering(kart, pos: dict, dag_i: int, terskel: float) -> bool:
    return any(e["artikkeldato"] > pos["artikkeldato"] and e["endring"] <= terskel
               for e in kart.get((pos["ticker"], dag_i), []))


def _markedsavkastning(md: Marked, inn: int, ut: int, buffer: dict) -> float:
    """Snittavkastning for hele universet over nøyaktig samme inn/ut-vindu."""
    import numpy as np
    nokkel = (int(inn), int(ut))
    if nokkel in buffer:
        return buffer[nokkel]
    if inn < 0 or ut >= len(md.close.index) or ut <= inn:
        return float("nan")
    r = (md.close.iloc[ut] / md.close.iloc[inn] - 1.0)
    r = r.replace([np.inf, -np.inf], np.nan).dropna()
    verdi = float(r.mean()) if len(r) else float("nan")
    buffer[nokkel] = verdi
    return verdi


def velg_alpha_horisonter(signaler, md: Marked, opp: Oppsett, buffer: dict):
    """
    Per inngangsstrategi: korteste holdetid innen 95 % av beste positive alpha.

    Måles KUN på handler som både starter og avsluttes innen treningsslutt.
    Finnes ingen positiv robust alpha, brukes standard 21 dager.
    """
    import numpy as np
    import pandas as pd

    cutoff = pd.Timestamp(opp.trening_slutt)
    cutoff_i = int(md.close.index.searchsorted(cutoff, side="right") - 1)
    tabell: List[dict] = []
    valgt_hold: Dict[str, int] = {}

    for s in bygg_strategier(opp):
        grense = s.terskel - 1e-9
        v = signaler[(signaler["bedring_pst"] >= grense) &
                     (signaler["over_sma"] if s.krev_sma
                      else signaler["bedring_pst"].notna())]
        rader_s = []
        for h in opp.alpha_horisonter:
            alpha = []
            aksje, marked = [], []
            for r in v.itertuples(index=False):
                inn = int(r.inn_i)
                ut = inn + h
                if ut > cutoff_i or ut >= len(md.close.index):
                    continue
                k = md.close[r.ticker]
                p0, p1 = k.iloc[inn], k.iloc[ut]
                if not (np.isfinite(p0) and np.isfinite(p1)) or p0 <= 0:
                    continue
                mr = _markedsavkastning(md, inn, ut, buffer)
                if not np.isfinite(mr):
                    continue
                ar = float(p1 / p0 - 1.0)
                aksje.append(ar)
                marked.append(mr)
                alpha.append(ar - mr)
            n = len(alpha)
            rad = {"Strategi": s.navn, "Hold_Dager": h, "N_Trening": n,
                   "Aksje_Pst": float(np.mean(aksje)) * 100 if n else np.nan,
                   "Marked_Pst": float(np.mean(marked)) * 100 if n else np.nan,
                   "Alpha_Pst": float(np.mean(alpha)) * 100 if n else np.nan}
            tabell.append(rad)
            rader_s.append(rad)

        gode = [r for r in rader_s if r["N_Trening"] >= opp.min_handler
                and np.isfinite(r["Alpha_Pst"])]
        valgt = opp.hold_dager
        if gode:
            beste = max(r["Alpha_Pst"] for r in gode)
            if beste > 0:
                robuste = [r for r in gode
                           if r["Alpha_Pst"] >= beste * opp.alpha_plateau_andel]
                valgt = min(robuste, key=lambda x: x["Hold_Dager"])["Hold_Dager"]
        valgt_hold[s.navn] = int(valgt)
        log.info("Alpha    : %-18s -> %2d dager", s.navn, valgt)

    return valgt_hold, pd.DataFrame(tabell)


# ─────────────────────────────────────────────────────────────────────────
# Simulatoren
# ─────────────────────────────────────────────────────────────────────────

def _maks_hold(e: Exit, alpha_hold: int) -> int:
    if e.type in ("ALPHA", "HYBRID", "HYBRID_ATR"):
        return int(alpha_hold)
    if e.type == "FIXED":
        return int(e.fast_dager)
    return int(e.maks_dager)


def _prioritet(pos: dict, dag_i: int, opp: Oppsett) -> float:
    """Signalstyrke som forvitrer med alderen — brukes ved erstatning."""
    alder = max(0, dag_i - pos["inn_i"])
    return float(pos["bedring_pst"]) * exp(-alder / opp.erstatt_halveringstid)


def _exit_arsak(pos: dict, dag_i: int, e: Exit, md: Marked, alpha_hold: int,
                kart, opp: Oppsett) -> Optional[str]:
    """
    Skal posisjonen selges? Returnerer årsaken, eller None.

    Rekkefølgen er bevisst: nyhetsbaserte exits først (ny informasjon kan
    ugyldiggjøre tesen), så pris og risiko, og tidstaket sist — slik at en
    ekte utløsning samme dag får den informative årsaken i loggen.
    """
    import numpy as np

    alder = dag_i - pos["inn_i"]
    if alder <= 0:
        return None
    px = md.close[pos["ticker"]].iloc[dag_i]
    if not np.isfinite(px) or px <= 0:
        return None

    avk = float(px / pos["entry_price"] - 1.0)
    pos["peak_close"] = max(pos["peak_close"], float(px))

    if e.type == "NEXT_REPORT" and _senere_rapport(kart, pos, dag_i):
        return "neste_rapport"
    if e.type in ("SENT_REV", "HYBRID", "HYBRID_ATR"):
        terskel = (e.sentiment_rev if e.sentiment_rev is not None
                   else opp.sentiment_reversering)
        if _reversering(kart, pos, dag_i, terskel):
            return "sentiment_reversering"

    if e.type == "STOP" and e.stop_loss is not None and avk <= e.stop_loss:
        return "stop_loss"

    if e.type in ("ATR_STOP", "HYBRID_ATR") and e.atr_mult is not None:
        atr0 = pos.get("entry_atr", float("nan"))
        if np.isfinite(atr0) and px <= pos["entry_price"] - e.atr_mult * atr0:
            return "atr_stop"

    if e.type == "TRAIL_PCT" and e.trail_pct is not None:
        if px <= pos["peak_close"] * (1.0 - e.trail_pct):
            return "trailing_stop"

    if e.type == "TRAIL_ATR" and e.trail_atr_mult is not None:
        atr = md.atr20[pos["ticker"]].iloc[dag_i]
        if np.isfinite(atr) and px <= pos["peak_close"] - e.trail_atr_mult * atr:
            return "trailing_atr"

    if e.type == "TARGET" and e.profit_target is not None and avk >= e.profit_target:
        return "profit_target"

    if e.type == "TARGET_STOP":
        if e.profit_target is not None and avk >= e.profit_target:
            return "profit_target"
        if e.stop_loss is not None and avk <= e.stop_loss:
            return "stop_loss"

    if e.type == "BREAKEVEN" and e.breakeven is not None:
        if not pos["be_armert"] and avk >= e.breakeven:
            pos["be_armert"] = True
            pos["be_armert_i"] = dag_i
        if (pos["be_armert"] and dag_i > pos["be_armert_i"]
                and px <= pos["entry_price"]):
            return "break_even"

    if (e.type == "RELATIVE" and e.relativ_stop is not None
            and alder >= opp.min_dager_for_relative_exit):
        m0, m1 = md.indeks.iloc[pos["inn_i"]], md.indeks.iloc[dag_i]
        mr = float(m1 / m0 - 1.0) if np.isfinite(m0) and m0 > 0 else float("nan")
        if np.isfinite(mr) and (avk - mr) <= e.relativ_stop:
            return "relativ_underprestasjon"

    if (e.type == "SMA" and e.sma_exit is not None
            and alder >= opp.min_dager_for_trend_exit):
        ma = (md.sma50 if e.sma_exit == 50 else md.sma10)[pos["ticker"]].iloc[dag_i]
        if np.isfinite(ma) and px < ma:
            return f"under_sma{e.sma_exit}"

    if (e.type == "EMA" and e.ema_exit is not None
            and alder >= opp.min_dager_for_trend_exit):
        ma = md.ema20[pos["ticker"]].iloc[dag_i]
        if np.isfinite(ma) and px < ma:
            return f"under_ema{e.ema_exit}"

    if alder >= _maks_hold(e, alpha_hold):
        if e.type == "FIXED":
            return "fast_hold"
        if e.type in ("ALPHA", "HYBRID", "HYBRID_ATR"):
            return "alpha_horisont"
        if e.type == "REPLACE":
            return "fast_hold"
        return "maks_hold"
    return None


def kjor_en_variant(s: Strategi, e: Exit, signaler, md: Marked,
                    alpha_hold_map: Dict[str, int], kart, opp: Oppsett,
                    buffer: dict) -> dict:
    """
    Dag-for-dag-simulering av én kombinasjon inngang + exit.

    Kapitalen deles i maks_posisjoner like plasser som forrenter seg hver for
    seg. Hver dag: først exits på dagens close, så nye signaler, så en ekte
    mark-to-market av porteføljen.

    To ting som er lette å gjøre feil, og som er gjort med vilje her:

      * Prisbaserte exits vurderes på GÅRSDAGENS close, men handelen skjer på
        dagens. Vurderer du på samme close som du selger til, har du brukt en
        kurs du ikke kunne kjent da beslutningen ble tatt.
      * Nyhetsbaserte exits og tidstaket vurderes på dagens indeks, fordi de
        ikke avhenger av en kurs du måtte observere først.
    """
    import numpy as np
    import pandas as pd

    grense = s.terskel - 1e-9
    valgte = signaler[(signaler["bedring_pst"] >= grense) &
                      (signaler["over_sma"] if s.krev_sma
                       else signaler["bedring_pst"].notna())].copy()

    alpha_hold = int(alpha_hold_map.get(s.navn, opp.hold_dager))
    maks_hold = _maks_hold(e, alpha_hold)
    n_dager = len(md.close.index)

    tomt = {"Strategi": s.navn, "Terskel_Pst": s.terskel, "SMA": s.krev_sma,
            "Exit_Kode": e.kode, "Exit": e.navn, "Valgt_Hold": maks_hold,
            "Variant": s.navn.split()[0] + "|" + e.kode,
            "Signaler": int(len(valgte)), "Handler": 0, "Tapt": 0,
            "Erstattet": 0, "Apne_Na": 0, "Slutt_NOK": opp.startkapital,
            "handler": pd.DataFrame(), "kurve": pd.Series(dtype=float),
            "apne": [], "data_ok": True, "kursmangler": []}
    if valgte.empty:
        return tomt

    per_dag: Dict[int, List] = {}
    for r in valgte.itertuples(index=False):
        per_dag.setdefault(int(r.inn_i), []).append(r)

    plass_kontant = [opp.startkapital / opp.maks_posisjoner
                     for _ in range(opp.maks_posisjoner)]
    apne: Dict[int, dict] = {}
    handler: List[dict] = []
    beholdning: List[dict] = []
    kursmangler: List[dict] = []
    kurve: List[Tuple] = []
    tapt = erstattet = 0

    forste_dag = max(0, int(signaler["inn_i"].min()) - 1)
    siste_dag = n_dager - 1

    def selg(plass: int, dag_i: int, grunn: str) -> bool:
        nonlocal erstattet
        pos = apne.get(plass)
        if pos is None:
            return False
        px = md.close[pos["ticker"]].iloc[dag_i]
        if not np.isfinite(px) or px <= 0:
            return False                  # ingen kurs = ingen handel

        avk = float(px / pos["entry_price"] - 1.0)
        plass_kontant[plass] = pos["kapital"] * (1.0 + avk)
        dager = int(dag_i - pos["inn_i"])
        marked = _markedsavkastning(md, pos["inn_i"], dag_i, buffer)

        # Dag+1: samme antall holdedager, men inngang én dag senere. Holder
        # tallet seg da, skyldes det ikke at vi traff selve meldingsdagen.
        inn1, ut1 = pos["inn_i"] + 1, pos["inn_i"] + 1 + dager
        dag1 = float("nan")
        if ut1 < n_dager:
            k = md.close[pos["ticker"]]
            p0, p1 = k.iloc[inn1], k.iloc[ut1]
            if np.isfinite(p0) and np.isfinite(p1) and p0 > 0:
                dag1 = float(p1 / p0 - 1.0)

        handler.append({
            "strategi": s.navn, "exit_kode": e.kode, "exit": e.navn,
            "signal_id": pos["signal_id"],
            "dato": md.close.index[pos["inn_i"]],
            "ut_dato": md.close.index[dag_i],
            "ticker": pos["ticker"], "selskap": pos["selskap"],
            "tittel": pos["tittel"], "bedring_pst": pos["bedring_pst"],
            "endring": pos["endring"], "gulv_bandt": pos["gulv_bandt"],
            "over_sma": pos["over_sma"], "inn_i": pos["inn_i"], "ut_i": dag_i,
            "hold_dager": dager, "exit_arsak": grunn,
            "entry_price": pos["entry_price"], "exit_price": float(px),
            "kapital": pos["kapital"], "avk": avk, "avk_dag1": dag1,
            "marked": marked,
            "alpha": avk - marked if np.isfinite(marked) else float("nan"),
            "utvalg": ("TRENING" if md.close.index[pos["inn_i"]]
                       <= pd.Timestamp(opp.trening_slutt) else "TEST"),
        })
        if grunn == "erstatning":
            erstattet += 1
        del apne[plass]
        return True

    def kjop(plass: int, r, dag_i: int) -> bool:
        px = md.close[r.ticker].iloc[dag_i]
        if not np.isfinite(px) or px <= 0:
            return False
        atr0 = md.atr20[r.ticker].iloc[dag_i]
        apne[plass] = {
            "plass": plass, "kapital": float(plass_kontant[plass]),
            "signal_id": int(r.signal_id), "inn_i": dag_i,
            "artikkeldato": r.artikkeldato, "ticker": r.ticker,
            "selskap": r.selskap, "tittel": r.tittel,
            "bedring_pst": float(r.bedring_pst), "endring": float(r.endring),
            "gulv_bandt": bool(r.gulv_bandt), "over_sma": bool(r.over_sma),
            "entry_price": float(px), "siste_kurs": float(px),
            "siste_kurs_i": dag_i,
            "entry_atr": float(atr0) if np.isfinite(atr0) else float("nan"),
            "peak_close": float(px), "be_armert": False, "be_armert_i": -1,
        }
        return True

    for dag_i in range(forste_dag, siste_dag + 1):
        # 1) Exits.
        for plass in list(apne.keys()):
            pos = apne[plass]
            alder = dag_i - pos["inn_i"]
            grunn = pos.get("ventende_exit")
            if not grunn and e.type == "NEXT_REPORT" and _senere_rapport(kart, pos, dag_i):
                grunn = "neste_rapport"
            if not grunn and e.type in ("SENT_REV", "HYBRID", "HYBRID_ATR"):
                terskel = (e.sentiment_rev if e.sentiment_rev is not None
                           else opp.sentiment_reversering)
                if _reversering(kart, pos, dag_i, terskel):
                    grunn = "sentiment_reversering"
            if not grunn:
                if alder >= maks_hold:
                    grunn = "utlopt"
                elif dag_i > pos["inn_i"]:
                    grunn = _exit_arsak(pos, dag_i - 1, e, md, alpha_hold, kart, opp)
            if grunn and not selg(plass, dag_i, grunn):
                pos["ventende_exit"] = grunn     # prøv igjen når kurs finnes

        # 2) Nye signaler.
        for r in per_dag.get(dag_i, []):
            ledige = [i for i in range(opp.maks_posisjoner) if i not in apne]
            if ledige:
                if not kjop(ledige[0], r, dag_i):
                    tapt += 1
                continue
            if e.erstatning:
                kandidater = [p for p in apne.values()
                              if dag_i - p["inn_i"] >= opp.erstatt_min_alder]
                if kandidater:
                    svakest = min(kandidater, key=lambda p: _prioritet(p, dag_i, opp))
                    if (float(r.bedring_pst)
                            >= _prioritet(svakest, dag_i, opp) * opp.erstatt_styrkekrav):
                        plass = svakest["plass"]
                        if selg(plass, dag_i, "erstatning"):
                            if not kjop(plass, r, dag_i):
                                tapt += 1
                            continue
            tapt += 1

        # 3) Mark-to-market. Antall aksjer er kapital/entry og settes én gang;
        #    en manglende kurs beholder siste observerte merking i stedet for
        #    å finne på en handel. Varer det lenge, merkes dataene som usikre.
        verdi = 0.0
        for plass in range(opp.maks_posisjoner):
            pos = apne.get(plass)
            if pos is None:
                verdi += plass_kontant[plass]
                continue
            px = md.close[pos["ticker"]].iloc[dag_i]
            if np.isfinite(px) and px > 0:
                pos["siste_kurs"] = float(px)
                pos["siste_kurs_i"] = dag_i
            elif dag_i - pos["siste_kurs_i"] == 6:
                kursmangler.append({"ticker": pos["ticker"],
                                    "dato": str(md.close.index[dag_i].date()),
                                    "sak": "seks_okter_uten_kurs"})
            verdi += pos["kapital"] / pos["entry_price"] * pos["siste_kurs"]
        kurve.append((md.close.index[dag_i], verdi))

        na = sorted(p["ticker"] for p in apne.values())
        if not beholdning or beholdning[-1]["tickere"] != na:
            beholdning.append({"dato": md.close.index[dag_i], "tickere": na})

    h = pd.DataFrame(handler)
    k = pd.Series({d: v for d, v in kurve}).sort_index() if kurve else pd.Series(dtype=float)
    apne_na = [dict(p) for p in apne.values()]
    slutt = float(k.iloc[-1]) if len(k) else float(sum(plass_kontant))

    rad = dict(tomt)
    rad.update({"Handler": len(h), "Tapt": tapt, "Erstattet": erstattet,
                "Apne_Na": len(apne_na), "Slutt_NOK": slutt, "handler": h,
                "kurve": k, "apne": apne_na,
                "beholdning": pd.DataFrame(
                    [{"dato": b["dato"], "beholdning": ", ".join(b["tickere"]) or "KONTANT"}
                     for b in beholdning]),
                "data_ok": not kursmangler, "kursmangler": kursmangler})
    if h.empty:
        return rad
    rad.update(_maaltall(h, k, slutt, opp))
    return rad


def _uten_toppvinnere(h, kolonne: str, andel: float = 0.01) -> float:
    """
    Samme snitt, men uten den øverste prosenten av handlene målt på avkastning.

    Et profit target på +10 % kan ikke gi 24 % snitthandel med mindre noen få
    aksjer gapper voldsomt opp fra en lav inngangskurs. Uten denne kolonnen
    ser en slik rad ut som en strategi.
    """
    import numpy as np
    x = h[["avk", "alpha"]].dropna()
    if x.empty:
        return float("nan")
    n = min(max(int(np.ceil(len(x) * andel)), 1), max(len(x) - 1, 0))
    if n > 0:
        x = x.drop(index=x.nlargest(n, "avk").index)
    return float(x[kolonne].mean()) * 100.0 if len(x) else float("nan")


def _maaltall(h, kurve, slutt: float, opp: Oppsett) -> dict:
    """Nøkkeltallene for én variant. MaxDD er ekte daglig, ikke per handel."""

    if len(kurve) >= 2:
        forste, siste = kurve.index[0], kurve.index[-1]
    else:
        forste, siste = h["dato"].min(), h["ut_dato"].max()
    aar = max((siste - forste).days / 365.25, 0.01)

    verdier = list(kurve.values) if len(kurve) else [opp.startkapital, slutt]
    topp, mdd = verdier[0], 0.0
    for v in verdier:
        topp = max(topp, v)
        mdd = min(mdd, v / topp - 1.0)

    trening = h[h["utvalg"] == "TRENING"]
    test = h[h["utvalg"] == "TEST"]
    alpha = h["alpha"].dropna()
    slotdager = max(float(h["hold_dager"].sum()), 1.0)

    def snitt(ramme, kol):
        return (float(ramme[kol].mean()) * 100.0
                if len(ramme) and ramme[kol].notna().any() else float("nan"))

    return {
        "Total_Pst": (slutt / opp.startkapital - 1.0) * 100.0,
        "CAGR_Pst": (((slutt / opp.startkapital) ** (1 / aar) - 1) * 100.0
                     if aar >= 0.5 and slutt > 0 else float("nan")),
        "MaxDD_Pst": mdd * 100.0,
        "Aar": round(aar, 2),
        "Snitt_Handel_Pst": snitt(h, "avk"),
        "Median_Handel_Pst": float(h["avk"].median()) * 100.0,
        "Treff_Pst": float((h["avk"] > 0).mean()) * 100.0,
        "Marked_Pst": snitt(h, "marked"),
        "Mot_marked_Pst": snitt(h, "alpha"),
        "Alpha_per_slotdag_Pst": (float(alpha.sum() / slotdager) * 100.0
                                  if len(alpha) else float("nan")),
        "Snitt_Hold_Dager": float(h["hold_dager"].mean()),
        "Median_Hold_Dager": float(h["hold_dager"].median()),
        "Dag1_Pst": snitt(h, "avk_dag1"),
        "Trening_Snitt_Pst": snitt(trening, "avk"),
        "Trening_Mot_marked_Pst": snitt(trening, "alpha"),
        "Test_Snitt_Pst": snitt(test, "avk"),
        "Test_Mot_marked_Pst": snitt(test, "alpha"),
        "Gulv_Pst": float(h["gulv_bandt"].mean()) * 100.0,
        "Snitt_Uten_Topp1pct_Pst": _uten_toppvinnere(h, "avk"),
        "Alpha_Uten_Topp1pct_Pst": _uten_toppvinnere(h, "alpha"),
        "Beste_Handel_Pst": float(h["avk"].max()) * 100.0,
        "Verste_Handel_Pst": float(h["avk"].min()) * 100.0,
    }


# ─────────────────────────────────────────────────────────────────────────
# Porten og variantvalget
# ─────────────────────────────────────────────────────────────────────────

def porten(r: dict, opp: Oppsett) -> Dict[str, bool]:
    """
    Kravene en variant må bestå for å kalles robust.

    Dette er en beskrivelse av raden, ikke et løfte om fremtiden. En variant
    som består alle punktene har fortsatt bare vist at den historiske serien
    ikke faller sammen på de åpenbare måtene.
    """
    import numpy as np

    def f(navn, standard=float("nan")):
        return float(r.get(navn, standard) or float("nan"))

    return {
        "slår markedet på samme vindu": f("Mot_marked_Pst") > 0,
        "positiv snitthandel": f("Snitt_Handel_Pst") > 0,
        "positiv også på testutvalget": (np.isfinite(f("Test_Snitt_Pst"))
                                         and f("Test_Snitt_Pst") > 0),
        "positiv alpha på testutvalget": (np.isfinite(f("Test_Mot_marked_Pst"))
                                          and f("Test_Mot_marked_Pst") > 0),
        "holder med kjøp dagen etter": (not np.isfinite(f("Dag1_Pst"))
                                        or f("Dag1_Pst") > f("Snitt_Handel_Pst") * 0.5),
        f"minst {opp.min_handler} handler": int(r.get("Handler", 0)) >= opp.min_handler,
        "gulvet binder under 30 % av handlene": f("Gulv_Pst") < 30.0,
        "holder uten øverste prosent vinnere": (
            np.isfinite(f("Snitt_Uten_Topp1pct_Pst"))
            and f("Snitt_Uten_Topp1pct_Pst") > 0),
    }


def _arlig(verdier: Sequence[float], datoer: Sequence[str],
           min_dager: int = 180) -> Optional[float]:
    if len(verdier) < 2:
        return None
    try:
        dager = (date.fromisoformat(str(datoer[-1])[:10])
                 - date.fromisoformat(str(datoer[0])[:10])).days
    except Exception:
        return None
    if dager < min_dager or verdier[0] <= 0 or verdier[-1] <= 0:
        return None
    v = (verdier[-1] / verdier[0]) ** (365.25 / dager) - 1
    return 100 * v if math.isfinite(v) else None


def _trening_test(kurve, cutoff: str) -> dict:
    """CAGR før og etter cutoff. Testperioden starter på treningens sluttverdi."""
    rader = sorted((str(d)[:10], float(v)) for d, v in kurve.items()
                   if math.isfinite(float(v)))
    trening = [(d, v) for d, v in rader if d <= cutoff]
    test = trening[-1:] + [(d, v) for d, v in rader if d > cutoff]
    return {
        "Train_CAGR_Pst": _arlig([v for _, v in trening], [d for d, _ in trening]),
        "Test_CAGR_Pst": _arlig([v for _, v in test], [d for d, _ in test]),
        "Train_Dager": len(trening),
        "Test_Dager": max(0, len(test) - 1),
    }


def velg_variant(rader: List[dict], opp: Oppsett) -> Tuple[Optional[dict], str]:
    """
    Velger ÉN variant — kun på treningsdata.

    Testperioden påvirker aldri valget; den er der for å vise hva som skjedde
    etterpå. Dette maksimerer et historisk mål, ikke fremtidig avkastning.
    """
    if opp.manuelt_valg:
        valgt = next((r for r in rader if r["Variant"] == opp.manuelt_valg.upper()), None)
        if valgt is None:
            log.error("Ukjent manuelt valg %s — faller tilbake på automatikk.",
                      opp.manuelt_valg)
        else:
            return valgt, ("Manuelt valgt variant. Ikke valgt på "
                           "evalueringsperioden, og merket som manuell.")

    gyldige = [r for r in rader if r.get("data_ok", True)]
    if not gyldige:
        return None, "Ingen variant har verifiserbare verdsettelser."

    kvalifiserte = [
        r for r in gyldige
        if r.get("Train_CAGR_Pst") is not None
        and math.isfinite(float(r["Train_CAGR_Pst"]))
        and int(r.get("Train_Handler", 0)) >= opp.min_handler
        and int(r.get("Train_Dager", 0)) >= opp.min_treningsdager
    ]
    if not kvalifiserte:
        return None, ("Ingen variant har nok treningshistorikk og handler "
                      f"(krav: {opp.min_handler} handler, "
                      f"{opp.min_treningsdager} treningsdager).")

    beste = sorted(kvalifiserte,
                   key=lambda r: (-float(r["Train_CAGR_Pst"]), r["Variant"]))[0]
    return beste, ("Høyest trenings-CAGR blant kvalifiserte varianter, uten "
                   f"handelskostnader. Testperioden er ikke brukt til valget. "
                   f"Treningsslutt: {opp.trening_slutt}.")


# ─────────────────────────────────────────────────────────────────────────
# DEL 2 — hovedfunksjonen
# ─────────────────────────────────────────────────────────────────────────

def kjor_backtest(opp: Optional[Oppsett] = None,
                  kun_exits: Optional[Sequence[str]] = None,
                  kun_strategier: Optional[Sequence[str]] = None) -> dict:
    """
    DEL 2 — kjører laben på dataene del 1 lagret.

    Parametre
    ---------
    opp             Oppsett. Må peke på samme mappe som last_ned_data().
    kun_exits       Valgfri liste exit-koder (f.eks. ["F21", "TP10"]) for en
                    rask deltest i stedet for alle 32.
    kun_strategier  Valgfri liste inngangskoder ("S1", "S7", …).

    Returnerer en dict med sammendrag, valgt variant, portresultat og stier.
    Alle filer skrives til <mappe>/resultater/.

    Ingen enkeltvariant kan velte kjøringen: hver av de 384 kjøres i sin egen
    try/except, og delresultatet skrives til disk hver 25. variant.
    """
    import pandas as pd

    opp = opp or Oppsett()
    opp.klargjor()
    sett_opp_logging()

    log.info("=" * 70)
    log.info("  LEDELSESSENTIMENT — DEL 2: BACKTEST")
    log.info("  Mappe: %s", opp.mappe.resolve())
    log.info("=" * 70)

    artikler = les_artikler(opp)
    md = bygg_marked(opp)
    signaler = bygg_signaler(artikler, md, opp)
    if signaler is None or signaler.empty:
        log.error("Ingen hendelser — artiklene og kursene overlapper ikke.")
        return {"status": "INGEN_SIGNALER"}

    try:
        signaler.to_csv(opp.resultatmappe / "signaler.csv", index=False)
    except Exception as e:
        log.warning("Kunne ikke lagre signaler.csv: %s", e)

    kart = lag_nyhetskart(signaler)
    buffer: dict = {}
    alpha_hold_map, alpha_tabell = velg_alpha_horisonter(signaler, md, opp, buffer)
    try:
        alpha_tabell.to_csv(opp.resultatmappe / "alpha_horisonter.csv", index=False)
    except Exception as e:
        log.warning("Kunne ikke lagre alpha_horisonter.csv: %s", e)

    strategier = [s for s in bygg_strategier(opp)
                  if not kun_strategier or s.navn.split()[0] in
                  {k.upper() for k in kun_strategier}]
    exits = [e for e in bygg_exits(opp)
             if not kun_exits or e.kode in {k.upper() for k in kun_exits}]
    totalt = len(strategier) * len(exits)
    log.info("Lab      : %d innganger x %d exits = %d backtester",
             len(strategier), len(exits), totalt)

    rader: List[dict] = []
    alle_handler: List = []
    beste_kjoring: Dict[str, dict] = {}
    feilet: List[str] = []
    nr = 0

    def lagre_delvis():
        try:
            if rader:
                pd.DataFrame([{k: v for k, v in r.items()
                               if not isinstance(v, (pd.DataFrame, pd.Series, list))}
                              for r in rader]).to_csv(
                    opp.resultatmappe / "backtest_alle.csv", index=False)
        except Exception as e:
            log.warning("Kunne ikke lagre delresultat: %s", e)

    for e in exits:
        log.info("Exit     : %s — %s", e.kode, e.navn)
        for s in strategier:
            nr += 1
            try:
                r = kjor_en_variant(s, e, signaler, md, alpha_hold_map,
                                    kart, opp, buffer)
            except Exception as feil:
                # Én variant som ryker skal ikke koste deg de 383 andre.
                feilet.append(f"{s.navn.split()[0]}|{e.kode}: {feil}")
                log.warning("  %s|%s feilet: %s", s.navn.split()[0], e.kode, feil)
                continue

            h = r.pop("handler", pd.DataFrame())
            kurve = r.pop("kurve", pd.Series(dtype=float))
            apne = r.pop("apne", [])
            beholdning = r.pop("beholdning", pd.DataFrame())

            r.update(_trening_test(kurve, opp.trening_slutt))
            trening_h = (h[h["ut_dato"] <= pd.Timestamp(opp.trening_slutt)]
                         if not h.empty else pd.DataFrame())
            r["Train_Handler"] = len(trening_h)
            r["data_ok"] = r.get("data_ok", True) and not any(
                m["dato"] <= opp.trening_slutt for m in r.get("kursmangler", []))
            r["Bestod_Porten"] = (all(porten(r, opp).values())
                                  if r["Handler"] >= opp.min_handler else False)

            beste_kjoring[r["Variant"]] = {"handler": h, "kurve": kurve,
                                           "apne": apne, "beholdning": beholdning}
            if not h.empty:
                alle_handler.append(h)
            rader.append(r)

            if nr % 25 == 0 or nr == totalt:
                log.info("Fremdrift: %d / %d", nr, totalt)
                lagre_delvis()

    if not rader:
        log.error("Ingen varianter fullførte.")
        return {"status": "INGEN_RESULTAT", "feilet": feilet}

    sammendrag = pd.DataFrame([{k: v for k, v in r.items()
                                if not isinstance(v, (pd.DataFrame, pd.Series, list))}
                               for r in rader])

    # ── Valget ───────────────────────────────────────────────────────────
    valgt, grunn = velg_variant(rader, opp)
    bestod = int(sammendrag["Bestod_Porten"].sum())

    sammendrag["Valgt"] = sammendrag["Variant"] == (valgt or {}).get("Variant", "")
    sammendrag = sammendrag.sort_values(
        ["Train_CAGR_Pst"], ascending=False, na_position="last")

    stier = {}
    try:
        p = opp.resultatmappe / "backtest_alle.csv"
        sammendrag.to_csv(p, index=False)
        stier["alle"] = str(p)

        beste_per_exit = (sammendrag.sort_values("Train_CAGR_Pst", ascending=False)
                          .groupby("Exit_Kode", as_index=False).first())
        p = opp.resultatmappe / "beste_per_exit.csv"
        beste_per_exit.to_csv(p, index=False)
        stier["beste_per_exit"] = str(p)

        if alle_handler:
            p = opp.resultatmappe / "handler_alle.csv"
            pd.concat(alle_handler, ignore_index=True).to_csv(p, index=False)
            stier["handler_alle"] = str(p)
    except Exception as e:
        log.error("Kunne ikke lagre sammendrag: %s", e)

    resultat = {"status": "OK", "antall_varianter": len(rader),
                "bestod_porten": bestod, "feilet": feilet,
                "valgt": None, "grunn": grunn, "stier": stier}

    if valgt is None:
        log.warning("Ingen variant kunne velges: %s", grunn)
        _skriv_json(opp.resultatmappe / "valgt_variant.json", resultat)
        return resultat

    detaljer = beste_kjoring.get(valgt["Variant"], {})
    port = porten(valgt, opp)
    try:
        h = detaljer.get("handler")
        if h is not None and not h.empty:
            p = opp.resultatmappe / "handler_valgt.csv"
            h.to_csv(p, index=False)
            stier["handler_valgt"] = str(p)
        kurve = detaljer.get("kurve")
        if kurve is not None and len(kurve):
            p = opp.resultatmappe / "kurve_valgt.csv"
            kurve.rename("Portefolje_NOK").to_csv(p, index_label="Dato")
            stier["kurve_valgt"] = str(p)
        beholdning = detaljer.get("beholdning")
        if beholdning is not None and not beholdning.empty:
            beholdning.to_csv(opp.resultatmappe / "beholdning_valgt.csv", index=False)
        apne = detaljer.get("apne") or []
        if apne:
            pd.DataFrame([{
                "ticker": p_["ticker"], "selskap": p_["selskap"],
                "inn_dato": str(md.close.index[p_["inn_i"]].date()),
                "entry_price": p_["entry_price"], "siste_kurs": p_["siste_kurs"],
                "avk_pst": (p_["siste_kurs"] / p_["entry_price"] - 1) * 100,
                "bedring_pst": p_["bedring_pst"], "tittel": p_["tittel"],
            } for p_ in apne]).to_csv(
                opp.resultatmappe / "posisjoner_na.csv", index=False)
    except Exception as e:
        log.error("Kunne ikke lagre detaljer for valgt variant: %s", e)

    resultat["valgt"] = {k: v for k, v in valgt.items()
                         if not isinstance(v, (list, dict))}
    resultat["porten"] = port
    resultat["porten_bestod"] = all(port.values())
    resultat["apne_posisjoner"] = len(detaljer.get("apne") or [])
    resultat["stier"] = stier
    _skriv_json(opp.resultatmappe / "valgt_variant.json", resultat)

    # ── Oppsummering ─────────────────────────────────────────────────────
    v = valgt
    log.info("-" * 70)
    log.info("VALGT VARIANT : %s  (%s + %s)", v["Variant"], v["Strategi"], v["Exit"])
    log.info("Grunn         : %s", grunn)
    log.info("Handler       : %d (%d i trening)", v["Handler"], v.get("Train_Handler", 0))
    log.info("Trenings-CAGR : %s", _fmt(v.get("Train_CAGR_Pst"), "%"))
    log.info("Test-CAGR     : %s   (kun visning, ikke brukt til valg)",
             _fmt(v.get("Test_CAGR_Pst"), "%"))
    log.info("Total / CAGR  : %s / %s", _fmt(v.get("Total_Pst"), "%"),
             _fmt(v.get("CAGR_Pst"), "%"))
    log.info("MaxDD         : %s", _fmt(v.get("MaxDD_Pst"), "%"))
    log.info("Snitt handel  : %s   uten topp 1 %%: %s",
             _fmt(v.get("Snitt_Handel_Pst"), "%"),
             _fmt(v.get("Snitt_Uten_Topp1pct_Pst"), "%"))
    log.info("Mot marked    : %s", _fmt(v.get("Mot_marked_Pst"), "%"))
    log.info("Treffrate     : %s", _fmt(v.get("Treff_Pst"), "%"))
    log.info("-" * 70)
    log.info("PORTEN        : %s  (%d av %d varianter består)",
             "BESTÅTT" if all(port.values()) else "IKKE BESTÅTT", bestod, len(rader))
    for krav, ok in port.items():
        log.info("   %s  %s", "JA " if ok else "NEI", krav)
    if feilet:
        log.info("%d varianter feilet og ble hoppet over.", len(feilet))
    log.info("Filer         : %s", opp.resultatmappe)
    return resultat


def _fmt(v, suffiks: str = "", d: int = 2) -> str:
    x = _tall(v)
    return "—" if x is None else f"{x:.{d}f}{suffiks}"


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(
        description="Ledelsessentiment (NLP) — nedlasting og backtest.")
    p.add_argument("--hent", action="store_true", help="kjør del 1 (nedlasting)")
    p.add_argument("--backtest", action="store_true", help="kjør del 2 (backtest)")
    p.add_argument("--alt", action="store_true", help="kjør begge deler")
    p.add_argument("--mappe", default="LedelseData", help="datamappe")
    p.add_argument("--full", action="store_true",
                   help="hent alle selskaper på nytt, ignorer checkpoint")
    p.add_argument("--synlig", action="store_true", help="vis nettleseren")
    p.add_argument("--selskaper", default="",
                   help="kommaseparerte symboler, f.eks. EQNR,DNB,TEL")
    p.add_argument("--uten-kurser", action="store_true",
                   help="hopp over kursnedlasting i del 1")
    p.add_argument("--behold-mistenkelige", action="store_true",
                   help="ikke dropp tickere med ubekreftede kurssprang")
    p.add_argument("--trening-slutt", default="",
                   help="cutoff for variantvalg, YYYY-MM-DD")
    p.add_argument("--valg", default="", help="manuell variant, f.eks. S1|TP10")
    p.add_argument("--exits", default="", help="bare disse exit-kodene")
    p.add_argument("--debug", action="store_true")
    a = p.parse_args(argv)

    sett_opp_logging(logging.DEBUG if a.debug else logging.INFO)

    opp = Oppsett(mappe=Path(a.mappe), headless=not a.synlig)
    if a.behold_mistenkelige:
        opp.dropp_mistenkelige_kurser = False
    if a.trening_slutt:
        opp.trening_slutt = a.trening_slutt
    if a.valg:
        opp.manuelt_valg = a.valg

    if not (a.hent or a.backtest or a.alt):
        p.print_help()
        return 1

    kode = 0
    if a.hent or a.alt:
        try:
            last_ned_data(
                opp,
                selskaper=[s.strip() for s in a.selskaper.split(",") if s.strip()] or None,
                full=a.full,
                hent_kurser_ogsaa=not a.uten_kurser)
        except Exception as e:
            log.exception("Del 1 stoppet")
            print(f"Nedlasting feilet: {e}", file=sys.stderr)
            kode = 2

    if a.backtest or a.alt:
        try:
            r = kjor_backtest(opp, kun_exits=[c.strip() for c in a.exits.split(",")
                                              if c.strip()] or None)
            if r.get("status") != "OK":
                kode = max(kode, 2)
        except Exception as e:
            log.exception("Del 2 stoppet")
            print(f"Backtest feilet: {e}", file=sys.stderr)
            kode = 2

    return kode


if __name__ == "__main__":
    raise SystemExit(main())
