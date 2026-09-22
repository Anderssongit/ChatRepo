#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  INNSIDEHANDEL PÅ OSLO BØRS — SEKS STEG I ÉN FIL                             ║
║                                                                              ║
║   1  NEDLASTING    hent artiklene for hvert selskap fra Euronext (rå HTML)    ║
║   2  TEKST         trekk meldingsteksten ut av HTML-en → én .txt per melding  ║
║   3  SCORE         les dato, hvem, hvor mye — og ranger på bullishness        ║
║   4  KURSER        hent aksjekursene med yfinance                             ║
║   5  SAMMENSLÅING  slå sammen score + kurs til én fil                         ║
║   6  BACKTEST      test om scoren faktisk forutsier avkastning                ║
║                                                                              ║
║  ┌────────────┐ ┌───────────┐ ┌────────────┐ ┌────────┐ ┌───────┐ ┌────────┐ ║
║  │ 1 Euronext │ │ 2 Tekst   │ │ 3 Score    │ │ 4 Kurs │ │ 5 Slå │ │ 6 Test │ ║
║  ├────────────┤ ├───────────┤ ├────────────┤ ├────────┤ │  sam- │ ├────────┤ ║
║  │ artikler/  │►│ tekst/    │►│ hendelser  │ │ <TICK> │►│  men  │►│ rapport│ ║
║  │  *.html    │ │  *.txt    │ │  .xlsx/csv │►│  .csv  │ │ .xlsx │ │  .html │ ║
║  └────────────┘ └───────────┘ └────────────┘ └────────┘ └───────┘ └────────┘ ║
║                                                                              ║
║  SLIK KJØRER DU                                                              ║
║      python innsidehandel_pipeline.py                 alle seks steg          ║
║      python innsidehandel_pipeline.py --steg 2,3      bare disse to           ║
║      python innsidehandel_pipeline.py --offline       rør ikke nettet         ║
║      python innsidehandel_pipeline.py --status        hva ligger på disk?     ║
║                                                                              ║
║  INGEN STEG KAN VELTE KJØRINGEN. Hvert steg er pakket inn: feiler steg 4,     ║
║  kjører 5 og 6 videre på det som allerede ligger på disk, og statustavlen     ║
║  til slutt viser nøyaktig hvilke steg som gikk bra og hvilke som ikke gjorde  ║
║  det.                                                                        ║
║                                                                              ║
║  PORTEFØLJEN ER HEL ELLER TOM                                                ║
║      Kvalifiserer det færre enn min_navn_portefolje (5) selskaper,           ║
║      kjøpes INGENTING. Å eie én aksje fordi den var den eneste som           ║
║      passerte filteret er ikke en strategi — det er et veddemål på det       ║
║      selskapet, og backtesten måler da det og ikke signalet.                 ║
║      En strategi eier derfor enten minst fem selskaper eller står i          ║
║      kontanter, og «Beholdning per …» kan aldri vise én aksje.               ║
║      Filtre som aldri finner fem sier det høyt i stedet for å levere en      ║
║      CAGR basert på ett navn.                                                ║
║                                                                              ║
║  «KVALIFISERER NÅ» ER DEN LISTEN DU SKAL LESE                                ║
║      Backtesten kan ikke si hva som gjelder i dag: den krever kurser         ║
║      langt nok fram til å måle en melding, så de ferskeste faller ut som     ║
║      FOR_NY. Mailen har derfor en egen liste per strategi over hva som       ║
║      kvalifiserer på siste kursdag, ferske meldinger inkludert. Den er en    ║
║      signalliste, ikke et resultat — ingen av navnene er etterprøvd.        ║
║                                                                              ║
║  ÉN AKSJE ER IKKE EN PORTEFØLJE                                              ║
║      min_navn_portefolje (5) er et TAK på hver posisjon: ingen får mer       ║
║      enn 1/5 av kapitalen. Kvalifiserer bare én aksje, kjøpes den for en     ║
║      femtedel, og resten blir stående i kontanter — synlig i «Kapital        ║
║      ute», ikke skjult i avkastningen. Uten taket sto porteføljen 100 %      ║
║      i ett selskap på mange dager, og da måler backtesten den aksjen og      ║
║      ikke signalet. --min-navn 0 slår det av.                                ║
║      Tabellen viser nå MEDIAN antall navn og største posisjon, ikke bare     ║
║      snittet: et snitt på åtte navn kan skjule at halvparten av dagene       ║
║      hadde ett.                                                              ║
║                                                                              ║
║  RESULTATET PÅ MAIL                                                          ║
║      Til slutt sendes én mail: statusen for stegene, strategiene side om     ║
║      side, og per strategi nøkkeltall, beholdning og siste handler.          ║
║      App-passordet står IKKE i koden — legg det i miljøvariabelen            ║
║      AKSJE_MAIL_APP_PASSWORD eller i <datamappe>/mail_passord.txt.           ║
║      Slå av med --ingen-mail, bygg uten å sende med --mail-kladd.            ║
║                                                                              ║
║  STEG 6 KJØRER NÅ FLERE STRATEGIER                                           ║
║      Én motor, tretten varianter, samme signaler og samme kurser. Den        ║
║      gamle simuleringen kunne bare kjøpe topp 20 én gang i måneden — et      ║
║      signal fra den 2. ventet til den 1. neste måned, og da var det          ║
║      meste av en tjuedagerseffekt allerede borte. Nå finnes daglig,          ║
║      ukentlig, hendelsesdrevet med fast holdetid, forfall på scoren,         ║
║      momentumfilter, snuoperasjon, volumsjokk, scorevekting og               ║
║      konsentrasjon — se VARIANTER i DEL H.                                   ║
║      Hver variant måles på inn- og ut-utvalget hver for seg, og              ║
║      rapporten sier hva tabellen TILLATER deg å konkludere: med tretten      ║
║      forsøk er den beste raden delvis heldig.                                ║
║                                                                              ║
║  RETTET I DENNE VERSJONEN                                                    ║
║      · ROTEN: steg 1 lagret aldri meldingen. Overskriften i Euronext sin     ║
║        treffliste har href="" og åpner en modal; leser man a.href, får       ║
║        man LISTESIDENS egen adresse. Hver av de 3912 «artiklene» var         ║
║        derfor den samme søkeresultatsida, en halv megabyte om gangen.        ║
║        Nå leses data-node-nid, og meldingen hentes fra modalen — første      ║
║        klikk lærer opp adressen, resten går rett.                            ║
║      · Node-nummeret er nå nøkkelen. Samme melding funnet gjennom to         ║
║        datovinduer ble før to meldinger: lageret var doblet, og hver         ║
║        handel ville telt to ganger i backtesten.                             ║
║      · «3912 lest, 319 unike» er nå FEIL på statustavlen, ikke et grønt      ║
║        flueben med en fotnote under.                                         ║
║                                                                              ║
║      · Steg 2 leste 0 av 3912 meldinger. Blokkvalget forkastet alt:          ║
║        «search» i mønsteret traff «research», og MAR-skjemaet er en          ║
║        TABELL — altså mange korte linjer, som var et krav om å forkaste.     ║
║        Nå: mildere andrerunde, og en reserve som finner meldingen ved        ║
║        hjelp av hva som går igjen på ALLE sidene i stedet for å gjette.      ║
║      · Steg 3 fant ingen transaksjoner selv når teksten var der: det kreves  ║
║        «merkelapp: verdi», og en tabell gir «merkelapp» og «verdi» på hver   ║
║        sin linje. Linjeskift godtas nå som skilletegn.                       ║
║      · Steg 4 hentet ti dager i stedet for ti år: vannmerket ble trodd uten  ║
║        å sjekkes mot filene. Nå holdes de opp mot hverandre.                 ║
║      · Børskalenderen ble ni dager lang, fordi tynne serier stemte over      ║
║        dager de ikke levde i. Terskelen måles nå mot dem som fantes.         ║
║      · Steg 5 ga hver melding kalenderens første dag når kursene manglet;    ║
║        ti år med meldinger så ut som «venter på flere kursdager».            ║
║      · Feilene sier nå hva DU skal gjøre, ikke bare at noe gikk galt.        ║
║                                                                              ║
║  KRAV                                                                        ║
║      Python 3.9+          alt annet er standardbiblioteket                    ║
║      steg 1:  pip install playwright  &&  playwright install chromium         ║
║      steg 4:  pip install yfinance    (faller tilbake på Yahoo direkte)       ║
║      valgfritt: pip install pymupdf   (leser tekst fra vedlagte PDF-er)       ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import html as html_modul
import json
import logging
import math
import os
import re
import sys
import time
import traceback
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime, time as klokke, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Sequence, Set, Tuple


# Mappen DENNE FILEN ligger i. Alt som skal finnes uten at du oppgir en sti,
# letes opp herfra — aldri fra «gjeldende mappe». Starter du skriptet fra
# VS Code, er gjeldende mappe programmappen til VS Code, ikke din egen.
SKRIPTMAPPE = Path(__file__).resolve().parent

VERSJON = "6.0"


# ══════════════════════════════════════════════════════════════════════════
# APP-PASSORDET TIL MAILEN
# ══════════════════════════════════════════════════════════════════════════
#
# «Legg passordet i datamappen» er lett å si og lett å bomme på: filen havner
# der du var da du lagde den, og heter det du kalte den. Derfor leter vi bredt.
#
# Viktigere: vi gir oss ikke på det FØRSTE passordet vi finner. Det var feilen
# 8. september. Masteren fant ett passord, Gmail svarte 535 BadCredentials, og
# masteren ga opp — mens et annet script sendte mail helt fint ti minutter
# senere, med en annen verdi. Ett funnet passord er ikke det samme som ett som
# virker. Derfor leverer passord_kandidater() alle verdiene vi kjenner, i
# rekkefølge, og send_epost() prøver dem til én slipper inn og sier fra i
# loggen hvilken det var — så du vet hvilken fil du skal rydde i.
#
# Ingen passordverdi står i denne filen, og ingen skal legges inn her. En
# verdi i en kildefil er i git-historikken for alltid.

MAIL_PASSORDFILNAVN = ("mail_passord.txt", "mail_password.txt",
                       "app_passord.txt", "app_password.txt", ".env")

# Nøklene vi godtar i en .env-fil. Den første er vår egen; de andre er der
# fordi en .env sjelden er skrevet for oss alene.
MAIL_PASSORD_NOKLER = ("AKSJE_MAIL_APP_PASSWORD", "GMAIL_APP_PASSWORD",
                       "EMAIL_PASSWORD", "MAIL_PASSWORD", "SMTP_PASSWORD")

# Basemappen for Excel-dataene. Samme miljøvariabel som master.py bruker, så
# de to ikke kan peke to forskjellige steder.
EXCEL_BASE = Path(os.environ.get(
    "AKSJE_BASE_DIR", r"C:\Users\ander\Desktop\Python_K4\ExcelData"))


def _les_passordfil(sti: Path) -> str:
    """
    Passordet ut av én fil, eller tom streng. To former godtas:

        xxxx xxxx xxxx xxxx                  hele filen er passordet
        AKSJE_MAIL_APP_PASSWORD=xxxx …       en linje i en .env

    Et Gmail-app-passord limes inn som fire grupper med mellomrom. De betyr
    ingenting for SMTP, men de er der når du limer inn, så vi lar dem stå.

    Feiler aldri: en fil vi ikke får lest er det samme som ingen fil.
    """
    try:
        if not sti.is_file():
            return ""
        tekst = sti.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError, ValueError):
        return ""
    for linje in tekst.splitlines():
        linje = linje.strip()
        if not linje or linje.startswith("#"):
            continue
        if "=" in linje:
            navn, _, verdi = linje.partition("=")
            navn = navn.strip()
            if navn.lower().startswith("export "):
                navn = navn[len("export "):].strip()
            if navn.upper() in MAIL_PASSORD_NOKLER:
                return verdi.strip().strip('"').strip("'")
            # En annen nøkkel i en .env — ikke vår, gå videre.
            continue
        # Første linje som bare er tekst: da er filen selve passordet.
        return linje
    return ""


def mail_passordfiler(datamappe: Optional[Path] = None) -> List[Path]:
    """
    Hver filsti vi prøver, i den rekkefølgen vi prøver dem.

    Lista er med vilje raus, og rekkefølgen er «nærmest dataene først», så en
    fersk fil i datamappen vinner over en gammel en på skrivebordet.
    """
    hjem = Path.home()
    mapper: List[Path] = [m for m in (datamappe, SKRIPTMAPPE, Path.cwd(),
                                      EXCEL_BASE) if m is not None]
    mapper += [hjem,
               hjem / "Desktop", hjem / "Skrivebord",
               hjem / "OneDrive" / "Desktop", hjem / "OneDrive" / "Skrivebord",
               hjem / "Documents", hjem / "Dokumenter",
               hjem / "OneDrive" / "Documents", hjem / "OneDrive" / "Dokumenter",
               hjem / "Downloads", hjem / "Nedlastinger"]
    sett: Set[str] = set()
    unike: List[Path] = []
    for m in mapper:
        try:
            n = str(Path(m).resolve())
        except OSError:
            continue
        if n not in sett:
            sett.add(n)
            unike.append(Path(m))
    return [mappe / navn for mappe in unike for navn in MAIL_PASSORDFILNAVN]


def passord_kandidater(datamappe: Optional[Path] = None,
                       fra_oppsett: str = "") -> List[Tuple[str, str]]:
    """
    (hvor det kom fra, passordet) for hver verdi vi kjenner, i prøverekkefølge.

    Duplikater faller ut: å prøve det samme feil passordet tre ganger er tre
    535-svar og ingen ny informasjon.
    """
    raa: List[Tuple[str, str]] = []
    if fra_oppsett:
        raa.append(("oppsettet i koden", fra_oppsett))
    fra_miljo = os.environ.get("AKSJE_MAIL_APP_PASSWORD", "").strip()
    if fra_miljo:
        raa.append(("miljøvariabelen AKSJE_MAIL_APP_PASSWORD", fra_miljo))
    for sti in mail_passordfiler(datamappe):
        p = _les_passordfil(sti)
        if p:
            raa.append((str(sti), p))

    sett: Set[str] = set()
    ut: List[Tuple[str, str]] = []
    for kilde, passord in raa:
        if passord not in sett:
            sett.add(passord)
            ut.append((kilde, passord))
    return ut


def finn_mail_passord(datamappe: Optional[Path] = None) -> str:
    """
    Det første passordet vi finner. Tom streng betyr «fant ingenting».

    Feiler aldri: en mail som ikke går ut skal ikke ta analysen med seg.
    """
    kandidater = passord_kandidater(datamappe)
    return kandidater[0][1] if kandidater else ""


def passord_leteforklaring(datamappe: Optional[Path] = None,
                           antall: int = 6) -> str:
    """
    De første stiene vi lette i, som én tekstblokk til loggen.

    «Mangler app-passord» forteller deg ingenting du kan handle på. En liste
    over hvor koden faktisk lette gjør det: da ser du med én gang at filen din
    ligger et sted som ikke står der.
    """
    stier = mail_passordfiler(datamappe)[:antall]
    linjer = "\n".join(f"         {s}" for s in stier)
    return (f"       Legg app-passordet i én av disse (første som finnes vinner):\n"
            f"{linjer}\n"
            f"       … eller sett miljøvariabelen AKSJE_MAIL_APP_PASSWORD.")


# ══════════════════════════════════════════════════════════════════════════
# OPPSETT
# ══════════════════════════════════════════════════════════════════════════

@dataclass
class Oppsett:
    """Alt som er verdt å justere, ett sted."""

    base_dir: Path = SKRIPTMAPPE / "data"

    # ── kjøremodus (settes av kommandolinjen) ────────────────────────────
    offline: bool = False          # rør ikke nettet
    full: bool = False             # se bort fra vannmerker, hent alt på nytt

    # ── felles ───────────────────────────────────────────────────────────
    # Oslo Børs: kontinuerlig handel til 16:20. Alt publisert 16:20 eller
    # senere er først handlebart neste dag. Denne verdien eies av ÉN
    # funksjon (Kalender.forste_handledag) og brukes av alle nedstrøms.
    stengetid: str = "16:20"
    historikk_ar: int = 10
    overlapp_dager: int = 10       # hentes om igjen bakover hver gang
    maks_forsok: int = 3
    forste_pause_s: float = 2.0

    # ── STEG 1 — nedlasting ──────────────────────────────────────────────
    euronext_base: str = "https://live.euronext.com"
    aksjeliste_url: str = "https://live.euronext.com/nb/markets/oslo/equities/list"
    hent_aksjeliste: bool = True
    aksjeliste_maks_alder_dager: int = 1
    sprak: str = "nb"
    kategori_id: int = 1081        # Euronext sin kode for meldepliktig handel
    maks_sider: int = 60
    pause_mellom_sider_s: float = 0.4
    pause_mellom_selskaper_s: float = 0.8
    pause_mellom_artikler_s: float = 0.15
    maks_sekunder_per_selskap: int = 2400
    headless: bool = True
    browser_sti: str = ""
    browser_timeout_ms: int = 30_000
    sondering_timeout_ms: int = 2_500
    nedlasting_timeout_ms: int = 90_000
    last_ned_pdf: bool = True
    pdf_timeout_ms: int = 20_000
    # Hvor mye HTML som må til før vi tror vi fikk en LISTESIDE i det hele
    # tatt. En feilside er som regel under dette.
    min_html_tegn: int = 4_000
    # Selve meldingen er et lite utklipp, ikke en hel side — et MAR-skjema er
    # noen få kilobyte. Den har sin egen, mye lavere grense.
    min_melding_tegn: int = 300
    melding_timeout_ms: int = 12_000

    # ── STEG 2 — tekstuttrekk ────────────────────────────────────────────
    min_tekstlengde: int = 250
    # En tekstblokk som står IDENTISK i minst denne andelen av artiklene er
    # sidemal — cookie-vindu, meny, bunntekst — og aldri en børsmelding.
    # Dette er vakthunden som erstatter den gamle «stopp hele kjøringen».
    sidemal_andel: float = 0.20
    sidemal_minst: int = 5
    # Sidemal ER sidemal: den står likt på alle sidene, så det holder å se
    # på et utvalg. Med 4000 artikler sparer det en halvtime, og svaret blir
    # det samme. 0 = les alle.
    sidemal_prove: int = 500
    # Reserveuttrekket (hele sida minus sidemalslinjene) kan bli langt på en
    # side med mye innhold. Vi kutter det her, så en enkelt melding ikke
    # sluker steg 3.
    maks_resttekst: int = 40_000
    bruk_pdf_reserve: bool = True

    # ── STEG 3 — score ───────────────────────────────────────────────────
    ta_med_emisjoner: bool = False
    min_verdi_nok: float = 50_000.0
    # Flere innsidere i samme selskap innenfor dette vinduet er ÉN klynge.
    klynge_dager: int = 30
    # Vektene i bullishness-scoren. Summen bør være 1,0.
    vekt_rolle: float = 0.30
    vekt_okning: float = 0.28
    vekt_belop: float = 0.17
    vekt_klynge: float = 0.25
    bonus_ny_posisjon: float = 0.10

    # ── STEG 4 — kurser ──────────────────────────────────────────────────
    kurs_ekstra_ar: int = 1        # historikk FØR meldingene, til snittvolum
    referanse_ticker: str = "OSEBX.OL"
    referanse_kandidater: Tuple[str, ...] = (
        "OSEBX.OL", "^OSEAX", "^OSEBX", "OBX.OL", "^OBX", "OSEAX.OL")
    likevekt_reserve: bool = True
    ticker_suffiks: str = ".OL"
    # «close» = prisavkastning, «adjclose» = totalavkastning (med utbytte).
    # Brukes for BÅDE aksje og referanse, ellers lekker utbytte inn som
    # falsk meravkastning.
    kursfelt: str = "close"
    handledag_terskel: float = 0.20
    pause_mellom_tickere_s: float = 0.25
    yf_bolk: int = 40              # tickere per yfinance-kall
    restatement_toleranse: float = 0.005
    # Feiler så mange tickere PÅ RAD, er det nettet som er nede — ikke
    # tickerne som ikke finnes. Da stopper vi i stedet for å bruke en time
    # på å få den samme feilen 300 ganger. 0 slår av grensen.
    maks_feil_paa_rad: int = 12
    kurs_timeout_s: int = 20

    # ── STEG 5 — sammenslåing ────────────────────────────────────────────
    horisonter: Tuple[int, ...] = (-20, -5, -1, 1, 5, 10, 20, 60, 120)
    maks_fyll_dager: int = 5       # hull vi tåler å fylle framover
    volum_vindu: int = 20

    # ── STEG 6 — backtest ────────────────────────────────────────────────
    event_horisont: int = 20
    bootstrap_runder: int = 2000
    bootstrap_fro: int = 20260829
    min_hendelser_for_dom: int = 200
    inn_utvalg_slutt: str = "2025-06-30"
    kun_primaer: bool = True
    antall_bøtter: int = 5         # score-kvintiler
    min_score_portefolje: float = 60.0
    # Hopper over strategisammenlikningen. Den koster noen sekunder, og noen
    # ganger vil du bare ha hovedstrategien.
    kun_hovedstrategi: bool = False
    signal_vindu_dager: int = 30
    maks_navn: int = 20
    # Minste antall posisjoner risikoen skal deles på. Kan ikke tvinge fram
    # navn som ikke finnes, så det virker som et TAK: ingen posisjon får mer
    # enn 1/min_navn av kapitalen, og mangler det navn, blir resten stående i
    # kontanter. 0 slår av taket — da kan porteføljen igjen stå 100 % i én
    # aksje, og da måler backtesten den aksjen og ikke signalet.
    min_navn_portefolje: int = 5
    min_omsetning_nok: float = 500_000.0
    spread_pst: float = 0.00       # 1.5 — full spread; vi betaler halve hver vei
    kurtasje_pst: float = 0.00     # 0.05
    startkapital: float = 1_000_000.0
    risikofri_pst: float = 3.0

    # ── MAIL ─────────────────────────────────────────────────────────────
    # Avsender og mottaker kan stå her; app-passordet skal IKKE. Det leses fra
    # miljøvariabelen AKSJE_MAIL_APP_PASSWORD, eller fra en fil ved siden av
    # dataene som git ikke tar med. Se lag_passordfil() rett under Oppsett.
    send_epost_ved_slutt: bool = True
    epost_fra: str = "andyxcx@gmail.com"
    epost_passord: str = ""
    epost_til: str = "andyxcx@gmail.com"
    smtp_vert: str = "smtp.gmail.com"
    smtp_port: int = 587

    # ── avledede stier ───────────────────────────────────────────────────
    def __post_init__(self) -> None:
        self.base_dir = Path(self.base_dir)
        # Miljøvariablene vinner over verdiene i koden, alltid.
        self.epost_fra = os.environ.get("AKSJE_MAIL_USER", self.epost_fra)
        self.epost_til = os.environ.get("AKSJE_MAIL_TO", self.epost_til)
        self.epost_passord = (os.environ.get("AKSJE_MAIL_APP_PASSWORD", "")
                              or self.epost_passord)

        # STEG 1
        self.s1_dir = self.base_dir / "1_nedlasting"
        self.artikkel_dir = self.s1_dir / "artikler"
        self.pdf_dir = self.s1_dir / "pdf"
        self.indeks_csv = self.s1_dir / "indeks.csv"
        self.selskapsliste = self.s1_dir / "selskaper.csv"

        # STEG 2
        self.s2_dir = self.base_dir / "2_tekst"
        self.tekst_dir = self.s2_dir / "tekst"
        self.tekst_indeks_csv = self.s2_dir / "tekst_indeks.csv"
        self.sidemal_csv = self.s2_dir / "_sidemal.csv"

        # STEG 3
        self.s3_dir = self.base_dir / "3_score"
        self.hendelser_csv = self.s3_dir / "hendelser.csv"
        self.hendelser_xlsx = self.s3_dir / "hendelser.xlsx"
        self.transaksjoner_csv = self.s3_dir / "transaksjonslinjer.csv"
        self.score_kvalitet_csv = self.s3_dir / "kvalitet.csv"

        # STEG 4
        self.s4_dir = self.base_dir / "4_kurser"
        self.kalender_csv = self.s4_dir / "_kalender.csv"
        self.referanse_fil = self.s4_dir / "_referanse.txt"
        self.dekning_csv = self.s4_dir / "_dekning.csv"

        # STEG 5
        self.s5_dir = self.base_dir / "5_sammenslatt"
        self.merget_csv = self.s5_dir / "innsidehandel_kurs.csv"
        self.merget_xlsx = self.s5_dir / "innsidehandel_kurs.xlsx"

        # STEG 6
        self.s6_dir = self.base_dir / "6_backtest"
        self.event_study_csv = self.s6_dir / "event_study.csv"
        self.event_kurve_csv = self.s6_dir / "event_kurve.csv"
        self.score_test_csv = self.s6_dir / "score_test.csv"
        self.undergrupper_csv = self.s6_dir / "undergrupper.csv"
        self.equity_csv = self.s6_dir / "equity.csv"
        self.strategier_csv = self.s6_dir / "strategier.csv"
        self.strategi_equity_csv = self.s6_dir / "strategi_equity.csv"
        self.beholdning_csv = self.s6_dir / "strategi_beholdning.csv"
        self.strategi_handler_csv = self.s6_dir / "strategi_handler.csv"
        self.dagens_liste_csv = self.s6_dir / "dagens_liste.csv"
        self.handler_csv = self.s6_dir / "handler.csv"
        self.rapport_html = self.s6_dir / "rapport.html"

        # felles
        self.vannmerke_json = self.base_dir / "vannmerke.json"
        self.status_json = self.base_dir / "status.json"
        self.logg_fil = self.base_dir / "pipeline.log"

    @property
    def passordfil(self) -> Path:
        r"""
        Filen app-passordet kan ligge i. Den står i datamappen, ikke i koden,
        og datamappen er ikke i git.

        Passordet hører ikke hjemme i en kildefil. Ligger det der, ligger det
        i git-historikken for alltid, og alle med lesetilgang til repoet kan
        sende mail som deg. Denne filen er den enkle veien utenom:

            echo xxxx xxxx xxxx xxxx > <datamappe>\mail_passord.txt

        Miljøvariabelen AKSJE_MAIL_APP_PASSWORD virker like godt og er enda
        tryggere, siden filen kan bli med i en zip.
        """
        return self.base_dir / "mail_passord.txt"

    def passord_kandidater(self) -> List[Tuple[str, str]]:
        """
        Alle passordene vi kjenner, i prøverekkefølge — ikke bare det første.

        Se kommentaren over MAIL_PASSORDFILNAVN: å stoppe på det første funnet
        var nettopp det som gjorde at masteren aldri fikk sendt mail.
        """
        return passord_kandidater(self.base_dir, self.epost_passord)

    def les_passord(self) -> str:
        """Det første passordet vi finner. Tom streng betyr «fant ingenting»."""
        kandidater = self.passord_kandidater()
        return kandidater[0][1] if kandidater else ""

    def lag_mapper(self) -> None:
        for p in (self.base_dir, self.s1_dir, self.artikkel_dir, self.pdf_dir,
                  self.s2_dir, self.tekst_dir, self.s3_dir, self.s4_dir,
                  self.s5_dir, self.s6_dir):
            p.mkdir(parents=True, exist_ok=True)

    # ── datovinduer ──────────────────────────────────────────────────────
    def eldste_melding(self) -> date:
        return date.today() - timedelta(days=int(self.historikk_ar * 365.25))

    def eldste_kurs(self) -> date:
        return date.today() - timedelta(
            days=int((self.historikk_ar + self.kurs_ekstra_ar) * 365.25))

    def kursfelt_navn(self) -> str:
        return "adjclose" if str(self.kursfelt).lower().startswith("adj") else "close"

    def avkastningstype(self) -> str:
        return ("totalavkastning (med utbytte)" if self.kursfelt_navn() == "adjclose"
                else "prisavkastning (uten utbytte)")


# ══════════════════════════════════════════════════════════════════════════
# DEL A — SMÅVERKTØY
# ══════════════════════════════════════════════════════════════════════════
#
# Ingen tredjepartsbiblioteker herfra og ned til steg 4. Datamengden er så
# liten (noen tusen meldinger, et par hundre tickere) at pandas ikke kjøper
# oss noe, og en avhengighet mindre er én ting mindre som kan mangle når du
# skal kjøre om et halvt år.


# ── TEKST ────────────────────────────────────────────────────────────────

# Tegn som ser ut som mellomrom, men ikke er det. Euronext-sidene er fulle
# av dem, og de ødelegger både talltolkning og sammenlikning av navn.
USYNLIGE = {
    " ": " ", " ": " ", " ": " ", " ": " ",
    "​": "", "﻿": "", "‎": "", "‏": "",
    "‘": "'", "’": "'", "ʼ": "'",
    "“": '"', "”": '"',
    "‐": "-", "‑": "-", "‒": "-",
    "–": "-", "—": "-", "−": "-",
}


def normaliser_tegn(t: str) -> str:
    for fra, til in USYNLIGE.items():
        if fra in t:
            t = t.replace(fra, til)
    return t


def rens(s: Any) -> str:
    """Til én linje uten dobbelt mellomrom. Trygg mot None."""
    if s is None:
        return ""
    return " ".join(normaliser_tegn(str(s)).split())


def rens_flerlinje(s: Any) -> str:
    """Beholder linjeskift — meldingstabeller mister mening uten dem."""
    if s is None:
        return ""
    linjer = [" ".join(l.split()) for l in normaliser_tegn(str(s)).splitlines()]
    return "\n".join(l for l in linjer if l).strip()


def filnavnvennlig(s: Any, maks: int = 60) -> str:
    t = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", rens(s)).strip()
    return (t.replace(" ", "_") or "UKJENT")[:maks]


def avtrykk(tekst: str, lengde: int = 16) -> str:
    return hashlib.sha1(str(tekst).encode("utf-8", "replace")).hexdigest()[:lengde]


# ── TALL ─────────────────────────────────────────────────────────────────
#
# Det farligste stedet i hele programmet. Én melding kan skrive det samme
# tallet som «1 234 567», «1.234.567», «1,234,567» eller «1234567», og
# prisen som «123,45» eller «123.45». Tolker vi feil, får vi et beløp som er
# tusen ganger for stort — og ingenting nedstrøms vil se at noe er galt.
#
#   1  Er begge skilletegn til stede, er DET SISTE desimaltegnet.
#   2  Er bare ett til stede og det gjentas, er det tusenskille.
#   3  Er det ett skilletegn med nøyaktig tre siffer etter, og 1-3 foran,
#      er det tusenskille.
#   4  Ellers er det desimaltegn.
# Med heltall=True hoppes 3 og 4 over: alt er tusenskille.

_GRUPPERT = re.compile(r"^\d{1,3}(?:[ .,]\d{3})+$")
_TALL_I_TEKST = re.compile(r"-?\d[\d .,]*\d(?:[eE][+-]?\d+)?|-?\d(?:[eE][+-]?\d+)?")

_EN_TUSEN = re.compile(r"\d,\d{3}(?!\d)")
_NB_TUSEN = re.compile(r"\d[. ]\d{3}(?!\d)")
_EN_DESIMAL = re.compile(r"\d\.\d{1,2}(?!\d)")
_NB_DESIMAL = re.compile(r"\d,\d{1,2}(?!\d)")


def finn_konvensjon(tekst: Any) -> str:
    """
    Hvilken tallskrivemåte bruker DENNE meldingen? «EN», «NB» eller «».

    «1.234» er 1234 i en norsk melding og 1,234 i en engelsk. Uten å vite
    hvilken vi leser, må vi gjette per tall — og da bommer vi med faktor
    tusen på noen av dem. Konvensjonen bestemmes ÉN gang for hele meldingen,
    av de tallene som ikke er tvetydige, og brukes så på alle.
    """
    t = normaliser_tegn(str(tekst or ""))
    en = len(_EN_TUSEN.findall(t)) + len(_EN_DESIMAL.findall(t))
    nb = len(_NB_TUSEN.findall(t)) + len(_NB_DESIMAL.findall(t))
    if en > nb:
        return "EN"
    if nb > en:
        return "NB"
    return ""


def tolk_maskin(rå: Any) -> Optional[float]:
    """
    Tall fra en fil VI har skrevet, eller fra et API. Ingen gjetting.

    Her er punktum alltid desimaltegn. Å slippe heuristikken løs på egne
    filer var en ekte feil: kursen 497.456 ble lest som 497 456, og
    avkastningen ble 102 000 % i stedet for 2 %.
    """
    if rå is None:
        return None
    if isinstance(rå, bool):
        return None
    if isinstance(rå, (int, float)):
        f = float(rå)
        return None if f != f else f
    t = normaliser_tegn(str(rå)).strip().replace(" ", "")
    if not t:
        return None
    try:
        f = float(t)
    except ValueError:
        return tolk_tall(t)
    return None if f != f else f


def tolk_tall(rå: Any, heltall: bool = False,
              konvensjon: str = "") -> Optional[float]:
    """Tolker ett tall fra menneskeskrevet tekst. None når det ikke går."""
    if rå is None or isinstance(rå, bool):
        return None
    if isinstance(rå, (int, float)):
        f = float(rå)
        return None if f != f else f

    t = normaliser_tegn(str(rå)).strip()
    if not t:
        return None
    negativ = t.lstrip().startswith("-") or ("(" in t and ")" in t)
    t = t.replace("(", "").replace(")", "")

    m = _TALL_I_TEKST.search(t)
    if not m:
        return None
    t = m.group(0).strip().lstrip("-")
    if not t:
        return None

    # Mellomrom er alltid tusenskille — ingen skriver desimaler med mellomrom.
    t = t.replace(" ", "")

    m_eks = re.search(r"[eE][+-]?\d+$", t)
    eksponent = ""
    if m_eks:
        eksponent = m_eks.group(0)
        t = t[: m_eks.start()]

    har_punkt, har_komma = "." in t, "," in t
    try:
        if konvensjon in ("EN", "NB"):
            if konvensjon == "EN":
                t = t.replace(",", "")
            else:
                t = t.replace(".", "").replace(",", "" if heltall else ".")
            verdi = float(t + eksponent)
        elif har_punkt and har_komma:
            desimal = "." if t.rfind(".") > t.rfind(",") else ","
            tusen = "," if desimal == "." else "."
            verdi = float(t.replace(tusen, "").replace(desimal, ".") + eksponent)
        elif har_punkt or har_komma:
            skille = "." if har_punkt else ","
            antall = t.count(skille)
            etter = len(t.split(skille)[-1])
            foran = len(t.split(skille)[0])
            if heltall or antall > 1 or (etter == 3 and 1 <= foran <= 3):
                t = t.replace(skille, "")
            else:
                t = t.replace(skille, ".")
            verdi = float(t + eksponent)
        else:
            verdi = float(t + eksponent)
    except ValueError:
        return None
    if verdi != verdi:
        return None
    return -verdi if negativ else verdi


def tolk_heltall(rå: Any, konvensjon: str = "") -> Optional[int]:
    """Antall aksjer, beholdninger — alltid hele tall, aldri desimaler."""
    v = tolk_tall(rå, heltall=True, konvensjon=konvensjon)
    if v is None:
        return None
    try:
        return int(round(v))
    except (ValueError, OverflowError):
        return None


VALUTAER = ("NOK", "SEK", "DKK", "EUR", "USD", "GBP", "CHF", "ISK", "KR")


def tolk_belop(rå: Any) -> Tuple[Optional[float], str]:
    """«NOK 123,45» → (123.45, 'NOK'). «123,45 kr» → (123.45, 'NOK')."""
    t = rens(rå)
    if not t:
        return None, ""
    stor = t.upper()
    valuta = ""
    for v in VALUTAER:
        if re.search(rf"\b{v}\b", stor):
            valuta = "NOK" if v == "KR" else v
            break
    return tolk_tall(t), valuta


# ── DATO OG KLOKKESLETT ──────────────────────────────────────────────────

MND = {
    "january": 1, "jan": 1, "januar": 1,
    "february": 2, "feb": 2, "februar": 2,
    "march": 3, "mar": 3, "mars": 3,
    "april": 4, "apr": 4,
    "may": 5, "mai": 5,
    "june": 6, "jun": 6, "juni": 6,
    "july": 7, "jul": 7, "juli": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10, "oktober": 10, "okt": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12, "desember": 12, "des": 12,
}

TIDLIGST = date(1996, 1, 1)


def _trygg_dato(år: int, mnd: int, dag: int) -> Optional[date]:
    try:
        d = date(år, mnd, dag)
    except ValueError:
        return None
    return d if TIDLIGST <= d <= date.today() + timedelta(days=2) else None


def tolk_dato(rå: Any) -> Optional[date]:
    """Tolker formatene Euronext og Yahoo bruker. None i stedet for å gjette."""
    if rå is None:
        return None
    if isinstance(rå, datetime):
        return rå.date()
    if isinstance(rå, date):
        return rå
    t = rens(rå)
    if not t:
        return None

    m = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", t)
    if m:
        return _trygg_dato(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    # 19/08/2026, 19-08-2026, 19.08.2026 — dag først, slik Euronext skriver
    m = re.search(r"\b(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})\b", t)
    if m:
        return _trygg_dato(int(m.group(3)), int(m.group(2)), int(m.group(1)))

    # 19. august 2026 / 19 Aug 2026
    m = re.search(r"\b(\d{1,2})\.?\s+([A-Za-zæøåÆØÅ]{3,9})\.?,?\s+(\d{4})\b", t)
    if m and m.group(2).lower() in MND:
        return _trygg_dato(int(m.group(3)), MND[m.group(2).lower()], int(m.group(1)))

    # August 19, 2026
    m = re.search(r"\b([A-Za-zæøåÆØÅ]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b", t)
    if m and m.group(1).lower() in MND:
        return _trygg_dato(int(m.group(3)), MND[m.group(1).lower()], int(m.group(2)))

    return None


def tolk_klokkeslett(rå: Any) -> Optional[klokke]:
    """«16:35» eller «16.35» → time(16, 35). None når det ikke finnes."""
    t = rens(rå)
    if not t:
        return None
    m = re.search(r"\b([01]?\d|2[0-3])[:.]([0-5]\d)\b", t)
    if not m:
        return None
    try:
        return klokke(int(m.group(1)), int(m.group(2)))
    except ValueError:
        return None


def iso(d: Optional[date]) -> str:
    return d.strftime("%Y-%m-%d") if d else ""


def fra_iso(s: Any) -> Optional[date]:
    if isinstance(s, datetime):
        return s.date()
    if isinstance(s, date):
        return s
    t = rens(s)[:10]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", t):
        return None
    try:
        return datetime.strptime(t, "%Y-%m-%d").date()
    except ValueError:
        return None


# ── DATOER FRA EXCEL ─────────────────────────────────────────────────────
#
# Excel lagrer en dato som et TALL: 45900 er 5. september 2025. Om cellen
# VISES som en dato eller som 45900 avgjøres av formatet på cellen, ikke av
# verdien. En leser som bare tar rå celleverdi får derfor «45900» — og en
# mottaker som krever ÅÅÅÅ-MM-DD forkaster hver eneste rad uten å si fra.
#
# Det er nøyaktig det som skjedde med SentMom-loggen: pandas skrev ekte
# datoer, leseren her ga serienumre, fra_iso() sa nei, og master.py talte
# 0 scorer med en hake foran seg.

_EXCEL_EPOKE = date(1899, 12, 30)          # serienummer 1 = 1900-01-01
_EXCEL_EPOKE_1904 = date(1904, 1, 1)       # Mac-arven, «1904 date system»
_EXCEL_MAKS_SERIENR = 2_958_465            # 9999-12-31
# Vindu for tall som ikke er merket som dato i det hele tatt. 1954-01-01 til
# rundt 2119. Snevert med vilje: en score på 0,73 eller et antall aksjer
# skal ALDRI kunne bli til en dato bare fordi det er et tall.
_SERIENR_GULV, _SERIENR_TAK = 19_723.0, 80_000.0


def fra_excel_serienr(rå: Any, dato1904: bool = False) -> Optional[datetime]:
    """
    Excels dagnummer → datetime. None når tallet umulig kan være en dato.

    Serienummeret 60 finnes ikke: Excel arvet fra Lotus 1-2-3 troen på at
    1900 var et skuddår. Alt UNDER 60 ligger derfor én dag feil i forhold
    til epoken, og korrigeres her.
    """
    try:
        f = float(str(rå).strip().replace(",", ".")) if isinstance(rå, str) else float(rå)
    except (TypeError, ValueError):
        return None
    if f != f or f < 1.0 or f > _EXCEL_MAKS_SERIENR:
        return None
    if dato1904:
        grunn = _EXCEL_EPOKE_1904
    elif f < 60.0:
        grunn = _EXCEL_EPOKE + timedelta(days=1)
    else:
        grunn = _EXCEL_EPOKE
    hele = int(f)
    # Excel regner klokkeslett i hele sekunder. Uten avrundingen blir 12:00
    # til 11:59:59 på grunn av flyttallet.
    sekunder = int(round((f - hele) * 86400.0))
    if sekunder >= 86400:
        hele, sekunder = hele + 1, 0
    try:
        return (datetime(grunn.year, grunn.month, grunn.day)
                + timedelta(days=hele, seconds=sekunder))
    except (OverflowError, ValueError):
        return None


_DATO_PUNKTUM = re.compile(r"(\d{1,2})[./-](\d{1,2})[./-](\d{4})")
_DATO_KOMPAKT = re.compile(r"\d{8}")
_BARE_TALL = re.compile(r"\d{1,7}(?:[.,]\d+)?")


def fra_dato_celle(rå: Any, dato1904: bool = False) -> Optional[date]:
    """
    Datoen i en celle — enten den kom som dato, tekst eller serienummer.

    Dette er den TOLERANTE leseren, og den brukes bare på filer ANDRE har
    skrevet. fra_iso() er og blir streng: den leser våre egne filer, der et
    tall i et datofelt er en feil og ikke en dato.

    Rekkefølgen er ikke tilfeldig. «20260905» er åtte siffer og leses som
    ÅÅÅÅMMDD før tallvinduet får se det; «45900» er fem og havner i
    serienummer-vinduet; «0,73» faller utenfor begge og blir None.
    """
    if rå is None or isinstance(rå, bool):
        return None
    if isinstance(rå, (date, datetime)):
        return fra_iso(rå)
    if isinstance(rå, (int, float)):
        f = float(rå)
        if not (_SERIENR_GULV <= f <= _SERIENR_TAK):
            return None
        dt = fra_excel_serienr(f, dato1904)
        return dt.date() if dt else None

    t = rens(rå)
    if not t:
        return None
    d = fra_iso(t)                       # 2026-09-05, med eller uten klokke
    if d:
        return d
    m = _DATO_PUNKTUM.fullmatch(t)       # 05.09.2026 og 05/09/2026
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            return None
    if _DATO_KOMPAKT.fullmatch(t):       # 20260905
        try:
            return datetime.strptime(t, "%Y%m%d").date()
        except ValueError:
            return None
    if _BARE_TALL.fullmatch(t):          # 45900  ← Excels serienummer
        try:
            f = float(t.replace(",", "."))
        except ValueError:
            return None
        if not (_SERIENR_GULV <= f <= _SERIENR_TAK):
            return None
        dt = fra_excel_serienr(f, dato1904)
        return dt.date() if dt else None
    return None


# ── FILER, FEIL, LOGG ────────────────────────────────────────────────────

def skriv_atomisk(sti: Path, skriv: Callable[[Path], Any]) -> None:
    """
    Skriv til midlertidig fil og bytt om.

    Et strømbrudd midt i skrivingen skal ikke kunne etterlate en halv fil.
    Enten er den gamle der, eller så er den nye der.
    """
    sti = Path(sti)
    sti.parent.mkdir(parents=True, exist_ok=True)
    midlertidig = sti.with_name(sti.name + ".tmp")
    try:
        skriv(midlertidig)
        os.replace(midlertidig, sti)
    finally:
        if midlertidig.exists():
            try:
                midlertidig.unlink()
            except OSError:
                pass


PAKKENAVN = {
    "playwright": "playwright   (og deretter: playwright install chromium)",
    "yfinance": "yfinance",
    "fitz": "pymupdf",
    "pymupdf": "pymupdf",
}


def feiltekst(e: BaseException) -> str:
    """
    Én linje som peker på seg selv: typenavnet først, alltid.

    «ValueError: fant ingen ISIN-kolonne» sier hva som er galt. Bare
    «fant ingen ISIN-kolonne» gjør det ikke, og en tom str(e) — som er helt
    vanlig — sier ingenting i det hele tatt.
    """
    navn = type(e).__name__
    melding = str(e).strip()
    if isinstance(e, ImportError):
        mangler = str(getattr(e, "name", "") or melding).split(".")[0]
        pakke = PAKKENAVN.get(mangler.lower(), mangler or "pakken")
        return f"{navn}: mangler «{mangler}» — kjør:  pip install {pakke}"
    return f"{navn}: {melding}" if melding else navn


def med_nye_forsok(handling: Callable[[], Any], logger: logging.Logger, hva: str,
                   maks: int = 3, pause: float = 2.0,
                   feiltyper: Tuple[type, ...] = (Exception,)) -> Any:
    """
    Prøv på nytt med doblende pause. None når alle forsøk feiler.

    En ImportError blir ikke bedre av tre forsøk og slipper rett gjennom,
    slik at feilmeldingen får si «pip install».
    """
    pause_nå = pause
    for forsøk in range(1, maks + 1):
        try:
            return handling()
        except ImportError:
            raise
        except KeyboardInterrupt:
            raise
        except feiltyper as e:
            if forsøk >= maks:
                logger.warning(f"   {hva}: ga opp etter {maks} forsøk — {feiltekst(e)[:130]}")
                return None
            logger.debug(f"   {hva}: forsøk {forsøk}/{maks} feilet ({feiltekst(e)[:80]}) "
                         f"— nytt om {pause_nå:.0f} s")
            time.sleep(pause_nå)
            pause_nå *= 2
    return None


def lag_logger(logg_fil: Optional[Path] = None, feilsok: bool = False,
               navn: str = "innsidehandel") -> logging.Logger:
    logger = logging.getLogger(navn)
    logger.setLevel(logging.DEBUG if feilsok else logging.INFO)
    for old_handler in list(logger.handlers):
        old_handler.close()
        logger.removeHandler(old_handler)
    logger.propagate = False

    fmt = logging.Formatter("%(asctime)s  %(levelname)-7s  %(message)s", "%H:%M:%S")
    konsoll = logging.StreamHandler(sys.stdout)
    try:
        konsoll.stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError, OSError):
        pass          # eldre Python, eller en strøm som ikke lar seg endre
    konsoll.setFormatter(fmt)
    logger.addHandler(konsoll)

    if logg_fil:
        try:
            logg_fil = Path(logg_fil)
            logg_fil.parent.mkdir(parents=True, exist_ok=True)
            if logg_fil.exists() and logg_fil.stat().st_size > 10 * 1024 * 1024:
                gammel = logg_fil.with_suffix(".log.old")
                if gammel.exists():
                    gammel.unlink()
                logg_fil.rename(gammel)
            fil = logging.FileHandler(logg_fil, encoding="utf-8")
            fil.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-7s  %(message)s"))
            logger.addHandler(fil)
        except OSError as e:
            print(f"Advarsel: ingen loggfil — {feiltekst(e)}. Konsollet får alt.")
    return logger


def stillelogger() -> logging.Logger:
    logger = logging.getLogger("innsidehandel.stille")
    logger.handlers.clear()
    logger.addHandler(logging.NullHandler())
    logger.propagate = False
    return logger


# ══════════════════════════════════════════════════════════════════════════
# DEL B — TABELLER: CSV OG EXCEL UTEN PANDAS
# ══════════════════════════════════════════════════════════════════════════
#
# En tabell er en liste av ordbøker — én ordbok per rad, nøklene er
# kolonnenavnene. Excel-filer skrives og leses direkte fra zip-en: en .xlsx
# ER en zip med XML inni, og det trengs ikke mer enn hundre linjer for å
# lage en fil Excel åpner uten å klage.

Rad = Dict[str, Any]

# Excel skriver BOM foran CSV-er og forventer det tilbake. utf-8-sig gjør at
# æøå ser riktige ut både i Excel og i en vanlig teksteditor.
CSV_KODING = "utf-8-sig"


def les_csv(sti: Path) -> List[Rad]:
    """Alt leses som tekst. Tolkning av tall skjer der de brukes."""
    sti = Path(sti)
    if not sti.exists():
        return []
    try:
        with sti.open("r", encoding=CSV_KODING, newline="") as f:
            return [{(k or ""): (v if v is not None else "") for k, v in rad.items()}
                    for rad in csv.DictReader(f)]
    except (OSError, UnicodeDecodeError, csv.Error):
        return []


def skriv_csv(sti: Path, rader: Sequence[Rad],
              kolonner: Optional[Sequence[str]] = None) -> None:
    """Skriver atomisk. Kolonnerekkefølgen er kontrakten mot neste steg."""
    rader = list(rader)
    if kolonner is None:
        sett: List[str] = []
        for rad in rader:
            for k in rad:
                if k not in sett:
                    sett.append(k)
        kolonner = sett

    def gjør(p: Path) -> None:
        with p.open("w", encoding=CSV_KODING, newline="") as f:
            skriver = csv.DictWriter(f, fieldnames=list(kolonner),
                                     extrasaction="ignore", lineterminator="\n")
            skriver.writeheader()
            for rad in rader:
                skriver.writerow({k: _celletekst(rad.get(k, "")) for k in kolonner})

    skriv_atomisk(sti, gjør)


def tallstreng(v: float) -> str:
    """
    Korteste form som leser tilbake til NØYAKTIG samme tall, aldri i
    eksponentform.

    To feller på én gang. repr(6007042.98) gir «6007042.98», mens
    f"{v:.10f}" gir «6007042.9800000004» — ti desimaler er nok til å blottlegge
    at tallet aldri var eksakt. Og repr(0.000012) gir «1.2e-05», som er en
    felle for enhver som leser CSV-en igjen. Så: repr først, fast form bare
    når repr faller ned i eksponentform.
    """
    if v != v:                         # NaN
        return ""
    if v == int(v) and abs(v) < 1e15:
        return str(int(v))
    s = repr(float(v))
    if "e" in s or "E" in s:
        s = f"{v:.10f}".rstrip("0").rstrip(".")
    return s or "0"


def _celletekst(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "JA" if v else "NEI"
    if isinstance(v, float):
        return tallstreng(v)
    if isinstance(v, (date, datetime)):
        return iso(v if isinstance(v, date) else v.date())
    return str(v)


# ── LESE .xlsx ───────────────────────────────────────────────────────────

_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
_M = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_CELLE = re.compile(r"^([A-Z]+)(\d+)$")


def _kolonnenummer(ref: str) -> int:
    """«A» → 0, «B» → 1, «AA» → 26."""
    m = _CELLE.match(ref or "")
    bokstaver = m.group(1) if m else re.sub(r"[^A-Z]", "", (ref or "").upper())
    n = 0
    for c in bokstaver:
        n = n * 26 + (ord(c) - 64)
    return max(0, n - 1)


def _kolonnebokstav(n: int) -> str:
    """0 → «A», 26 → «AA»."""
    ut = ""
    n += 1
    while n:
        n, rest = divmod(n - 1, 26)
        ut = chr(65 + rest) + ut
    return ut


def _finn_ark(z: zipfile.ZipFile, navn: str) -> Optional[str]:
    """
    Stien til arket som heter `navn`. None når det ikke finnes.

    Arknavn står i xl/workbook.xml, men filnavnet på disk står i relasjons-
    filen ved siden av — rekkefølgen i zip-en stemmer ikke nødvendigvis med
    rekkefølgen i arkfanen, så vi kan ikke telle oss fram.
    """
    try:
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    except (KeyError, ET.ParseError):
        return None
    mål = {}
    for r in rels:
        mål[r.get("Id", "")] = str(r.get("Target", "")).lstrip("/")
    rid = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
    for ark in wb.iter(_M + "sheet"):
        if rens(ark.get("name", "")).lower() == rens(navn).lower():
            sti = mål.get(ark.get(rid, ""), "")
            if not sti:
                return None
            return sti if sti.startswith("xl/") else "xl/" + sti
    return None


# Excels innebygde formatnumre som betyr dato eller klokkeslett. 14-22 er
# de vanlige, 45-47 er varigheter, 27-36 og 50-58 er de østasiatiske
# kalenderne. Alt over 163 er egendefinert og må leses som formatkode.
_INNEBYGDE_DATOFORMAT = frozenset(
    list(range(14, 23)) + list(range(27, 37)) + [45, 46, 47] + list(range(50, 59)))


def _er_datoformat(kode: str) -> bool:
    """
    Betyr denne formatkoden en dato?

    Vi fjerner først alt som IKKE er formatbokstaver: tekst i hermetegn
    («"kr"»), hakeparenteser ([Red], [$-409]) og skråstrek-rømte tegn.
    Står det da igjen en y, m, d, h eller s, er cellen en dato eller et
    klokkeslett. «#,##0.00» og «0.0%» overlever ikke prøven, og skal ikke.
    """
    t = re.sub(r'"[^"]*"', "", kode or "")
    t = re.sub(r"\[[^\]]*\]", "", t)
    t = re.sub(r"\\.", "", t)
    t = t.replace("General", "")
    return bool(re.search(r"[yYmMdDhHsS]", t))


def _datostiler(z: zipfile.ZipFile) -> Set[int]:
    """
    Stilindeksene (cellens s-attributt) som betyr «denne cellen er en dato».

    Uten dette oppslaget er 45900 bare 45900. Med det er det 2025-08-31.
    """
    try:
        rot = ET.fromstring(z.read("xl/styles.xml"))
    except (KeyError, ET.ParseError, OSError):
        return set()
    egne: Dict[int, str] = {}
    for nf in rot.iter(_M + "numFmt"):
        try:
            egne[int(nf.get("numFmtId", "-1"))] = nf.get("formatCode", "")
        except (TypeError, ValueError):
            continue
    ut: Set[int] = set()
    xfs = rot.find("m:cellXfs", _NS)
    if xfs is None:
        return ut
    for i, xf in enumerate(xfs.findall("m:xf", _NS)):
        try:
            nid = int(xf.get("numFmtId", "0"))
        except (TypeError, ValueError):
            continue
        if nid in egne:
            if _er_datoformat(egne[nid]):
                ut.add(i)
        elif nid in _INNEBYGDE_DATOFORMAT:
            ut.add(i)
    return ut


def _bruker_1904(z: zipfile.ZipFile) -> bool:
    """Gamle Mac-arbeidsbøker teller dager fra 1904, ikke fra 1900."""
    try:
        wb = ET.fromstring(z.read("xl/workbook.xml"))
    except (KeyError, ET.ParseError, OSError):
        return False
    for pr in wb.iter(_M + "workbookPr"):
        if str(pr.get("date1904", "")).strip().lower() in ("1", "true"):
            return True
    return False


def les_xlsx_rader(sti: Path, maks_rader: int = 200_000,
                   ark_navn: str = "") -> List[List[str]]:
    """
    Rå rader fra et ark. Uten `ark_navn`: det første. Tomme celler → "" .

    Datoceller kommer ut som ÅÅÅÅ-MM-DD (med klokkeslett bak når cellen har
    et), ikke som Excels serienummer. Det er hele forskjellen på at en
    scorelogg fra pandas kan leses og at den stilltiende blir null rader.
    """
    with zipfile.ZipFile(Path(sti)) as z:
        delte: List[str] = []
        if "xl/sharedStrings.xml" in z.namelist():
            rot = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in rot.findall("m:si", _NS):
                delte.append("".join(t.text or "" for t in si.iter(_M + "t")))
        ark = _finn_ark(z, ark_navn) if ark_navn else None
        if ark_navn and ark is None:
            return []
        if ark is None:
            ark = next((n for n in z.namelist()
                        if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")), None)
        if not ark or ark not in z.namelist():
            return []
        rot = ET.fromstring(z.read(ark))
        datostil = _datostiler(z)
        dato1904 = _bruker_1904(z)

    ut: List[List[str]] = []
    for rad in rot.iter(_M + "row"):
        celler: Dict[int, str] = {}
        for c in rad.findall("m:c", _NS):
            nr = _kolonnenummer(c.get("r", ""))
            type_ = c.get("t", "")
            if type_ == "inlineStr":
                verdi = "".join(t.text or "" for t in c.iter(_M + "t"))
            else:
                v = c.find("m:v", _NS)
                verdi = v.text if v is not None and v.text else ""
                if type_ == "s" and verdi.isdigit():
                    i = int(verdi)
                    verdi = delte[i] if 0 <= i < len(delte) else ""
                elif verdi and type_ in ("", "n") and datostil:
                    # Et tall i en datoformatert celle ER en dato. Uten dette
                    # leddet leverer vi «45900» til en mottaker som venter
                    # ÅÅÅÅ-MM-DD, og raden forsvinner uten et ord.
                    s_nr = c.get("s") or ""
                    if s_nr.isdigit() and int(s_nr) in datostil:
                        dt = fra_excel_serienr(verdi, dato1904)
                        if dt is not None:
                            verdi = (iso(dt.date()) if not (dt.hour or dt.minute
                                                            or dt.second)
                                     else f"{iso(dt.date())} {dt:%H:%M:%S}")
            celler[nr] = rens(verdi)
        ut.append([celler.get(i, "") for i in range(max(celler) + 1)] if celler else [])
        if len(ut) >= maks_rader:
            break
    return ut


def xlsx_arknavn(sti: Path) -> List[str]:
    """
    Navnene på arkene i en .xlsx, i fanerekkefølge. Tom liste ved uleselig fil.

    Brukes til å velge FIL ut fra innhold og ikke ut fra alder: to kjøringer
    av samme modell kan skrive to filnavn som begge passer søkemønsteret, og
    bare den ene har arket vi trenger.
    """
    try:
        with zipfile.ZipFile(Path(sti)) as z:
            wb = ET.fromstring(z.read("xl/workbook.xml"))
    except (OSError, KeyError, zipfile.BadZipFile, ET.ParseError):
        return []
    return [rens(a.get("name", "")) for a in wb.iter(_M + "sheet")]


def har_xlsx_ark(sti: Path, navn: str) -> bool:
    """Finnes arket? Sammenlikningen er uten hensyn til store og små bokstaver."""
    ønsket = rens(navn).lower()
    return any(a.lower() == ønsket for a in xlsx_arknavn(sti))


def les_xlsx(sti: Path, overskriftsord: Sequence[str] = ("isin",),
             maks_leting: int = 15, ark_navn: str = "") -> List[Rad]:
    """
    Leser et ark og finner selv hvilken rad som er overskriften.

    Euronext-eksporten har metadata på rad 2-4 («European Equities», en dato,
    en fotnote). Uten overskriftsleting leses de som data.
    """
    rader = les_xlsx_rader(sti, ark_navn=ark_navn)
    if not rader:
        return []
    ønsket = {o.lower() for o in overskriftsord}
    hode_nr = 0
    for nr in range(min(maks_leting, len(rader))):
        if ønsket & {c.strip().lower() for c in rader[nr] if c}:
            hode_nr = nr
            break
    hode = [c.strip() or f"kol{i}" for i, c in enumerate(rader[hode_nr])]
    ut: List[Rad] = []
    for rad in rader[hode_nr + 1:]:
        if not any(c.strip() for c in rad):
            continue
        ut.append({hode[i]: (rad[i] if i < len(rad) else "") for i in range(len(hode))})
    return ut


# ── SKRIVE .xlsx ─────────────────────────────────────────────────────────
#
# Minimal, men ekte: frosset overskriftsrad, autofilter, tall som TALL (ikke
# tekst), så du kan sortere på Bullish_Score med ett klikk. Ingen openpyxl.

_XLSX_TYPER = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>"""

_XLSX_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""

_XLSX_WB_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

# To stiler: 0 = vanlig, 1 = fet (overskriftsraden).
_XLSX_STILER = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font>
<font><b/><sz val="11"/><name val="Calibri"/></font></fonts>
<fills count="2"><fill><patternFill patternType="none"/></fill>
<fill><patternFill patternType="gray125"/></fill></fills>
<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs>
</styleSheet>"""

_UGYLDIG_XML = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _xml_tekst(v: Any) -> str:
    return html_modul.escape(_UGYLDIG_XML.sub("", str(v)), quote=False)


def _xlsx_celle(ref: str, verdi: Any, stil: int = 0) -> str:
    s = f' s="{stil}"' if stil else ""
    if verdi is None or verdi == "":
        return f'<c r="{ref}"{s}/>'
    if isinstance(verdi, bool):
        verdi = "JA" if verdi else "NEI"
    elif isinstance(verdi, (int, float)):
        f = float(verdi)
        if f == f and abs(f) < 1e15:
            return f'<c r="{ref}"{s}><v>{tallstreng(f)}</v></c>'
        verdi = "" if f != f else str(verdi)
    return (f'<c r="{ref}" t="inlineStr"{s}><is><t xml:space="preserve">'
            f'{_xml_tekst(verdi)}</t></is></c>')


def skriv_xlsx(sti: Path, rader: Sequence[Rad],
               kolonner: Optional[Sequence[str]] = None,
               arknavn: str = "Data", tallkolonner: Sequence[str] = ()) -> None:
    """
    Skriver en ekte Excel-fil uten openpyxl.

    `tallkolonner` skrives som tall slik at Excel kan sortere og regne på
    dem. Alt annet blir tekst — en ISIN som «NO0010096985» skal ikke bli
    et tall, og en dato skal ikke bli et serienummer.
    """
    rader = list(rader)
    if kolonner is None:
        sett: List[str] = []
        for r in rader:
            for k in r:
                if k not in sett:
                    sett.append(k)
        kolonner = sett
    kolonner = list(kolonner)
    tall = {str(t) for t in tallkolonner}

    biter = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
             '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
             '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" '
             'topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>',
             '<sheetData>']
    biter.append('<row r="1">' + "".join(
        _xlsx_celle(f"{_kolonnebokstav(i)}1", k, 1) for i, k in enumerate(kolonner)) + "</row>")
    for nr, r in enumerate(rader, start=2):
        celler = []
        for i, k in enumerate(kolonner):
            v = r.get(k, "")
            if k in tall and not isinstance(v, (int, float)):
                v2 = tolk_maskin(v)
                v = v2 if v2 is not None else ""
            celler.append(_xlsx_celle(f"{_kolonnebokstav(i)}{nr}", v))
        biter.append(f'<row r="{nr}">' + "".join(celler) + "</row>")
    biter.append("</sheetData>")
    if kolonner:
        biter.append(f'<autoFilter ref="A1:{_kolonnebokstav(len(kolonner)-1)}'
                     f'{max(1, len(rader) + 1)}"/>')
    biter.append("</worksheet>")

    wb = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
          'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
          f'<sheets><sheet name="{_xml_tekst(arknavn[:31])}" sheetId="1" r:id="rId1"/></sheets>'
          '</workbook>')

    def gjør(p: Path) -> None:
        with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml", _XLSX_TYPER)
            z.writestr("_rels/.rels", _XLSX_RELS)
            z.writestr("xl/workbook.xml", wb)
            z.writestr("xl/_rels/workbook.xml.rels", _XLSX_WB_RELS)
            z.writestr("xl/styles.xml", _XLSX_STILER)
            z.writestr("xl/worksheets/sheet1.xml", "".join(biter))

    skriv_atomisk(sti, gjør)


def skriv_tabell(sti_csv: Path, sti_xlsx: Optional[Path], rader: Sequence[Rad],
                 kolonner: Sequence[str], logger: logging.Logger,
                 tallkolonner: Sequence[str] = (), arknavn: str = "Data") -> None:
    """CSV alltid, Excel i tillegg når det lar seg gjøre. Excel er valgfritt."""
    skriv_csv(sti_csv, rader, kolonner)
    logger.info(f"💾 {sti_csv.name}  ({len(rader)} rader)")
    if sti_xlsx is None:
        return
    try:
        skriv_xlsx(sti_xlsx, rader, kolonner, arknavn=arknavn, tallkolonner=tallkolonner)
        logger.info(f"💾 {sti_xlsx.name}  ({len(rader)} rader, sorterbar i Excel)")
    except Exception as e:
        logger.warning(f"   Klarte ikke skrive Excel-filen — {feiltekst(e)[:100]}. "
                       f"CSV-en er uansett skrevet.")


# ── SMÅHJELP ─────────────────────────────────────────────────────────────

def finn_kolonne(rad: Rad, *alias: str) -> Optional[str]:
    """Finner et kolonnenavn uansett store/små bokstaver og mellomrom."""
    kart = {str(k).strip().lower(): k for k in rad}
    for a in alias:
        if a.lower() in kart:
            return kart[a.lower()]
    return None


def unike(verdier: Iterable[Any]) -> List[Any]:
    sett, ut = set(), []
    for v in verdier:
        if v not in sett:
            sett.add(v)
            ut.append(v)
    return ut


# ══════════════════════════════════════════════════════════════════════════
# DEL C — VANNMERKER: «HVOR LANGT HAR JEG KOMMET?»
# ══════════════════════════════════════════════════════════════════════════
#
# I stedet for å skru nedlasting av og på for hånd, husker programmet per
# selskap og per ticker hvilken dato dataene er komplette til, og henter bare
# det som mangler neste gang. Tre regler gjør at det holder:
#
#   1  Et vannmerke betyr «jeg har komplette data TIL OG MED denne datoen»,
#      ikke «en kjøring skjedde». Det flyttes bare når hentingen lyktes.
#   2  Vi henter alltid med et OVERLAPP bakover. Euronext publiserer
#      rettelser og etternølere med eldre dato; uten overlapp ses de aldri.
#   3  Overlappet er samtidig en KONTROLLSUM for kurser: en splitt skriver om
#      hele historikken bakover, og stemmer ikke de overlappende dagene, er
#      serien omskrevet og hentes på nytt i sin helhet.

class Vannmerke:
    """Ett JSON-lager med en post per (gruppe, nøkkel)."""

    def __init__(self, sti: Path, logger: Optional[logging.Logger] = None):
        self.sti = Path(sti)
        self.logger = logger
        self._data: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._endret = False
        self._last()

    def _last(self) -> None:
        if not self.sti.exists():
            return
        try:
            rå = json.loads(self.sti.read_text(encoding="utf-8"))
            if isinstance(rå, dict):
                self._data = {g: dict(v) for g, v in rå.items() if isinstance(v, dict)}
        except (OSError, ValueError) as e:
            if self.logger:
                self.logger.warning(f"   Kunne ikke lese {self.sti.name} — {feiltekst(e)}. "
                                    f"Alt behandles som ikke hentet.")
            self._data = {}

    def post(self, gruppe: str, nokkel: str) -> Dict[str, Any]:
        return self._data.get(gruppe, {}).get(str(nokkel), {})

    def komplett_til(self, gruppe: str, nokkel: str) -> Optional[date]:
        return fra_iso(self.post(gruppe, nokkel).get("komplett_til"))

    def startdato(self, gruppe: str, nokkel: str, eldste: date,
                  overlapp_dager: int, full: bool = False) -> date:
        """Uten vannmerke, eller med --full: helt tilbake. Ellers: minus overlapp."""
        if full:
            return eldste
        til = self.komplett_til(gruppe, nokkel)
        if til is None:
            return eldste
        return max(eldste, til - timedelta(days=max(0, overlapp_dager)))

    def er_ajour(self, gruppe: str, nokkel: str, mål: date) -> bool:
        til = self.komplett_til(gruppe, nokkel)
        return til is not None and til >= mål

    def sett(self, gruppe: str, nokkel: str, komplett_til: date, **ekstra: Any) -> None:
        """Kalles BARE når hentingen lyktes. Ellers står det gamle igjen."""
        post = dict(self.post(gruppe, nokkel))
        gammel = fra_iso(post.get("komplett_til"))
        ny = komplett_til if gammel is None else max(gammel, komplett_til)
        post.update(ekstra)
        post["komplett_til"] = iso(ny)
        post["sist_ok"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        post.pop("siste_feil", None)
        self._data.setdefault(gruppe, {})[str(nokkel)] = post
        self._endret = True

    def merk_feil(self, gruppe: str, nokkel: str, grunn: str) -> None:
        """Registrerer feilen uten å flytte vannmerket."""
        post = dict(self.post(gruppe, nokkel))
        post["siste_feil"] = str(grunn)[:200]
        post["siste_feil_tid"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        self._data.setdefault(gruppe, {})[str(nokkel)] = post
        self._endret = True

    def nullstill(self, gruppe: str, nokkel: Optional[str] = None) -> None:
        if nokkel is None:
            self._data.pop(gruppe, None)
        else:
            self._data.get(gruppe, {}).pop(str(nokkel), None)
        self._endret = True

    def lagre(self, tving: bool = False) -> None:
        if not (self._endret or tving):
            return
        try:
            skriv_atomisk(self.sti, lambda p: p.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=1, sort_keys=True),
                encoding="utf-8"))
            self._endret = False
        except OSError as e:
            if self.logger:
                self.logger.warning(f"   Kunne ikke lagre vannmerket — {feiltekst(e)}")

    def oppsummering(self, gruppe: str) -> Dict[str, Any]:
        poster = self._data.get(gruppe, {})
        datoer = [d for d in (fra_iso(p.get("komplett_til")) for p in poster.values()) if d]
        return {"antall": len(poster),
                "eldste": min(datoer) if datoer else None,
                "nyeste": max(datoer) if datoer else None,
                "med_feil": sum(1 for p in poster.values() if p.get("siste_feil"))}


# ══════════════════════════════════════════════════════════════════════════
# DEL D — BØRSKALENDEREN
# ══════════════════════════════════════════════════════════════════════════
#
# Vi har ingen offisiell kalender for Oslo Børs, og trenger ingen: en dag der
# to hundre selskaper har sluttkurs ER en handledag. Terskelen luker bort
# enkeltdatoer som bare én ticker har — de skyldes som regel en feil hos
# datakilden, og hadde de sluppet inn, ville alle avkastningsvinduene
# forskjøvet seg med én dag.

def utled_handledager(datoer_per_ticker: Dict[str, Iterable[date]],
                      terskel: float = 0.20,
                      unntatt: Sequence[str] = ()) -> List[date]:
    """`unntatt` holder indekser utenfor: de beregnes, de handles ikke."""
    unntatt_sett = {str(u).upper() for u in unntatt}
    teller: Dict[date, int] = {}
    levetid: List[Tuple[date, date]] = []
    for ticker, datoer in datoer_per_ticker.items():
        if str(ticker).upper() in unntatt_sett:
            continue
        d_sett = set(datoer)
        if not d_sett:
            continue
        levetid.append((min(d_sett), max(d_sett)))
        for d in d_sett:
            teller[d] = teller.get(d, 0) + 1
    if not teller:
        return []

    # Terskelen måles mot tickerne som FANTES den dagen, ikke mot alle.
    #
    # Dette var feilen som gjorde kalenderen ni dager lang: 241 av 269 serier
    # hadde bare de siste ti dagene, og da klarte ingen eldre dato å samle
    # 20 % av 269. Resultatet var at ti år med meldinger ble stemplet FOR_NY
    # mot en kalender som begynte forrige uke. Et selskap som ble notert i
    # fjor kan ikke stemme over om 2019 hadde børsdager.
    levende: Dict[date, int] = {}
    for d in teller:
        levende[d] = sum(1 for f, si in levetid if f <= d <= si)
    return sorted(d for d, n in teller.items()
                  if n >= max(1, int(levende.get(d, 0) * float(terskel))))


class Kalender:
    """Sortert liste av handledager, med raskt oppslag."""

    def __init__(self, dager: Sequence[date], stengetid: str = "16:20"):
        self.dager: List[date] = sorted(set(dager))
        self.stengetid = stengetid
        self._grense = tolk_klokkeslett(stengetid) or klokke(16, 20)
        self._pos: Dict[date, int] = {d: i for i, d in enumerate(self.dager)}

    def __len__(self) -> int:
        return len(self.dager)

    def __bool__(self) -> bool:
        return bool(self.dager)

    @property
    def forste(self) -> Optional[date]:
        return self.dager[0] if self.dager else None

    @property
    def siste(self) -> Optional[date]:
        return self.dager[-1] if self.dager else None

    def posisjon(self, d: date) -> Optional[int]:
        return self._pos.get(d)

    def dag(self, i: int) -> Optional[date]:
        return self.dager[i] if 0 <= i < len(self.dager) else None

    def neste_handledag(self, d: date, inklusiv: bool = True) -> Optional[date]:
        i = (bisect.bisect_left(self.dager, d) if inklusiv
             else bisect.bisect_right(self.dager, d))
        return self.dager[i] if i < len(self.dager) else None

    def forste_handledag(self, meldingsdato: Any, klokkeslett: Any) -> Optional[date]:
        """
        Første dag meldingen faktisk kan handles på sluttkurs.

        Hele forsvaret mot look-ahead, og det er to tilfeller:
            publisert FØR 16:20           → samme dag, hvis den er handledag
            publisert 16:20 eller senere  → første handledag ETTER meldingsdagen

        Mangler klokkeslettet, antar vi det verste: at meldingen kom etter
        stengetid. Det koster en dags avkastning, og det er riktig vei å
        bomme — antar du det motsatte, kjøper du på informasjon du ikke
        hadde, og backtesten måler en gevinst som ikke fantes.
        """
        d = tolk_dato(meldingsdato)
        if d is None or not self.dager:
            return None
        kl = tolk_klokkeslett(klokkeslett)
        etter_stengetid = kl is None or kl >= self._grense
        return self.neste_handledag(d, inklusiv=not etter_stengetid)

    def etter_stengetid(self, klokkeslett: Any) -> bool:
        kl = tolk_klokkeslett(klokkeslett)
        return kl is None or kl >= self._grense

    def forskyv(self, d: date, handledager: int) -> Optional[date]:
        i = self.posisjon(d)
        return None if i is None else self.dag(i + handledager)


# ══════════════════════════════════════════════════════════════════════════
# DEL E — STATISTIKK
# ══════════════════════════════════════════════════════════════════════════
#
# Det viktigste her er ikke gjennomsnittet — det er FEILMARGINEN. Regner du
# den som om hver hendelse var uavhengig, blir den for liten, t-verdien for
# pen, og en tilfeldighet ser ut som et funn. Og hendelsene her er alt annet
# enn uavhengige: tre innsidekjøp i samme selskap samme uke er én historie
# fortalt tre ganger, og en dag der hele børsen faller drar alle hendelsene
# den dagen i samme retning.

NAN = float("nan")


def snitt(x: Sequence[float]) -> float:
    return sum(x) / len(x) if x else NAN


def median(x: Sequence[float]) -> float:
    if not x:
        return NAN
    s = sorted(x)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0


def andel_over_null(x: Sequence[float]) -> float:
    return sum(1 for v in x if v > 0) / len(x) if x else NAN


def standardavvik(x: Sequence[float]) -> float:
    if len(x) < 2:
        return NAN
    m = snitt(x)
    return math.sqrt(sum((v - m) ** 2 for v in x) / (len(x) - 1))


def klyngevarians(verdier: Sequence[float], grupper: Sequence[Any]) -> float:
    """
    Varians til gjennomsnittet når observasjoner i samme klynge henger sammen.

    Sandwich-estimatoren for en regresjon på bare et konstantledd: summer
    residualene innenfor hver klynge, kvadrer summene, del på n².
    """
    x = [float(v) for v in verdier]
    n = len(x)
    if n < 2:
        return NAN
    m = sum(x) / n
    per: Dict[Any, float] = {}
    for verdi, g in zip(x, grupper):
        per[g] = per.get(g, 0.0) + (verdi - m)
    g_antall = len(per)
    if g_antall < 2:
        return NAN
    justering = g_antall / (g_antall - 1.0)     # med få klynger undervurderer den
    return justering * sum(s * s for s in per.values()) / (n * n)


def toveis_klyngefeil(verdier: Sequence[float], klynge_a: Sequence[Any],
                      klynge_b: Sequence[Any]) -> Tuple[float, str]:
    """
    Standardfeil som tar høyde for BEGGE avhengighetene samtidig.

    Cameron-Gelbach-Miller: Var = Var(A) + Var(B) − Var(A∩B). Her er A
    selskap og B dato, så både «samme selskap flere ganger» og «samme dag
    over hele børsen» er dekket. Summen kan bli negativ i små utvalg — en
    kjent svakhet ved metoden, ikke en feil i dataene — og da faller vi
    tilbake på den strengeste enveis-varianten og sier fra.
    """
    va = klyngevarians(verdier, klynge_a)
    vb = klyngevarians(verdier, klynge_b)
    vab = klyngevarians(verdier, [f"{a}|{b}" for a, b in zip(klynge_a, klynge_b)])
    if any(v != v for v in (va, vb, vab)):
        enkel = va if va == va else vb
        return ((math.sqrt(enkel) if enkel == enkel and enkel > 0 else NAN), "enveis")
    samlet = va + vb - vab
    if samlet <= 0:
        strengest = max(va, vb)
        return ((math.sqrt(strengest) if strengest > 0 else NAN),
                "enveis (toveis ble negativ)")
    return math.sqrt(samlet), "toveis"


def bootstrap_ki(verdier: Sequence[float], grupper: Sequence[Any],
                 runder: int = 2000, fro: int = 0,
                 niva: float = 0.95) -> Tuple[float, float]:
    """
    Konfidensintervall ved å trekke om igjen SELSKAPER, ikke hendelser.

    Avkastninger har tunge haler, så et intervall bygget på
    normalfordelingen er for smalt i endene. Det er selskapene som trekkes,
    med alle hendelsene sine samlet — trakk vi enkelthendelser, ville vi
    latt som om de var uavhengige.
    """
    import random as _rnd
    per: Dict[Any, List[float]] = {}
    for verdi, g in zip(verdier, grupper):
        per.setdefault(g, []).append(float(verdi))
    nokler = list(per)
    g = len(nokler)
    if g < 5:
        return NAN, NAN
    summer = [sum(per[k]) for k in nokler]
    antall = [len(per[k]) for k in nokler]

    rng = _rnd.Random(fro)
    snitter: List[float] = []
    for _ in range(runder):
        s, a = 0.0, 0
        for _ in range(g):
            i = rng.randrange(g)
            s += summer[i]
            a += antall[i]
        if a:
            snitter.append(s / a)
    if not snitter:
        return NAN, NAN
    snitter.sort()

    def persentil(p: float) -> float:
        i = min(len(snitter) - 1, max(0, int(round(p / 100.0 * (len(snitter) - 1)))))
        return snitter[i]

    lav = (1.0 - niva) / 2.0 * 100.0
    return persentil(lav), persentil(100.0 - lav)


def nokkeltall(equity: Sequence[float], risikofri_pst: float = 3.0,
               dager_per_ar: int = 252) -> Dict[str, float]:
    """CAGR, Sharpe, Sortino, max drawdown og andel dager opp."""
    ut = {k: NAN for k in ("CAGR", "Sharpe", "Sortino", "MaxDD",
                           "AndelDagerOpp", "Slutt", "Volatilitet")}
    verdier = [float(v) for v in equity if v == v and v > 0]
    if len(verdier) < 3:
        return ut

    start, slutt = verdier[0], verdier[-1]
    ut["Slutt"] = slutt
    ar = len(verdier) / float(dager_per_ar)
    if ar > 0 and start > 0:
        ut["CAGR"] = (slutt / start) ** (1.0 / ar) - 1.0

    avk = [verdier[i] / verdier[i - 1] - 1.0 for i in range(1, len(verdier))]
    if not avk:
        return ut
    m = snitt(avk)
    rf_daglig = (1.0 + risikofri_pst / 100.0) ** (1.0 / dager_per_ar) - 1.0

    sd = standardavvik(avk)
    if sd == sd and sd > 0:
        ut["Volatilitet"] = sd * math.sqrt(dager_per_ar)
        ut["Sharpe"] = (m - rf_daglig) / sd * math.sqrt(dager_per_ar)

    nedside = [a - rf_daglig for a in avk if a < rf_daglig]
    if nedside:
        ned = math.sqrt(sum(a * a for a in nedside) / len(nedside))
        if ned > 0:
            ut["Sortino"] = (m - rf_daglig) / ned * math.sqrt(dager_per_ar)

    topp, verste = verdier[0], 0.0
    for v in verdier:
        topp = max(topp, v)
        if topp > 0:
            verste = min(verste, v / topp - 1.0)
    ut["MaxDD"] = verste
    ut["AndelDagerOpp"] = sum(1 for a in avk if a > 0) / float(len(avk))
    return ut


def boetter(verdier: Sequence[float], antall: int = 5) -> List[float]:
    """Grensene som deler i `antall` like store grupper."""
    x = sorted(v for v in verdier if v == v)
    if len(x) < antall * 4:
        return []
    return [x[int(len(x) * (i + 1) / antall)] for i in range(antall - 1)]


def bøttemerke(v: float, grenser: Sequence[float], navn: str = "Q") -> str:
    if not grenser or v != v:
        return ""
    for i, g in enumerate(grenser):
        if v <= g:
            return f"{navn}{i + 1}"
    return f"{navn}{len(grenser) + 1}"


# ══════════════════════════════════════════════════════════════════════════
# DEL F — LES MELDINGEN: KJØP ELLER SALG, HVEM, HVOR MYE
# ══════════════════════════════════════════════════════════════════════════
#
# Uten denne delen behandles et innsideSALG som et innsideKJØP, og omtrent
# halvparten av signalene peker motsatt vei av det rapporten påstår.
#
# Meldingene følger EUs markedsmisbruksforordning artikkel 19, så de har en
# gjenkjennelig form:
#
#     4) Opplysninger om transaksjonen(e)
#     a) Beskrivelse av det finansielle instrumentet: Aksjer
#     b) Transaksjonens art: Kjøp av aksjer
#     c) Pris(er) og volum(er):   Pris: NOK 123,45   Volum: 5 000
#     e) Dato for transaksjonen: 2024-05-13
#
# Men langt fra alle er så snille. Derfor leses de i tre lag, fra sikrest til
# løsest, og det sikreste laget vinner:
#
#     LAG 1   merkelappen «Transaksjonens art» / «Nature of the transaction»
#     LAG 2   fritekst: «har kjøpt 5 000 aksjer til kurs 123,45»
#     LAG 3   regnestykket: gikk beholdningen opp eller ned?
#
# Over alt dette står én regel: VI GJETTER ALDRI. Kommer vi ikke fram til et
# svar vi kan stå for, blir meldingen UKJENT. En melding uten retning er et
# hull i statistikken. En melding med FEIL retning er gift.

KJOP_ORD = ("acquisition", "acquire", "acquired", "acquires", "purchase", "purchased",
            "purchases", "bought", "buy", "buys", "subscription", "subscribed",
            "erverv", "ervervet", "kjøp", "kjøpt", "kjoper", "kjøper", "tegning",
            "tegnet", "tegner", "økning", "increase")

SALG_ORD = ("disposal", "dispose", "disposed", "disposes", "sale", "sold", "sell",
            "sells", "selling", "avhendelse", "avhendet", "salg", "solgt", "selger",
            "nedsalg", "reduksjon", "decrease")

AKSJE_ORD = ("share", "shares", "ordinary share", "ordinary shares", "equity",
             "aksje", "aksjer", "stamaksje", "stamaksjer", "egenkapitalbevis")

OPSJON_ORD = ("option", "options", "opsjon", "opsjoner", "warrant", "warrants",
              "subscription right", "subscription rights", "tegningsrett",
              "tegningsretter", "convertible", "konvertibelt", "synthetic share",
              "syntetisk aksje", "phantom share")

RSU_ORD = ("restricted stock unit", "restricted share unit", "rsu", "rsus", "psu",
           "psus", "performance share unit", "performance share", "performance stock",
           "betinget aksje", "betingede aksjer", "matching share", "matching shares")

# Ting som IKKE er en frivillig handel i markedet. Personen valgte ikke
# tidspunktet, eller betalte ikke markedspris. En innvinning er en kalender,
# ikke en beslutning — og fordi de skjer på de samme datoene hvert år,
# klumper de seg og lurer statistikken til å se mønstre som bare er lønn.
UTELUKK: Dict[str, Tuple[str, ...]] = {
    "VESTING": ("vesting", "vested", "vest of", "innvinning", "innvunnet",
                "innvinnes", "release of shares", "utdeling av aksjer",
                "settlement of rsu", "settlement of psu", "oppgjør av rsu"),
    "RSU": RSU_ORD,
    "OPSJON": ("option grant", "grant of option", "granted options",
               "tildeling av opsjoner", "tildelte opsjoner", "exercise of option",
               "exercised options", "innløsning av opsjon", "innløste opsjoner",
               "utøvelse av opsjoner", "opsjonsprogram", "option programme",
               "option program"),
    "PROGRAM": ("share savings", "share saving", "savings scheme", "spareprogram",
                "aksjespareprogram", "aksjespareordning", "employee share purchase",
                "employee stock purchase", "ansatteaksje", "ansattaksje",
                "employee share programme", "employee share program",
                "share purchase plan", "incentive scheme", "insentivprogram",
                "bonusaksjer", "bonus shares", "gratisaksjer", "free shares",
                "quarterly allocation to employees", "shares allocated to employees"),
    "UTBYTTEAKSJER": ("dividend in shares", "scrip dividend", "utbytte i aksjer",
                      "aksjeutbytte i form av aksjer"),
    "FUSJON": ("merger consideration", "demerger", "fusjonsvederlag", "fisjon",
               "vederlagsaksjer", "consideration shares"),
    "INTERN": ("transfer between", "internal transfer", "overføring mellom",
               "intern overføring", "transferred to a company controlled",
               "overført til eget selskap", "no change in beneficial ownership",
               "ingen endring i reelt eierskap"),
    "GAVE": ("gift", "gave", "inheritance", "arv", "donation", "donasjon"),
    "PANT": ("pledge", "pledged", "pantsatt", "pantsettelse", "collateral",
             "sikkerhetsstillelse", "lending of shares", "utlån av aksjer"),
    "TILBAKEKJOP": ("own shares", "egne aksjer", "buy-back", "buyback",
                    "tilbakekjøp", "share repurchase", "repurchase of shares"),
    "SKATTESALG": ("sold to cover tax", "sale to cover tax", "cover the tax",
                   "salg for å dekke skatt", "dekke skattetrekk", "net settlement",
                   "sell to cover"),
}

# Emisjoner: personen betalte ekte penger, men selskapet valgte tidspunktet.
# Egen merkelapp, ikke slått sammen med de andre — se `ta_med_emisjoner`.
EMISJON_ORD = ("rights issue", "private placement", "directed issue", "share issue",
               "rettet emisjon", "fortrinnsrettsemisjon", "reparasjonsemisjon",
               "emisjon", "subscription in the private placement",
               "allocation in the private placement", "repair offering")

# Rangeringen er nærhet til tallene. Forskningen finner gjennomgående at
# kjøp fra konsernsjef og finansdirektør bærer mest informasjon.
ROLLER: Sequence[Tuple[int, str, Tuple[str, ...]]] = (
    (1, "CEO", ("chief executive", "ceo", "administrerende direktør", "adm. dir",
                "adm.dir", "konsernsjef", "daglig leder", "managing director")),
    (2, "CFO", ("chief financial", "cfo", "finansdirektør", "økonomidirektør",
                "group cfo")),
    (3, "LEDELSE", ("chief operating", "coo", "chief technology", "cto",
                    "chief commercial", "cco", "chief investment", "cio",
                    "executive vice president", "evp", "senior vice president", "svp",
                    "chief ", "konserndirektør", "direktør", "ledergruppen",
                    "konsernledelsen", "group management", "executive management",
                    "head of")),
    (4, "STYRELEDER", ("chair of the board", "chairman", "chairperson", "chair ",
                       "styreleder", "styrets leder")),
    (5, "STYRE", ("board member", "member of the board", "board of directors",
                  "styremedlem", "styret", "varamedlem", "deputy board",
                  "non-executive director", "director")),
)

NAERSTAAENDE_ORD = ("closely associated", "close associate", "closely-associated",
                    "nærstående", "naerstaaende", "person closely associated",
                    "primærinnsiders nærstående", "related party of")

LABEL_ART = ("nature of the transaction", "nature of transaction",
             "type of transaction", "transaction type", "transaksjonens art",
             "type transaksjon", "transaksjonstype", "handelstype", "art")
LABEL_INSTRUMENT = ("description of the financial instrument", "financial instrument",
                    "type of instrument", "instrument type", "instrument",
                    "beskrivelse av det finansielle instrumentet",
                    "finansielt instrument", "instrumenttype")
LABEL_VOLUM = ("volume", "volumes", "volum", "number of shares", "no. of shares",
               "antall aksjer", "quantity", "antall", "aggregated volume",
               "samlet volum", "aggregert volum")
LABEL_PRIS = ("price per share", "kurs per aksje", "average price", "gjennomsnittskurs",
              "gjennomsnittlig kurs", "volume weighted average price", "vwap",
              "aggregated price", "prices", "price", "priser", "pris", "kurs")
LABEL_BEHOLDNING = ("holding after the transaction", "holdings after the transaction",
                    "shareholding after the transaction", "new holding",
                    "new shareholding", "total holding after", "holding after",
                    "beholdning etter transaksjonen", "aksjebeholdning etter",
                    "ny beholdning", "samlet beholdning etter", "beholdning etter",
                    "eier etter transaksjonen")
LABEL_BEHOLDNING_FOR = ("holding before the transaction", "shareholding before",
                        "previous holding", "holding before",
                        "beholdning før transaksjonen", "beholdning før",
                        "tidligere beholdning")
LABEL_NAVN = ("name", "navn")
LABEL_ROLLE = ("position/status", "position / status", "position", "status",
               "stilling/status", "stilling", "rolle", "role",
               "reason for the notification", "reason for responsibility",
               "årsak til meldeplikten", "grunnlag for meldeplikt")
LABEL_DATO = ("date of the transaction", "date of transaction", "transaction date",
              "dato for transaksjonen", "transaksjonsdato", "handelsdato")

AGGREGAT_ORD = ("aggregated", "aggregert", "samlet", "totalt", "total")


@dataclass
class Transaksjon:
    """Én linje i meldingen. En melding kan ha flere."""
    linje_nr: int = 0
    retning: str = "UKJENT"            # KJOP | SALG | UKJENT
    instrument: str = "UKJENT"         # AKSJE | OPSJON | RSU | ANNET | UKJENT
    instrument_tekst: str = ""
    antall: Optional[int] = None
    kurs: Optional[float] = None
    valuta: str = ""
    verdi: Optional[float] = None
    dato: str = ""
    regel: str = ""
    utdrag: str = ""


@dataclass
class Uttrekk:
    """Resultatet for én melding."""
    klasse: str = "UKJENT"             # KJOP | SALG | IGNORERT | UKJENT
    grunn: str = ""
    tillit: str = "LAV"                # HOY | MIDDELS | LAV
    metode: str = ""

    person: str = ""
    rolle: str = "UKJENT"
    rolle_rang: int = 9
    naerstaaende: str = "NEI"

    antall_netto: Optional[int] = None
    kurs_snitt: Optional[float] = None
    valuta: str = ""
    verdi: Optional[float] = None

    beholdning_for: Optional[int] = None
    beholdning_etter: Optional[int] = None
    okning_pst: Optional[float] = None
    ny_posisjon: str = "NEI"

    transaksjonsdato: str = ""
    antall_linjer: int = 0
    kontroll: str = ""                 # OK | AVVIK | MANGLER
    emisjon: str = "NEI"
    transaksjoner: List[Transaksjon] = field(default_factory=list)


def _liten(t: Any) -> str:
    return normaliser_tegn(str(t or "")).lower()


def _inneholder(tekst_liten: str, ord_: Sequence[str]) -> Optional[str]:
    """Første ord fra lista som finnes i teksten. Hele ord der det gir mening."""
    for o in ord_:
        o = o.lower()
        if " " in o or not o.isalpha():
            if o in tekst_liten:
                return o
        elif re.search(rf"(?<![a-zæøå]){re.escape(o)}(?![a-zæøå])", tekst_liten):
            return o
    return None


_LABEL_SLUTT = re.compile(r"[\n\r]|(?:\s{3,})|(?:\s*[;|]\s*)")


def _merkelapp_treff(liten: str, label: str) -> Iterator[Any]:
    """
    Hvert sted merkelappen står med verdien rett etter.

    Skilletegnet er kolon ELLER linjeskift, og linjeskiftet er ikke en
    detalj: MAR-skjemaet er en HTML-TABELL, og når en tabell leses som tekst
    havner hver celle på sin egen linje uten kolon:

        Nature of transaction
        Purchase of shares
        Volume
        1035

    Den gamle regelen krevde «merkelapp:» og fant følgelig ingenting i noen
    av dem — meldingen var lest, men ingen tall kom ut, og hendelsen ble
    UKJENT.

    Linjeskift godtas bare når merkelappen er ALT som står på linja. Ellers
    ville et avsnitt som tilfeldigvis slutter på «… price» stjålet neste
    linje som verdi, og et påstått beløp er verre enn ingen beløp.
    """
    møn = (rf"(?<![a-zæøå]){re.escape(label.lower())}"
           r"[ \t]*(?:[:\-–]+[ \t]*(?:\r?\n[ \t]*)?|\r?\n[ \t]*)")
    for m in re.finditer(møn, liten):
        skille = liten[m.start():m.end()]
        if "\n" in skille and not re.search(r"[:\-–]", skille):
            linjestart = liten.rfind("\n", 0, m.start()) + 1
            if liten[linjestart:m.start()].strip():
                continue                  # merkelappen er ikke hele linja
        yield m


def finn_verdi(tekst: str, labels: Sequence[str], maks_lengde: int = 120) -> str:
    """
    Henter verdien som står etter «merkelapp:».

    Leter etter den LENGSTE merkelappen først, slik at «price per share»
    vinner over «price». Verdien slutter ved linjeskift, tre mellomrom (en
    tabellkolonne), eller neste merkelapp.
    """
    liten = _liten(tekst)
    for label in sorted(labels, key=len, reverse=True):
        for m in _merkelapp_treff(liten, label):
            rest = tekst[m.end(): m.end() + maks_lengde]
            stopp = _LABEL_SLUTT.search(rest)
            verdi = rens(rest[: stopp.start()] if stopp else rest)
            if verdi:
                return verdi
    return ""


def klassifiser_instrument(tekst: str) -> Tuple[str, str]:
    """(gruppe, råtekst). RSU og opsjon sjekkes FØR aksje — «RSU shares»."""
    t = _liten(tekst)
    if not t:
        return "UKJENT", ""
    if _inneholder(t, RSU_ORD):
        return "RSU", rens(tekst)
    if _inneholder(t, OPSJON_ORD):
        return "OPSJON", rens(tekst)
    if _inneholder(t, AKSJE_ORD):
        return "AKSJE", rens(tekst)
    return "ANNET", rens(tekst)


def retning_fra_ord(tekst: str) -> str:
    """
    KJOP, SALG eller UKJENT ut fra ordene i teksten.

    Står begge deler, teller det hvilket som kommer FØRST — «Purchase of
    shares (no shares sold)» er et kjøp.
    """
    t = _liten(tekst)
    if not t:
        return "UKJENT"
    kjop = min((t.find(o) for o in KJOP_ORD if o in t), default=-1)
    salg = min((t.find(o) for o in SALG_ORD if o in t), default=-1)
    if kjop < 0 and salg < 0:
        return "UKJENT"
    if kjop < 0:
        return "SALG"
    if salg < 0:
        return "KJOP"
    return "KJOP" if kjop < salg else "SALG"


def finn_rolle(tekst: str) -> Tuple[str, int, bool]:
    """(rolle, rang, nærstående)."""
    t = _liten(tekst)
    naer = bool(_inneholder(t, NAERSTAAENDE_ORD))
    for rang, navn, ord_ in ROLLER:
        if _inneholder(t, ord_):
            # En nærstående handler ikke selv, men på vegne av en innsider.
            # Signalet er svakere, uansett hvilken rolle innsideren har.
            return (navn, 6 if naer else rang, naer)
    return ("NAERSTAAENDE" if naer else "UKJENT", 6 if naer else 9, naer)


def _blokker(tekst: str) -> List[str]:
    """
    Deler meldingen i én blokk per «Transaksjonens art».

    En melding kan inneholde flere transaksjoner — typisk «kjøpt 10 000» og
    «solgt 2 000 for å dekke skatt». Leser vi bare den første, får vi feil
    fortegn og feil beløp.
    """
    liten = _liten(tekst)
    start: List[int] = []
    for label in LABEL_ART:
        if label == "art":              # for kort alene, gir falske treff
            continue
        for m in _merkelapp_treff(liten, label):
            start.append(m.start())
    if not start:
        return []
    start = sorted(set(start))
    return [tekst[s: (start[i + 1] if i + 1 < len(start) else len(tekst))]
            for i, s in enumerate(start)]


_PAR_PRIS_VOLUM = re.compile(
    r"(?:pris|price|kurs)\s*[:\-–]?\s*(?:nok|kr|eur|usd|sek|dkk)?\s*"
    r"([\d][\d .,]*\d|\d)[^\n\d]{0,40}?"
    r"(?:volum|volume|antall|quantity)\s*[:\-–]?\s*([\d][\d .,]*\d|\d)", re.IGNORECASE)
_PAR_VOLUM_PRIS = re.compile(
    r"(?:volum|volume|antall|quantity)\s*[:\-–]?\s*([\d][\d .,]*\d|\d)[^\n\d]{0,40}?"
    r"(?:pris|price|kurs)\s*[:\-–]?\s*(?:nok|kr|eur|usd|sek|dkk)?\s*"
    r"([\d][\d .,]*\d|\d)", re.IGNORECASE)


def _pris_volum_par(blokk: str, konv: str = "") -> List[Tuple[Optional[float], Optional[int]]]:
    """
    Alle (kurs, antall)-par i blokken. Tre skrivemåter finnes i praksis:
        Pris: NOK 123,45   Volum: 5 000
        Volum: 5 000       Pris: NOK 123,45
        Pris        Volum
        NOK 123,45  5 000
    «Aggregert» hoppes over når vi har enkeltlinjer — ellers telles de samme
    aksjene to ganger.
    """
    par: List[Tuple[int, Optional[float], Optional[int]]] = []
    for m in _PAR_PRIS_VOLUM.finditer(blokk):
        par.append((m.start(), tolk_tall(m.group(1), konvensjon=konv),
                    tolk_heltall(m.group(2), konvensjon=konv)))
    for m in _PAR_VOLUM_PRIS.finditer(blokk):
        if any(abs(p[0] - m.start()) < 5 for p in par):
            continue
        par.append((m.start(), tolk_tall(m.group(2), konvensjon=konv),
                    tolk_heltall(m.group(1), konvensjon=konv)))

    if par:
        ekte = [(k, a) for s, k, a in sorted(par)
                if not _inneholder(_liten(blokk[max(0, s - 60):s]), AGGREGAT_ORD)]
        return ekte if ekte else [(k, a) for _, k, a in sorted(par)]

    linjer = blokk.splitlines()
    ut: List[Tuple[Optional[float], Optional[int]]] = []
    tabell = any(_inneholder(_liten(l), ("pris", "price", "kurs")) and
                 _inneholder(_liten(l), ("volum", "volume", "antall")) for l in linjer)
    if tabell:
        for l in linjer:
            tall = re.findall(r"[\d][\d .,]*\d|\d", l)
            if len(tall) == 2 and not re.search(r"[a-zæøå]{4,}", _liten(l).replace("nok", "")):
                ut.append((tolk_tall(tall[0], konvensjon=konv),
                           tolk_heltall(tall[1], konvensjon=konv)))
    if ut:
        return ut

    volum = tolk_heltall(finn_verdi(blokk, LABEL_VOLUM), konvensjon=konv)
    pris = tolk_tall(finn_verdi(blokk, LABEL_PRIS), konvensjon=konv)
    return [(pris, volum)] if (volum is not None or pris is not None) else []


def les_med_merkelapper(tekst: str, konv: str = "") -> List[Transaksjon]:
    """LAG 1 — den autoritative lesningen."""
    ut: List[Transaksjon] = []
    for blokk in _blokker(tekst):
        art = finn_verdi(blokk, LABEL_ART) or blokk[:160]
        retning = retning_fra_ord(art)
        instrument_tekst = finn_verdi(blokk, LABEL_INSTRUMENT)
        gruppe, rå_instr = klassifiser_instrument(instrument_tekst or art)
        dato = tolk_dato(finn_verdi(blokk, LABEL_DATO))
        _, valuta = tolk_belop(finn_verdi(blokk, LABEL_PRIS) or blokk[:200])
        for kurs, antall in (_pris_volum_par(blokk, konv) or [(None, None)]):
            ut.append(Transaksjon(
                linje_nr=len(ut) + 1, retning=retning, instrument=gruppe,
                instrument_tekst=rå_instr, antall=antall, kurs=kurs, valuta=valuta,
                verdi=(kurs * antall) if (kurs and antall) else None,
                dato=iso(dato), regel="MERKELAPP", utdrag=rens(blokk)[:300]))
    return ut


_FRITEKST = re.compile(
    r"(?P<verb>" + "|".join(sorted(set(KJOP_ORD + SALG_ORD), key=len, reverse=True)) + r")"
    r"[^.;\n]{0,120}?(?P<antall>[\d][\d .,]*\d|\d)\s*"
    r"(?P<hva>shares|aksjer|share|aksje|options|opsjoner|rsus?|psus?)", re.IGNORECASE)

_PRIS_ETTER = re.compile(
    r"(?:at\s+(?:an?\s+)?(?:average\s+|volume[- ]weighted\s+average\s+)?price\s+of"
    r"|for\s+a\s+price\s+of|price\s+of|til\s+(?:en\s+)?(?:gjennomsnittlig\s+|gjennomsnitts)?kurs"
    r"(?:\s+(?:på|av))?|til\s+kurs|til\s+en\s+kurs\s+på|a\s+NOK|à\s*NOK)"
    r"\s*(?:nok|kr|eur|usd|sek|dkk)?\s*(?P<kurs>[\d][\d .,]*\d|\d)", re.IGNORECASE)


def les_fritekst(tekst: str, konv: str = "") -> List[Transaksjon]:
    """LAG 2 — «har kjøpt 5 000 aksjer til kurs NOK 123,45»."""
    ut: List[Transaksjon] = []
    for m in _FRITEKST.finditer(tekst):
        retning = retning_fra_ord(m.group("verb"))
        if retning == "UKJENT":
            continue
        gruppe, rå_instr = klassifiser_instrument(m.group("hva"))
        antall = tolk_heltall(m.group("antall"), konvensjon=konv)
        hale = tekst[m.end(): m.end() + 160]
        pm = _PRIS_ETTER.search(hale)
        kurs = tolk_tall(pm.group("kurs"), konvensjon=konv) if pm else None
        _, valuta = tolk_belop(hale[:80])
        ut.append(Transaksjon(
            linje_nr=len(ut) + 1, retning=retning, instrument=gruppe,
            instrument_tekst=rå_instr, antall=antall, kurs=kurs, valuta=valuta,
            verdi=(kurs * antall) if (kurs and antall) else None, regel="FRITEKST",
            utdrag=rens(tekst[max(0, m.start() - 40): m.end() + 120])[:300]))
    return ut


_BEHOLDNING_FRITEKST = re.compile(
    r"(?:new\s+|total\s+|remaining\s+|ny\s+|samlet\s+|resterende\s+)?"
    r"(?:holding|shareholding|beholdning|aksjebeholdning|eierandel)"
    r"[^.\n]{0,60}?(?P<antall>[\d][\d .,]*\d|\d)\s*(?:shares|aksjer)?", re.IGNORECASE)
_EIER_ETTER = re.compile(
    r"(?:eier|owns?|holds?|innehar|har)\s+(?:deretter\s+|etter\s+dette\s+|now\s+)?"
    r"(?P<antall>[\d][\d .,]*\d|\d)\s*(?:shares|aksjer)", re.IGNORECASE)


def finn_beholdning(tekst: str, konv: str = "") -> Tuple[Optional[int], Optional[int]]:
    """(før, etter). Merkelapp først, så fritekst."""
    etter = tolk_heltall(finn_verdi(tekst, LABEL_BEHOLDNING), konvensjon=konv)
    forr = tolk_heltall(finn_verdi(tekst, LABEL_BEHOLDNING_FOR), konvensjon=konv)
    if etter is None:
        m = _BEHOLDNING_FRITEKST.search(tekst) or _EIER_ETTER.search(tekst)
        if m:
            etter = tolk_heltall(m.group("antall"), konvensjon=konv)
    return forr, etter


def finn_utelukkelse(tittel: str, tekst: str) -> str:
    """
    Hvilken kategori av «ikke en frivillig markedshandel» ser vi?

    Tittelen veier tyngst. I brødteksten leter vi bare i de første 3000
    tegnene: lenger ned kommer standardformuleringer om opsjonsprogrammer
    som gjelder selskapet generelt, ikke denne handelen.
    """
    t_tittel = _liten(tittel)
    for grunn, ord_ in UTELUKK.items():
        if _inneholder(t_tittel, ord_):
            return grunn
    t_tekst = _liten(tekst)[:3000]
    for grunn, ord_ in UTELUKK.items():
        if _inneholder(t_tekst, ord_):
            return grunn
    return ""


def er_emisjon(tittel: str, tekst: str) -> bool:
    return bool(_inneholder(_liten(tittel), EMISJON_ORD)
                or _inneholder(_liten(tekst)[:3000], EMISJON_ORD))


def les_melding(tittel: str, tekst: str, ta_med_emisjoner: bool = False) -> Uttrekk:
    """
    Leser én melding og svarer med hva den faktisk var.

    Rekkefølgen er nøye valgt: vi leser FØRST og bestemmer oss ETTERPÅ. En
    melding kan inneholde både en innvinning og et ekte markedskjøp, og da
    skal kjøpet overleve.
    """
    tittel = rens(tittel)
    tekst = rens_flerlinje(tekst)
    u = Uttrekk()
    samlet = f"{tittel}\n{tekst}"

    if not tekst and not tittel:
        u.klasse, u.grunn = "UKJENT", "INGEN_TEKST"
        return u

    u.person = rens(finn_verdi(samlet, LABEL_NAVN))[:80]
    rolletekst = finn_verdi(samlet, LABEL_ROLLE)
    u.rolle, u.rolle_rang, naer = finn_rolle(rolletekst or f"{tittel}\n{tekst[:600]}")
    u.naerstaaende = "JA" if naer else "NEI"
    u.emisjon = "JA" if er_emisjon(tittel, tekst) else "NEI"

    # Tallskrivemåten bestemmes ÉN gang for hele meldingen.
    konv = finn_konvensjon(samlet)
    linjer = les_med_merkelapper(samlet, konv)
    metode = "MERKELAPP" if linjer else ""
    if not linjer or all(t.retning == "UKJENT" for t in linjer):
        fritekst = les_fritekst(samlet, konv)
        if fritekst:
            linjer = fritekst
            metode = "FRITEKST"
    u.transaksjoner = linjer
    u.antall_linjer = len(linjer)

    u.beholdning_for, u.beholdning_etter = finn_beholdning(samlet, konv)
    u.transaksjonsdato = next((t.dato for t in linjer if t.dato), "")

    aksjelinjer = [t for t in linjer
                   if t.instrument == "AKSJE" and t.retning in ("KJOP", "SALG")]
    utelukket = finn_utelukkelse(tittel, tekst)

    if not aksjelinjer:
        if utelukket:
            u.klasse, u.grunn, u.tillit = "IGNORERT", utelukket, "HOY"
        elif any(t.instrument in ("OPSJON", "RSU") for t in linjer):
            u.klasse, u.grunn, u.tillit = "IGNORERT", "IKKE_AKSJE", "HOY"
        else:
            u.klasse, u.grunn = "UKJENT", "INGEN_TRANSAKSJON_FUNNET"
        u.metode = metode
        return u

    # Vesting utbetalt i aksjer ER en aksjelinje, men ikke en beslutning.
    if utelukket and utelukket != "SKATTESALG":
        u.klasse, u.grunn, u.tillit, u.metode = "IGNORERT", utelukket, "HOY", metode
        _fyll_tall(u, aksjelinjer)
        return u

    if u.emisjon == "JA" and not ta_med_emisjoner:
        u.klasse, u.grunn, u.tillit, u.metode = "IGNORERT", "EMISJON", "HOY", metode
        _fyll_tall(u, aksjelinjer)
        return u

    _fyll_tall(u, aksjelinjer)
    if u.antall_netto is None or u.antall_netto == 0:
        u.klasse = "UKJENT"
        u.grunn = "NETTO_NULL" if u.antall_netto == 0 else "INGEN_ANTALL"
        u.metode = metode
        return u

    u.klasse = "KJOP" if u.antall_netto > 0 else "SALG"
    u.metode = metode

    # LAG 3: stemmer regnestykket før + netto = etter?
    u.kontroll = _kontroller(u)
    if u.kontroll == "AVVIK":
        u.klasse, u.grunn, u.tillit = "UKJENT", "MOTSTRID_BEHOLDNING", "LAV"
        return u

    # «MANGLER» på kontrollen er det NORMALE: de fleste meldinger oppgir bare
    # beholdningen ETTER handelen. Bare et faktisk AVVIK skal trekke ned.
    if metode == "MERKELAPP" and u.verdi is not None:
        u.tillit = "HOY"
    elif metode == "MERKELAPP":
        u.tillit = "MIDDELS"           # retningen er sikker, beløpet mangler
    elif u.verdi is not None:
        u.tillit = "MIDDELS"           # fritekst, men både antall og kurs lest
    else:
        u.tillit = "LAV"

    _fyll_okning(u)
    return u


def _fyll_tall(u: Uttrekk, linjer: Sequence[Transaksjon]) -> None:
    """Netter kjøp mot salg og regner snittkurs vektet på antall."""
    netto = 0
    har_antall = False
    verdi_sum = 0.0
    antall_med_kurs = 0
    valuta = ""
    for t in linjer:
        if t.antall is None:
            continue
        har_antall = True
        fortegn = 1 if t.retning == "KJOP" else -1
        netto += fortegn * abs(t.antall)
        if t.kurs:
            verdi_sum += fortegn * abs(t.antall) * t.kurs
            antall_med_kurs += fortegn * abs(t.antall)
        valuta = valuta or t.valuta
    u.antall_netto = netto if har_antall else None
    u.valuta = valuta or "NOK"
    if antall_med_kurs:
        u.kurs_snitt = round(verdi_sum / antall_med_kurs, 6)
        u.verdi = round(abs(verdi_sum), 2)
    elif u.antall_netto is not None:
        kurser = [t.kurs for t in linjer if t.kurs]
        if kurser:
            u.kurs_snitt = round(sum(kurser) / len(kurser), 6)
            u.verdi = round(abs(u.antall_netto) * u.kurs_snitt, 2)


def _kontroller(u: Uttrekk) -> str:
    """
    Regnestykket som avslører lesefeil: før + netto skal bli etter.

    Gratis, og går over hele datasettet i hver kjøring. Slår det ut ofte,
    har uttrekket et problem du ellers aldri ville sett.
    """
    if u.beholdning_for is None or u.beholdning_etter is None or u.antall_netto is None:
        return "MANGLER"
    ventet = u.beholdning_for + u.antall_netto
    if ventet == u.beholdning_etter:
        return "OK"
    # Ett aksjeslag av flere, eller avrunding — vi tåler en promille.
    if abs(ventet - u.beholdning_etter) <= max(1, abs(u.beholdning_etter) * 0.001):
        return "OK"
    return "AVVIK"


def _fyll_okning(u: Uttrekk) -> None:
    """
    Hvor mye endret personen sin egen posisjon, i prosent?

    Det mest informative størrelsesmålet. «Han økte beholdningen sin med
    40 %» sier noe helt annet enn «han kjøpte for 500 000 kroner» — det
    siste er stort for et styremedlem i et lite selskap og ingenting for
    konsernsjefen i Equinor.
    """
    if u.antall_netto is None:
        return
    forr = u.beholdning_for
    if forr is None and u.beholdning_etter is not None:
        forr = u.beholdning_etter - u.antall_netto
    if forr is None:
        return
    u.beholdning_for = forr
    if forr <= 0:
        u.ny_posisjon = "JA" if u.antall_netto > 0 else "NEI"
        u.okning_pst = 100.0 if u.antall_netto > 0 else -100.0
        return
    u.okning_pst = round(100.0 * u.antall_netto / forr, 3)


# ══════════════════════════════════════════════════════════════════════════
# DEL G — SELSKAPSLISTEN
# ══════════════════════════════════════════════════════════════════════════
#
# Én kilde: Excel-lista fra Euronext,
#     https://live.euronext.com/nb/markets/oslo/equities/list
# Den har Name, ISIN og Symbol på SAMME rad. Da finnes det ingenting å matche
# på navn, og dermed ingenting å bomme på. Den gamle prefiksmatchingen kunne
# gi ZALARIS sine meldinger til Bouvet, og gjorde det.

ISIN_MONSTER = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}\d$")
SELSKAP_KOLONNER = ["Selskap", "Ticker", "Symbol", "ISIN", "Marked", "Valuta"]
AKSJELISTE_MONSTER = "Euronext_Equities*.xlsx"
AKSJELISTE_DYBDE = 2
_DATO_I_NAVN = re.compile(r"(\d{4})-(\d{2})-(\d{2})")


def aksjeliste_roter(opp: Oppsett) -> List[Path]:
    """
    Rotmappene vi leter i. Under hver av dem søkes det to nivåer ned.

    Lista er med vilje raus: Excel-fila havner der nettleseren legger den, og
    det er sjelden der du hadde tenkt.
    """
    hjem = Path.home()
    roter = [SKRIPTMAPPE, opp.base_dir, opp.s1_dir, Path.cwd(),
             SKRIPTMAPPE / "steg1",
             hjem / "Downloads", hjem / "Nedlastinger",
             hjem / "Desktop", hjem / "Skrivebord",
             hjem / "OneDrive" / "Desktop", hjem / "OneDrive" / "Skrivebord",
             hjem / "OneDrive" / "Dokumenter", hjem / "Documents"]
    sett, ut = set(), []
    for r in roter:
        try:
            n = r.resolve()
        except OSError:
            continue
        if n not in sett and r.exists():
            sett.add(n)
            ut.append(r)
    return ut


def finn_aksjeliste(opp: Oppsett, egen: str = "") -> Optional[Path]:
    """Nyeste nedlastede aksjeliste, eller None."""
    if egen:
        p = Path(egen).expanduser()
        return p if p.exists() else None
    monstre = ["/".join(["*"] * d + [AKSJELISTE_MONSTER])
               for d in range(AKSJELISTE_DYBDE + 1)]
    treff: List[Path] = []
    for rot in aksjeliste_roter(opp):
        for m in monstre:
            try:
                treff.extend(t for t in rot.glob(m) if t.is_file())
            except OSError:
                continue
    if not treff:
        return None
    return max(treff, key=lambda p: (p.stat().st_mtime, p.name))


def aksjeliste_dato(sti: Optional[Path]) -> Optional[date]:
    """Datoen i filnavnet er DATAENES dato. Mangler den: filens tidsstempel."""
    if sti is None:
        return None
    m = _DATO_I_NAVN.search(Path(sti).name)
    if m:
        d = _trygg_dato(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if d:
            return d
    try:
        return datetime.fromtimestamp(Path(sti).stat().st_mtime).date()
    except OSError:
        return None


def aksjeliste_alder(sti: Optional[Path]) -> Optional[int]:
    d = aksjeliste_dato(sti)
    return None if d is None else (date.today() - d).days


def gyldig_aksjeliste(sti: Path, min_rader: int = 50) -> Tuple[bool, str]:
    """
    Er dette faktisk en aksjeliste?

    En nedlasting som feiler gir sjelden en feilmelding — den gir en
    HTML-side med .xlsx som filnavn. Uten denne kontrollen ville en slik fil
    overskrevet en god liste og tatt hele kjeden med seg.
    """
    try:
        rader = les_xlsx(sti, overskriftsord=("isin",))
    except Exception as e:
        return False, f"lot seg ikke lese som Excel ({feiltekst(e)[:60]})"
    if not rader:
        return False, "ingen rader"
    kol = finn_kolonne(rader[0], "isin")
    if not kol:
        return False, f"ingen ISIN-kolonne (fant: {', '.join(list(rader[0])[:6])})"
    gyldige = sum(1 for r in rader if ISIN_MONSTER.match(rens(r.get(kol)).upper()))
    if gyldige < min_rader:
        return False, f"bare {gyldige} gyldige ISIN-rader"
    return True, f"{gyldige} selskaper"


def bygg_selskaper(opp: Oppsett, logger: logging.Logger, aksjeliste: str = "",
                   bare: Sequence[str] = ()) -> List[Rad]:
    """Leser aksjelista og skriver selskaper.csv."""
    fil = finn_aksjeliste(opp, aksjeliste)
    if fil is None:
        return []
    rader = les_xlsx(fil, overskriftsord=("isin",))
    if not rader:
        logger.error(f"❌ {fil.name} inneholdt ingen rader.")
        return []

    prove = rader[0]
    k_navn = finn_kolonne(prove, "name", "company", "navn", "selskap")
    k_isin = finn_kolonne(prove, "isin")
    k_sym = finn_kolonne(prove, "symbol", "ticker")
    k_marked = finn_kolonne(prove, "market", "exchange", "marked")
    k_valuta = finn_kolonne(prove, "currency", "valuta")
    if not k_isin or not k_sym:
        logger.error(f"❌ {fil.name} mangler ISIN- eller symbolkolonne "
                     f"(fant: {', '.join(list(prove)[:8])})")
        return []

    ønsket = {rens(t).upper().replace(".OL", "") for t in bare if rens(t)}
    ut: List[Rad] = []
    sett: Set[str] = set()
    for r in rader:
        isin = rens(r.get(k_isin)).upper()
        # Metadataradene øverst i eksporten har ingen gyldig ISIN og faller
        # ut her av seg selv.
        if not ISIN_MONSTER.match(isin):
            continue
        symbol = rens(r.get(k_sym)).upper().replace(".OL", "")
        if not symbol or (ønsket and symbol not in ønsket) or symbol in sett:
            continue
        sett.add(symbol)
        ut.append({"Selskap": rens(r.get(k_navn)) if k_navn else symbol,
                   "Ticker": symbol + opp.ticker_suffiks,
                   "Symbol": symbol, "ISIN": isin,
                   "Marked": rens(r.get(k_marked)) if k_marked else "",
                   "Valuta": rens(r.get(k_valuta)) if k_valuta else ""})

    skriv_csv(opp.selskapsliste, ut, SELSKAP_KOLONNER)
    alder = aksjeliste_alder(fil)
    logger.info(f"📋 {len(ut)} selskaper fra {fil.name}"
                + (f"  ({alder} dager gammel)" if alder is not None else "")
                + f" → {opp.selskapsliste.name}")
    if ønsket:
        mangler = ønsket - {r["Symbol"] for r in ut}
        if mangler:
            logger.warning(f"   ⚠️  Ikke i aksjelista: {', '.join(sorted(mangler)[:12])}")
    return ut


def les_selskaper(opp: Oppsett) -> List[Rad]:
    return les_csv(opp.selskapsliste)


def forklar_manglende_aksjeliste(opp: Oppsett, logger: logging.Logger,
                                 egen: str = "") -> None:
    if egen:
        logger.error(f"❌ Fant ikke aksjelista du oppga: {egen}")
        return
    lette = "\n".join(f"        {m}" for m in aksjeliste_roter(opp))
    logger.error(
        f"\n❌ Ingen aksjeliste — verken hentet fra Euronext eller funnet på disk.\n"
        f"\n   Normalt henter steg 1 lista selv fra\n        {opp.aksjeliste_url}\n"
        f"   Gikk det galt, kan du gjøre det for hånd:\n"
        f"   1. Åpne lenken over\n"
        f"   2. Trykk nedlastingsikonet, så «Go»\n"
        f"   3. Legg fila her:  {opp.s1_dir}\n"
        f"      (filnavnet må begynne med «Euronext_Equities»)\n"
        f"\n   Eller pek på den direkte:\n"
        f"        --aksjeliste \"C:\\sti\\til\\Euronext_Equities.xlsx\"\n"
        f"\n   Jeg lette i disse mappene, og {AKSJELISTE_DYBDE} nivåer under hver:\n"
        f"{lette}\n")


# ══════════════════════════════════════════════════════════════════════════
# DEL H — NETTLESER (Playwright)
# ══════════════════════════════════════════════════════════════════════════

COOKIE_KNAPPER = (
    "#onetrust-reject-all-handler",
    "#onetrust-accept-btn-handler",
    "button#truste-consent-required",
    "button#truste-consent-button",
    ".ot-pc-refuse-all-handler",
    "button[aria-label*='reject' i]",
    "button:has-text('Reject All')",
    "button:has-text('Avvis alle')",
    "button:has-text('Godta alle')",
    "button:has-text('Accept all')",
    "button:has-text('Continue without accepting')",
    "button:has-text('Fortsett uten å godta')",
)

# Nedlastingsikonet på aksjelistesiden. aria-controls er det mest stabile
# holdepunktet — den peker på tabellen knappen hører til. Klassene deles med
# resten av sida, og svg-en har verken id eller tekst.
NEDLASTINGSKNAPPER = (
    "div.dt-buttons button[aria-controls*='stocks-data-table']",
    "button[aria-controls*='stocks-data-table']",
    "div.dt-buttons button.btn-link",
    "div.dt-buttons button",
    "button:has(svg use[href*='download'])",
    "[data-ih-nedlasting='1']",
)

FINN_NEDLASTINGSKNAPP_JS = """
(function () {
  for (const u of document.querySelectorAll('use')) {
    const h = u.getAttribute('xlink:href') || u.getAttribute('href') || '';
    if (h.indexOf('#download') === -1) continue;
    const svg = u.closest('svg');
    const el = u.closest('a, button, [role="button"]') || (svg ? svg.parentElement : null);
    if (el) { el.setAttribute('data-ih-nedlasting', '1'); return true; }
  }
  return false;
})()
"""

GO_KNAPPER = ("input[type='submit'][value='Go']", "input.btn-primary[value='Go']",
              ".modal input[type='submit'].btn-primary", "//input[@value='Go']")

FORMATVALG = ("//label[contains(., 'MS Excel')]", "label:has-text('MS Excel')",
              "input[type='radio'][value*='xlsx']", "input[type='radio'][value*='excel']")

# Innholdet i filtypevinduet er høyere enn vinduet selv, så «Go» ligger
# utenfor skjermen til du ruller. Et vindu med EGET rullefelt må dyttes ned.
RULL_MODAL_JS = """
(function () {
  let n = 0;
  for (const el of document.querySelectorAll(
        '.modal, .modal-dialog, .modal-content, .modal-body, [role="dialog"], '
        + '[role="dialog"] div, .modal div')) {
    if (el.scrollHeight > el.clientHeight + 8) { el.scrollTop = el.scrollHeight; n++; }
  }
  window.scrollTo(0, document.body.scrollHeight);
  return n;
})()
"""


class Nettleser:
    """Tynn innpakning rundt Playwright som alltid rydder etter seg."""

    def __init__(self, opp: Oppsett, logger: logging.Logger):
        self.opp = opp
        self.logger = logger
        self.pw = self.browser = self.context = self.page = None

    def __enter__(self) -> "Nettleser":
        from playwright.sync_api import sync_playwright     # ImportError → «pip install»
        self.pw = sync_playwright().start()
        start: Dict[str, Any] = {"headless": self.opp.headless}
        if self.opp.browser_sti:
            start["executable_path"] = self.opp.browser_sti
        self.browser = self.pw.chromium.launch(**start)
        # accept_downloads: uten den forkaster Playwright fila i det den
        # kommer, og «trykk last ned» blir et klikk uten resultat.
        self.context = self.browser.new_context(
            viewport={"width": 1600, "height": 1200}, locale="en-GB",
            accept_downloads=True)
        self.page = self.context.new_page()
        self.page.set_default_timeout(self.opp.browser_timeout_ms)
        return self

    def __exit__(self, *_exc) -> None:
        for navn, o in (("side", self.page), ("kontekst", self.context),
                        ("nettleser", self.browser)):
            try:
                if o:
                    o.close()
            except Exception as e:
                self.logger.debug(f"Kunne ikke lukke {navn}: {feiltekst(e)}")
        try:
            if self.pw:
                self.pw.stop()
        except Exception as e:
            self.logger.debug(f"Kunne ikke stoppe Playwright: {feiltekst(e)}")

    def ga_til(self, url: str, vent_ms: int = 1200) -> bool:
        def apne() -> bool:
            response = self.page.goto(url, wait_until="domcontentloaded",
                                      timeout=self.opp.browser_timeout_ms)
            if response is None or response.status >= 400:
                raise RuntimeError(f"HTTP {getattr(response, 'status', 'no response')}")
            self.page.wait_for_timeout(vent_ms)
            return True
        return bool(med_nye_forsok(apne, self.logger, f"åpne {url[:60]}",
                                   self.opp.maks_forsok, self.opp.forste_pause_s))

    def klikk(self, selektorer: Iterable[str], hva: str, stille: bool = False,
              rull: bool = True) -> bool:
        """
        Prøver velgerne i tur og orden. True på første som traff.

        Fire ting gjør den seigere enn en rå click():
          · en velger som begynner med «/» tolkes som XPath
          · elementet rulles inn i synsfeltet først
          · treffer ikke et vanlig klikk, prøves force=True, som går gjennom
            et gjennomsiktig lag som ligger over
          · stille=True for klikk som gjerne kan bomme
        """
        t = self.opp.sondering_timeout_ms
        for sel in selektorer:
            try:
                loc = (self.page.locator(f"xpath={sel}") if sel.startswith("/")
                       else self.page.locator(sel)).first
            except Exception as e:
                self.logger.debug(f"Velgeren «{sel}» duger ikke: {feiltekst(e)}")
                continue
            for måte in ("normal", "force"):
                try:
                    if rull:
                        try:
                            loc.scroll_into_view_if_needed(timeout=t)
                        except Exception:
                            pass          # skjult element — force-forsøket tar det
                    if måte == "force":
                        loc.click(force=True, timeout=t)
                    else:
                        if not loc.is_visible(timeout=t):
                            continue
                        loc.click(timeout=t)
                    self.page.wait_for_timeout(500)
                    if not stille:
                        self.logger.info(f"      ✓ {hva}")
                    return True
                except Exception as e:
                    self.logger.debug(f"«{sel}» ({måte}) traff ikke ({hva}): {feiltekst(e)}")
        if not stille:
            self.logger.debug(f"      · fant ikke: {hva}")
        return False


def _lagre_feilsok(nl: Nettleser, opp: Oppsett, logger: logging.Logger,
                   navn: str) -> None:
    """Tar vare på sida slik den faktisk så ut da det gikk galt."""
    try:
        opp.s1_dir.mkdir(parents=True, exist_ok=True)
        png = opp.s1_dir / f"feilsok_{navn}.png"
        htm = opp.s1_dir / f"feilsok_{navn}.html"
        nl.page.screenshot(path=str(png), full_page=True)
        htm.write_text(nl.page.content(), encoding="utf-8")
        logger.warning(f"   Lagret {png.name} og {htm.name} i {opp.s1_dir} — "
                       f"åpne dem for å se hva sida viste. Kjør gjerne med --synlig.")
    except Exception as e:
        logger.debug(f"Kunne ikke lagre feilsøksfiler: {feiltekst(e)}")


def last_ned_aksjeliste(opp: Oppsett, logger: logging.Logger,
                        nl: Nettleser) -> Optional[Path]:
    """
    Henter en fersk aksjeliste med nettleseren som allerede er åpen.

    Flyten er den du gjør for hånd: åpne lista, trykk nedlastingsikonet,
    trykk «Go» i vinduet som spretter opp.
    """
    logger.info(f"⬇️  Henter fersk aksjeliste fra {opp.aksjeliste_url}")
    try:
        if not nl.ga_til(opp.aksjeliste_url):
            logger.warning("   Kom ikke inn på aksjelistesiden.")
            return None
        nl.klikk(COOKIE_KNAPPER, "cookie-banner", stille=True)

        if not nl.klikk(NEDLASTINGSKNAPPER, "nedlastingsikonet"):
            try:
                funnet = nl.page.evaluate(FINN_NEDLASTINGSKNAPP_JS)
            except Exception as e:
                logger.debug(f"JS-søk etter nedlastingsikonet feilet: {feiltekst(e)}")
                funnet = False
            if not funnet or not nl.klikk(["[data-ih-nedlasting='1']"],
                                          "nedlastingsikonet (via JS)"):
                logger.warning("   Fant ikke nedlastingsikonet på sida.")
                _lagre_feilsok(nl, opp, logger, "nedlastingsikon")
                return None
        try:
            nl.page.wait_for_selector(
                "input[type='submit'][value='Go'], .modal, [role='dialog']",
                timeout=opp.sondering_timeout_ms * 4)
        except Exception as e:
            logger.debug(f"Ventet forgjeves på filtypevinduet: {feiltekst(e)}")
        nl.page.wait_for_timeout(1000)

        # Standardvalget er MS Excel (.xlsx). Vi bekrefter det, men bryr oss
        # ikke om klikket bommer.
        nl.klikk(FORMATVALG, "MS Excel (.xlsx)", stille=True)
        try:
            nl.page.evaluate(RULL_MODAL_JS)
        except Exception as e:
            logger.debug(f"Klarte ikke rulle vinduet: {feiltekst(e)}")
        nl.page.wait_for_timeout(400)

        with nl.page.expect_download(timeout=opp.nedlasting_timeout_ms) as info:
            if not nl.klikk(GO_KNAPPER, "Go"):
                _lagre_feilsok(nl, opp, logger, "go_knapp")
                raise RuntimeError("fant ingen «Go»-knapp i filtypevinduet")
        nedlasting = info.value

        foreslatt = rens(getattr(nedlasting, "suggested_filename", "")) or ""
        m = _DATO_I_NAVN.search(foreslatt)
        dagen = m.group(0) if m else date.today().strftime("%Y-%m-%d")
        mal = opp.s1_dir / f"Euronext_Equities_{dagen}.xlsx"
        opp.s1_dir.mkdir(parents=True, exist_ok=True)
        nedlasting.save_as(str(mal))
    except Exception as e:
        logger.warning(f"   Nedlastingen av aksjelista feilet — {feiltekst(e)[:130]}")
        logger.debug("Full sporing:", exc_info=True)
        return None

    ok, hva = gyldig_aksjeliste(mal)
    if not ok:
        # En ødelagt nedlasting skal ALDRI få stå igjen: neste kjøring ville
        # plukket den opp som «nyeste» og trodd den var god.
        logger.warning(f"   Den nedlastede fila er ikke en aksjeliste ({hva}). "
                       f"Beholder den forrige.")
        try:
            mal.unlink()
        except OSError:
            pass
        return None
    logger.info(f"✅ Fersk aksjeliste: {mal.name} — {hva}")
    return mal


def sikre_aksjeliste(opp: Oppsett, logger: logging.Logger,
                     nl: Optional[Nettleser] = None, egen: str = "",
                     tving: bool = False) -> Optional[Path]:
    """
    Sørger for at vi har en liste vi kan stole på, og sier hvor gammel den er.

    En sti du selv oppgir vinner alltid. Ellers hentes en fersk når den vi
    har er for gammel. Går hentingen galt, brukes den gamle — men med en
    advarsel som sier nøyaktig hvor gammel den er, i stedet for at kjøringen
    stille bruker fjorårets univers.
    """
    if egen:
        p = Path(egen).expanduser()
        if not p.exists():
            logger.error(f"❌ Fant ikke aksjelista du oppga: {egen}")
            return None
        ok, hva = gyldig_aksjeliste(p)
        if ok:
            logger.info(f"📋 Bruker aksjelista du oppga: {p}  ({hva})")
            return p
        logger.error(f"❌ {p} er ikke en brukbar aksjeliste ({hva}).")
        return None

    lokal = finn_aksjeliste(opp)
    alder = aksjeliste_alder(lokal)

    if opp.offline:
        grunn = "--offline"
    elif not opp.hent_aksjeliste and not tving:
        grunn = "automatisk henting er slått av"
    elif tving or lokal is None:
        grunn = ""
    elif alder is not None and alder <= opp.aksjeliste_maks_alder_dager:
        grunn = f"lista er {alder} dag(er) gammel — fersk nok"
    else:
        grunn = ""

    if not grunn and nl is not None:
        ny = last_ned_aksjeliste(opp, logger, nl)
        if ny is not None:
            return ny
        if lokal is not None:
            logger.warning(f"   ⚠️  Bruker den lokale lista i stedet: {lokal.name}")
    elif lokal is not None and grunn:
        logger.info(f"📋 {grunn} — bruker {lokal.name}")

    if lokal is None:
        return None
    alder = aksjeliste_alder(lokal)
    if alder is not None and alder > max(7, opp.aksjeliste_maks_alder_dager):
        logger.warning(
            f"   ⚠️  Aksjelista er {alder} dager gammel ({lokal.name}). Selskaper "
            f"notert eller strøket siden da mangler, og et univers som ikke "
            f"stemmer gir hull du ikke ser i backtesten.")
    return lokal


# ══════════════════════════════════════════════════════════════════════════
# STEG 1 — LAST NED ARTIKLENE FRA EURONEXT
# ══════════════════════════════════════════════════════════════════════════
#
# Steget gjør ÉN ting: henter rå HTML for hver innsidemelding og legger den
# på disk. Ingen tolkning, ingen tekstuttrekk, ingen vurdering.
#
# Det er hele poenget. Da kan steg 2 kjøres om igjen på ti år med meldinger
# på minutter, hver gang du forbedrer tekstuttrekket — uten å gå til Euronext
# en eneste gang. Slår uttrekket feil (som da hele lageret ble fylt med
# cookie-tekst), er det en omkjøring av steg 2, ikke en ny nedlasting på åtte
# timer.
#
# URL-en bygges direkte i stedet for å klikke gjennom menyer:
#     /<språk>/listview/company-press-release/<ISIN>
#         ?field_company_press_releases_target_id[1081]=1081   ← innsidehandel
#         &field_company_pr_pub_datetime_start=<fra> 00:00:00
#         &field_company_pr_pub_datetime_end=today 00:00 +1 day

GRUPPE_ARTIKLER = "artikler"
ARTIKKEL_VALIDERING = 2


def artikkel_vindu(vm, navn, opp, today):
    """Old completion markers need one full, validated historical rescan."""
    post = vm.post(GRUPPE_ARTIKLER, navn)
    validated = post.get("liste_validering") == ARTIKKEL_VALIDERING
    full = opp.full or not validated
    ready = (not full and not post.get("siste_feil")
             and vm.er_ajour(GRUPPE_ARTIKLER, navn, today))
    start = vm.startdato(GRUPPE_ARTIKLER, navn, opp.eldste_melding(),
                        opp.overlapp_dager, full)
    return ready, start

INDEKS_KOLONNER = [
    "Melding_ID", "Node_ID", "Selskap", "Selskap_Euronext", "Ticker", "ISIN",
    "Dato", "Klokkeslett", "Tittel", "Kategori", "Sektor", "Sprak", "Kilde_URL",
    "HTML_Fil", "HTML_Tegn", "PDF_Fil", "Hentet", "Status",
]

NORSKE_ORD = ("meldepliktig", "primærinnsider", "aksjer", "kjøp", "salg",
              "beholdning", "handel", "styremedlem", "konsernsjef")
ENGELSKE_ORD = ("mandatory", "notification", "primary insider", "shares",
                "purchase", "disposal", "holding", "trade", "board member")


def gjett_sprak(tekst: str) -> str:
    t = rens(tekst).lower()
    if not t:
        return ""
    n = sum(1 for o in NORSKE_ORD if o in t)
    e = sum(1 for o in ENGELSKE_ORD if o in t)
    return "NB" if n > e else ("EN" if e > n else "")


def lag_id(url: str, selskap: str, dato: str, klokkeslett: str, tittel: str,
           nid: str = "") -> str:
    """
    Primærnøkkelen. Lik ved hver kjøring, ellers er tilvekst umulig.

    Euronext gir hver melding et node-nummer (`data-node-nid`). Finnes det,
    ER det nøkkelen — og det løser en feil som doblet hele lageret: samme
    melding ble hentet én gang per datovindu, og siden URL-en inngikk i
    hashen ble de to til to ulike meldinger. 3912 rader var i virkeligheten
    ~1950 meldinger, hver talt to ganger, og hver handel ville telt dobbelt
    i backtesten.

    Uten node-nummer må hashen inneholde klokkeslett og URL. Med bare
    selskap+dato+tittel fikk to ekte meldinger samme dag identisk nøkkel — og
    siden titlene gjentar seg («Mandatory notification of trade», hver eneste
    gang) ble melding nummer to stille forkastet. Det er nettopp flere
    handler samme dag som er klyngesignalet.
    """
    if rens(nid).isdigit():
        return f"EN-{rens(nid)}"
    if url:
        m = re.search(r"/(?:node|press-release[s]?|announcement|news)/(\d{3,})", url)
        if not m:
            siste = url.rstrip("/").split("/")[-1].split("?")[0]
            if siste.isdigit() and len(siste) >= 4:
                m = re.match(r"(\d+)", siste)
        if m:
            return f"EN-{m.group(1)}"
    nøkkel = "|".join([rens(selskap).upper(), rens(dato), rens(klokkeslett),
                       rens(tittel).upper()[:120], rens(url)])
    return "H-" + avtrykk(nøkkel)


class Euronext:
    """
    Leser resultattabellen via KOLONNEOVERSKRIFTENE, ikke via posisjon, så
    den tåler både norsk og engelsk grensesnitt og at Euronext bytter om.
    """

    OVERSKRIFTER = {
        "tid": "tid", "time": "tid", "date": "tid", "dato": "tid",
        "selskap": "selskap", "company": "selskap", "issuer": "selskap",
        "tittel": "tittel", "title": "tittel", "headline": "tittel",
        "sektor": "sektor", "sector": "sektor", "icb": "sektor",
        "kategori": "kategori", "category": "kategori",
    }

    def __init__(self, nl: Nettleser, opp: Oppsett, logger: logging.Logger):
        self.nl = nl
        self.opp = opp
        self.logger = logger
        self._cookies = False
        # URL-malen for én melding, lært av det første klikket. Tom til vi
        # har sett nettleseren gjøre det selv.
        self.mal = ""
        self._forespørsler: List[str] = []
        self._lytter = False
        self.via_klikk = 0
        self.via_url = 0

    # ── én melding ───────────────────────────────────────────────────────
    def _start_lytt(self) -> None:
        """
        Noterer hvilke adresser nettleseren ber om.

        Meldingen ligger ikke i listesida — lenken har href="" og åpner en
        modal som JavaScript fyller i etterkant. Vi kan ikke gjette den
        adressen, men vi kan SE den: klikk én gang, og les hva nettleseren
        selv spurte om. Deretter kan de neste tre tusen hentes rett, uten
        klikk og uten å tegne en eneste side.
        """
        if self._lytter:
            return
        try:
            def notér(forespørsel: Any) -> None:
                try:
                    self._forespørsler.append(forespørsel.url)
                    if len(self._forespørsler) > 60:
                        del self._forespørsler[:-40]
                except Exception:
                    pass
            self.nl.page.on("request", notér)
            self._lytter = True
        except Exception as e:
            self.logger.debug(f"Fikk ikke lyttet på forespørsler: {feiltekst(e)}")

    def _lær_mal(self, nid: str) -> None:
        """Bygger malen av den adressen som faktisk hentet meldingen."""
        if self.mal or not nid:
            return
        for url in reversed(self._forespørsler):
            if nid in url and "listview" not in url:
                self.mal = url.replace(nid, "{nid}")
                self.logger.info(f"   🔗 Lærte adressen til én melding: "
                                 f"{self.mal[:96]}")
                return

    @staticmethod
    def _som_html(svar: str) -> str:
        """
        Drupal svarer på slike kall med en JSON-konvolutt rundt HTML-en:
        en liste av kommandoer der «data» er innholdet. Lagrer vi konvolutten
        rå, får steg 2 en tekst full av \u003C og ingen tagger å lese.
        """
        t = (svar or "").lstrip()
        if not t[:1] in ("[", "{"):
            return svar
        try:
            data = json.loads(t)
        except ValueError:
            return svar
        biter: List[str] = []

        def samle(x: Any) -> None:
            if isinstance(x, dict):
                for nøkkel, verdi in x.items():
                    if nøkkel in ("data", "html", "content", "body") and isinstance(verdi, str):
                        biter.append(verdi)
                    else:
                        samle(verdi)
            elif isinstance(x, list):
                for e in x:
                    samle(e)

        samle(data)
        return "\n".join(biter) if biter else svar

    def _duger(self, html: str) -> bool:
        """
        Er dette ÉN melding, eller fikk vi listesida tilbake igjen?

        Den andre halvdelen er ikke teoretisk: det var nøyaktig den feilen
        som fylte lageret med 3912 kopier av et søkeresultat. En listeside
        har mange data-node-nid; en melding har ingen.
        """
        if not html or len(html) < self.opp.min_melding_tegn:
            return False
        return html.count("data-node-nid") <= 1

    def _hent_via_url(self, nid: str) -> str:
        if not self.mal or not nid:
            return ""
        try:
            svar = self.nl.context.request.get(
                self.mal.format(nid=nid), timeout=self.opp.melding_timeout_ms)
            if not svar.ok:
                return ""
            html = self._som_html(svar.text() or "")
        except Exception as e:
            self.logger.debug(f"Direkte henting av {nid} feilet: {feiltekst(e)}")
            return ""
        return html if self._duger(html) else ""

    def _hent_via_klikk(self, nid: str) -> str:
        """Gjør det du ville gjort selv: klikk på overskriften, les vinduet."""
        if not nid:
            return ""
        self._start_lytt()
        try:
            self.nl.page.evaluate(
                "(nid) => { const a = document.querySelector("
                "`a[data-node-nid='${nid}']`); if (a) { a.scrollIntoView();"
                " a.click(); } }", nid)
            self.nl.page.wait_for_function(
                "(nid) => { const d = document.querySelector("
                "`#CompanyPressRelease-${nid} .modal-body`);"
                " return !!d && d.innerText.trim().length > 80; }",
                arg=nid, timeout=self.opp.melding_timeout_ms)
            html = self.nl.page.evaluate(
                "(nid) => { const d = document.querySelector("
                "`#CompanyPressRelease-${nid} .modal-body`);"
                " return d ? d.innerHTML : ''; }", nid) or ""
        except Exception as e:
            self.logger.debug(f"Modalen for {nid} åpnet seg ikke: {feiltekst(e)}")
            html = ""
        finally:
            try:
                self.nl.page.evaluate(
                    "(nid) => { const m = document.querySelector("
                    "`#CompanyPressRelease-${nid}`);"
                    " if (m && window.jQuery) window.jQuery(m).modal('hide'); }", nid)
            except Exception:
                pass
        if html:
            self._lær_mal(nid)
        return html if self._duger(html) else ""

    def hent_melding(self, rad: Dict[str, str]) -> str:
        """
        HTML-en for ÉN melding. Tom streng når vi ikke fikk tak i den.

        Rekkefølgen er lært adresse først (rask, ingen tegning), så klikk
        (treg, men virker alltid). Første melding går alltid via klikk, og
        det er den som lærer opp resten.
        """
        nid = rens(rad.get("nid"))
        html = self._hent_via_url(nid)
        if html:
            self.via_url += 1
            return html
        html = self._hent_via_klikk(nid)
        if html:
            self.via_klikk += 1
            return html
        # Siste utvei: en ekte lenke, hvis raden hadde en.
        href = rens(rad.get("href"))
        if href and "listview" not in href and self.nl.ga_til(href, vent_ms=700):
            try:
                html = self.nl.page.content() or ""
            except Exception:
                html = ""
            if self._duger(html):
                return html
        return ""

    def pdf_i(self, html: str) -> str:
        """PDF-lenken inne i meldingen, ikke i sidas ramme."""
        m = re.search(r'href=["\']([^"\']+\.pdf(?:\?[^"\']*)?)["\']',
                      html or "", re.IGNORECASE)
        if not m:
            return ""
        return urllib.parse.urljoin(self.opp.euronext_base, m.group(1))

    def bygg_url(self, isiner: Sequence[str], fra: date, side: int = 0) -> str:
        q = urllib.parse.quote
        sti = q(",".join(isiner), safe="")
        kat = (f"field_company_press_releases_target_id"
               f"{q('[' + str(self.opp.kategori_id) + ']', safe='')}={self.opp.kategori_id}")
        deler = ["combine=", kat,
                 f"field_company_pr_pub_datetime_start="
                 f"{q(fra.strftime('%Y-%m-%d') + ' 00:00:00', safe='')}",
                 f"field_company_pr_pub_datetime_end={q('today 00:00 +1 day', safe='')}"]
        if side:
            deler.append(f"page={side}")
        return (f"{self.opp.euronext_base}/{self.opp.sprak}"
                f"/listview/company-press-release/{sti}?{'&'.join(deler)}")

    def avvis_cookies(self) -> None:
        if self._cookies:
            return
        self.nl.klikk(COOKIE_KNAPPER, "cookie-banner", stille=True)
        self._cookies = True

    def hent_liste(self, isiner: Sequence[str], fra: date
                   ) -> Tuple[List[Dict[str, str]], bool]:
        """Return success only after every result page was validated.

        HTTP success alone is not evidence of an empty result set. A loading,
        blocked or missing table is retried and must never advance a watermark.
        """
        for attempt in range(min(3, max(1, self.opp.maks_forsok))):
            rows, complete = self._hent_liste_validert(isiner, fra)
            if complete:
                return rows, True
            self.logger.warning("Incomplete Euronext response; retrying company (%s/3)", attempt + 1)
            if attempt < 2:
                time.sleep(min(30, 3 * (2 ** attempt)))
                self._cookies = False
        return [], False

    def _hent_liste_validert(self, isiner, fra):
        all_rows, seen, expected = [], set(), None
        for page_no in range(self.opp.maks_sider):
            url = self.bygg_url(isiner, fra, page_no)
            if not self.nl.ga_til(url):
                return [], False
            self.avvis_cookies()
            try:
                self.nl.page.wait_for_function(r"""() => {
                    const body = document.body?.innerText || '';
                    return document.querySelector('table tbody tr td') ||
                        /no results found|no results match|ingen resultater|ingen treff/i.test(body);
                }""", timeout=self.opp.browser_timeout_ms)
                state = self.nl.page.evaluate(r"""() => {
                    const text = document.body?.innerText || '';
                    return {
                      blocked: /access denied|too many requests|verify you are human|captcha|service unavailable/i.test(text),
                      empty: /no results found|no results match|ingen resultater|ingen treff/i.test(text),
                      table: !!document.querySelector('table tbody tr td')
                    };
                }""")
            except Exception:
                return [], False
            if not state or state.get('blocked'):
                return [], False
            if page_no == 0:
                expected = self._antall_treff()
            rows = self._les_tabell(url)
            if not rows:
                confirmed_empty = state.get('empty', False)
                if not confirmed_empty or (expected is not None and len(all_rows) < expected):
                    return [], False
                return all_rows, True
            if not state.get('table'):
                return [], False
            new = 0
            for row in rows:
                key = (row.get('nid') or row.get('href'), row.get('tid_ra'), row.get('tittel'))
                if key not in seen:
                    seen.add(key)
                    all_rows.append(row)
                    new += 1
            if not new:
                return [], False
            if expected is not None and len(all_rows) >= expected:
                return all_rows, True
            # With no result count, require explicit empty next page; never guess.
            time.sleep(self.opp.pause_mellom_sider_s)
        return [], False

    def _antall_treff(self) -> Optional[int]:
        try:
            tekst = self.nl.page.evaluate(
                "document.body ? document.body.innerText.slice(0,4000) : ''") or ""
        except Exception as e:
            self.logger.debug(f"Fant ikke «viser N av M»: {feiltekst(e)}")
            return None
        m = re.search(r"\d+\s*[-–]\s*\d+\s+(?:av|of)\s+([\d\s.,]+)\s*"
                      r"(?:resultater|results)", tekst, re.IGNORECASE)
        if not m:
            return None
        try:
            return int(re.sub(r"\D", "", m.group(1)))
        except ValueError:
            return None

    def _les_tabell(self, side_url: str = "") -> List[Dict[str, str]]:
        try:
            # r-streng: \d hører til JavaScript-regexen under, ikke til Python.
            # Uten r-en tolker Python \d som en ukjent escape (advarsel i dag,
            # feil i en senere versjon) — og JS-en ville fått noe annet enn den ba om.
            rå = self.nl.page.evaluate(r"""
                (function () {
                  function tekst(el) { return (el.innerText || el.textContent || '').trim(); }
                  let beste = null, flest = 0;
                  for (const t of document.querySelectorAll('table')) {
                    const n = t.querySelectorAll('tbody tr').length;
                    if (n > flest) { flest = n; beste = t; }
                  }
                  if (!beste) return null;
                  const overskrifter = Array.from(
                    beste.querySelectorAll('thead th, thead td')).map(tekst);
                  const rader = [];
                  beste.querySelectorAll('tbody tr').forEach(function (tr) {
                    const celler = Array.from(tr.querySelectorAll('td')).map(function (td) {
                      // Tittellenken på Euronext har href="" og åpner en modal.
                      // Leser vi a.href, får vi LISTESIDENS egen adresse — og
                      // det var nettopp det som gjorde at hele lageret ble fylt
                      // med den samme søkeresultatsida i stedet for meldinger.
                      // Nummeret vi trenger står i data-node-nid.
                      const a = td.querySelector('a');
                      let nid = '';
                      if (a) {
                        nid = a.getAttribute('data-node-nid') || '';
                        if (!nid) {
                          const mal = a.getAttribute('data-target') || '';
                          const t = mal.match(/(\d{3,})/);
                          if (t) nid = t[1];
                        }
                      }
                      const rå = a ? (a.getAttribute('href') || '') : '';
                      return {tekst: tekst(td), nid: nid,
                              href: (a && rå && rå !== '#') ? a.href : ''};
                    });
                    if (celler.length) rader.push(celler);
                  });
                  return {overskrifter: overskrifter, rader: rader};
                })()
            """)
        except Exception as e:
            self.logger.warning(f"   Klarte ikke lese resultattabellen — {feiltekst(e)}")
            return []
        if not rå or not rå.get("rader"):
            return []

        plass: Dict[str, int] = {}
        for i, o in enumerate(rå.get("overskrifter") or []):
            nøkkel = self.OVERSKRIFTER.get(rens(o).lower())
            if nøkkel and nøkkel not in plass:
                plass[nøkkel] = i

        ut: List[Dict[str, str]] = []
        for celler in rå["rader"]:
            def hent(felt: str, standard: int) -> Dict[str, str]:
                i = plass.get(felt, standard if not plass else None)
                if i is None or i >= len(celler):
                    return {"tekst": "", "href": ""}
                return celler[i]

            tid = hent("tid", 0)["tekst"]
            tittelcelle = hent("tittel", 2)
            d = tolk_dato(tid)
            kl = tolk_klokkeslett(tid)
            href = tittelcelle.get("href") or next(
                (c["href"] for c in celler if c.get("href")), "")
            nid = rens(tittelcelle.get("nid")) or next(
                (rens(c.get("nid")) for c in celler if rens(c.get("nid"))), "")
            ut.append({
                "nid": nid, "side_url": rens(side_url),
                "tid_ra": rens(tid), "dato": iso(d),
                "klokkeslett": kl.strftime("%H:%M") if kl else "",
                "selskap_euronext": rens(hent("selskap", 1)["tekst"]),
                "tittel": rens(tittelcelle.get("tekst")),
                "sektor": rens(hent("sektor", 3)["tekst"]),
                "kategori": rens(hent("kategori", 4)["tekst"]),
                "href": rens(href),
            })
        return ut

    def finn_pdf_lenke(self) -> str:
        try:
            return self.nl.page.evaluate(
                "(function(){const a=document.querySelector("
                "'a[href$=\".pdf\"], a[href*=\".pdf?\"]');return a?a.href:'';})()") or ""
        except Exception:
            return ""

    def last_ned_pdf(self, lenke: str, mal: Path) -> bool:
        try:
            svar = self.nl.context.request.get(lenke, timeout=self.opp.pdf_timeout_ms)
            if not svar.ok:
                return False
            kropp = svar.body()
            if not kropp or not kropp[:5].startswith(b"%PDF"):
                return False
            mal.parent.mkdir(parents=True, exist_ok=True)
            mal.write_bytes(kropp)
            return True
        except Exception as e:
            self.logger.debug(f"PDF-nedlasting feilet: {feiltekst(e)}")
            return False


def fjern_sprakdubletter(rader: List[Dict[str, str]], minutter: int = 3
                         ) -> Tuple[List[Dict[str, str]], int]:
    """
    Euronext publiserer den SAMME meldingen på norsk og engelsk. Uten dette
    telles hvert innsidekjøp to ganger.

    Den gamle regelen krevde nøyaktig samme klokkeslett. Blir de to
    versjonene stemplet ett minutt fra hverandre — og det blir de ofte —
    overlevde begge. Nå slås de sammen når de er innenfor noen få minutter OG
    har ulikt språk. Er språket det samme, er det to ekte meldinger, og da
    skal begge stå: flere handler samme dag ER klyngesignalet.
    """
    per_dag: Dict[Tuple[str, str], List[Dict[str, str]]] = {}
    for r in rader:
        per_dag.setdefault((rens(r.get("selskap_euronext")).upper(),
                            r.get("dato", "")), []).append(r)

    beholdt: List[Dict[str, str]] = []
    fjernet = 0
    for gruppe in per_dag.values():
        for r in gruppe:
            r.setdefault("sprak", gjett_sprak(f"{r.get('tittel')} {r.get('kategori')}"))
        gruppe.sort(key=lambda r: r.get("klokkeslett", ""))
        brukt: List[Dict[str, str]] = []
        for r in gruppe:
            kl = tolk_klokkeslett(r.get("klokkeslett"))
            par = None
            for b in brukt:
                kl_b = tolk_klokkeslett(b.get("klokkeslett"))
                if not kl or not kl_b:
                    continue
                diff = abs((kl.hour * 60 + kl.minute) - (kl_b.hour * 60 + kl_b.minute))
                if (diff <= minutter and r.get("sprak") != b.get("sprak")
                        and r.get("sprak") and b.get("sprak")):
                    par = b
                    break
            if par is None:
                brukt.append(r)
                continue
            fjernet += 1
            # Behold den engelske: uttrekket kjenner begge språk, men engelsk
            # MAR-skjema er mest ensartet.
            if par.get("sprak") != "EN" and r.get("sprak") == "EN":
                brukt[brukt.index(par)] = r
        beholdt.extend(brukt)

    beholdt.sort(key=lambda r: (r.get("dato", ""), r.get("klokkeslett", "")), reverse=True)
    return beholdt, fjernet


def rydd_gammelt_format(opp: Oppsett, lagret: Dict[str, Rad],
                        logger: logging.Logger) -> int:
    """
    Kaster artiklene fra før node-nummeret ble nøkkelen.

    De er ikke meldinger. Det er den samme søkeresultatsida, lagret én gang
    per melding, en halv megabyte om gangen. Blir de stående, leser steg 2
    dem om igjen ved hver kjøring og finner det samme intet — og de gamle
    radene ville dessuten telt hver melding to ganger, siden samme melding
    fikk to nøkler når den ble funnet gjennom to datovinduer.

    En rad uten `Node_ID` som peker på en fil så stor at den bare KAN være
    en hel side, ryddes bort. Rader uten fil ryddes også: de har ingenting å
    gi steg 2 uansett.
    """
    kastet = frigjort = 0
    for mid in list(lagret):
        rad = lagret[mid]
        if rens(rad.get("Node_ID")):
            continue
        navn = rens(rad.get("HTML_Fil"))
        sti = opp.artikkel_dir / navn if navn else None
        stor = bool(sti and sti.exists() and sti.stat().st_size >= 100_000)
        if navn and sti is not None and sti.exists() and not stor:
            continue                       # ekte melding fra en eldre kjøring
        if sti is not None and sti.exists():
            try:
                frigjort += sti.stat().st_size
                sti.unlink()
            except OSError:
                pass
        del lagret[mid]
        kastet += 1
    if kastet:
        logger.warning(
            f"🧹 {kastet} artikler fra forrige format kastet — de var "
            f"LISTESIDEN, ikke meldingen ({frigjort / 1e6:.0f} MB frigjort). "
            f"De hentes på nytt nå, som ekte meldinger.")
    return kastet


def steg1_nedlasting(opp: Oppsett, logger: logging.Logger, kun: str = "",
                     aksjeliste: str = "", fersk_liste: bool = False) -> Dict[str, Any]:
    """
    Henter artiklene. Returnerer en oppsummering til statustavlen.

    Kaster videre ved ImportError (Playwright mangler) og andre uventede
    feil — kjøreren fanger dem og markerer steget som feilet uten å ta
    resten av kjeden med seg.
    """
    opp.lag_mapper()
    lagret = {r["Melding_ID"]: r for r in les_csv(opp.indeks_csv) if r.get("Melding_ID")}
    logger.info(f"📂 {len(lagret)} artikler i lageret fra før")
    if rydd_gammelt_format(opp, lagret, logger):
        _lagre_indeks(opp, lagret)
        # Vannmerkene beskrev det gamle lageret. Står de, hopper vi over hvert
        # eneste selskap og henter aldri meldingene vi nettopp kastet.
        vm_rydd = Vannmerke(opp.vannmerke_json, logger)
        vm_rydd.nullstill(GRUPPE_ARTIKLER)
        vm_rydd.lagre()

    if opp.offline:
        logger.info("⏭️  --offline: henter ingenting fra Euronext.")
        return {"status": "HOPPET", "detaljer": f"--offline · {len(lagret)} artikler på disk",
                "artikler": len(lagret), "nye": 0}

    vm = Vannmerke(opp.vannmerke_json, logger)
    eldste = opp.eldste_melding()
    i_dag = date.today()
    nye = oppdatert = hoppet = dubletter = feil = uten_html = ajour = 0
    uten_svar = 0
    kjoring_start = time.time()

    with Nettleser(opp, logger) as nl:
        # Aksjelista hentes med den SAMME nettleseren steg 1 uansett må
        # starte. Da slipper vi å åpne Chromium to ganger, og lista er fersk
        # før første selskap røres.
        fil = sikre_aksjeliste(opp, logger, nl, egen=aksjeliste, tving=fersk_liste)
        if fil is None:
            forklar_manglende_aksjeliste(opp, logger, aksjeliste)
            raise RuntimeError("ingen aksjeliste å hente selskaper fra")
        selskaper = bygg_selskaper(opp, logger, str(fil))
        if not selskaper:
            raise RuntimeError(f"aksjelista {fil.name} ga null selskaper")
        if kun:
            nål = kun.strip().upper()
            selskaper = [s for s in selskaper
                         if nål in rens(s.get("Selskap")).upper()
                         or nål in rens(s.get("Ticker")).upper()]
            if not selskaper:
                raise RuntimeError(f"fant ikke «{kun}» i selskapslista")
            logger.info(f"🔍 Begrenset til {len(selskaper)} selskap(er) via --selskap")

        klient = Euronext(nl, opp, logger)
        for nr, s in enumerate(selskaper, start=1):
            navn = rens(s.get("Selskap"))
            isin = rens(s.get("ISIN")).upper()
            ticker = rens(s.get("Ticker")).upper()
            if not isin:
                continue
            ajour_validert, fra = artikkel_vindu(vm, navn, opp, i_dag)
            if ajour_validert:
                ajour += 1
                continue

            logger.info(f"\n[{nr}/{len(selskaper)}] {navn}  ({ticker})  fra {fra}")
            start_tid = time.time()
            try:
                rader, inne = klient.hent_liste([isin], fra)
            except KeyboardInterrupt:
                raise
            except Exception as e:
                feil += 1
                uten_svar += 1
                vm.merk_feil(GRUPPE_ARTIKLER, navn, feiltekst(e))
                vm.lagre()
                logger.error(f"   ❌ {feiltekst(e)[:140]}")
                continue

            if not inne:
                # Vi kom aldri inn på lista. Vannmerket skal IKKE flyttes —
                # ellers står selskapet som ferdig uten at vi har sett en
                # eneste melding, og neste kjøring hopper over det.
                feil += 1
                uten_svar += 1
                vm.merk_feil(GRUPPE_ARTIKLER, navn, "kom ikke inn på listesiden")
                vm.lagre()
                logger.error("   ❌ Kom ikke inn på listesiden — vannmerket "
                             "står urørt, selskapet prøves på nytt neste gang")
                if opp.maks_feil_paa_rad and uten_svar >= opp.maks_feil_paa_rad:
                    raise RuntimeError(
                        f"{uten_svar} selskaper på rad uten svar fra "
                        f"{opp.euronext_base} — det er forbindelsen som er nede, "
                        f"ikke selskapene. Stoppet uten å prøve de "
                        f"{len(selskaper) - nr} som var igjen.")
                continue
            uten_svar = 0

            rader, d = fjern_sprakdubletter(rader)
            dubletter += d
            if not rader:
                logger.info("   Ingen meldinger i perioden")
                vm.sett(GRUPPE_ARTIKLER, navn, i_dag, artikler=0,
                        liste_validering=ARTIKKEL_VALIDERING)
                vm.lagre()
                continue

            n_ny, n_opp, n_hopp, n_tom = _hent_artikler(
                klient, opp, logger, lagret, rader, s, start_tid)
            nye += n_ny
            oppdatert += n_opp
            hoppet += n_hopp
            uten_html += n_tom

            if klient.mal and not getattr(klient, "_meldt_mal", False):
                klient._meldt_mal = True
                logger.info("   ⚡ Meldingene hentes nå direkte, uten å åpne "
                            "hver enkelt i nettleseren.")

            datoer = sorted(r["dato"] for r in rader if r.get("dato"))
            periode = f"  {datoer[0]} … {datoer[-1]}" if datoer else ""
            deler = [f"{n_ny} nye"]
            if n_opp:
                deler.append(f"{n_opp} oppdatert")
            if n_hopp:
                deler.append(f"{n_hopp} hadde vi")
            if n_tom:
                deler.append(f"{n_tom} uten HTML")
            if d:
                deler.append(f"{d} språkdubletter slått sammen")
            logger.info(f"   → {len(rader)} meldinger{periode}   ({', '.join(deler)})   "
                        f"lager: {len(lagret)}")

            # Vannmerket flyttes bare når vi faktisk fikk noe. Ellers ville en
            # kjøring som hentet tusen tomme rader blitt stående som «ferdig».
            hentet = n_ny + n_opp
            if n_tom or n_ny + n_opp + n_hopp < len(rader):
                feil += 1
                vm.merk_feil(GRUPPE_ARTIKLER, navn, "incomplete article bodies — retry required")
                logger.warning(f"   ⚠️  artikkelteksten er ufullstendig — "
                               f"{navn} merkes for ny henting")
            else:
                vm.sett(GRUPPE_ARTIKLER, navn, i_dag, artikler=len(rader),
                        liste_validering=ARTIKKEL_VALIDERING)
            vm.lagre()
            _lagre_indeks(opp, lagret)

            if nr % 10 == 0 and nr < len(selskaper):
                brukt = time.time() - kjoring_start
                igjen = brukt / nr * (len(selskaper) - nr)
                logger.info(f"   ⏳ {nr}/{len(selskaper)} selskaper på {brukt/60:.0f} min "
                            f"— anslagsvis {igjen/60:.0f} min igjen")
            time.sleep(opp.pause_mellom_selskaper_s)

    vm.lagre()
    _lagre_indeks(opp, lagret)
    logger.info(f"\nNye: {nye}   Oppdatert: {oppdatert}   Hadde fra før: {hoppet}   "
                f"Språkdubletter: {dubletter}   Uten HTML: {uten_html}   Feil: {feil}")
    # Uten denne linjen står det «Nye: 0  Oppdatert: 0  Hadde fra før: 0» over
    # et lager på 3912 artikler, og tallene ser ut som en feil i tellingen. De
    # er riktige — selskapene ble aldri åpnet, fordi vannmerket sa ferdig.
    if ajour:
        logger.info(f"{ajour} av {len(selskaper)} selskaper var ajour og ble ikke "
                    f"åpnet i det hele tatt. Bruk --full for å hente dem uansett.")
    logger.info(f"Lageret: {len(lagret)} artikler  •  HTML i {opp.artikkel_dir}")
    if klient.via_url or klient.via_klikk:
        logger.info(f"Meldingene: {klient.via_url} hentet direkte, "
                    f"{klient.via_klikk} åpnet i nettleseren")

    # Noen få selskaper som feiler er Euronext som hikker, ikke en ødelagt
    # nedlasting: vannmerket deres står urørt, så de prøves igjen neste gang,
    # og artiklene på disk er fortsatt gyldige. Samme toleranse som kursene i
    # steg 4. Før ga ÉN feil DELVIS, og DELVIS i steg 1 stanser kjeden før
    # backtesten — da ble ingenting i 6_backtest oppdatert.
    status = ("OK" if feil == 0 or (feil <= max(3, len(selskaper) * 0.1)
                                   and feil < len(selskaper))
              else "DELVIS")
    return {"status": status, "artikler": len(lagret), "nye": nye,
            "feil": feil, "uten_html": uten_html, "ajour": ajour,
            "detaljer": f"{len(lagret)} artikler på disk ({nye} nye"
                        + (f", {ajour} selskaper ajour" if ajour else "")
                        + (f", {feil} selskaper feilet" if feil else "") + ")"}


def _hent_artikler(klient: Euronext, opp: Oppsett, logger: logging.Logger,
                   lagret: Dict[str, Rad], rader: List[Dict[str, str]],
                   s: Rad, start_tid: float) -> Tuple[int, int, int, int]:
    """
    Henter SELVE MELDINGEN for hver rad. (nye, oppdatert, hoppet, tomme).

    Den gamle versjonen navigerte til `rad["href"]` — men den href-en var
    listesidas egen adresse, fordi Euronext lar overskriften ha href="" og
    åpner en modal i stedet. Resultatet var at hver eneste «artikkel» på disk
    var den samme søkeresultatsida, lastet 3912 ganger. Alt nedstrøms arvet
    det: ingen transaksjoner, ingen kjøp, ingen backtest.

    Nå hentes meldingene per listeside, så sida lastes ÉN gang og alle
    meldingene på den plukkes mens vi står der.
    """
    navn = rens(s.get("Selskap"))
    nye = oppdatert = hoppet = tomme = 0

    # Rekkefølgen per side beholdes, så vi laster hver side høyst én gang.
    per_side: Dict[str, List[Dict[str, str]]] = {}
    for r in rader:
        if r.get("dato"):
            per_side.setdefault(rens(r.get("side_url")), []).append(r)

    for side_url, gruppe in per_side.items():
        if time.time() - start_tid > opp.maks_sekunder_per_selskap:
            logger.warning("   ⏱️  Tidsgrense for selskapet nådd — går videre")
            break

        # Hvilke på denne sida mangler vi i det hele tatt?
        mangler: List[Tuple[Dict[str, str], str, Path]] = []
        for r in gruppe:
            mid = lag_id(r.get("href", ""), navn, r["dato"],
                         r.get("klokkeslett", ""), r.get("tittel", ""),
                         r.get("nid", ""))
            htmlfil = opp.artikkel_dir / f"{mid}.html"
            gammel = lagret.get(mid)
            if (gammel and rens(gammel.get("HTML_Fil")) and htmlfil.exists()
                    and htmlfil.stat().st_size > opp.min_melding_tegn):
                hoppet += 1
                continue
            mangler.append((r, mid, htmlfil))
        if not mangler:
            continue

        # Sida lastes bare når vi faktisk trenger å klikke på den. Har vi
        # lært adressen, holder det å be om meldingene rett.
        på_sida = False
        if not klient.mal and side_url:
            på_sida = klient.nl.ga_til(side_url, vent_ms=700)
            if på_sida:
                klient.avvis_cookies()

        for i, (r, mid, htmlfil) in enumerate(mangler, start=1):
            if time.time() - start_tid > opp.maks_sekunder_per_selskap:
                logger.warning("   ⏱️  Tidsgrense for selskapet nådd — går videre")
                break
            råhtml = klient.hent_melding(r)
            if not råhtml and not på_sida and side_url:
                # Direkte henting slo feil. Da må vi inn på sida og klikke.
                på_sida = klient.nl.ga_til(side_url, vent_ms=700)
                if på_sida:
                    klient.avvis_cookies()
                    råhtml = klient.hent_melding(r)

            pdf_fil = ""
            if råhtml and opp.last_ned_pdf:
                lenke = klient.pdf_i(råhtml)
                if lenke and klient.last_ned_pdf(lenke, opp.pdf_dir / f"{mid}.pdf"):
                    pdf_fil = f"{mid}.pdf"

            if råhtml:
                try:
                    htmlfil.write_text(råhtml, encoding="utf-8")
                except OSError as e:
                    logger.debug(f"Kunne ikke skrive {htmlfil.name}: {feiltekst(e)}")
                    råhtml = ""
            if not råhtml:
                tomme += 1

            gammel = lagret.get(mid)
            lagret[mid] = {
                "Melding_ID": mid,
                "Node_ID": rens(r.get("nid")),
                "Selskap": navn,
                "Selskap_Euronext": r.get("selskap_euronext", ""),
                "Ticker": rens(s.get("Ticker")).upper(),
                "ISIN": rens(s.get("ISIN")).upper(),
                "Dato": r["dato"],
                "Klokkeslett": r.get("klokkeslett", ""),
                "Tittel": r.get("tittel", ""),
                "Kategori": r.get("kategori", ""),
                "Sektor": r.get("sektor", ""),
                "Sprak": r.get("sprak", "") or gjett_sprak(r.get("tittel", "")),
                "Kilde_URL": rens(r.get("href")) or rens(side_url),
                "HTML_Fil": f"{mid}.html" if råhtml else "",
                "HTML_Tegn": len(råhtml),
                "PDF_Fil": pdf_fil,
                "Hentet": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                "Status": "OK" if råhtml else "MANGLER_HTML",
            }
            if gammel is None:
                nye += 1
            else:
                oppdatert += 1

            if i % 10 == 0 or i == len(mangler):
                logger.info(f"   [{i}/{len(mangler)}] {r['dato']}  "
                            f"{len(råhtml):>6} tegn  {r.get('tittel','')[:44]}")
            time.sleep(opp.pause_mellom_artikler_s)
    return nye, oppdatert, hoppet, tomme


def _lagre_indeks(opp: Oppsett, lagret: Dict[str, Rad]) -> None:
    rader = sorted(lagret.values(),
                   key=lambda r: (str(r.get("Dato")), str(r.get("Selskap"))), reverse=True)
    skriv_csv(opp.indeks_csv, rader, INDEKS_KOLONNER)


# ══════════════════════════════════════════════════════════════════════════
# STEG 2 — TREKK MELDINGSTEKSTEN UT AV HTML-EN
# ══════════════════════════════════════════════════════════════════════════
#
# Her løses feilen som veltet den forrige kjøringen: 5 meldinger med NØYAKTIG
# samme brødtekst på 11 235 tegn, som begynte med «Cookies PreferencesWe
# process your data …». Uttrekket plukket cookie-vinduet i stedet for
# meldingen.
#
# Den gamle koden hadde to svakheter. Den lette etter cookie-tekst med en
# ORDLISTE («we use cookies»), og ordlista traff ikke akkurat denne
# formuleringen. Og når den til slutt oppdaget at teksten gjentok seg,
# STOPPET den hele kjøringen i stedet for å kaste teksten.
#
# Her er begge deler snudd:
#
#   GLOBAL SIDEMALSGJENKJENNING, ikke ordliste. To meldinger fra to selskaper
#   i to ulike år kan ikke ha identisk brødtekst — men et cookie-vindu, en
#   meny og en bunntekst står identisk på HVER side. Så vi går gjennom alle
#   artiklene ÉN gang og teller hvilke tekstblokker som går igjen. En blokk
#   som står ordrett i minst 20 % av artiklene ER sidemal, uansett hva den
#   inneholder. Ingen ordliste å vedlikeholde, og den fanger like godt den
#   neste banneren Euronext finner på.
#
#   SIDEMAL KASTES, KJØRINGEN FORTSETTER. En melding vi ikke fikk lest blir
#   stående som MANGLER_TEKST og kan hentes igjen. Den skal ikke kunne stoppe
#   de 3 000 andre.
#
# Reservene, i rekkefølge:  beste HTML-blokk → vedlagt PDF → ingenting.

TEKST_INDEKS_KOLONNER = ["Melding_ID", "Selskap", "Ticker", "Dato", "Klokkeslett",
                         "Tittel", "Tekst_Fil", "Tegn", "Kilde", "Sprak", "Status"]

# Tagger som ALDRI inneholder lesbar tekst. Disse kastes for godt.
_ALLTID_FJERN = {"script", "style", "noscript", "svg", "template", "iframe",
                 "canvas", "audio", "video", "select", "option"}

# Tagger som nesten aldri inneholder brødtekst. Disse fjernes MYKT: de kan
# ikke bli meldingskandidater, men teksten tas vare på til reserveuttrekket.
# Treffer regelen feil, er meldingen fortsatt lesbar.
_FJERN_TAGGER = {"script", "style", "noscript", "nav", "header", "footer", "aside",
                 "form", "svg", "button", "select", "option", "iframe", "template",
                 "figure", "picture", "video", "audio", "canvas", "label"}

# class/id-mønstre som betyr «dette er sidas ramme». Sikkerhetsnett i tillegg
# til den globale sidemalsgjenkjenningen — de to fanger ulike ting.
#
# Ordene står mellom ORDGRENSER, og de mest tvetydige er tatt ut. Den gamle
# lista traff som løs delstreng, og da fjernet «search» hele «research»-
# seksjonen, «share» tok «share-price» og «shareholder-info», og «header»
# tok hver eneste «card-header». På en side der meldingen tilfeldigvis ligger
# i en slik beholder forsvant HELE meldingen — og steget svarte null lest
# uten å kunne si hvorfor. Det som står igjen her er ord som aldri betyr noe
# annet enn sidas ramme. Resten fanges av den globale sidemalstellingen, som
# er et sterkere bevis uansett: en meny står ORDRETT likt på hver side.
_FJERN_MONSTER = re.compile(
    r"(?:^|[^a-z])("
    r"menu|nav|navbar|navigation|cookie|consent|onetrust|truste|gdpr|privacy|"
    r"breadcrumb|pager|pagination|footer|masthead|sidebar|"
    r"newsletter|subscribe|login|signin|toolbar|"
    r"skip|screen-reader|visually-hidden|sr-only|advert"
    r")(?:$|[^a-z])", re.IGNORECASE)

_BLOKK_TAGGER = {"div", "section", "article", "main", "p", "li", "tr", "td", "th",
                 "h1", "h2", "h3", "h4", "h5", "h6", "table", "ul", "ol", "dl",
                 "dt", "dd", "pre", "blockquote", "br"}
_KANDIDAT_TAGGER = {"div", "section", "article", "main", "td"}
_TOMME_TAGGER = {"br", "hr", "img", "input", "meta", "link", "source", "col",
                 "area", "base", "embed", "param", "track", "wbr"}

# Ord som bare finnes i sidas ramme. «close menu» står i mega-menyen og aldri
# i en børsmelding.
MENYORD = ("close menu", "lukk meny", "skip to main content", "hopp til hovedinnhold",
           "my watchlist", "min overvåkningsliste", "cookies preferences",
           "we process your data", "legitimate interest", "vendor list",
           "manage your preferences", "informasjonskapsler")

# Ord en ekte meldepliktig handel nesten alltid inneholder. Ett treff er ikke
# bevis, men det skiller en melding fra en meny.
MELDINGSORD = ("transaction", "transaksjon", "shares", "aksjer", "notification",
               "meldepliktig", "primary insider", "primærinnsider", "isin",
               "volume", "volum", "holding", "beholdning")


class _Blokkleser(HTMLParser):
    """
    Bygger et grovt tre av HTML-en og gir tilbake kandidatblokker med mål på
    hvor tekstlige de er.

    Skrevet på html.parser fra standardbiblioteket, ikke BeautifulSoup: én
    avhengighet mindre å mangle når du skal kjøre om et halvt år, og
    Euronext-sidene er ikke kompliserte nok til å trenge mer.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stabel: List[Dict[str, Any]] = [
            {"tag": "rot", "biter": [], "lenketegn": 0, "fjern": False, "hard": False}]
        self.kandidater: List[Dict[str, Any]] = []
        # Teksten fra mykt fjernede blokker. Den blir aldri en kandidat, men
        # den er med i sidetekst() — reserveuttrekket skal ikke gå tomt bare
        # fordi en class het noe med «search».
        self.mykt: List[str] = []

    # ── tre ──────────────────────────────────────────────────────────────
    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if tag in _TOMME_TAGGER:
            if tag == "br":
                self.stabel[-1]["biter"].append("\n")
            return
        d = {k.lower(): (v or "") for k, v in attrs}
        merke = " ".join([d.get("class", ""), d.get("id", ""), d.get("role", ""),
                          d.get("aria-label", ""), d.get("data-testid", "")])
        hard = self.stabel[-1]["hard"] or tag in _ALLTID_FJERN
        fjern = (hard or self.stabel[-1]["fjern"] or tag in _FJERN_TAGGER
                 or bool(_FJERN_MONSTER.search(merke))
                 or d.get("aria-hidden") == "true" or "hidden" in d)
        self.stabel.append({"tag": tag, "biter": [], "lenketegn": 0,
                            "fjern": fjern, "hard": hard})

    def handle_startendtag(self, tag, attrs) -> None:
        if tag.lower() == "br":
            self.stabel[-1]["biter"].append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in _TOMME_TAGGER:
            return
        # Tolerant lukking: finn nærmeste åpne tagg med samme navn. HTML i
        # naturen er full av glemte sluttagger, og en streng parser ville
        # kastet halve dokumentet.
        traff = None
        for i in range(len(self.stabel) - 1, 0, -1):
            if self.stabel[i]["tag"] == tag:
                traff = i
                break
        if traff is None:
            return
        while len(self.stabel) > traff:
            self._lukk()

    def handle_data(self, data: str) -> None:
        if data:
            self.stabel[-1]["biter"].append(data)

    def close(self) -> None:                      # type: ignore[override]
        super().close()
        while len(self.stabel) > 1:
            self._lukk()

    def sidetekst(self) -> str:
        """Hele sidas lesbare tekst — også det som ble mykt fjernet."""
        deler = ["".join(self.stabel[0]["biter"])] + self.mykt
        return rens_flerlinje("\n".join(deler))

    def _lukk(self) -> None:
        n = self.stabel.pop()
        forelder = self.stabel[-1]
        tekst = "".join(n["biter"])
        if n["hard"] or not tekst.strip():
            return                                # hele undertreet forsvinner
        if n["fjern"]:
            # Myk fjerning: blokka kan ikke bli meldingskandidat, men teksten
            # spares til reserveuttrekket.
            #
            # Den må bobles opp til den YTTERSTE fjernede blokka først. Tok vi
            # vare på hver bit for seg, ville en <h1> og hver enkelt <td> falt
            # under lengdekravet og forsvunnet — og en MAR-melding ER en
            # tabell med korte celler. Da satt vi igjen med avsnittene og
            # mistet alle tallene, som er hele poenget.
            if forelder["fjern"]:
                forelder["biter"].append(
                    "\n" + tekst + "\n" if n["tag"] in _BLOKK_TAGGER else tekst)
            elif len(tekst) >= 60:
                self.mykt.append(tekst)
            return
        if n["tag"] in _BLOKK_TAGGER:
            forelder["biter"].append("\n" + tekst + "\n")
        else:
            forelder["biter"].append(tekst)
        forelder["lenketegn"] += n["lenketegn"] + (len(tekst) if n["tag"] == "a" else 0)
        if n["tag"] in _KANDIDAT_TAGGER:
            ren = rens_flerlinje(tekst)
            if len(ren) >= 150:
                self.kandidater.append(_mål(ren, n["tag"], n["lenketegn"]))


def _mål(tekst: str, tag: str, lenketegn: int) -> Dict[str, Any]:
    """Tallene som skiller en melding fra en meny."""
    linjer = [l for l in tekst.splitlines() if l.strip()]
    korte = sum(1 for l in linjer if len(l) < 30)
    liten = tekst.lower()
    return {"tekst": tekst, "tag": tag, "tegn": len(tekst),
            "lenketetthet": min(1.0, lenketegn / max(1, len(tekst))),
            "kortlinjer": (korte / len(linjer)) if linjer else 1.0,
            "meldingsord": sum(1 for o in MELDINGSORD if o in liten),
            "menyord": sum(1 for o in MENYORD if o in liten),
            "avtrykk": avtrykk(tekst)}


def les_side(rå_html: str) -> Tuple[List[Dict[str, Any]], str]:
    """
    Én gjennomgang av HTML-en gir BEGGE delene: kandidatblokkene og hele
    sidas lesbare tekst.

    De to er reserve for hverandre. Blokkvalget er presist, men avhenger av
    at Euronext bygger sidene sine på en bestemt måte — endrer de en class,
    står vi med null kandidater og null tekst. Sideteksten avhenger bare av
    at det finnes tekst på sida.
    """
    if not rå_html:
        return [], ""
    leser = _Blokkleser()
    try:
        leser.feed(rå_html)
        leser.close()
    except Exception:
        # En ødelagt side skal gi det vi rakk å lese, ikke velte steget.
        pass
    try:
        return leser.kandidater, leser.sidetekst()
    except Exception:
        return leser.kandidater, ""


def kandidatblokker(rå_html: str) -> List[Dict[str, Any]]:
    """Alle blokkene på sida som kan tenkes å være meldingen."""
    return les_side(rå_html)[0]


def velg_beste(kandidater: Sequence[Dict[str, Any]], sidemal: Set[str],
               min_lengde: int) -> Optional[Dict[str, Any]]:
    """
    Velger den blokken som ser ut som en melding. None når ingen gjør det.

    Den gamle regelen var «første beholder som er lang nok». Den fanget
    Euronext sin hovedmeny og cookie-vinduet. Det som skiller en melding fra
    sidas ramme er ikke lengden:
        · en meny er mange KORTE linjer, en melding er prosa
        · en meny er nesten bare LENKER
        · en meny inneholder aldri «transaksjon» eller «meldepliktig»
        · og en meny står ORDRETT likt på hver eneste side  ← sterkeste tegnet

    Ved praktisk talt lik poengsum vinner den KORTESTE — den er den mest
    spesifikke beholderen, altså selve meldingen og ikke noe rundt den.
    """
    # To runder. Den strenge er den vi vil ha. Den milde finnes fordi den
    # forrige kjøringen endte på 0 av 3912 leste: hver eneste kandidat falt
    # på ett av kravene under, og da satt vi igjen med ingenting. En melding
    # lest med litt meny rundt seg er uendelig mye bedre enn ingen melding —
    # og MAR-skjemaet er en TABELL, altså mange korte linjer, så nettopp
    # kortlinjekravet rammer de riktige meldingene hardest.
    for kortlinjer, lenker, tål_menyord in ((0.55, 0.45, False), (0.92, 0.75, True)):
        gode = []
        for k in kandidater:
            if k["avtrykk"] in sidemal:
                continue                      # står ordrett på alle sidene
            if k["menyord"] and not (tål_menyord and k["meldingsord"] >= 2):
                continue
            if k["kortlinjer"] > kortlinjer or k["lenketetthet"] > lenker:
                continue
            gode.append(k)
        if gode:
            break
    if not gode:
        return None

    # Har noen kandidat meldingsord, er de andre uinteressante.
    med_ord = [g for g in gode if g["meldingsord"] > 0]
    if med_ord:
        gode = med_ord

    lange = [g for g in gode if g["tegn"] >= min_lengde]
    if not lange:
        lange = [g for g in gode if g["tegn"] >= 150]   # korte meldinger finnes
    if not lange:
        return None

    def poeng(g: Dict[str, Any]) -> float:
        return (g["tegn"] * (1 - g["lenketetthet"]) * (1 - g["kortlinjer"])
                * (1.0 + 0.5 * min(g["meldingsord"], 4)))

    beste = max(lange, key=poeng)
    beste_poeng = poeng(beste)
    for g in lange:                     # like god, men kortere = mer presis
        if poeng(g) > beste_poeng * 0.95 and g["tegn"] < beste["tegn"]:
            beste = g
    return beste


def _linjeavtrykk(tekst: str) -> Set[str]:
    """Ett avtrykk per LINJE — grunnlaget for reserveuttrekket."""
    ut: Set[str] = set()
    for l in tekst.splitlines():
        l = l.strip().lower()
        if len(l) >= 4:
            ut.add(avtrykk(l, 12))
    return ut


def uten_sidemal(sidetekst: str, linjemal: Set[str], min_lengde: int,
                 maks: int = 40_000) -> str:
    """
    Reserven: den delen av sida som ligner mest på en melding.

    Første forsøk her var å STRYKE hver linje som gikk igjen på de andre
    sidene. Det virket på menyen og drepte meldingen: et MAR-skjema har de
    samme merkelappene på hver eneste melding — «Nature of transaction»,
    «Volume», «Price» står ordrett i alle sammen. De ble strøket som sidemal,
    og igjen sto tallene uten å si hva de var tall for.

    Gjentakelsene brukes derfor til å FINNE meldingen, ikke til å slette noe,
    i tre forsøk som gir seg mer og mer:

      1  Strekningen med høyest overvekt av unik tekst. Unike linjer teller
         positivt, gjentatte negativt, begge etter lengde — så en meny, som
         er en lang ubrutt rekke gjentatte linjer, faller ut, mens en
         merkelapp midt inne i meldingen blir med.
      2  Alle linjer som er unike eller står tett inntil noe unikt. En
         merkelapp står alltid ved siden av verdien sin; en meny gjør ikke.
      3  Hele sida — men BARE hvis den har nok unikt innhold til at det kan
         være en melding. Uten den siste betingelsen ville sider uten melding
         fått cookie-vinduet lagret som «tekst», og da er vi tilbake til
         feilen som veltet forrige kjøring: tre tusen meldinger med samme
         brødtekst.
    """
    linjer = [l for l in sidetekst.splitlines() if l.strip()]
    if not linjer:
        return ""

    def svar(valgte: Sequence[str]) -> str:
        ren = rens_flerlinje("\n".join(valgte))[:max(1000, int(maks))]
        return ren if len(ren) >= min_lengde else ""

    if not linjemal:                       # ingen sammenlikningsgrunnlag ennå
        return svar(linjer)

    unik = [avtrykk(l.strip().lower(), 12) not in linjemal for l in linjer]
    lengder = [float(max(4, len(l.strip()))) for l in linjer]

    # 1 — største sammenhengende overvekt av unik tekst (Kadane)
    beste_sum, beste = float("-inf"), (0, len(linjer))
    løpende, start = 0.0, 0
    for i, n in enumerate(lengder):
        v = n if unik[i] else -0.5 * n
        if løpende <= 0:
            løpende, start = v, i
        else:
            løpende += v
        if løpende > beste_sum:
            beste_sum, beste = løpende, (start, i + 1)
    ut = svar(linjer[beste[0]:beste[1]])
    if ut:
        return ut

    # 2 — unikt, pluss det som står inntil noe unikt
    nær = [i for i in range(len(linjer))
           if any(unik[j] for j in range(max(0, i - 2), min(len(linjer), i + 3)))]
    ut = svar([linjer[i] for i in nær])
    if ut:
        return ut

    # 3 — hele sida, men bare når det finnes noe eget på den
    if sum(lengder[i] for i in range(len(linjer)) if unik[i]) >= 100:
        return svar(linjer)
    return ""


def _les_html(opp: Oppsett, r: Rad) -> str:
    navn = rens(r.get("HTML_Fil"))
    if not navn:
        return ""
    sti = opp.artikkel_dir / Path(navn).name
    if not sti.exists():
        return ""
    try:
        return sti.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _utvalg(rader: Sequence[Rad], maks: int) -> List[Rad]:
    """Jevnt fordelt utvalg — ikke de 500 første, som er de 500 nyeste."""
    if not maks or len(rader) <= maks:
        return list(rader)
    steg = len(rader) / float(maks)
    return [rader[min(len(rader) - 1, int(i * steg))] for i in range(maks)]


def finn_sidemal(opp: Oppsett, rader: Sequence[Rad],
                 logger: logging.Logger) -> Tuple[Set[str], Set[str], List[Rad]]:
    """
    Første gjennomgang: hvilke tekstblokker går igjen på tvers av artikler?

    Dette er hele fiksen. En blokk som står ORDRETT likt i minst
    `sidemal_andel` av artiklene er cookie-vindu, meny eller bunntekst — den
    kan ikke være en børsmelding. Vi trenger ingen ordliste og fanger like
    godt den neste banneren Euronext finner på.
    """
    if len(rader) < 20:
        logger.info("   (for få artikler til å lete etter sidemal — hopper over)")
        return set(), set(), []

    utval = _utvalg(rader, opp.sidemal_prove)
    if len(utval) < len(rader):
        logger.info(f"   (ser på {len(utval)} jevnt fordelte artikler av {len(rader)} "
                    f"— sidemal står likt på alle)")

    teller: Dict[str, int] = {}
    linjeteller: Dict[str, int] = {}
    prøve: Dict[str, str] = {}
    lest = 0
    for nr, r in enumerate(utval, start=1):
        rå = _les_html(opp, r)
        if not rå:
            continue
        lest += 1
        kandidater, sidetekst = les_side(rå)
        for k in {kb["avtrykk"]: kb for kb in kandidater}.values():
            teller[k["avtrykk"]] = teller.get(k["avtrykk"], 0) + 1
            prøve.setdefault(k["avtrykk"], k["tekst"][:160])
        for a in _linjeavtrykk(sidetekst):
            linjeteller[a] = linjeteller.get(a, 0) + 1
        if nr % 100 == 0:
            logger.info(f"   … leter etter sidemal, {nr}/{len(utval)} artikler")

    if lest < 20:
        return set(), set(), []
    grense = max(opp.sidemal_minst, int(lest * opp.sidemal_andel))
    sidemal = {a for a, n in teller.items() if n >= grense}
    linjemal = {a for a, n in linjeteller.items() if n >= grense}
    logger.info(f"🧹 {len(linjemal)} tekstLINJER går igjen i ≥{grense} av {lest} "
                f"artikler — de lukes ut av reserveuttrekket.")

    rapport = [{"Avtrykk": a, "Artikler": teller[a],
                "Andel_Pst": round(100.0 * teller[a] / lest, 1),
                "Utdrag": rens(prøve.get(a, ""))[:120]}
               for a in sorted(sidemal, key=lambda x: -teller[x])]
    if sidemal:
        logger.info(f"🧹 {len(sidemal)} tekstblokker går igjen i ≥{grense} av {lest} "
                    f"artikler og er dermed sidemal, ikke melding:")
        for r in rapport[:6]:
            logger.info(f"      {r['Artikler']:>5} artikler ({r['Andel_Pst']:>5.1f} %)  "
                        f"«{r['Utdrag'][:70]}»")
        if len(rapport) > 6:
            logger.info(f"      … og {len(rapport) - 6} til (se {opp.sidemal_csv.name})")
    else:
        logger.info("🧹 Fant ingen gjennomgående sidemalsBLOKK — "
                    "uttrekket står fritt.")
    return sidemal, linjemal, rapport


def _pdf_tekst(sti: Path, logger: logging.Logger) -> str:
    """
    Teksten fra en vedlagt PDF — den EKTE teksten, ikke et bilde av den.

    Har PDF-en ingen innebygd tekst, gir vi opp med vilje. Alternativet er
    tegngjenkjenning, og den leser TALL feil. En melding vi ikke fikk lest kan
    hentes igjen; et beløp som er lest feil oppdager ingen.
    """
    if not sti.exists():
        return ""
    try:
        import fitz                      # PyMuPDF, valgfritt
    except ImportError:
        return ""
    try:
        dok = fitz.open(str(sti))
        try:
            biter = [side.get_text() or "" for side in dok]
        finally:
            dok.close()
        return rens_flerlinje("\n\n".join(biter))
    except Exception as e:
        logger.debug(f"PDF-tekst feilet for {sti.name}: {feiltekst(e)}")
        return ""


def steg2_tekst(opp: Oppsett, logger: logging.Logger,
                tving: bool = False) -> Dict[str, Any]:
    """Leser HTML-en fra steg 1 og skriver én .txt per melding."""
    opp.lag_mapper()
    indeks = les_csv(opp.indeks_csv)
    if not indeks:
        return {"status": "HOPPET",
                "detaljer": f"ingen {opp.indeks_csv.name} — kjør steg 1 først"}

    logger.info(f"📂 {len(indeks)} artikler i indeksen")
    sidemal, linjemal, sidemal_rapport = finn_sidemal(opp, indeks, logger)
    if sidemal_rapport:
        skriv_csv(opp.sidemal_csv, sidemal_rapport,
                  ["Avtrykk", "Artikler", "Andel_Pst", "Utdrag"])

    # Hvor teksten kom fra sist. Uten den mister en ny runde sporet av hvilke
    # meldinger som ble lest ordentlig og hvilke som kom fra reserven.
    forrige_kilde = {rens(r.get("Melding_ID")): rens(r.get("Kilde"))
                     for r in les_csv(opp.tekst_indeks_csv)}

    ut: List[Rad] = []
    ok = fra_pdf = fra_rest = uendret = uten = 0
    per_kilde: Dict[str, int] = {}
    lengder: List[int] = []
    avtrykkene: Set[str] = set()

    for nr, r in enumerate(indeks, start=1):
        mid = rens(r.get("Melding_ID"))
        if not mid:
            continue
        tekstfil = opp.tekst_dir / f"{mid}.txt"
        tittel = rens(r.get("Tittel"))
        tekst, kilde = "", "INGEN"

        # Har vi allerede en brukbar tekst, og ingen ba om ny runde, er det
        # ingenting å gjøre. Det gjør steg 2 nesten gratis å kjøre om igjen.
        if not tving and tekstfil.exists() and tekstfil.stat().st_size > 200:
            try:
                tekst = tekstfil.read_text(encoding="utf-8")
                kilde = forrige_kilde.get(mid) or "LAGRET"
                uendret += 1
            except OSError:
                tekst = ""

        if not tekst:
            rå = _les_html(opp, r)
            if rå:
                kandidater, sidetekst = les_side(rå)
                beste = velg_beste(kandidater, sidemal, opp.min_tekstlengde)
                if beste:
                    tekst, kilde = beste["tekst"], "HTML"
                else:
                    # Reserven. Fant vi ingen blokk som SER UT som en melding,
                    # tar vi hele sida og luker ut linjene som står på alle de
                    # andre sidene også. Litt meny på slutten er en billig pris
                    # for å slippe «0 av 3912 lest».
                    rest = uten_sidemal(sidetekst, linjemal, opp.min_tekstlengde,
                                        opp.maks_resttekst)
                    if rest:
                        tekst, kilde = rest, "HTML_RESTTEKST"
                        fra_rest += 1
            if not tekst and opp.bruk_pdf_reserve and rens(r.get("PDF_Fil")):
                tekst = _pdf_tekst(opp.pdf_dir / rens(r.get("PDF_Fil")), logger)
                if tekst:
                    kilde = "PDF"
                    fra_pdf += 1
            if tekst:
                try:
                    tekstfil.write_text(tekst, encoding="utf-8")
                except OSError as e:
                    logger.debug(f"Kunne ikke skrive {tekstfil.name}: {feiltekst(e)}")

        if tekst:
            ok += 1
            lengder.append(len(tekst))
            avtrykkene.add(avtrykk(tekst))
        else:
            uten += 1
        per_kilde[kilde] = per_kilde.get(kilde, 0) + 1

        ut.append({"Melding_ID": mid, "Selskap": rens(r.get("Selskap")),
                   "Ticker": rens(r.get("Ticker")).upper(), "Dato": rens(r.get("Dato")),
                   "Klokkeslett": rens(r.get("Klokkeslett")), "Tittel": tittel,
                   "Tekst_Fil": f"{mid}.txt" if tekst else "", "Tegn": len(tekst),
                   "Kilde": kilde,
                   "Sprak": rens(r.get("Sprak")) or gjett_sprak(tekst or tittel),
                   "Status": "OK" if tekst else "MANGLER_TEKST"})

        if nr % 500 == 0:
            logger.info(f"   … {nr}/{len(indeks)} artikler behandlet")

    skriv_csv(opp.tekst_indeks_csv, ut, TEKST_INDEKS_KOLONNER)
    logger.info(f"💾 {opp.tekst_indeks_csv.name}  ({len(ut)} rader)")
    logger.info(f"📝 Tekstfilene ligger i {opp.tekst_dir}")

    logger.info(f"\n   Med tekst .......... {ok}/{len(ut)}  "
                f"({100.0*ok/max(1,len(ut)):.1f} %)")
    if lengder:
        logger.info(f"   Lengde ............. median {int(median(lengder))} tegn, "
                    f"korteste {min(lengder)}, lengste {max(lengder)}")
    # Kontrollen som ville fanget den gamle feilen med én gang: to meldinger
    # fra to selskaper i to ulike år kan ikke ha samme brødtekst. Er antallet
    # UNIKE tekster mye lavere enn antallet meldinger, lagrer vi sidas ramme.
    if ok:
        andel_unike = 100.0 * len(avtrykkene) / ok
        merke = ("  ✓" if andel_unike >= 95 else
                 "  ⚠️  SIDEMAL: meldinger deler brødtekst — se etter en blokk "
                 "uttrekket ikke greide å skille fra innholdet")
        logger.info(f"   Unike tekster ...... {len(avtrykkene)}/{ok}  "
                    f"({andel_unike:.1f} %){merke}")
    logger.info("   Kilde .............. " + "  ".join(
        f"{k}: {v}" for k, v in sorted(per_kilde.items(), key=lambda x: -x[1])))
    if fra_rest:
        logger.info(f"   Av dem fra reserven  {fra_rest}  (hele sida minus sidemal — "
                    f"les noen av dem i {opp.tekst_dir.name}/ og se om de holder)")
    if uendret:
        logger.info(f"   Lå der fra før ..... {uendret}  (kjør --tving-tekst for ny runde)")
    if uten:
        logger.warning(f"   ⚠️  {uten} meldinger har ingen lesbar tekst. De blir UKJENT "
                       f"i steg 3. Kjør steg 1 igjen for å hente HTML-en på nytt.")
    if not ok:
        _hvorfor_ingen_tekst(opp, indeks, sidemal, logger)

    andel = ok / max(1, len(ut))
    unike = (100.0 * len(avtrykkene) / ok) if ok else 100.0
    status = "OK" if andel >= 0.75 else ("DELVIS" if andel >= 0.25 else "FEIL")
    raad: List[str] = []

    # 3912 leste meldinger med bare 319 ulike tekster er ikke en vellykket
    # kjøring med en fotnote. Det betyr at vi lagrer sidas ramme og kaller den
    # melding — nøyaktig den feilen dette steget finnes for å hindre. Da skal
    # statustavlen si FEIL, ikke ✅.
    if ok and unike < 50.0:
        status = "FEIL" if unike < 25.0 else "DELVIS"
        raad = [f"bare {unike:.0f} % av tekstene er ulike — to meldinger fra to "
                f"selskaper KAN ikke ha samme brødtekst",
                "det er sidas ramme som blir lagret, ikke meldingen: sjekk at "
                "steg 1 henter selve meldingen og ikke listesiden"]
    return {"status": status, "med_tekst": ok, "uten_tekst": uten,
            "sidemal": len(sidemal), "unike_pst": round(unike, 1), "raad": raad,
            "detaljer": f"{ok}/{len(ut)} med tekst ({100*andel:.0f} %), "
                        f"{unike:.0f} % unike, "
                        f"{len(sidemal)} sidemalsblokker filtrert bort"}


def _hvorfor_ingen_tekst(opp: Oppsett, indeks: Sequence[Rad], sidemal: Set[str],
                         logger: logging.Logger) -> None:
    """
    Null leste meldinger er alltid ÉN feil, ikke tre tusen. Her står tallene
    som peker på hvilken: fantes HTML-en i det hele tatt, ga den kandidater,
    og hva var det i så fall som diskvalifiserte dem?
    """
    logger.warning("\n   🔎  DIAGNOSE — ingen av artiklene ga tekst:")
    vist = 0
    for r in indeks:
        rå = _les_html(opp, r)
        if not rå:
            continue
        kandidater, sidetekst = les_side(rå)
        logger.warning(f"      {rens(r.get('Melding_ID'))[:28]}  "
                       f"HTML {len(rå)} tegn  ·  {len(kandidater)} kandidatblokker  ·  "
                       f"sidetekst {len(sidetekst)} tegn")
        for k in sorted(kandidater, key=lambda x: -x["tegn"])[:3]:
            logger.warning(
                f"         {k['tag']:<8} {k['tegn']:>6} tegn  lenker {k['lenketetthet']:.2f}  "
                f"korte linjer {k['kortlinjer']:.2f}  meldingsord {k['meldingsord']}  "
                f"menyord {k['menyord']}  sidemal {'JA' if k['avtrykk'] in sidemal else 'nei'}")
        vist += 1
        if vist >= 3:
            break
    if not vist:
        logger.warning("      Ingen av radene har en HTML-fil på disk. Feilen sitter i "
                       "steg 1, ikke her — kjør steg 1 på nytt.")
    else:
        logger.warning("      Er «sidetekst» over ~500 tegn, FINNES teksten og det er "
                       "uttrekket som avviser den.\n"
                       "      Kjør: python innsidehandel_pipeline.py --steg 2 "
                       "--tving-tekst --feilsok")


# ══════════════════════════════════════════════════════════════════════════
# STEG 3 — DATO, HVEM, HVOR MYE — OG HVOR BULLISH?
# ══════════════════════════════════════════════════════════════════════════
#
# Steget rører ikke nettet. Det leser tekstfilene fra steg 2 og kan derfor
# kjøres om igjen på sekunder hver gang du justerer vektene i scoren.
#
# SCOREN. Fem ting avgjør hvor mye et innsidekjøp er verdt å se på, og de er
# rangert etter hvor godt de er dokumentert i forskningen:
#
#   ROLLE (30 %)        Konsernsjefen og finansdirektøren sitter nærmest
#                       tallene. Et styremedlems kjøp er svakere. En
#                       nærstående som handler på vegne av en innsider er
#                       svakest av alle.
#
#   ØKNING (28 %)       Hvor mye personen økte SIN EGEN posisjon. Dette er
#                       det mest informative enkeltmålet: «han økte
#                       beholdningen sin med 50 %» sier noe helt annet enn
#                       «han kjøpte for 500 000 kroner» — det siste er stort
#                       for et styremedlem i et lite selskap og ingenting for
#                       konsernsjefen i Equinor. En helt ny posisjon (fra
#                       null) gir toppscore pluss et påslag.
#
#   KLYNGE (25 %)       Flere ULIKE innsidere som kjøper i samme selskap i
#                       samme periode. Dette er det sterkest dokumenterte
#                       tilfellet av signalet: én person kan ha en privat
#                       grunn, fem samtidig har det ikke.
#
#   BELØP (17 %)        Absolutt størrelse, logaritmisk. Betyr minst av de
#                       fire, men et kjøp på 40 000 kroner er støy.
#
#   TILLIT (skalerer)   Leste vi meldingen sikkert, teller scoren fullt.
#                       Var uttrekket usikkert, dempes den — vi later ikke
#                       som om vi er sikrere enn vi er.
#
# Resultatet:
#     Bullish_Score   0-100, der 50 er nøytralt. Kjøp over 50, salg under.
#     Signal_Styrke   0-100 uten fortegn — hvor kraftig signalet er.
#     Signal          en merkelapp du kan lese uten å tolke tall.
#
# Salg scores speilvendt, men mildere: innsidere selger for å kjøpe hus og
# betale skatt, og et salg bærer derfor mindre informasjon enn et kjøp av
# samme størrelse. Faktoren står i SALG_DEMPING.

SKJEMA_SCORE = "6.0-score"
SALG_DEMPING = 0.75

ROLLEVEKT = {"CEO": 1.00, "CFO": 0.92, "LEDELSE": 0.72, "STYRELEDER": 0.68,
             "STYRE": 0.52, "NAERSTAAENDE": 0.28, "UKJENT": 0.35}
TILLITVEKT = {"HOY": 1.00, "MIDDELS": 0.85, "LAV": 0.55}

SIGNALTRAPP = ((85.0, "STERKT KJØPSSIGNAL"), (70.0, "KJØPSSIGNAL"),
               (57.0, "SVAKT KJØPSSIGNAL"), (43.0, "NØYTRAL"),
               (30.0, "SVAKT SALGSSIGNAL"), (15.0, "SALGSSIGNAL"),
               (0.0, "STERKT SALGSSIGNAL"))

HENDELSE_KOLONNER = [
    # hvem, hva, når
    "Melding_ID", "Dato", "Klokkeslett", "Selskap", "Ticker", "ISIN", "Tittel",
    # dommen
    "Klasse", "Bullish_Score", "Signal", "Signal_Styrke", "Rangering",
    # hvorfor
    "Rolle", "Rolle_Rang", "Naerstaaende", "Person",
    "Antall_Netto", "Kurs_Snitt", "Valuta", "Verdi_NOK",
    "Beholdning_For", "Beholdning_Etter", "Okning_Pst", "Ny_Posisjon",
    "Klynge_ID", "Klynge_Personer", "Klynge_Meldinger", "Klynge_NOK",
    "Primaer_I_Klynge",
    # delpoengene, så scoren kan etterprøves rad for rad
    "P_Rolle", "P_Okning", "P_Belop", "P_Klynge", "P_Bonus", "P_Tillit",
    # kvalitet og sporbarhet
    "Tillit", "Metode", "Grunn", "Kontroll", "Emisjon", "Transaksjonsdato",
    "Antall_Linjer", "Tekst_Kilde", "Tekst_Tegn", "Kilde_URL", "Skjema",
]

TALLKOLONNER_HENDELSER = [
    "Bullish_Score", "Signal_Styrke", "Rangering", "Rolle_Rang", "Antall_Netto",
    "Kurs_Snitt", "Verdi_NOK", "Beholdning_For", "Beholdning_Etter", "Okning_Pst",
    "Klynge_Personer", "Klynge_Meldinger", "Klynge_NOK", "P_Rolle", "P_Okning",
    "P_Belop", "P_Klynge", "P_Bonus", "P_Tillit", "Antall_Linjer", "Tekst_Tegn",
]

TRANSAKSJON_KOLONNER = ["Melding_ID", "Linje_Nr", "Retning", "Instrument",
                        "Instrument_Tekst", "Antall", "Kurs", "Valuta", "Verdi",
                        "Dato", "Regel", "Utdrag"]


def _demp(x: float, halv: float) -> float:
    """
    0 → 0, `halv` → 0,5, uendelig → 1. Mykt og uten knekkpunkter.

    Brukes på beløp og på økning i posisjon. Poenget er at forskjellen
    mellom 10 000 og 100 000 kroner betyr mye, mens forskjellen mellom
    10 og 100 millioner nesten ikke betyr noe — begge er «stort».
    """
    if x <= 0 or halv <= 0:
        return 0.0
    return x / (x + halv)


def poeng_rolle(rolle: str, naerstaaende: str) -> float:
    p = ROLLEVEKT.get(rens(rolle).upper(), 0.35)
    if rens(naerstaaende).upper() == "JA":
        p = min(p, ROLLEVEKT["NAERSTAAENDE"])
    return round(p, 4)


def poeng_okning(okning_pst: Optional[float], ny_posisjon: str) -> float:
    """
    Halvverdien er 25 %: en økning på 25 % gir 0,5, 50 % gir 0,67, en
    dobling gir 0,8. En helt ny posisjon er så nær et rent signal som du
    kommer, og gir full pott.
    """
    if rens(ny_posisjon).upper() == "JA":
        return 1.0
    if okning_pst is None:
        return 0.35                    # ukjent er ikke det samme som lite
    return round(_demp(abs(float(okning_pst)), 25.0), 4)


def poeng_belop(verdi: Optional[float]) -> float:
    """Halvverdi 1,5 mill.: 500 000 gir 0,25, 1,5 mill. 0,5, 10 mill. 0,87."""
    if verdi is None:
        return 0.30
    return round(_demp(abs(float(verdi)), 1_500_000.0), 4)


def poeng_klynge(personer: int, meldinger: int) -> float:
    """
    Én person er utgangspunktet. Hver ekstra PERSON teller mye mer enn hver
    ekstra melding: fem meldinger fra samme mann er én beslutning, fem
    meldinger fra fem personer er fem.
    """
    p = max(1, int(personer or 1))
    m = max(1, int(meldinger or 1))
    return round(min(1.0, 0.25 + 0.25 * (p - 1) + 0.05 * min(m - p, 6)), 4)


def scor_hendelse(u: Uttrekk, personer: int, meldinger: int,
                  opp: Oppsett) -> Dict[str, Any]:
    """
    Regner ut bullishness for én melding og legger igjen alle delpoengene.

    Delpoengene skrives til fila med vilje. Uten dem er scoren et tall du må
    tro på; med dem kan du åpne Excel, sortere på Bullish_Score, og se rad
    for rad HVORFOR den ble som den ble.
    """
    if u.klasse not in ("KJOP", "SALG"):
        return {"Bullish_Score": "", "Signal": "IKKE VURDERT", "Signal_Styrke": "",
                "P_Rolle": "", "P_Okning": "", "P_Belop": "", "P_Klynge": "",
                "P_Bonus": "", "P_Tillit": ""}

    p_rolle = poeng_rolle(u.rolle, u.naerstaaende)
    p_okning = poeng_okning(u.okning_pst, u.ny_posisjon)
    p_belop = poeng_belop(u.verdi)
    p_klynge = poeng_klynge(personer, meldinger)
    p_tillit = TILLITVEKT.get(u.tillit, 0.55)

    styrke = (opp.vekt_rolle * p_rolle + opp.vekt_okning * p_okning
              + opp.vekt_belop * p_belop + opp.vekt_klynge * p_klynge)
    bonus = opp.bonus_ny_posisjon if u.ny_posisjon == "JA" else 0.0
    styrke = min(1.0, styrke + bonus) * p_tillit

    fortegn = 1.0 if u.klasse == "KJOP" else -SALG_DEMPING
    score = 50.0 + 50.0 * fortegn * styrke
    score = max(0.0, min(100.0, score))

    signal = next(navn for grense, navn in SIGNALTRAPP if score >= grense)
    return {"Bullish_Score": round(score, 1), "Signal": signal,
            "Signal_Styrke": round(100.0 * styrke, 1),
            "P_Rolle": p_rolle, "P_Okning": p_okning, "P_Belop": p_belop,
            "P_Klynge": p_klynge, "P_Bonus": round(bonus, 4), "P_Tillit": p_tillit}


def finn_klynger(rader: List[Rad], klynge_dager: int) -> None:
    """
    Grupperer handler i samme selskap og samme retning innenfor et vindu.

    Flere innsidere som kjøper i samme selskap i samme periode er det
    sterkest dokumenterte tilfellet av dette signalet. Men det er ÉN hendelse,
    ikke fem: bare den første er handlebar på ny informasjon, og statistikken
    skal ikke telle den samme historien om igjen. Derfor merkes den første
    som primær, og steg 6 kan velge å bare bruke dem.

    Kjøp og salg klynges hver for seg. Kjøper A og selger B samme uke, er det
    to motstridende signaler, ikke ett forsterket.
    """
    per: Dict[Tuple[str, str], List[Rad]] = {}
    for r in rader:
        if r.get("Klasse") not in ("KJOP", "SALG"):
            r.update({"Klynge_ID": "", "Klynge_Personer": "", "Klynge_Meldinger": "",
                      "Klynge_NOK": "", "Primaer_I_Klynge": "NEI"})
            continue
        per.setdefault((rens(r.get("Ticker")).upper(), str(r.get("Klasse"))), []).append(r)

    for (ticker, klasse), gruppe in per.items():
        gruppe.sort(key=lambda r: (str(r.get("Dato")), str(r.get("Klokkeslett"))))
        klynge: List[Rad] = []
        start: Optional[date] = None
        nr = 0

        def lukk() -> None:
            if not klynge:
                return
            personer = set()
            verdi = 0.0
            kid = f"{ticker}-{klasse[:1]}{nr}-{iso(start)}"
            for i, r in enumerate(klynge):
                person = rens(r.get("Person")).upper()
                if person:
                    personer.add(person)
                verdi += tolk_maskin(r.get("Verdi_NOK")) or 0.0
                r["Klynge_ID"] = kid
                # Antall ULIKE personer. Kan ingen navn leses, faller vi
                # tilbake på antall meldinger i klyngen.
                r["Klynge_Personer"] = len(personer) or (i + 1)
                r["Klynge_Meldinger"] = i + 1
                r["Klynge_NOK"] = round(verdi, 0) if verdi else ""
                r["Primaer_I_Klynge"] = "JA" if i == 0 else "NEI"

        for r in gruppe:
            d = fra_iso(r.get("Dato"))
            if start is None or (d and (d - start).days > klynge_dager):
                lukk()
                klynge, start, nr = [r], d, nr + 1
            else:
                klynge.append(r)
        lukk()


def _les_tekst(opp: Oppsett, r: Rad) -> str:
    navn = rens(r.get("Tekst_Fil")) or f"{rens(r.get('Melding_ID'))}.txt"
    sti = opp.tekst_dir / Path(navn).name
    if not sti.exists():
        return ""
    try:
        return sti.read_text(encoding="utf-8")
    except OSError:
        return ""


def steg3_score(opp: Oppsett, logger: logging.Logger) -> Dict[str, Any]:
    """Leser hver melding, klynger dem, scorer dem, og skriver én fil."""
    opp.lag_mapper()
    tekstindeks = les_csv(opp.tekst_indeks_csv)
    if not tekstindeks:
        return {"status": "HOPPET",
                "detaljer": f"ingen {opp.tekst_indeks_csv.name} — kjør steg 2 først"}

    # ISIN og URL står i steg 1 sin indeks, ikke i steg 2 sin.
    ekstra = {rens(r.get("Melding_ID")): r for r in les_csv(opp.indeks_csv)}
    logger.info(f"📂 {len(tekstindeks)} meldinger fra {opp.tekst_indeks_csv.name}")

    rader: List[Rad] = []
    linjer_ut: List[Rad] = []
    uten_tekst = 0

    for r in tekstindeks:
        mid = rens(r.get("Melding_ID"))
        tittel = rens(r.get("Tittel"))
        tekst = _les_tekst(opp, r)
        if not tekst.strip():
            uten_tekst += 1
        u = les_melding(tittel, tekst, ta_med_emisjoner=opp.ta_med_emisjoner)
        e = ekstra.get(mid, {})

        rader.append({
            "Melding_ID": mid, "Dato": rens(r.get("Dato")),
            "Klokkeslett": rens(r.get("Klokkeslett")),
            "Selskap": rens(r.get("Selskap")), "Ticker": rens(r.get("Ticker")).upper(),
            "ISIN": rens(e.get("ISIN")).upper(), "Tittel": tittel,
            "Klasse": u.klasse, "Rolle": u.rolle, "Rolle_Rang": u.rolle_rang,
            "Naerstaaende": u.naerstaaende, "Person": u.person,
            "Antall_Netto": u.antall_netto, "Kurs_Snitt": u.kurs_snitt,
            "Valuta": u.valuta, "Verdi_NOK": u.verdi,
            "Beholdning_For": u.beholdning_for, "Beholdning_Etter": u.beholdning_etter,
            "Okning_Pst": u.okning_pst, "Ny_Posisjon": u.ny_posisjon,
            "Tillit": u.tillit, "Metode": u.metode, "Grunn": u.grunn,
            "Kontroll": u.kontroll, "Emisjon": u.emisjon,
            "Transaksjonsdato": u.transaksjonsdato, "Antall_Linjer": u.antall_linjer,
            "Tekst_Kilde": rens(r.get("Kilde")), "Tekst_Tegn": rens(r.get("Tegn")),
            "Kilde_URL": rens(e.get("Kilde_URL")), "Skjema": SKJEMA_SCORE,
            "_uttrekk": u,
        })
        for t in u.transaksjoner:
            linjer_ut.append({"Melding_ID": mid, "Linje_Nr": t.linje_nr,
                              "Retning": t.retning, "Instrument": t.instrument,
                              "Instrument_Tekst": t.instrument_tekst,
                              "Antall": t.antall, "Kurs": t.kurs, "Valuta": t.valuta,
                              "Verdi": t.verdi, "Dato": t.dato, "Regel": t.regel,
                              "Utdrag": t.utdrag})

    # Klyngene må være på plass FØR scoren: klyngestørrelse er en av de fire
    # komponentene, og «fem innsidere kjøper» er den sterkeste av dem.
    finn_klynger(rader, opp.klynge_dager)

    for r in rader:
        u: Uttrekk = r.pop("_uttrekk")
        r.update(scor_hendelse(u, tolk_maskin(r.get("Klynge_Personer")) or 1,
                               tolk_maskin(r.get("Klynge_Meldinger")) or 1, opp))

    # Rangeringen: 1 er mest bullish. Bare vurderte handler får et nummer.
    vurderte = [r for r in rader if r.get("Bullish_Score") != ""]
    vurderte.sort(key=lambda r: (-float(r["Bullish_Score"]), str(r.get("Dato"))))
    for i, r in enumerate(vurderte, start=1):
        r["Rangering"] = i
    for r in rader:
        r.setdefault("Rangering", "")

    rader.sort(key=lambda r: (str(r.get("Dato")), str(r.get("Klokkeslett"))), reverse=True)

    skriv_tabell(opp.hendelser_csv, opp.hendelser_xlsx, rader, HENDELSE_KOLONNER,
                 logger, tallkolonner=TALLKOLONNER_HENDELSER, arknavn="Innsidehandel")
    skriv_csv(opp.transaksjoner_csv, linjer_ut, TRANSAKSJON_KOLONNER)
    logger.info(f"💾 {opp.transaksjoner_csv.name}  ({len(linjer_ut)} transaksjonslinjer)")

    resultat = _score_rapport(opp, rader, logger, uten_tekst)
    return resultat


def _score_rapport(opp: Oppsett, rader: List[Rad], logger: logging.Logger,
                   uten_tekst: int) -> Dict[str, Any]:
    """
    Regnskapet over uttrekket. Dette er tallet som avgjør om resten er verdt
    å lese: er en fjerdedel UKJENT, er ikke konklusjonen i steg 6 verdt mye —
    og det skal du se her, ikke ane etterpå.
    """
    n = len(rader)
    if not n:
        return {"status": "FEIL", "detaljer": "ingen rader"}

    def tell(felt: str) -> List[Tuple[str, int]]:
        t: Dict[str, int] = {}
        for r in rader:
            v = str(r.get(felt) or "(tom)")
            t[v] = t.get(v, 0) + 1
        return sorted(t.items(), key=lambda x: -x[1])

    logger.info(f"\n{'═' * 74}")
    logger.info("UTTREKKET — HVA BLE MELDINGENE TIL?")
    logger.info(f"{'═' * 74}")
    merker = {"KJOP": "  ← signalet", "SALG": "  ← kontrollgruppen",
              "IGNORERT": "  ← ikke frivillig markedshandel", "UKJENT": "  ⚠️  ikke lest"}
    for klasse, antall in tell("Klasse"):
        logger.info(f"  {klasse:<10} {antall:>6}  ({100.0*antall/n:5.1f} %)"
                    f"{merker.get(klasse, '')}")

    for merkelapp, felt in (("Hvorfor ignorert", "IGNORERT"), ("Hvorfor ukjent", "UKJENT")):
        del_ = [r for r in rader if r.get("Klasse") == felt]
        if not del_:
            continue
        t: Dict[str, int] = {}
        for r in del_:
            t[str(r.get("Grunn"))] = t.get(str(r.get("Grunn")), 0) + 1
        logger.info(f"\n  {merkelapp}:")
        for grunn, antall in sorted(t.items(), key=lambda x: -x[1]):
            logger.info(f"    {grunn:<24} {antall:>6}")

    handler = [r for r in rader if r.get("Klasse") in ("KJOP", "SALG")]
    kjop = [r for r in rader if r.get("Klasse") == "KJOP"]
    if handler:
        logger.info("\n  Tillit til de leste handlene:")
        t = {}
        for r in handler:
            t[str(r.get("Tillit"))] = t.get(str(r.get("Tillit")), 0) + 1
        for tillit in ("HOY", "MIDDELS", "LAV"):
            if tillit in t:
                logger.info(f"    {tillit:<24} {t[tillit]:>6}  "
                            f"({100.0*t[tillit]/len(handler):.1f} %)")
        kontrollert = [r for r in handler if r.get("Kontroll") in ("OK", "AVVIK")]
        if kontrollert:
            ok = sum(1 for r in kontrollert if r.get("Kontroll") == "OK")
            andel = 100.0 * ok / len(kontrollert)
            merke = "  ✓" if andel >= 98 else "  ⚠️  uttrekket leser noe feil"
            logger.info(f"\n  Beholdningsregnestykket (før + netto = etter) stemmer: "
                        f"{ok}/{len(kontrollert)} ({andel:.1f} %){merke}")

    # ── scoren ───────────────────────────────────────────────────────────
    logger.info(f"\n{'─' * 74}")
    logger.info("BULLISHNESS")
    logger.info(f"{'─' * 74}")
    for signal, antall in sorted(tell("Signal"), key=lambda x: -x[1]):
        if signal == "(tom)":
            continue
        logger.info(f"  {signal:<22} {antall:>6}")

    scorer = [float(r["Bullish_Score"]) for r in rader if r.get("Bullish_Score") != ""]
    if scorer:
        logger.info(f"\n  Score: median {median(scorer):.1f}, snitt {snitt(scorer):.1f}, "
                    f"høyest {max(scorer):.1f}, lavest {min(scorer):.1f}")

    topp = sorted((r for r in rader if r.get("Bullish_Score") != ""),
                  key=lambda r: -float(r["Bullish_Score"]))[:10]
    if topp:
        logger.info("\n  De ti mest bullish meldingene:")
        logger.info(f"    {'Score':>6}  {'Dato':<11} {'Ticker':<11} {'Rolle':<11} "
                    f"{'Økning':>8}  {'Beløp':>13}  Klynge")
        for r in topp:
            okning = tolk_maskin(r.get("Okning_Pst"))
            verdi = tolk_maskin(r.get("Verdi_NOK"))
            logger.info(f"    {float(r['Bullish_Score']):>6.1f}  {str(r.get('Dato')):<11} "
                        f"{str(r.get('Ticker')):<11} {str(r.get('Rolle')):<11} "
                        f"{(f'{okning:+.0f} %' if okning is not None else '—'):>8}  "
                        f"{(f'{verdi:,.0f} kr' if verdi else '—'):>13}  "
                        f"{r.get('Klynge_Personer')} pers.")

    if uten_tekst:
        logger.warning(f"\n  ⚠️  {uten_tekst} meldinger hadde ingen tekst å lese.")
    if len(kjop) < 100:
        logger.warning(f"  ⚠️  Bare {len(kjop)} rene kjøp. Det er for lite til å "
                       f"konkludere på i steg 6.")
    logger.info(f"{'═' * 74}")

    # Kvalitetsrapporten som fil, så den kan følges over tid.
    kval = []
    for felt in ("Klasse", "Grunn", "Tillit", "Kontroll", "Rolle", "Metode",
                 "Signal", "Tekst_Kilde"):
        for verdi, antall in tell(felt):
            kval.append({"Felt": felt, "Verdi": verdi, "Antall": antall,
                         "Andel_Pst": round(100.0 * antall / n, 2)})
    skriv_csv(opp.score_kvalitet_csv, kval, ["Felt", "Verdi", "Antall", "Andel_Pst"])

    ukjent = sum(1 for r in rader if r.get("Klasse") == "UKJENT")
    andel_ukjent = ukjent / n
    status = "OK" if (andel_ukjent < 0.25 and kjop) else ("DELVIS" if kjop else "FEIL")
    return {"status": status, "hendelser": n, "kjop": len(kjop),
            "salg": sum(1 for r in rader if r.get("Klasse") == "SALG"),
            "ukjent": ukjent,
            "detaljer": f"{len(kjop)} kjøp, "
                        f"{sum(1 for r in rader if r.get('Klasse') == 'SALG')} salg, "
                        f"{100*andel_ukjent:.0f} % ukjent → {opp.hendelser_xlsx.name}"}


# ══════════════════════════════════════════════════════════════════════════
# STEG 4 — AKSJEKURSER FRA YFINANCE
# ══════════════════════════════════════════════════════════════════════════
#
# Én fil per ticker i stedet for én bred matrise. Det gjør tilvekst trivielt:
# skal EQNR.OL oppdateres med ti nye dager, skrives EQNR.OL.csv om, og de 299
# andre filene ligger urørt.
#
# Hver fil har fire kolonner:
#     Dato        handelsdagen
#     Close       sluttkurs justert for SPLITT, ikke for utbytte  → prisavk.
#     AdjClose    justert for både splitt og utbytte              → totalavk.
#     Volum       antall aksjer omsatt
#
# BEGGE kursene lagres med vilje. Den gamle koden brukte utbyttejustert kurs
# for aksjene og målte dem mot OSEAX, som er en PRISindeks — da får du hele
# utbytteavkastningen, rundt en prosent i året, gratis som falsk
# meravkastning. Nå velges ett felt i oppsettet og brukes for BÅDE aksje og
# referanse, slik at de umulig kan bli ulike.
#
# yfinance er primærkilden, slik du ba om. Yahoo sitt kurs-API kalles direkte
# som reserve: yfinance blir av og til stengt ute av en ny cookie-sperre, og
# da er det greit å ha en vei til.

GRUPPE_KURSER = "kurser"
KURS_KOLONNER = ["Dato", "Close", "AdjClose", "Volum"]
LIKEVEKT = "IDX_LIKEVEKT"
YAHOO_API = "https://query1.finance.yahoo.com/v8/finance/chart/"
BRUKERAGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def filnavn_for(ticker: str) -> str:
    """«^OSEAX» → «IDX_OSEAX.csv». Filsystemer liker ikke ^ og *."""
    t = rens(ticker).upper().replace("^", "IDX_")
    return re.sub(r"[^A-Z0-9_.\-]", "_", t) + ".csv"


class Kursbok:
    """Alle kursene i minnet. Noen hundre tickere × 2700 dager er ingenting."""

    def __init__(self, mappe: Path):
        self.mappe = Path(mappe)
        self.serier: Dict[str, Dict[date, Dict[str, Optional[float]]]] = {}

    def last(self, bare: Optional[Sequence[str]] = None) -> "Kursbok":
        ønsket = {rens(t).upper() for t in bare} if bare else None
        if not self.mappe.exists():
            return self
        for fil in sorted(self.mappe.glob("*.csv")):
            if fil.name.startswith("_"):
                continue
            ticker = self._ticker_fra_fil(fil)
            if ønsket is not None and ticker not in ønsket:
                continue
            self.serier[ticker] = self._les_fil(fil)
        return self

    @staticmethod
    def _ticker_fra_fil(fil: Path) -> str:
        navn = fil.stem
        return ("^" + navn[4:]) if navn.startswith("IDX_") and navn != LIKEVEKT else navn

    @staticmethod
    def _les_fil(fil: Path) -> Dict[date, Dict[str, Optional[float]]]:
        ut: Dict[date, Dict[str, Optional[float]]] = {}
        for rad in les_csv(fil):
            d = fra_iso(rad.get("Dato"))
            if not d:
                continue
            ut[d] = {"close": tolk_maskin(rad.get("Close")),
                     "adjclose": tolk_maskin(rad.get("AdjClose")),
                     "volum": tolk_maskin(rad.get("Volum"))}
        return ut

    def lagre_ticker(self, ticker: str) -> None:
        serie = self.serier.get(rens(ticker).upper(), {})
        rader = [{"Dato": iso(d), "Close": v.get("close"), "AdjClose": v.get("adjclose"),
                  "Volum": v.get("volum")} for d, v in sorted(serie.items())]
        skriv_csv(self.mappe / filnavn_for(ticker), rader, KURS_KOLONNER)

    def slå_sammen(self, ticker: str, nye: Dict[date, Dict[str, Optional[float]]]) -> None:
        """Nye dager legges til, overlappende dager overskrives med det ferske."""
        self.serier.setdefault(rens(ticker).upper(), {}).update(nye)

    def erstatt(self, ticker: str, nye: Dict[date, Dict[str, Optional[float]]]) -> None:
        """Hele serien byttes ut — når kilden har skrevet om historikken."""
        self.serier[rens(ticker).upper()] = dict(nye)

    def datoer_per_ticker(self) -> Dict[str, List[date]]:
        return {t: sorted(s) for t, s in self.serier.items()}

    def siste_dag(self, ticker: str) -> Optional[date]:
        s = self.serier.get(rens(ticker).upper())
        return max(s) if s else None

    def verdi(self, ticker: str, d: date, felt: str = "close") -> Optional[float]:
        rad = self.serier.get(rens(ticker).upper(), {}).get(d)
        if not rad:
            return None
        v = rad.get(felt)
        return v if (v is not None and v == v and v > 0) else None

    def justert_serie(self, ticker: str, kalender: Sequence[date], felt: str,
                      maks_fyll: int = 5) -> List[Optional[float]]:
        """
        Kursene satt på børskalenderen, med korte hull fylt framover.

        Fyllet er begrenset med vilje. Uten grense ville et strøket selskap
        fått siste kjente kurs gjentatt i seksti dager, og avkastningen ville
        blitt nøyaktig 0 % — altså ville en avnotering sett ut som en helt
        rolig periode i stedet for som manglende data.
        """
        serie = self.serier.get(rens(ticker).upper(), {})
        ut: List[Optional[float]] = []
        sist: Optional[float] = None
        fylt = 0
        for d in kalender:
            rad = serie.get(d)
            v = rad.get(felt) if rad else None
            if v is not None and v == v and v > 0:
                ut.append(v)
                sist, fylt = v, 0
            elif sist is not None and fylt < maks_fyll:
                ut.append(sist)
                fylt += 1
            else:
                ut.append(None)
        return ut

    def volumserie(self, ticker: str, kalender: Sequence[date],
                   maks_fyll: int = 5) -> List[Optional[float]]:
        return self.justert_serie(ticker, kalender, "volum", maks_fyll)


def les_kalenderfil(sti: Path) -> List[date]:
    return [d for d in (fra_iso(r.get("Dato")) for r in les_csv(sti)) if d]


def skriv_kalenderfil(sti: Path, dager: Sequence[date]) -> None:
    skriv_csv(sti, [{"Dato": iso(d)} for d in dager], ["Dato"])


# ── HENTING ──────────────────────────────────────────────────────────────

def hent_yfinance(tickere: Sequence[str], fra: date, til: date
                  ) -> Dict[str, Dict[date, Dict[str, Optional[float]]]]:
    """
    Bolkhenting med yfinance. Kaster ved feil — kalleren tar reserven.

    auto_adjust=False fordi vi vil ha BEGGE kursene: Close (bare
    splittjustert) og Adj Close (også utbyttejustert). Med auto_adjust=True
    får du bare den ene, og da kan du ikke lenger velge målestokk.
    """
    import yfinance as yf                        # ImportError → kalleren gir opp
    data = yf.download(list(tickere), start=fra.strftime("%Y-%m-%d"),
                       end=(til + timedelta(days=1)).strftime("%Y-%m-%d"),
                       interval="1d", auto_adjust=False, actions=False,
                       group_by="ticker", threads=True, progress=False,
                       repair=False)
    ut: Dict[str, Dict[date, Dict[str, Optional[float]]]] = {}
    if data is None or not len(data):
        return ut

    # Med flere tickere gir yfinance en tonivås kolonneindeks (ticker, felt);
    # med én ticker er den flat. Hvilken av delene vi får varierer mellom
    # versjoner, så vi spør heller enn å anta.
    flernivaa = getattr(getattr(data, "columns", None), "nlevels", 1) > 1
    for t in tickere:
        if flernivaa:
            try:
                del_ = data[t]
            except (KeyError, IndexError, TypeError):
                continue
        else:
            del_ = data
        if del_ is None or not len(del_):
            continue
        serie: Dict[date, Dict[str, Optional[float]]] = {}
        kol = {str(c).lower(): c for c in del_.columns}
        k_close, k_adj, k_vol = kol.get("close"), kol.get("adj close"), kol.get("volume")
        if k_close is None:
            continue
        for stempel, rad in del_.iterrows():
            try:
                d = stempel.date()
                c = float(rad[k_close])
            except (AttributeError, KeyError, TypeError, ValueError):
                continue
            if c != c or c <= 0:
                continue           # dag uten handel — skal ikke lagres som null
            try:
                a = float(rad[k_adj]) if k_adj is not None else c
            except (KeyError, TypeError, ValueError):
                a = c
            try:
                v = float(rad[k_vol]) if k_vol is not None else None
            except (KeyError, TypeError, ValueError):
                v = None
            serie[d] = {"close": c, "adjclose": a if a == a and a > 0 else c,
                        "volum": v if v is not None and v == v else None}
        if serie:
            ut[rens(t).upper()] = serie
    return ut


def hent_yahoo_direkte(ticker: str, fra: date, til: date,
                       timeout: int = 30) -> Dict[date, Dict[str, Optional[float]]]:
    """
    Reserve når yfinance svikter. Kaster ved feil.

    Datoen regnes ut fra børsens egen tidssone (gmtoffset i svaret), ikke fra
    UTC. Uten det havner dagsstolpene på feil dato i deler av året, og hele
    avkastningsvinduet forskyves med én dag.
    """
    p = urllib.parse.urlencode({
        "period1": int(datetime(fra.year, fra.month, fra.day,
                                tzinfo=timezone.utc).timestamp()),
        "period2": int(datetime(til.year, til.month, til.day,
                                tzinfo=timezone.utc).timestamp()) + 86400,
        "interval": "1d", "includeAdjustedClose": "true", "events": "div,split"})
    req = urllib.request.Request(f"{YAHOO_API}{urllib.parse.quote(ticker)}?{p}",
                                 headers={"User-Agent": BRUKERAGENT,
                                          "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as svar:
        data = json.load(svar)

    diagram = (data or {}).get("chart") or {}
    if diagram.get("error"):
        raise ValueError(str(diagram["error"])[:150])
    treff = diagram.get("result") or []
    if not treff:
        return {}
    r = treff[0]
    tider = r.get("timestamp") or []
    if not tider:
        return {}
    ind = r.get("indicators") or {}
    quote = (ind.get("quote") or [{}])[0]
    close = quote.get("close") or []
    volum = quote.get("volume") or []
    adj = ((ind.get("adjclose") or [{}])[0]).get("adjclose") or []
    forskyvning = int(r.get("meta", {}).get("gmtoffset") or 0)

    ut: Dict[date, Dict[str, Optional[float]]] = {}
    for i, ts in enumerate(tider):
        try:
            d = datetime.fromtimestamp(int(ts) + forskyvning, timezone.utc).date()
        except (TypeError, ValueError, OSError):
            continue
        c = close[i] if i < len(close) else None
        if c is None or c != c:
            continue
        a = adj[i] if i < len(adj) else None
        v = volum[i] if i < len(volum) else None
        ut[d] = {"close": float(c),
                 "adjclose": float(a) if a is not None and a == a else float(c),
                 "volum": float(v) if v is not None and v == v else None}
    return ut


def er_omskrevet(gammel: Dict[date, Dict[str, Optional[float]]],
                 ny: Dict[date, Dict[str, Optional[float]]],
                 toleranse: float) -> Optional[str]:
    """
    Kontrollsummen. Har det vært en splitt eller en justering, stemmer ikke
    de gamle tallene lenger, og hele serien må hentes på nytt. Uten dette
    ville en 1:10-splitt gitt et falskt kursfall på 90 % i dataene dine.
    """
    felles = sorted(set(gammel) & set(ny))
    if len(felles) < 2:
        return None
    avvik = 0
    verste = 0.0
    for d in felles:
        g, n = gammel[d].get("close"), ny[d].get("close")
        if not g or not n:
            continue
        rel = abs(n - g) / max(abs(g), 1e-9)
        if rel > toleranse:
            avvik += 1
            verste = max(verste, rel)
    if avvik >= max(2, len(felles) // 4):
        return (f"{avvik} av {len(felles)} overlappende dager avviker "
                f"(verste {verste*100:.1f} %) — serien er skrevet om")
    return None


def ikke_aksjer(opp: Oppsett) -> List[str]:
    """
    Serier som ikke er aksjer, og som derfor ikke skal lage handledager.

    En indeks BEREGNES — den kan ha en verdi på dager børsen var stengt.
    Slipper den inn i kalenderen, forskyves alle avkastningsvinduene med én
    dag. Steg 4 og steg 5 må bruke nøyaktig samme liste, ellers bygger de to
    ulike kalendere av de samme dataene.
    """
    ut = [LIKEVEKT]
    for k in (rens(opp.referanse_ticker),) + tuple(opp.referanse_kandidater):
        k = rens(k).upper()
        if k and k not in ut:
            ut.append(k)
    return ut


def skriv_referansevalg(opp: Oppsett, ticker: str, kilde: str) -> None:
    try:
        opp.referanse_fil.parent.mkdir(parents=True, exist_ok=True)
        opp.referanse_fil.write_text(f"{ticker}\n{kilde}\n", encoding="utf-8")
    except OSError:
        pass


def les_referansevalg(opp: Oppsett) -> Tuple[str, str]:
    try:
        linjer = opp.referanse_fil.read_text(encoding="utf-8").splitlines()
        if linjer and linjer[0].strip():
            return linjer[0].strip(), (linjer[1].strip() if len(linjer) > 1 else "")
    except OSError:
        pass
    return rens(opp.referanse_ticker).upper(), "oppsett"


def bygg_likevekt(bok: Kursbok, kalender: Sequence[date], felt: str,
                  uten: Sequence[str] = ()) -> Dict[date, Dict[str, Optional[float]]]:
    """
    Likevektet indeks av tickerne vi har: snitt av daglige avkastninger,
    kjedet opp fra 100.

    Reserven når ingen ekte indeks svarer. Den måler mot SNITTSELSKAPET, ikke
    mot børsen — og det skal stå i rapporten, ikke skjules. Men den er
    uendelig mye bedre enn ingen referanse: uten en serie å trekke fra er
    meravkastningen tom, og hele analysen faller.
    """
    ute = {rens(u).upper() for u in uten}
    serier = {t: bok.justert_serie(t, kalender, felt, maks_fyll=5)
              for t in bok.serier if rens(t).upper() not in ute}
    ut: Dict[date, Dict[str, Optional[float]]] = {}
    niva = 100.0
    for i, d in enumerate(kalender):
        if i == 0:
            ut[d] = {"close": niva, "adjclose": niva, "volum": 0.0}
            continue
        avk = []
        for serie in serier.values():
            forr, na = serie[i - 1], serie[i]
            if forr and na and forr > 0:
                avk.append(na / forr - 1.0)
        if avk:
            niva *= 1.0 + sum(avk) / len(avk)
        ut[d] = {"close": round(niva, 6), "adjclose": round(niva, 6), "volum": 0.0}
    return ut


def finn_tickere(opp: Oppsett, logger: logging.Logger, alle: bool = False) -> List[str]:
    """
    Hvilke tickere trenger vi kurser for?

    Primærkilden er hendelsene fra steg 3: det er ingen vits i å hente kurser
    for selskaper vi ikke har en eneste innsidemelding fra. `--alle` tar hele
    aksjelista, og er nyttig når du vil ha en bredere børskalender.
    """
    fra_hendelser: List[str] = []
    for kilde in (opp.hendelser_csv, opp.tekst_indeks_csv, opp.indeks_csv):
        for rad in les_csv(kilde):
            t = rens(rad.get("Ticker")).upper()
            if t and t not in fra_hendelser:
                fra_hendelser.append(t)
        if fra_hendelser:
            logger.info(f"📋 {len(fra_hendelser)} tickere fra {kilde.name}")
            break

    fra_liste: List[str] = []
    if alle or not fra_hendelser:
        fra_liste = [rens(r.get("Ticker")).upper() for r in les_selskaper(opp)]
        if fra_liste:
            logger.info(f"📋 {len(fra_liste)} tickere fra {opp.selskapsliste.name}")

    return sorted({t for t in fra_hendelser + fra_liste
                   if t and " " not in t and len(t) <= 14})


def steg4_kurser(opp: Oppsett, logger: logging.Logger,
                 alle: bool = False) -> Dict[str, Any]:
    """Henter kurser og volum, bygger børskalenderen og velger referanse."""
    opp.lag_mapper()
    bok = Kursbok(opp.s4_dir).last()
    vm = Vannmerke(opp.vannmerke_json, logger)

    tickere = finn_tickere(opp, logger, alle)
    if not tickere:
        return {"status": "HOPPET",
                "detaljer": "ingen tickere — kjør steg 1-3 først, eller bruk --alle"}

    eldste = opp.eldste_kurs()
    i_dag = date.today()

    if opp.offline:
        logger.info(f"⏭️  --offline: henter ingenting. Bruker de {len(bok.serier)} "
                    f"seriene som ligger i {opp.s4_dir.name}.")
        hentet = {"nye": 0, "feilet": [], "omskrevet": 0, "ajour": len(bok.serier)}
    else:
        hentet = _hent_alle_kurser(opp, logger, bok, vm, tickere, eldste, i_dag)
        vm.lagre()

    if not bok.serier:
        return {"status": "FEIL", "detaljer": "ingen kursdata i det hele tatt"}

    # Kalenderen bygges av AKSJENE. En indeks beregnes og kan ha kurs på dager
    # børsen var stengt, så den må holdes utenfor.
    dager = utled_handledager(bok.datoer_per_ticker(), opp.handledag_terskel,
                              unntatt=ikke_aksjer(opp))
    skriv_kalenderfil(opp.kalender_csv, dager)
    logger.info(f"📅 {len(dager)} handledager"
                + (f" ({dager[0]} → {dager[-1]})" if dager else ""))

    ref_navn, kilde = _hent_referanse(opp, logger, bok, eldste, i_dag, dager,
                                      opp.kursfelt_navn())
    tynne = _dekningsrapport(opp, bok, logger, eldste)

    if not ref_navn:
        return {"status": "DELVIS", "tickere": len(bok.serier),
                "detaljer": f"{len(bok.serier)} tickere, MEN ingen referanseindeks "
                            f"— meravkastning blir tom"}
    if kilde == "likevekt":
        logger.warning("   ⚠️  Husk: referansen er en likevektet reserve, ikke børsen.")

    feilet = len(hentet.get("feilet", []))
    if hentet.get("stoppet"):
        return {"status": "FEIL", "tickere": len(bok.serier), "feilet": feilet,
                "detaljer": hentet["stoppet"]}
    status = "OK" if feilet <= max(3, len(tickere) * 0.1) else "DELVIS"
    return {"status": status, "tickere": len(bok.serier), "handledager": len(dager),
            "referanse": ref_navn, "feilet": feilet, "tynne": tynne,
            "detaljer": f"{len(bok.serier)} tickere · {len(dager)} handledager · "
                        f"referanse {ref_navn}"
                        + (f" · {feilet} uten data" if feilet else "")}


def _hent_en_ticker(t: str, fra: date, til: date, logger: logging.Logger,
                    opp: Oppsett) -> Dict[date, Dict[str, Optional[float]]]:
    """yfinance for én ticker, med Yahoo direkte som reserve."""
    try:
        data = hent_yfinance([t], fra, til)
        if data.get(rens(t).upper()):
            return data[rens(t).upper()]
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"yfinance feilet for {t}: {feiltekst(e)}")
    data2 = med_nye_forsok(
        lambda: hent_yahoo_direkte(t, fra, til, opp.kurs_timeout_s), logger,
        f"kurser for {t}", opp.maks_forsok, opp.forste_pause_s,
        feiltyper=(urllib.error.URLError, TimeoutError, ValueError, OSError))
    return data2 or {}


def _hent_alle_kurser(opp: Oppsett, logger: logging.Logger, bok: Kursbok,
                      vm: Vannmerke, tickere: Sequence[str], eldste: date,
                      i_dag: date) -> Dict[str, Any]:
    """
    Henter i bolker der det går, og enkeltvis der bolken ikke ga noe.

    Bolkhenting er mye raskere (yfinance åpner én økt for førti tickere), men
    en enkelt ticker som ikke finnes kan gjøre hele bolken tom. Derfor faller
    vi tilbake til å hente de manglende én og én, i stedet for å konkludere
    med at de ikke finnes.
    """
    å_hente: List[Tuple[str, date]] = []
    ajour = 0
    mangler_historikk = 0
    for t in tickere:
        # Vannmerket alene er ikke nok, og det er en dyr lærdom: står det at
        # serien er komplett til i går, henter vi bare de siste ti dagene —
        # selv om CSV-en på disk er tom eller begynner forrige uke. Da får du
        # 268 tickere med ni dagers historikk, en kalender på ni dager, og en
        # backtest uten et eneste brukbart kjøp. Ingenting av det klager.
        #
        # Derfor holdes vannmerket opp mot dataene: dekker de ikke `eldste`,
        # og har vi ikke ALLEREDE spurt kilden helt tilbake (`hentet_fra` —
        # et selskap notert i fjor HAR ikke ti års historikk), hentes alt om
        # igjen. Feilen retter seg selv ved neste kjøring.
        egne = bok.serier.get(rens(t).upper()) or {}
        bedt_fra = fra_iso(vm.post(GRUPPE_KURSER, t).get("hentet_fra"))
        dekker = bool(egne) and (
            min(egne) <= eldste + timedelta(days=opp.overlapp_dager + 5)
            or (bedt_fra is not None and bedt_fra <= eldste))
        if not dekker:
            mangler_historikk += 1
        elif vm.er_ajour(GRUPPE_KURSER, t, i_dag - timedelta(days=1)) and not opp.full:
            ajour += 1
            continue
        fra = (eldste if not dekker else
               vm.startdato(GRUPPE_KURSER, t, eldste, opp.overlapp_dager, opp.full))
        å_hente.append((t, fra))
    if mangler_historikk:
        logger.info(f"   ⟲ {mangler_historikk} tickere mangler historikk tilbake til "
                    f"{eldste} — de hentes helt om igjen.")
    if not å_hente:
        logger.info(f"📈 Alle {ajour} tickere er allerede ajour.")
        return {"nye": 0, "feilet": [], "omskrevet": 0, "ajour": ajour}

    logger.info(f"📈 {len(å_hente)} tickere skal hentes ({ajour} er ajour). "
                f"Prøver yfinance i bolker på {opp.yf_bolk}.")

    ferske: Dict[str, Dict[date, Dict[str, Optional[float]]]] = {}
    # Alle med samme startdato kan hentes sammen. I praksis er de fleste like.
    per_start: Dict[date, List[str]] = {}
    for t, fra in å_hente:
        per_start.setdefault(fra, []).append(t)

    yf_virker = True
    for fra, gruppe in sorted(per_start.items()):
        for i in range(0, len(gruppe), opp.yf_bolk):
            bolk = gruppe[i:i + opp.yf_bolk]
            if not yf_virker:
                break
            try:
                svar = hent_yfinance(bolk, fra, i_dag)
                ferske.update(svar)
                logger.info(f"   yfinance: {len(svar)}/{len(bolk)} tickere "
                            f"fra {fra}  ({len(ferske)}/{len(å_hente)} totalt)")
            except ImportError as e:
                logger.warning(f"   {feiltekst(e)}")
                logger.warning("   Faller tilbake på Yahoo direkte for alle tickere.")
                yf_virker = False
            except Exception as e:
                logger.warning(f"   yfinance-bolken feilet ({feiltekst(e)[:90]}) — "
                               f"henter de {len(bolk)} enkeltvis")
            time.sleep(opp.pause_mellom_tickere_s)

    nye, omskrevet, feilet = 0, 0, []
    paa_rad = 0
    stoppet = ""
    for nr, (t, fra) in enumerate(å_hente, start=1):
        data = ferske.get(rens(t).upper()) or {}
        if not data:
            data = _hent_en_ticker(t, fra, i_dag, logger, opp)
        if not data:
            feilet.append(t)
            paa_rad += 1
            vm.merk_feil(GRUPPE_KURSER, t, "ingen data")
            # Strømbryteren. Én ticker uten data er normalt — den finnes
            # kanskje ikke på Yahoo. Tolv på rad er ikke tolv rare tickere;
            # det er kilden som ikke svarer, og da er de 280 neste bortkastet
            # tid. Uten denne bruker en kjøring uten nett en time på å få den
            # samme feilen 300 ganger.
            if opp.maks_feil_paa_rad and paa_rad >= opp.maks_feil_paa_rad:
                stoppet = (f"{paa_rad} tickere på rad uten data — det er kilden som "
                           f"ikke svarer, ikke tickerne. Stoppet uten å prøve de "
                           f"{len(å_hente) - nr} som var igjen.")
                logger.error(f"   ❌ {stoppet}")
                break
            continue
        paa_rad = 0

        gammel = bok.serier.get(rens(t).upper(), {})
        grunn = er_omskrevet(gammel, data, opp.restatement_toleranse)
        if grunn and fra > eldste:
            logger.warning(f"   ⟳ {t:<12} {grunn}. Henter hele historikken på nytt.")
            full = _hent_en_ticker(t, eldste, i_dag, logger, opp)
            if full:
                bok.erstatt(t, full)
                data = full
                fra = eldste
                omskrevet += 1
            else:
                feilet.append(t)
                vm.merk_feil(GRUPPE_KURSER, t, "kunne ikke hente om igjen")
                continue
        else:
            bok.slå_sammen(t, data)

        bok.lagre_ticker(t)
        gammel_fra = fra_iso(vm.post(GRUPPE_KURSER, t).get("hentet_fra"))
        vm.sett(GRUPPE_KURSER, t, max(data),
                dager=len(bok.serier.get(rens(t).upper(), {})),
                hentet_fra=iso(fra if gammel_fra is None else min(gammel_fra, fra)))
        nye += 1
        if nr % 50 == 0 or nr == len(å_hente):
            logger.info(f"   [{nr}/{len(å_hente)}] lagret  ({nye} ok, {len(feilet)} uten data)")

    logger.info(f"📈 {nye} oppdatert, {ajour} allerede ajour, "
                f"{omskrevet} hentet om igjen etter splitt, {len(feilet)} uten data")
    if feilet:
        logger.warning(f"   ⚠️  Uten data: {', '.join(feilet[:12])}"
                       f"{' …' if len(feilet) > 12 else ''}")
    return {"nye": nye, "feilet": feilet, "omskrevet": omskrevet, "ajour": ajour,
            "stoppet": stoppet}


def _hent_referanse(opp: Oppsett, logger: logging.Logger, bok: Kursbok, eldste: date,
                    i_dag: date, kalender: Sequence[date], felt: str) -> Tuple[str, str]:
    """
    Skaffer serien meravkastningen måles mot. (ticker, kilde).

    Yahoo bytter symboler for Oslo-indeksene med jevne mellomrom, og et symbol
    som svarer 404 gir ingen referanse — da måler du ikke mot noe. Vi prøver
    flere med ETT forsøk hver (et symbol som ikke finnes blir ikke bedre av
    tre), og bygger en likevektet indeks av tickerne vi HAR hvis ingen svarer.
    """
    kandidater: List[str] = []
    for k in (rens(opp.referanse_ticker),) + tuple(opp.referanse_kandidater):
        k = rens(k).upper()
        if k and k not in kandidater:
            kandidater.append(k)

    if not opp.offline:
        for k in kandidater:
            if k in bok.serier and len(bok.serier[k]) > 100:
                logger.info(f"📊 Referanse: {k} (allerede hentet)")
                skriv_referansevalg(opp, k, "indeks")
                return k, "indeks"
            data: Dict[date, Dict[str, Optional[float]]] = {}
            try:
                data = hent_yfinance([k], eldste, i_dag).get(k, {})
            except ImportError:
                pass
            except Exception as e:
                logger.debug(f"yfinance ga ikke {k}: {feiltekst(e)[:70]}")
            if not data:
                try:
                    data = hent_yahoo_direkte(k, eldste, i_dag)
                except Exception as e:
                    logger.info(f"   · referanse {k}: {feiltekst(e)[:70]}")
                    continue
            if data and len(data) > 100:
                bok.erstatt(k, data)
                bok.lagre_ticker(k)
                logger.info(f"📊 Referanse: {k} ({len(data)} dager)")
                skriv_referansevalg(opp, k, "indeks")
                return k, "indeks"
            logger.info(f"   · referanse {k}: for lite data ({len(data or {})} dager)")

    for k in kandidater:                       # offline: bruk det som ligger der
        if k in bok.serier and len(bok.serier[k]) > 100:
            skriv_referansevalg(opp, k, "indeks")
            return k, "indeks"

    if not opp.likevekt_reserve or not kalender:
        logger.warning("   ⚠️  Ingen referanseindeks, og likevektet reserve er av. "
                       "Meravkastning blir tom.")
        return "", ""

    logger.warning(
        f"   ⚠️  Ingen av indeksene svarte ({', '.join(kandidater[:4])} …). Bygger en "
        f"LIKEVEKTET reserve av de {len(bok.serier)} tickerne vi har. Meravkastningen "
        f"måles da mot snittselskapet, ikke mot børsen — det står i rapporten.")
    serie = bygg_likevekt(bok, kalender, felt, uten=kandidater)
    bok.erstatt(LIKEVEKT, serie)
    bok.lagre_ticker(LIKEVEKT)
    skriv_referansevalg(opp, LIKEVEKT, "likevekt")
    return LIKEVEKT, "likevekt"


def _dekningsrapport(opp: Oppsett, bok: Kursbok, logger: logging.Logger,
                     eldste: date) -> int:
    """
    Filen som skiller «ingen signaler her» fra «ingen data her».

    Uten den ser de to helt like ut i backtesten, og et selskap uten
    kurshistorikk blir stille borte i stedet for å bli et varsel.
    """
    alle_ar = list(range(eldste.year, date.today().year + 1))
    rader = []
    for t in sorted(bok.serier):
        dager = sorted(bok.serier[t])
        if not dager:
            rader.append({"Ticker": t, "Dager": 0, "Forste": "", "Siste": "",
                          "Ar_med_data": 0, "Ar_totalt": len(alle_ar),
                          "Dekning_Pst": 0.0, "Status": "INGEN_DATA"})
            continue
        ar = {d.year for d in dager}
        dekning = 100.0 * len(ar & set(alle_ar)) / max(1, len(alle_ar))
        rader.append({"Ticker": t, "Dager": len(dager), "Forste": iso(dager[0]),
                      "Siste": iso(dager[-1]), "Ar_med_data": len(ar & set(alle_ar)),
                      "Ar_totalt": len(alle_ar), "Dekning_Pst": round(dekning, 1),
                      "Status": ("FULL" if dekning >= 95 else
                                 "DELVIS" if dekning >= 40 else "TYNN")})
    rader.sort(key=lambda r: (r["Dekning_Pst"], r["Ticker"]))
    skriv_csv(opp.dekning_csv, rader,
              ["Ticker", "Dager", "Forste", "Siste", "Ar_med_data", "Ar_totalt",
               "Dekning_Pst", "Status"])

    tell: Dict[str, int] = {}
    for r in rader:
        tell[r["Status"]] = tell.get(r["Status"], 0) + 1
    logger.info(f"💾 Dekning: {opp.dekning_csv.name} — "
                + "  ".join(f"{k}: {v}" for k, v in sorted(tell.items())))
    tynne = [r["Ticker"] for r in rader if r["Status"] in ("TYNN", "INGEN_DATA")]
    if tynne:
        logger.warning(f"   ⚠️  {len(tynne)} tickere har tynn eller ingen historikk. De "
                       f"blir usynlige i backtesten, og det ser ut som fravær av signal: "
                       f"{', '.join(tynne[:10])}{' …' if len(tynne) > 10 else ''}")
    return len(tynne)


# ══════════════════════════════════════════════════════════════════════════
# STEG 5 — SLÅ SAMMEN SCORE OG KURS TIL ÉN FIL
# ══════════════════════════════════════════════════════════════════════════
#
# Én rad per innsidehandel, med scoren fra steg 3 og kursutviklingen fra
# steg 4 side om side. Dette er fila du åpner i Excel når du vil se med egne
# øyne om innsidekjøp gir avkastning.
#
# Tre ting skjer her, og alle tre er steder man taper penger på papiret som
# man ikke ville tapt i virkeligheten — eller motsatt:
#
#   1  HANDELSDAGEN. En melding etter 16:20 kan først handles neste dag.
#      Regelen bor i Kalender.forste_handledag og ingen andre steder.
#
#   2  AVNOTERINGER TELLES. Slutter en aksje å handles før horisonten er ute,
#      brukes siste observerte kurs og raden merkes AVNOTERT. Regnet vi ingen
#      avkastning i det hele tatt, ville nettopp de dårlige utfallene
#      forsvunnet ut av snittet — og backtesten ville sett bedre ut enn
#      virkeligheten.
#
#   3  SAMME MÅLESTOKK PÅ BEGGE SIDER. Aksje og referanse leses fra samme
#      kursfelt. Ellers får du utbytteavkastningen som falsk alfa.
#
# I tillegg regnes likviditeten ut på dagene FØR kjøpsdagen — aldri på
# kjøpsdagen selv. Tar vi med dag 0, bruker vi omsetningen meldingen selv
# skapte, og likviditetsfilteret slipper gjennom aksjer som bare var likvide
# fordi nyheten kom.

SKJEMA_MERGE = "6.0-merge"

FRA_STEG3 = [
    "Melding_ID", "Dato", "Klokkeslett", "Selskap", "Ticker", "ISIN", "Tittel",
    "Klasse", "Bullish_Score", "Signal", "Signal_Styrke", "Rangering",
    "Rolle", "Rolle_Rang", "Naerstaaende", "Person",
    "Antall_Netto", "Kurs_Snitt", "Verdi_NOK", "Beholdning_For",
    "Beholdning_Etter", "Okning_Pst", "Ny_Posisjon",
    "Klynge_ID", "Klynge_Personer", "Klynge_Meldinger", "Klynge_NOK",
    "Primaer_I_Klynge", "Tillit", "Metode", "Grunn", "Kontroll", "Emisjon",
    "Kilde_URL",
]


def merge_kolonner(opp: Oppsett) -> Tuple[List[str], List[str]]:
    """(alle kolonner, de som skal være TALL i Excel)."""
    ut = list(FRA_STEG3) + [
        "Handelsdag_0", "Dager_Forsinket", "Etter_Stengetid", "Kurs_0",
        "Volum_Snitt", "Omsetning_Snitt_NOK", "Andel_Dagsomsetning",
        "Score_Likviditetsjustert"]
    tall = ["Bullish_Score", "Signal_Styrke", "Rangering", "Rolle_Rang",
            "Antall_Netto", "Kurs_Snitt", "Verdi_NOK", "Beholdning_For",
            "Beholdning_Etter", "Okning_Pst", "Klynge_Personer", "Klynge_Meldinger",
            "Klynge_NOK", "Dager_Forsinket", "Kurs_0", "Volum_Snitt",
            "Omsetning_Snitt_NOK", "Andel_Dagsomsetning", "Score_Likviditetsjustert"]
    for h in opp.horisonter:
        ut += [f"Kurs_{h}", f"Avk_{h}", f"Ref_Avk_{h}", f"Meravk_{h}", f"Status_{h}"]
        tall += [f"Kurs_{h}", f"Avk_{h}", f"Ref_Avk_{h}", f"Meravk_{h}"]
    ut += ["Kurs_Status", "Skjema"]
    return ut, tall


# Hvor mange kalenderdager en melding kan vente på første handledag før vi
# sier at den ligger utenfor kursdataene. En lang påske er ti dager; et halvt
# år er at kursene mangler.
MAKS_FORSINKELSE_DAGER = 21


def steg5_merge(opp: Oppsett, logger: logging.Logger) -> Dict[str, Any]:
    opp.lag_mapper()
    hendelser = les_csv(opp.hendelser_csv)
    if not hendelser:
        return {"status": "HOPPET",
                "detaljer": f"ingen {opp.hendelser_csv.name} — kjør steg 3 først"}

    bok = Kursbok(opp.s4_dir).last()
    if not bok.serier:
        return {"status": "HOPPET",
                "detaljer": f"ingen kurser i {opp.s4_dir.name} — kjør steg 4 først"}

    ref, ref_kilde = les_referansevalg(opp)
    felt = opp.kursfelt_navn()
    logger.info(f"📂 {len(hendelser)} hendelser  •  {len(bok.serier)} tickere  •  "
                f"måler {opp.avkastningstype()} mot {ref}"
                + ("  (likevektet reserve, ikke børsen)" if ref_kilde == "likevekt" else ""))

    dager = utled_handledager(bok.datoer_per_ticker(), opp.handledag_terskel,
                              unntatt=ikke_aksjer(opp) + [ref])
    kal = Kalender(dager, opp.stengetid)
    if not kal:
        return {"status": "FEIL", "detaljer": "klarte ikke utlede en børskalender"}
    skriv_kalenderfil(opp.kalender_csv, kal.dager)
    logger.info(f"📅 {len(kal)} handledager ({kal.forste} → {kal.siste})")

    if ref not in bok.serier:
        logger.warning(f"   ⚠️  Ingen referanseserie ({ref}). Meravkastning blir tom, "
                       f"og da måler du ikke mot noe.")
    ref_serie = (bok.justert_serie(ref, kal.dager, felt, opp.maks_fyll_dager)
                 if ref in bok.serier else [None] * len(kal))

    # Kurs- og volumserier bygges én gang per ticker, ikke én gang per melding.
    tickere = {rens(h.get("Ticker")).upper() for h in hendelser if rens(h.get("Ticker"))}
    kurs: Dict[str, List[Optional[float]]] = {}
    volum: Dict[str, List[Optional[float]]] = {}
    siste_kursdag: Dict[str, Optional[date]] = {}
    for t in tickere:
        if t in bok.serier:
            kurs[t] = bok.justert_serie(t, kal.dager, felt, opp.maks_fyll_dager)
            volum[t] = bok.volumserie(t, kal.dager, opp.maks_fyll_dager)
            siste_kursdag[t] = bok.siste_dag(t)

    kolonner, tallkolonner = merge_kolonner(opp)
    rader: List[Rad] = []
    teller: Dict[str, int] = {}
    etter_stengetid_antall = 0

    for h in hendelser:
        rad: Rad = {k: h.get(k, "") for k in FRA_STEG3}
        rad["Skjema"] = SKJEMA_MERGE
        for k in kolonner:
            rad.setdefault(k, "")

        ticker = rens(h.get("Ticker")).upper()
        if not ticker:
            _sett_status(rad, teller, "INGEN_TICKER")
            rader.append(rad); continue
        if ticker not in kurs:
            _sett_status(rad, teller, "UKJENT_TICKER")
            rader.append(rad); continue

        handelsdag = kal.forste_handledag(h.get("Dato"), h.get("Klokkeslett"))
        if handelsdag is None:
            _sett_status(rad, teller, "NYERE_ENN_KURSDATA")
            rader.append(rad); continue

        meldingsdato = fra_iso(h.get("Dato"))
        # Ligger meldingen FØR første kursdag, finnes det ingen handelsdag å
        # snakke om — men `neste_handledag` svarer villig med kalenderens
        # aller første dag. Da fikk en melding fra 2019 kjøpskurs fra 2026,
        # og alle horisontene falt utenfor som «FOR_NY». Det så ut som at vi
        # ventet på flere kursdager. Vi manglet gamle.
        if meldingsdato is None or (handelsdag - meldingsdato).days > MAKS_FORSINKELSE_DAGER:
            _sett_status(rad, teller, "ELDRE_ENN_KURSDATA")
            rader.append(rad); continue
        etter = kal.etter_stengetid(h.get("Klokkeslett"))
        if etter:
            etter_stengetid_antall += 1
        rad["Handelsdag_0"] = iso(handelsdag)
        rad["Dager_Forsinket"] = (handelsdag - meldingsdato).days if meldingsdato else ""
        rad["Etter_Stengetid"] = "JA" if etter else "NEI"

        pos = kal.posisjon(handelsdag)
        serie = kurs[ticker]
        kurs_0 = serie[pos] if pos is not None else None
        if not kurs_0:
            _sett_status(rad, teller, "INGEN_KURS_DAG_0")
            rader.append(rad); continue
        rad["Kurs_0"] = round(kurs_0, 6)

        _likviditet(rad, opp, serie, volum[ticker], pos, h)
        status = _avkastninger(rad, opp, serie, ref_serie, kal, pos,
                               siste_kursdag.get(ticker))
        _sett_status(rad, teller, status)
        rader.append(rad)

    rader.sort(key=lambda r: (str(r.get("Dato")), str(r.get("Klokkeslett"))), reverse=True)
    skriv_tabell(opp.merget_csv, opp.merget_xlsx, rader, kolonner, logger,
                 tallkolonner=tallkolonner, arknavn="Innsidehandel og kurs")

    return _merge_rapport(rader, teller, etter_stengetid_antall, opp, logger, kal)


def _sett_status(rad: Rad, teller: Dict[str, int], status: str) -> None:
    rad["Kurs_Status"] = status
    teller[status] = teller.get(status, 0) + 1


def _likviditet(rad: Rad, opp: Oppsett, kurs: Sequence[Optional[float]],
                volum: Sequence[Optional[float]], pos: int, h: Rad) -> None:
    """Omsetning målt på dagene FØR kjøpsdagen — aldri på kjøpsdagen selv."""
    fra = max(0, pos - opp.volum_vindu)
    if pos <= fra:
        return
    v = [x for x in volum[fra:pos] if x]
    k = [x for x in kurs[fra:pos] if x]
    if not v or not k:
        return
    snitt_v = sum(v) / len(v)
    snitt_k = sum(k) / len(k)
    omsetning = snitt_v * snitt_k
    rad["Volum_Snitt"] = round(snitt_v, 1)
    rad["Omsetning_Snitt_NOK"] = round(omsetning, 0)
    verdi = tolk_maskin(h.get("Verdi_NOK"))
    if verdi and omsetning > 0:
        # Hvor stor handelen var i forhold til det aksjen normalt omsetter for.
        # Et kjøp på 5 % av dagsomsetningen er en helt annen sak enn ett på
        # 0,01 %, selv om beløpet er det samme.
        andel = verdi / omsetning
        rad["Andel_Dagsomsetning"] = round(andel, 4)
        # Scoren fra steg 3 vet ikke hvor likvid aksjen er — den kunnskapen
        # finnes først her. Et kjøp som er stort MOT omsetningen får et
        # påslag, ett som drukner i normal handel får et fradrag.
        score = tolk_maskin(h.get("Bullish_Score"))
        styrke = tolk_maskin(h.get("Signal_Styrke"))
        # Uten signalstyrke kan denne kolonnen ikke regnes ut. Skrev vi den
        # likevel, ble den nøyaktig 50,0 — nøytral — og steg 6 foretrekker den
        # framfor Bullish_Score. Hele scoren ble da borte i det stille, og
        # ingen hendelse kvalifiserte lenger. Mangler styrken, står feltet tomt
        # og steg 6 bruker den ujusterte scoren.
        if score is not None and styrke:
            faktor = 0.75 + 0.5 * _demp(andel, 0.05)      # 0,75 … 1,25
            fortegn = 1.0 if str(h.get("Klasse")) == "KJOP" else -1.0
            ny = 50.0 + 50.0 * fortegn * min(1.0, styrke / 100.0 * faktor)
            rad["Score_Likviditetsjustert"] = round(max(0.0, min(100.0, ny)), 1)


def _avkastninger(rad: Rad, opp: Oppsett, serie: Sequence[Optional[float]],
                  ref: Sequence[Optional[float]], kal: Kalender, pos: int,
                  siste_kursdag: Optional[date]) -> str:
    """
    Avkastning per horisont, normalisert til kjøpsdagen.

    For ALLE horisonter, også negative:  Avk(h) = P(h) / P(0) − 1.
    Negative horisonter gir da dagene FØR kjøpet, tegnet som en kurve som
    stiger opp mot null på dag 0. Det er den vanlige måten å vise opptakten
    på, og den er riktig vei.
    """
    kurs_0 = serie[pos]
    ref_0 = ref[pos] if pos < len(ref) else None
    siste_pos = len(serie) - 1
    for_ny = avnotert = minst_en = False

    for h in opp.horisonter:
        mål = pos + h
        felt_status = f"Status_{h}"
        if mål > siste_pos or mål < 0:
            rad[felt_status] = "FOR_NY" if mål > siste_pos else "FOR_KORT_HISTORIKK"
            if mål > siste_pos:
                for_ny = True
            continue

        kurs_h = serie[mål]
        status = "OK"
        if not kurs_h:
            # Ingen kurs. Er måldagen etter siste dag aksjen handlet, har den
            # sluttet å handles: da regner vi med siste observerte kurs og
            # merker raden. Det er dette som gjør at avnoteringer TELLER som
            # tap i stedet for å forsvinne ut av snittet.
            måldag = kal.dag(mål)
            if siste_kursdag and måldag and måldag > siste_kursdag:
                kurs_h = next((serie[i] for i in range(mål, pos, -1) if serie[i]), None)
                status = "AVNOTERT"
                avnotert = True
            if not kurs_h:
                rad[felt_status] = "MANGLER_KURS"
                continue

        avk = kurs_h / kurs_0 - 1.0
        rad[f"Kurs_{h}"] = round(kurs_h, 6)
        rad[f"Avk_{h}"] = round(avk, 6)
        rad[felt_status] = status
        minst_en = True

        if ref_0 and mål < len(ref):
            ref_h = ref[mål]
            if ref_h:
                ref_avk = ref_h / ref_0 - 1.0
                rad[f"Ref_Avk_{h}"] = round(ref_avk, 6)
                rad[f"Meravk_{h}"] = round(avk - ref_avk, 6)

    if avnotert:
        return "AVNOTERT"
    if for_ny:
        return "FOR_NY"
    return "OK" if minst_en else "INGEN_KURS_DAG_0"


def _merge_rapport(rader: List[Rad], teller: Dict[str, int], etter_stengetid: int,
                   opp: Oppsett, logger: logging.Logger,
                   kal: "Kalender") -> Dict[str, Any]:
    n = len(rader)
    logger.info(f"\n{'═' * 74}")
    logger.info("SAMMENSLÅINGEN")
    logger.info(f"{'═' * 74}")
    merker = {
        "OK": "  ✓",
        "AVNOTERT": "  · sluttet å handles — tapet telles, ikke fjernet",
        "FOR_NY": "  · venter på flere kursdager",
        "UKJENT_TICKER": "  ⚠️  ikke i kursfilene",
        "INGEN_TICKER": "  ⚠️  tom Ticker fra steg 1",
        "INGEN_KURS_DAG_0": "  ⚠️  ingen kurs på handelsdagen",
        "NYERE_ENN_KURSDATA": "  ⚠️  nyere enn kursdataene — kjør steg 4",
        "ELDRE_ENN_KURSDATA": "  ⚠️  ELDRE enn kursdataene — steg 4 har for kort "
                              "historikk. Kjør: --steg 4 --full",
    }
    for status, antall in sorted(teller.items(), key=lambda x: -x[1]):
        logger.info(f"  {status:<18} {antall:>6}  ({100.0*antall/max(1,n):5.1f} %)"
                    f"{merker.get(status, '')}")
    logger.info(f"\n  Etter stengetid ..... {etter_stengetid} "
                f"({100.0*etter_stengetid/max(1,n):.1f} %) — handles først neste dag.")

    brukbare = [r for r in rader if r.get("Kurs_Status") in ("OK", "AVNOTERT")]
    kjop = [r for r in brukbare if r.get("Klasse") == "KJOP"]
    salg = [r for r in brukbare if r.get("Klasse") == "SALG"]
    logger.info(f"  Brukbare kjøp ....... {len(kjop)}")
    logger.info(f"  Brukbare salg ....... {len(salg)}")

    # Et første, uformelt blikk på om scoren gjør noe som helst. Den ordentlige
    # prøven står i steg 6.
    h = opp.event_horisont
    kol = f"Meravk_{h}"
    med = [(tolk_maskin(r.get("Bullish_Score")), tolk_maskin(r.get(kol)))
           for r in brukbare]
    med = [(s, m) for s, m in med if s is not None and m is not None]
    if len(med) >= 40:
        med.sort()
        halv = len(med) // 2
        lav = snitt([m for _, m in med[:halv]])
        hoy = snitt([m for _, m in med[halv:]])
        logger.info(f"\n  Førsteinntrykk på {h} dagers meravkastning:")
        logger.info(f"    lav halvdel av scoren  {lav*100:+6.2f} %   (n={halv})")
        logger.info(f"    høy halvdel av scoren  {hoy*100:+6.2f} %   (n={len(med)-halv})")
        logger.info(f"    forskjell              {(hoy-lav)*100:+6.2f} prosentpoeng"
                    + ("   ← peker riktig vei" if hoy > lav else "   ← peker feil vei"))
    logger.info(f"{'═' * 74}")

    ok = teller.get("OK", 0) + teller.get("AVNOTERT", 0)
    status = "OK" if ok >= max(20, 0.4 * n) else ("DELVIS" if ok else "FEIL")

    # Hva er det som stopper flertallet? Uten dette svaret er «0/3912 rader
    # med kurs» like taust som ingen melding i det hele tatt.
    raad: List[str] = []
    verste = max((x for x in teller.items() if x[0] not in ("OK", "AVNOTERT")),
                 key=lambda x: x[1], default=("", 0))
    if status != "OK" and verste[1] >= 0.3 * max(1, n):
        raad = {
            "ELDRE_ENN_KURSDATA": [
                f"{verste[1]} meldinger er ELDRE enn kursene: steg 4 har for kort "
                f"historikk (kalenderen begynner {kal.forste}).",
                "kjør: python innsidehandel_pipeline.py --steg 4,5,6 --full"],
            "NYERE_ENN_KURSDATA": [
                f"{verste[1]} meldinger er nyere enn siste kursdag ({kal.siste}).",
                "kjør steg 4 på nytt så kursene blir ajour"],
            "UKJENT_TICKER": [
                f"{verste[1]} meldinger har en ticker uten kursfil.",
                "sjekk _dekning.csv fra steg 4 — og at aksjelista er fersk"],
            "UKJENT_KLASSE": [],
        }.get(verste[0], [])
    if not kjop and ok:
        raad.append("kurser finnes, men ingen KJØP: feilen sitter i steg 2/3 "
                    "(uttrekket), ikke her")
    return {"status": status, "rader": n, "brukbare": ok, "kjop": len(kjop),
            "salg": len(salg), "raad": raad,
            "detaljer": f"{ok}/{n} rader med kurs ({len(kjop)} kjøp, {len(salg)} salg) "
                        f"→ {opp.merget_xlsx.name}"
                        + (f" · flest {verste[0]}" if verste[1] else "")}


# ══════════════════════════════════════════════════════════════════════════
# DEL I — RAPPORT: HTML OG SVG
# ══════════════════════════════════════════════════════════════════════════
#
# Grafene tegnes som SVG for hånd. Det sparer oss for matplotlib, gir en fil
# som er skarp i alle størrelser, og gjør at hele rapporten er ÉN fil du kan
# sende til noen.
#
# All tekst som kommer utenfra — selskapsnavn, titler, personnavn — går
# gjennom `trygg`. Et selskap som heter «A & B <Holding>» skal ikke kunne
# ødelegge siden.

def trygg(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        if v != v:
            return ""
        return f"{v:,.4f}".rstrip("0").rstrip(".") if abs(v) < 1e6 else f"{v:,.0f}"
    return html_modul.escape(str(v), quote=True)


def tabell_html(rader: Sequence[Rad], kolonner: Optional[Sequence[str]] = None) -> str:
    rader = list(rader)
    if not rader:
        return "<p class='fot'>(ingen rader)</p>"
    if kolonner is None:
        kolonner = list(rader[0].keys())
    hode = "".join(f"<th>{trygg(k)}</th>" for k in kolonner)
    kropp = ["<tr>" + "".join(f"<td>{trygg(r.get(k, ''))}</td>" for k in kolonner) + "</tr>"
             for r in rader]
    return (f"<div class='tabell'><table><thead><tr>{hode}</tr></thead>"
            f"<tbody>{''.join(kropp)}</tbody></table></div>")


FARGER = ["#1F5C63", "#A2492A", "#7A5E1B", "#4A5568", "#5B7C99", "#6B4C7A"]


def svg_linje(serier: Dict[str, Sequence[Tuple[float, float]]], bredde: int = 780,
              hoyde: int = 300, null_linje: bool = True, y_etikett: str = "") -> str:
    """Enkel linjegraf. Tomme eller for korte serier hoppes over."""
    rene = {n: sorted(p) for n, p in serier.items() if len(p) >= 2}
    if not rene:
        return ""
    alle = [p for punkter in rene.values() for p in punkter]
    x_min = min(p[0] for p in alle); x_maks = max(p[0] for p in alle)
    y_min = min(p[1] for p in alle); y_maks = max(p[1] for p in alle)
    if null_linje:
        y_min, y_maks = min(y_min, 0.0), max(y_maks, 0.0)
    if x_maks == x_min:
        x_maks = x_min + 1.0
    if y_maks == y_min:
        y_maks = y_min + 1.0
    pad = (y_maks - y_min) * 0.08
    y_min -= pad; y_maks += pad

    venstre, topp, hoyre, bunn = 68, 16, 16, 34
    b, h = bredde - venstre - hoyre, hoyde - topp - bunn

    def px(x: float) -> float:
        return venstre + (x - x_min) / (x_maks - x_min) * b

    def py(y: float) -> float:
        return topp + (y_maks - y) / (y_maks - y_min) * h

    ut = [f'<svg viewBox="0 0 {bredde} {hoyde}" width="100%" role="img" '
          f'xmlns="http://www.w3.org/2000/svg">',
          f'<rect x="{venstre}" y="{topp}" width="{b}" height="{h}" fill="none" '
          f'stroke="var(--line)"/>']
    if y_min <= 0 <= y_maks:
        y0 = py(0.0)
        ut.append(f'<line x1="{venstre}" y1="{y0:.1f}" x2="{venstre+b}" y2="{y0:.1f}" '
                  f'stroke="var(--muted)" stroke-dasharray="3 3"/>')
    for i, (navn, punkter) in enumerate(rene.items()):
        farge = FARGER[i % len(FARGER)]
        d = " ".join(f"{'M' if j == 0 else 'L'}{px(x):.1f},{py(y):.1f}"
                     for j, (x, y) in enumerate(punkter))
        ut.append(f'<path d="{d}" fill="none" stroke="{farge}" stroke-width="2"/>')
        ut.append(f'<text x="{venstre+10}" y="{topp+18+i*16}" font-size="12" '
                  f'fill="{farge}">{trygg(navn)}</text>')
    for verdi in (y_maks, (y_maks + y_min) / 2.0, y_min):
        ut.append(f'<text x="{venstre-8}" y="{py(verdi)+4:.1f}" font-size="11" '
                  f'text-anchor="end" fill="var(--muted)">{verdi:,.2f}</text>')
    for x in (x_min, (x_min + x_maks) / 2.0, x_maks):
        ut.append(f'<text x="{px(x):.1f}" y="{hoyde-12}" font-size="11" '
                  f'text-anchor="middle" fill="var(--muted)">{x:,.0f}</text>')
    if y_etikett:
        ut.append(f'<text x="6" y="{topp+12}" font-size="11" '
                  f'fill="var(--muted)">{trygg(y_etikett)}</text>')
    ut.append("</svg>")
    return "".join(ut)


def svg_stolper(navn: Sequence[str], verdier: Sequence[float], bredde: int = 780,
                hoyde: int = 260, y_etikett: str = "") -> str:
    """Stolpediagram — brukes til score-bøttene, som er hele poenget med testen."""
    rene = [(n, float(v)) for n, v in zip(navn, verdier) if v == v]
    if not rene:
        return ""
    y_min = min(0.0, min(v for _, v in rene))
    y_maks = max(0.0, max(v for _, v in rene))
    if y_maks == y_min:
        y_maks = y_min + 1.0
    pad = (y_maks - y_min) * 0.15
    y_min -= pad; y_maks += pad

    venstre, topp, hoyre, bunn = 68, 16, 16, 46
    b, h = bredde - venstre - hoyre, hoyde - topp - bunn
    bredde_stolpe = b / max(1, len(rene)) * 0.62

    def py(y: float) -> float:
        return topp + (y_maks - y) / (y_maks - y_min) * h

    ut = [f'<svg viewBox="0 0 {bredde} {hoyde}" width="100%" role="img" '
          f'xmlns="http://www.w3.org/2000/svg">']
    y0 = py(0.0)
    ut.append(f'<line x1="{venstre}" y1="{y0:.1f}" x2="{venstre+b}" y2="{y0:.1f}" '
              f'stroke="var(--muted)"/>')
    for i, (n, v) in enumerate(rene):
        midt = venstre + b * (i + 0.5) / len(rene)
        x = midt - bredde_stolpe / 2
        y = py(max(0.0, v))
        høyde_stolpe = abs(py(v) - y0)
        farge = FARGER[0] if v >= 0 else FARGER[1]
        ut.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bredde_stolpe:.1f}" '
                  f'height="{max(1.0, høyde_stolpe):.1f}" fill="{farge}" opacity="0.85"/>')
        ut.append(f'<text x="{midt:.1f}" y="{hoyde-26}" font-size="11" '
                  f'text-anchor="middle" fill="var(--muted)">{trygg(n)}</text>')
        ut.append(f'<text x="{midt:.1f}" y="{(y-6) if v >= 0 else (py(v)+14):.1f}" '
                  f'font-size="11" text-anchor="middle" fill="var(--ink)">{v:+.2f}</text>')
    for verdi in (y_maks, 0.0, y_min):
        ut.append(f'<text x="{venstre-8}" y="{py(verdi)+4:.1f}" font-size="11" '
                  f'text-anchor="end" fill="var(--muted)">{verdi:,.2f}</text>')
    if y_etikett:
        ut.append(f'<text x="6" y="{topp+12}" font-size="11" '
                  f'fill="var(--muted)">{trygg(y_etikett)}</text>')
    ut.append("</svg>")
    return "".join(ut)


HODE = """<!doctype html><html lang="nb"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Innsidehandel på Oslo Børs</title><style>
:root { --ink:#12191A; --muted:#53605F; --line:#D5DEDD; --ground:#F3F6F6;
        --flat:#FFF; --accent:#1F5C63; --flag:#A2492A; --flagbg:#F7E8E1;
        --okbg:#E7F1EA; --ok:#1F6B45; }
@media (prefers-color-scheme: dark) {
  :root { --ink:#E8EDEC; --muted:#9AA8A7; --line:#2C3838; --ground:#0E1414;
          --flat:#161E1E; --accent:#63B6BE; --flag:#E08A63; --flagbg:#2A1C16;
          --okbg:#15281F; --ok:#79C79B; }
}
* { box-sizing:border-box; }
body { margin:0; background:var(--ground); color:var(--ink);
       font:16px/1.6 Georgia,"Times New Roman",serif; }
.wrap { max-width:64rem; margin:0 auto; padding:3rem 1.5rem 5rem; }
h1 { font-size:2rem; margin:0 0 .3rem; letter-spacing:-.02em; }
h2 { font-size:1.3rem; margin:2.5rem 0 .6rem; letter-spacing:-.01em; }
h3 { font-size:1.05rem; margin:1.6rem 0 .4rem; }
p { margin:.5rem 0; color:var(--muted); }
.undertittel { font-size:.95rem; }
.dom { border-radius:6px; padding:1.1rem 1.35rem; margin:1.5rem 0; border-left:4px solid; }
.dom h2 { margin:0 0 .4rem; font-size:1.15rem; }
.dom p { color:var(--ink); font-size:.95rem; }
.stengt { background:var(--flagbg); border-color:var(--flag); }
.stengt h2 { color:var(--flag); }
.apen { background:var(--okbg); border-color:var(--ok); }
.apen h2 { color:var(--ok); }
.varsel { background:var(--flagbg); border-left:3px solid var(--flag);
          border-radius:4px; padding:1rem 1.25rem; margin:1.5rem 0; }
.varsel h2 { margin:0 0 .5rem; font-size:1.05rem; color:var(--flag); }
.varsel ul { margin:0; padding-left:1.1rem; }
.varsel li { color:var(--ink); font-size:.93rem; margin:.35rem 0; }
.tabell { overflow-x:auto; background:var(--flat); border:1px solid var(--line);
          border-radius:4px; margin:1rem 0; }
table { border-collapse:collapse; width:100%; font-size:.87rem;
        font-variant-numeric:tabular-nums; }
th { text-align:left; padding:.55rem .8rem; border-bottom:1px solid var(--line);
     font:600 .68rem/1.4 ui-monospace,Consolas,monospace; letter-spacing:.08em;
     text-transform:uppercase; color:var(--muted); white-space:nowrap; }
td { padding:.45rem .8rem; border-bottom:1px solid var(--line); white-space:nowrap; }
tbody tr:last-child td { border-bottom:none; }
.graf { background:var(--flat); border:1px solid var(--line); border-radius:4px;
        padding:1rem; margin:1rem 0; }
.fot { font-size:.85rem; }
</style></head><body><div class="wrap">"""

FOT = "</div></body></html>"


# ══════════════════════════════════════════════════════════════════════════
# STEG 6 — BACKTEST
# ══════════════════════════════════════════════════════════════════════════
#
# Fire spørsmål, i denne rekkefølgen:
#
#   A  VIRKER SIGNALET?     Gjennomsnittlig meravkastning etter innsidekjøp,
#                           med klyngerobust standardfeil og bootstrap.
#                           Salgene kjøres som KONTROLLGRUPPE: går kjøpene
#                           bedre enn børsen og salgene dårligere, ser du
#                           sannsynligvis en ekte effekt. Ser de to like ut,
#                           er det noe galt lenger oppe i røret — uansett
#                           hvor pent kjøpstallet er.
#
#   B  VIRKER SCOREN?       Hendelsene deles i fem like store bøtter etter
#                           Bullish_Score. Stiger meravkastningen monotont
#                           fra bøtte 1 til bøtte 5, måler scoren noe. Er
#                           kurven flat eller rotete, gjør den det ikke — og
#                           da er scoren pynt, ikke informasjon. Dette er den
#                           ærligste prøven på arbeidet i steg 3.
#
#   C  ER DET NOK TIL Å HANDLE PÅ?   En port. Er meravkastningen ikke til å
#                           skille fra null, sier rapporten det øverst, og
#                           porteføljetallene under merkes som pynt.
#
#   D  OVERLEVER DET FRIKSJON?       Månedlig rebalansering med spread og
#                           kurtasje trukket løpende, ikke til slutt.

BRUKBAR_KURS = ("OK", "AVNOTERT")
GODE_TILLITSNIVA = ("HOY", "MIDDELS")


def _bt(rad: Rad, felt: str) -> Optional[float]:
    return tolk_maskin(rad.get(felt))


def velg(rader: Sequence[Rad], opp: Oppsett, klasse: str,
         avvist: Optional[Dict[str, int]] = None,
         krev_kurs: bool = True) -> List[Rad]:
    """
    Hvilke hendelser er egnet til å regne på?

    Merk hva som IKKE står her: ingen betingelse om at aksjen fortsatt
    handles om 60 dager. Avnoterte selskaper er med, med tapet sitt.
    """
    # `avvist` er ikke pynt: er utvalget tomt, er det ETT av kravene under
    # som tømte det, og uten tellingen ser alle seks like skyldige ut.
    def nei(grunn: str) -> None:
        if avvist is not None:
            avvist[grunn] = avvist.get(grunn, 0) + 1

    ut = []
    for r in rader:
        if r.get("Klasse") != klasse:
            nei(f"klasse er {r.get('Klasse') or 'tom'}, ikke {klasse}")
            continue
        if krev_kurs and r.get("Kurs_Status") not in BRUKBAR_KURS:
            # krev_kurs=False brukes til DAGENS liste: en melding fra i går har
            # ingen avkastning å måles på ennå, men den er fullt handlebar.
            nei(f"kurs: {r.get('Kurs_Status') or 'tom'}")
            continue
        if r.get("Tillit") not in GODE_TILLITSNIVA:
            nei(f"tillit: {r.get('Tillit') or 'tom'}")
            continue
        if opp.kun_primaer and r.get("Primaer_I_Klynge") != "JA":
            nei("ikke primær i klyngen (--alle-i-klynge tar dem med)")
            continue
        verdi = _bt(r, "Verdi_NOK")
        # Mangler beløpet, beholder vi hendelsen — retningen er lest, og å
        # kaste den ville vært å kaste data på grunn av vår egen lesefeil.
        if verdi is not None and verdi < opp.min_verdi_nok:
            nei(f"beløp under {opp.min_verdi_nok:,.0f} kr")
            continue
        if not r.get("Handelsdag_0"):
            nei("ingen handelsdag fra steg 5")
            continue
        ut.append(r)
    return sorted(ut, key=lambda r: str(r.get("Handelsdag_0")))


def horisonter_i(rader: Sequence[Rad]) -> List[int]:
    if not rader:
        return []
    ut = []
    for k in rader[0]:
        m = re.fullmatch(r"Meravk_(-?\d+)", str(k))
        if m:
            ut.append(int(m.group(1)))
    return sorted(ut)


def del_utvalg(rader: Sequence[Rad], slutt: str) -> Tuple[List[Rad], List[Rad]]:
    grense = fra_iso(slutt) or date(2021, 12, 31)
    inn, ut = [], []
    for r in rader:
        d = fra_iso(r.get("Handelsdag_0"))
        (inn if (d and d <= grense) else ut).append(r)
    return inn, ut


def en_rad(utvalg: str, h: int, rader: Sequence[Rad], opp: Oppsett) -> Rad:
    kol = f"Meravk_{h}"
    gyldige = [(v, r) for r, v in ((r, _bt(r, kol)) for r in rader) if v is not None]
    n = len(gyldige)
    rad: Rad = {"Utvalg": utvalg, "Horisont": h, "N": n,
                "Selskaper": len({r.get("Ticker") for _, r in gyldige})}
    if n < 10:
        return rad

    verdier = [v for v, _ in gyldige]
    selskap = [str(r.get("Ticker")) for _, r in gyldige]
    dato = [str(r.get("Handelsdag_0")) for _, r in gyldige]

    m = snitt(verdier)
    rad["Snitt_Pst"] = round(m * 100, 4)
    rad["Median_Pst"] = round(median(verdier) * 100, 4)
    rad["Andel_Opp_Pst"] = round(andel_over_null(verdier) * 100, 2)

    feil, metode = toveis_klyngefeil(verdier, selskap, dato)
    if feil == feil and feil > 0:
        rad["Std_Feil_Pst"] = round(feil * 100, 4)
        rad["Feilmetode"] = metode
        t = m / feil
        rad["t"] = round(t, 3)
        rad["Signifikant_5pst"] = "JA" if abs(t) > 1.96 else "nei"

    lav, hoy = bootstrap_ki(verdier, selskap, opp.bootstrap_runder, opp.bootstrap_fro)
    if lav == lav:
        rad["KI_Lav_Pst"] = round(lav * 100, 4)
        rad["KI_Hoy_Pst"] = round(hoy * 100, 4)
        rad["KI_Krysser_Null"] = "JA" if lav <= 0 <= hoy else "nei"
    return rad


def event_study(rader: Sequence[Rad], opp: Oppsett, merkelapp: str = "kjøp") -> List[Rad]:
    """
    «alt» står nederst med vilje: konklusjonen skal leses ut av UT-UTVALGET.
    Totalen inneholder dataene parametrene ble valgt på.
    """
    inn, ut = del_utvalg(rader, opp.inn_utvalg_slutt)
    tabell = []
    for navn, del_ in (("inn-utvalg", inn), ("ut-utvalg", ut), ("alt", rader)):
        if not del_:
            continue
        for h in horisonter_i(rader):
            r = en_rad(navn, h, del_, opp)
            r["Gruppe"] = merkelapp
            tabell.append(r)
    return tabell


def event_kurve(rader: Sequence[Rad]) -> List[Rad]:
    """Snitt meravkastning per horisont — kurven rundt kjøpsdagen."""
    ut = []
    for h in horisonter_i(rader):
        verdier = [v for v in (_bt(r, f"Meravk_{h}") for r in rader) if v is not None]
        if len(verdier) >= 10:
            ut.append({"Horisont": h, "N": len(verdier),
                       "Snitt_Pst": round(snitt(verdier) * 100, 4),
                       "Median_Pst": round(median(verdier) * 100, 4)})
    return ut


def test_scoren(kjop: Sequence[Rad], salg: Sequence[Rad], opp: Oppsett) -> List[Rad]:
    """
    Virker bullishness-scoren?

    Alle vurderte hendelser — kjøp OG salg — sorteres på Bullish_Score og
    deles i like store bøtter. Er scoren informativ, skal meravkastningen
    stige fra bøtte 1 til bøtte 5. Er den flat, måler scoren ingenting, og
    da skal du vite det.

    Dette er den eneste ærlige prøven på arbeidet i steg 3, og den er verdt
    mer enn hele porteføljesimuleringen.
    """
    h = opp.event_horisont
    kol = f"Meravk_{h}"
    alle = [r for r in list(kjop) + list(salg)
            if _bt(r, "Bullish_Score") is not None and _bt(r, kol) is not None]
    if len(alle) < opp.antall_bøtter * 10:
        return []

    grenser = boetter([_bt(r, "Bullish_Score") for r in alle], opp.antall_bøtter)
    if not grenser:
        return []
    bøtte: Dict[str, List[Rad]] = {}
    for r in alle:
        bøtte.setdefault(bøttemerke(_bt(r, "Bullish_Score"), grenser), []).append(r)

    ut: List[Rad] = []
    for navn in sorted(bøtte):
        del_ = bøtte[navn]
        v = [_bt(r, kol) for r in del_]
        s = [_bt(r, "Bullish_Score") for r in del_]
        m = snitt(v)
        feil, _ = toveis_klyngefeil(v, [str(r.get("Ticker")) for r in del_],
                                    [str(r.get("Handelsdag_0")) for r in del_])
        ut.append({
            "Bøtte": navn, "Score_fra": round(min(s), 1), "Score_til": round(max(s), 1),
            "N": len(v), "Snitt_Meravk_Pst": round(m * 100, 3),
            "Median_Pst": round(median(v) * 100, 3),
            "Andel_Opp_Pst": round(andel_over_null(v) * 100, 1),
            "t": round(m / feil, 2) if feil == feil and feil > 0 else "",
            "Andel_Kjop_Pst": round(100.0 * sum(1 for r in del_
                                                if r.get("Klasse") == "KJOP") / len(del_), 1),
        })
    return ut


def score_dom(tabell: Sequence[Rad]) -> str:
    """Én setning om hvorvidt scoren rangerer riktig vei."""
    if len(tabell) < 3:
        return "For få hendelser til å teste om scoren rangerer riktig."
    verdier = [float(r["Snitt_Meravk_Pst"]) for r in tabell]
    nederst, øverst = verdier[0], verdier[-1]
    spenn = øverst - nederst
    stigende = sum(1 for i in range(1, len(verdier)) if verdier[i] > verdier[i - 1])
    monoton = stigende == len(verdier) - 1
    if monoton and spenn > 0.5:
        return (f"✓ Scoren rangerer riktig vei og monotont: nederste bøtte "
                f"{nederst:+.2f} %, øverste {øverst:+.2f} % — {spenn:.2f} "
                f"prosentpoeng spenn.")
    if spenn > 0.5:
        return (f"~ Scoren peker riktig vei ({nederst:+.2f} % nederst mot "
                f"{øverst:+.2f} % øverst), men ikke monotont "
                f"({stigende} av {len(verdier)-1} trinn stiger). Deler av "
                f"rangeringen er støy.")
    if spenn < -0.5:
        return (f"⚠️  Scoren peker FEIL vei: nederste bøtte {nederst:+.2f} % slår "
                f"øverste {øverst:+.2f} %. Enten er vektene gale, eller så leser "
                f"uttrekket noe feil.")
    return (f"⚠️  Scoren skiller ikke: {nederst:+.2f} % nederst mot {øverst:+.2f} % "
            f"øverst er praktisk talt likt. Rangeringen bærer ingen informasjon, "
            f"og da er den pynt.")


def vurder(tabell: Sequence[Rad], opp: Oppsett) -> Dict[str, Any]:
    """
    Er det noe her i det hele tatt?

    Dommen leses av UT-utvalget på hovedhorisonten. Finnes det ikke noe
    ut-utvalg ennå, brukes «alt», og det sies tydelig fra at tallet da er
    målt på de samme dataene parametrene ble valgt på.
    """
    h = opp.event_horisont

    def finn(utvalg: str) -> Optional[Rad]:
        for r in tabell:
            if (r.get("Gruppe") == "kjøp" and r.get("Utvalg") == utvalg
                    and r.get("Horisont") == h):
                return r
        return None

    rad = finn("ut-utvalg")
    grunnlag = "ut-utvalg"
    if rad is None or int(rad.get("N", 0)) < 10:
        rad = finn("alt")
        grunnlag = "alt (ingen ut-utvalg ennå — tallet er ikke uavhengig testet)"

    dom: Dict[str, Any] = {"horisont": h, "grunnlag": grunnlag, "rad": rad,
                           "apen": False, "tekst": "", "kort": ""}
    if rad is None or rad.get("Snitt_Pst") in (None, ""):
        dom["kort"] = "INGEN DOM"
        dom["tekst"] = f"For få hendelser på {h} dager til å regne på i det hele tatt."
        return dom

    n = int(rad.get("N", 0))
    m = float(rad.get("Snitt_Pst"))
    t = rad.get("t", "")
    if n < opp.min_hendelser_for_dom:
        dom["kort"] = "FOR TYNT GRUNNLAG"
        dom["tekst"] = (
            f"Bare {n} hendelser på {h} dager, mot en grense på "
            f"{opp.min_hendelser_for_dom}. Meravkastningen på {m:+.2f} % er en "
            f"indikasjon, ikke et svar. Porteføljen under er regnet ut, men den "
            f"hviler på for få observasjoner til å bety noe.")
        return dom

    if rad.get("KI_Krysser_Null") == "JA" or rad.get("Signifikant_5pst") == "nei":
        dom["kort"] = "PORTEN ER STENGT"
        dom["tekst"] = (
            f"Meravkastningen på {h} dager er {m:+.2f} % (t = {t}), men "
            f"konfidensintervallet krysser null. Det er ikke grunnlag for å bygge en "
            f"strategi på dette. Ikke let videre etter et filter som gjør tallet pent "
            f"— det er å lete etter et resultat, ikke etter et svar. "
            f"Porteføljetallene under er tatt med for åpenhetens skyld.")
        return dom

    dom["apen"] = True
    dom["kort"] = "PORTEN ER ÅPEN"
    dom["tekst"] = (
        f"{m:+.2f} % meravkastning på {h} dager, n = {n}, t = {t}, 95 % KI "
        f"[{rad.get('KI_Lav_Pst')}, {rad.get('KI_Hoy_Pst')}] — målt på {grunnlag}. "
        f"Da er porteføljesimuleringen verdt å lese.")
    return dom


def kontroll_salg(kjop_tabell: Sequence[Rad], salg_tabell: Sequence[Rad],
                  opp: Oppsett) -> str:
    """
    Kontrollen som avslører feil ingen andre tall avslører.

    Kjøp bør slå børsen; salg bør ligge under. Ser de to like ut, er det ikke
    et resultat — det er et varsel om at noe lenger oppe i røret er galt.
    """
    h = opp.event_horisont

    def hent(tabell):
        return next((r for r in tabell
                     if r.get("Utvalg") == "alt" and r.get("Horisont") == h), None)

    k, s = hent(kjop_tabell), hent(salg_tabell)
    if not k or not s or k.get("Snitt_Pst") in (None, "") or s.get("Snitt_Pst") in (None, ""):
        return "Ingen kontrollgruppe: for få salg til å sammenlikne med."
    kv, sv = float(k["Snitt_Pst"]), float(s["Snitt_Pst"])
    forskjell = kv - sv
    if forskjell > 0.5:
        return (f"✓ Kjøp {kv:+.2f} % mot salg {sv:+.2f} % på {h} dager — "
                f"{forskjell:.2f} prosentpoeng fra hverandre, i riktig retning.")
    if abs(forskjell) <= 0.5:
        return (f"⚠️  Kjøp {kv:+.2f} % og salg {sv:+.2f} % er praktisk talt like. Et "
                f"ekte innsidesignal skiller dem. Mistenk uttrekket eller "
                f"sammenslåingen før du tror på kjøpstallet.")
    return (f"⚠️  Salg ({sv:+.2f} %) slår kjøp ({kv:+.2f} %) på {h} dager. Det er "
            f"motsatt av hypotesen — sjekk at retningen leses riktig.")


def undergrupper(rader: Sequence[Rad], opp: Oppsett) -> List[Rad]:
    """
    Deler utvalget på det vi faktisk har kolonner for.

    «Etter stengetid» og «Tillit» er KONTROLLER, ikke hypoteser. Store
    forskjeller der er varsler om at handelsdagsregelen eller uttrekket
    svikter — ikke funn.
    """
    h = opp.event_horisont
    kol = f"Meravk_{h}"
    med = [r for r in rader if _bt(r, kol) is not None]
    if len(med) < 40:
        return []
    ut: List[Rad] = []

    def legg_til(gruppe: str, verdi: str, del_: Sequence[Rad]) -> None:
        if len(del_) < 10:
            return
        v = [_bt(r, kol) for r in del_]
        m = snitt(v)
        feil, _ = toveis_klyngefeil(v, [str(r.get("Ticker")) for r in del_],
                                    [str(r.get("Handelsdag_0")) for r in del_])
        ut.append({"Gruppe": gruppe, "Verdi": verdi, "N": len(v),
                   "Snitt_Pst": round(m * 100, 3),
                   "Andel_Opp_Pst": round(andel_over_null(v) * 100, 1),
                   "t": round(m / feil, 2) if feil == feil and feil > 0 else ""})

    def del_på(gruppe: str, nokkel) -> None:
        bøtter: Dict[str, List[Rad]] = {}
        for r in med:
            k = nokkel(r)
            if k not in ("", None):
                bøtter.setdefault(str(k), []).append(r)
        for k in sorted(bøtter):
            legg_til(gruppe, k, bøtter[k])

    del_på("År", lambda r: (fra_iso(r.get("Handelsdag_0")) or date(1970, 1, 1)).year)
    del_på("Rolle", lambda r: r.get("Rolle") or "UKJENT")
    del_på("Signal", lambda r: r.get("Signal"))
    del_på("Nærstående (kontroll)", lambda r: r.get("Naerstaaende"))
    del_på("Etter stengetid (kontroll)", lambda r: r.get("Etter_Stengetid"))
    del_på("Tillit (kontroll)", lambda r: r.get("Tillit"))
    del_på("Antall kjøpere i klyngen",
           lambda r: "1" if (_bt(r, "Klynge_Personer") or 1) <= 1 else "2 eller flere")

    def kvartilgruppe(navn: str, felt: str) -> None:
        grenser = boetter([v for v in (_bt(r, felt) for r in med) if v is not None], 4)
        if not grenser:
            return
        bøtter: Dict[str, List[Rad]] = {}
        for r in med:
            v = _bt(r, felt)
            if v is not None:
                bøtter.setdefault(bøttemerke(v, grenser), []).append(r)
        for k in sorted(bøtter):
            legg_til(navn, k, bøtter[k])

    kvartilgruppe("Beløp (NOK)", "Verdi_NOK")
    kvartilgruppe("Økning av egen post (%)", "Okning_Pst")
    kvartilgruppe("Andel av dagsomsetning", "Andel_Dagsomsetning")
    return ut


# ── PORTEFØLJEN ──────────────────────────────────────────────────────────

# ══════════════════════════════════════════════════════════════════════════
# DEL H — PORTEFØLJEN: ÉN MOTOR, MANGE STRATEGIER
# ══════════════════════════════════════════════════════════════════════════
#
# Den gamle simuleringen kunne én ting: kjøpe de tjue beste på score, én gang
# i måneden. Det er to problemer med det. Et signal fra den 2. ventet til den
# 1. neste måned — nesten en hel måned av den avkastningen event studyen
# måler på tjue dager var da allerede borte. Og med bare ÉN strategi vet du
# ikke om resultatet skyldes signalet eller det ene rebalanseringsvalget.
#
# Her er alt som skiller strategiene samlet i én dataklasse, og motoren under
# kjenner bare den. Da kan tolv varianter kjøres på nøyaktig de samme dataene
# og stilles opp mot hverandre.
#
# ADVARSELEN FØRST, FORDI DEN ER VIKTIGERE ENN TABELLEN:
# Kjører du tolv strategier og velger den beste, har du ikke funnet den beste
# strategien. Du har funnet den heldigste. Med tolv forsøk er det ventet at
# den beste ser omtrent 0,5 i Sharpe bedre ut enn den fortjener, ren flaks.
# Derfor måles hver variant på BEGGE utvalgene hver for seg: rangeringen gjør
# du på inn-utvalget, dommen leser du av ut-utvalget — og den kolonnen tåler
# å bli brukt ÉN gang. Leser du den, velger, og leser igjen, er den ikke
# lenger et ut-utvalg.


@dataclass(frozen=True)
class Strategi:
    """Alt som skiller én strategi fra en annen. Motoren kjenner bare denne."""

    navn: str
    hvorfor: str = ""

    # ── når kjøpes det ───────────────────────────────────────────────────
    takt: str = "maaned"           # «dag», «uke» eller «maaned»
    hold_dager: int = 0            # >0: hendelsesdrevet, fast holdetid
    vindu_dager: int = 0           # 0 = arv fra Oppsett
    stopp_pst: float = 0.0         # 0 = av

    # ── hva kjøpes ───────────────────────────────────────────────────────
    maks_navn: int = 0             # 0 = arv
    # Minste antall posisjoner risikoen skal deles på. Det kan ikke tvinge
    # fram navn som ikke finnes, så det virker som et TAK på hver posisjon:
    # ingen får mer enn 1/min_navn av kapitalen. Kvalifiserer bare én aksje,
    # kjøpes den for en femtedel, og de fire femtedelene blir stående i
    # kontanter — synlig i «Kapital ute», ikke skjult i avkastningen.
    #
    # Uten dette lå porteføljen med 100 % i ett selskap på mange dager, og da
    # måler backtesten den ene aksjen, ikke signalet. 0 = av.
    min_navn: int = 0              # 0 = arv fra Oppsett.min_navn_portefolje
    vekting: str = "lik"           # «lik» eller «score»
    # «full»: kapitalen fordeles på de posisjonene som faktisk finnes.
    # «fast»: hver posisjon får 1/maks_navn, resten blir stående i kontanter.
    # Forskjellen er stor når signalene er få, og den er ikke et mål på
    # signalet — den er et mål på hvor mye kapital som ligger ubrukt.
    kapitalbruk: str = "full"
    min_score: float = -1.0        # -1 = arv
    min_omsetning: float = -1.0    # -1 = arv
    halveringstid: int = 0         # dager; 0 = ingen forfall på scoren

    # ── filtrene ─────────────────────────────────────────────────────────
    momentum_dager: int = 0        # 0 = av
    momentum_min: float = 0.0
    snu_lang_dager: int = 0        # 0 = av
    snu_lang_maks: float = 0.0
    snu_kort_dager: int = 0
    snu_kort_min: float = 0.0
    volum_faktor: float = 0.0      # 0 = av


# Varianten som står FØRST er hovedstrategien: det er den som blir «PORTEFØLJE»
# øverst i rapporten og i equity.csv. Endrer du rekkefølgen, endrer du hva
# rapporten kaller strategien sin.
#
# Ti varianter er kokt ned til de fem som ga høyest CAGR på hele historikken.
# Ute: basis og ukentlig (ventet for lenge på et månedsskifte), hendelse-60
# (satt med posisjoner lenge etter at signalet var dødt), hendelse-fast (lot
# 60 % av kapitalen ligge i kontanter), momentum, snuoperasjon, volumsjokk og
# kombinert (filtrene var så stramme at porteføljen sjelden kunne fylles).
#
# Merk hva det utvalget ER: de fem ble valgt på de samme tallene de nå
# rapporterer. Tallene deres er derfor litt for pene — den skjevheten
# forsvinner ikke ved å la være å nevne den.
VARIANTER: Tuple[Strategi, ...] = (
    Strategi("daglig", "handler signalet med én gang det er lovlig", takt="dag"),
    Strategi("hendelse-20", "kjøper på signaldagen, holder 20 børsdager, ferdig",
             takt="dag", hold_dager=20),
    Strategi("forfall-60", "scoren halveres hver 60. dag: ferske signaler vinner",
             takt="dag", halveringstid=60),
    Strategi("scorevektet", "vekt etter score i stedet for likt", takt="dag",
             halveringstid=60, vekting="score"),
    Strategi("konsentrert", "bare de 5 beste — hvis scoren duger, skal den tåle det",
             takt="dag", halveringstid=60, maks_navn=5),
)


@dataclass
class Posisjon:
    antall: float
    inn_kurs: float
    inn_i: int


class Marked:
    """
    Kursene, volumene og signalene stilt opp på børskalenderen ÉN gang.

    Alle variantene leser fra den samme. Det er både raskere og strengere:
    to strategier som ser ulike tall har fått dem fra ulike data, og det
    skal ikke kunne skje her.
    """

    def __init__(self, kjop: Sequence[Rad], opp: Oppsett) -> None:
        self.kalender = les_kalenderfil(opp.kalender_csv)
        bok = Kursbok(opp.s4_dir).last()
        felt = opp.kursfelt_navn()
        ref, _ = les_referansevalg(opp)

        tickere = sorted({str(r.get("Ticker")) for r in kjop if r.get("Ticker")})
        self.kurs = {t: bok.justert_serie(t, self.kalender, felt, opp.maks_fyll_dager)
                     for t in tickere if t in bok.serier}
        self.volum = {t: bok.volumserie(t, self.kalender, opp.maks_fyll_dager)
                      for t in self.kurs}
        self.ref = (bok.justert_serie(ref, self.kalender, felt, opp.maks_fyll_dager)
                    if ref in bok.serier else None)

        # (dag-indeks, ticker, score, omsetning). Ingen filtrering her — den
        # hører hjemme i strategien, ellers kan ikke variantene være uenige.
        pos = {d: i for i, d in enumerate(self.kalender)}
        self.signaler: List[Tuple[int, str, float, float]] = []
        for r in kjop:
            d = fra_iso(r.get("Handelsdag_0"))
            t = str(r.get("Ticker"))
            if d is None or t not in self.kurs or d not in pos:
                continue
            score = _bt(r, "Score_Likviditetsjustert")
            if score is None:
                score = _bt(r, "Bullish_Score")
            if score is None:
                continue
            self.signaler.append((pos[d], t, float(score),
                                  _bt(r, "Omsetning_Snitt_NOK") or 0.0))
        self.signaler.sort()
        self._dager_i_signal = [j for j, _, _, _ in self.signaler]

        self.start = min((i for i, _, _, _ in self.signaler), default=0)
        self.dager = [i for i in range(len(self.kalender)) if i >= self.start]

    def __bool__(self) -> bool:
        return bool(self.kalender and self.kurs and len(self.dager) >= 40)

    def avkastning(self, t: str, i: int, tilbake: int) -> Optional[float]:
        """Avkastning fram til OG MED dag i. Aldri en dag fram i tid."""
        serie = self.kurs.get(t)
        j = i - tilbake
        if not serie or j < 0 or i >= len(serie):
            return None
        nå, før = serie[i], serie[j]
        if not nå or not før:
            return None
        return nå / før - 1.0

    def volumlyft(self, t: str, i: int, kort: int = 5, lang: int = 60
                  ) -> Optional[float]:
        v = self.volum.get(t)
        if not v or i - lang < 0:
            return None
        nær = [x for x in v[max(0, i - kort + 1):i + 1] if x]
        fjern = [x for x in v[i - lang:i + 1] if x]
        if not nær or len(fjern) < lang // 2:
            return None
        snitt_fjern = sum(fjern) / len(fjern)
        if snitt_fjern <= 0:
            return None
        return (sum(nær) / len(nær)) / snitt_fjern


def _beslutningsdag(kalender: Sequence[date], i: int, takt: str,
                    sett: Set[Any]) -> bool:
    d = kalender[i]
    if takt == "dag":
        return True
    nøkkel = (d.isocalendar()[0], d.isocalendar()[1]) if takt == "uke" else (d.year, d.month)
    if nøkkel in sett:
        return False
    sett.add(nøkkel)
    return True


def _kandidater(marked: Marked, st: Strategi, opp: Oppsett, i: int) -> List[Tuple[str, float]]:
    """
    Selskapene som kvalifiserer på dag i, best først. (ticker, vekt-score).

    Alt som leses her er kjent ved stengetid på dag i. Det er hele forsvaret
    mot look-ahead, og det er verdt å si høyt: `marked.avkastning` og
    `volumlyft` ser bakover fra i, aldri framover.
    """
    vindu = st.vindu_dager or opp.signal_vindu_dager
    maks = st.maks_navn or opp.maks_navn
    min_score = opp.min_score_portefolje if st.min_score < 0 else st.min_score
    min_oms = opp.min_omsetning_nok if st.min_omsetning < 0 else st.min_omsetning

    # Signalene er sortert på dag, så vi hopper rett til vinduet i stedet for
    # å lese alle fra starten. Med daglig takt er det forskjellen på et par
    # sekunder og et par minutter.
    # Vinduet er i KALENDERdager, som i Oppsett — en påske skal ikke gjøre
    # vinduet lengre enn det står at det er.
    grense = bisect.bisect_right(marked.kalender,
                                 marked.kalender[i] - timedelta(days=vindu))
    fra = bisect.bisect_left(marked._dager_i_signal, grense)
    til = bisect.bisect_right(marked._dager_i_signal, i)

    beste: Dict[str, float] = {}
    for j, t, score, oms in marked.signaler[fra:til]:
        if oms < min_oms:
            continue
        v = score
        if st.halveringstid > 0:
            v = score * (0.5 ** ((i - j) / float(st.halveringstid)))
        if v < min_score:
            continue
        if marked.kurs.get(t) is None or not marked.kurs[t][i]:
            continue

        if st.momentum_dager:
            a = marked.avkastning(t, i, st.momentum_dager)
            if a is None or a < st.momentum_min:
                continue
        if st.snu_lang_dager:
            lang = marked.avkastning(t, i, st.snu_lang_dager)
            kort = marked.avkastning(t, i, st.snu_kort_dager or 20)
            if lang is None or kort is None:
                continue
            if lang > st.snu_lang_maks or kort < st.snu_kort_min:
                continue
        if st.volum_faktor:
            lyft = marked.volumlyft(t, i)
            if lyft is None or lyft < st.volum_faktor:
                continue

        if v > beste.get(t, float("-inf")):
            beste[t] = v

    ut = sorted(beste.items(), key=lambda x: (-x[1], x[0]))
    return ut[:maks]


def kjor_strategi(marked: Marked, st: Strategi, opp: Oppsett
                  ) -> Tuple[List[Rad], List[Rad], int, List[Rad]]:
    """
    Simulerer én strategi. (equity, handler, nedskrevne, beholdning ved slutt).

    Motoren er den samme uansett variant. To måter å komme inn på:

      REBALANSERING (hold_dager = 0)  På hver beslutningsdag settes hele
      porteføljen til de kvalifiserte navnene. Ingen kvalifiserte navn
      betyr kontanter — det er ikke en feil, det er fraværet av signal.

      HENDELSE (hold_dager > 0)  Hvert nytt signal kjøpes den dagen det er
      lovlig, og posisjonen holdes et fast antall børsdager. Ingen venting
      på et månedsskifte, og ingen som selges bare fordi noe annet kom inn.
    """
    kostnad_sats = (opp.spread_pst / 2.0 + opp.kurtasje_pst) / 100.0
    maks = st.maks_navn or opp.maks_navn
    kontanter = float(opp.startkapital)
    bok: Dict[str, Posisjon] = {}
    equity: List[Rad] = []
    handler: List[Rad] = []
    nedskrevet = 0
    sett: Set[Any] = set()
    min_navn_krav = st.min_navn or opp.min_navn_portefolje
    # Tre kandidater til hvilken dag beholdningen skal vises fra. Se
    # kommentaren der valget tas, nederst i funksjonen.
    siste_full: Tuple[int, Dict[str, Posisjon]] = (-1, {})
    flest: Tuple[int, Dict[str, Posisjon]] = (-1, {})
    siste_bok: Tuple[int, Dict[str, Posisjon]] = (-1, {})

    def selg(t: str, i: int, dag: date, grunn: str) -> float:
        p = bok.pop(t)
        k = marked.kurs[t][i]
        if not k:
            return 0.0
        brutto = p.antall * k
        kost = brutto * kostnad_sats
        handler.append({"Dato": iso(dag), "Ticker": t, "Type": grunn,
                        "Verdi_NOK": round(brutto, 2), "Kostnad_NOK": round(kost, 2)})
        return brutto - kost

    for i in marked.dager:
        dag = marked.kalender[i]

        # 1. Posisjoner som mistet kursdata skrives ned til null. Et selskap
        #    som slutter å handles er som regel et selskap du ikke kom deg
        #    ut av, og det skal koste.
        for t in [t for t in bok if not marked.kurs[t][i]]:
            handler.append({"Dato": iso(dag), "Ticker": t, "Type": "NEDSKREVET",
                            "Verdi_NOK": 0.0, "Kostnad_NOK": 0.0})
            bok.pop(t)
            nedskrevet += 1

        # 2. Utganger som ikke handler om nye signaler: holdetid og stopp.
        endret = False
        for t in list(bok):
            pos, k = bok[t], marked.kurs[t][i]
            if st.hold_dager and i - pos.inn_i >= st.hold_dager:
                kontanter += selg(t, i, dag, "UTLØPT")
                endret = True
            elif st.stopp_pst and k and k <= pos.inn_kurs * (1 - st.stopp_pst / 100.0):
                kontanter += selg(t, i, dag, "STOPP")
                endret = True

        beslutning = _beslutningsdag(marked.kalender, i, st.takt, sett)
        if beslutning:
            mål = _kandidater(marked, st, opp, i)
            poeng = dict(mål)

            if st.hold_dager:
                # Hendelsesdrevet: det som ligger blir liggende til holdetiden
                # er ute. Nye kjøp er signaler som kom I DAG.
                a = bisect.bisect_left(marked._dager_i_signal, i)
                b = bisect.bisect_right(marked._dager_i_signal, i)
                ferske = {tk for _, tk, _, _ in marked.signaler[a:b]}
                ønsket = list(bok) + [t for t, _ in mål
                                      if t not in bok and t in ferske]
                if len(ønsket) < min_navn_krav:
                    # For få til å spre risikoen. Da fylles det opp fra resten
                    # av puljen — eldre signaler som fortsatt kvalifiserer —
                    # før vi eventuelt gir opp og går i kontanter.
                    ønsket += [t for t, _ in mål if t not in ønsket]
            else:
                ønsket = [t for t, _ in mål]
            ønsket = ønsket[:maks]

            # PORTEFØLJEN ER ENTEN HEL ELLER TOM.
            #
            # Kvalifiserer det færre enn min_navn selskaper, kjøpes ingenting.
            # Å eie én aksje fordi den var den eneste som passerte filteret er
            # ikke en strategi — det er en veddemål på det selskapet, og
            # backtesten måler da det og ikke signalet. Uten denne regelen sto
            # ni av ti strategier med ÉN posisjon når signalene tørket inn.
            if len(ønsket) < min_navn_krav:
                ønsket = []

            if st.kapitalbruk == "fast" and ønsket:
                verdi = kontanter + sum(p.antall * (marked.kurs[t][i] or 0.0)
                                        for t, p in bok.items())
                for t in ønsket:
                    if t in bok:
                        continue
                    k = marked.kurs[t][i]
                    beløp = min(kontanter / (1.0 + kostnad_sats), verdi / maks)
                    if not k or beløp <= 1.0:
                        continue
                    kost = beløp * kostnad_sats
                    kontanter -= beløp + kost
                    bok[t] = Posisjon(beløp / k, k, i)
                    handler.append({"Dato": iso(dag), "Ticker": t, "Type": "KJØP",
                                    "Verdi_NOK": round(beløp, 2),
                                    "Kostnad_NOK": round(kost, 2)})
            elif set(ønsket) != set(bok) or endret or not st.hold_dager:
                # Kapitalen fordeles på de posisjonene som faktisk finnes, og
                # for holdestrategier bare når settet ENDRER seg. Uten den
                # betingelsen ville «hold i 20 dager» blitt rebalansert daglig.
                kontanter = _sett_portefolje(
                    marked, bok, [(t, poeng.get(t, 51.0)) for t in ønsket],
                    i, dag, kontanter, kostnad_sats, st, opp, handler)

        verdi = kontanter + sum(p.antall * (marked.kurs[t][i] or 0.0)
                                for t, p in bok.items())
        if bok:
            kopi = (i, {t: Posisjon(pp.antall, pp.inn_kurs, pp.inn_i)
                        for t, pp in bok.items()})
            siste_bok = kopi
            if len(bok) >= max(1, min_navn_krav):
                siste_full = kopi
            if len(bok) >= len(flest[1]):
                flest = kopi
        investert = verdi - kontanter
        størst = max((pos.antall * (marked.kurs[t][i] or 0.0)
                      for t, pos in bok.items()), default=0.0)
        rad: Rad = {"Dato": iso(dag), "Verdi_NOK": round(verdi, 2),
                    "Antall_Navn": len(bok),
                    "_investert": (investert / verdi) if verdi > 0 else 0.0,
                    # Den største enkeltposisjonen den dagen, MED drift:
                    # taket settes ved kjøp, og en aksje som stiger mens de
                    # andre faller vokser forbi det uten at noen handler.
                    # Snittet av antall navn skjuler at porteføljen kan ha
                    # stått 100 % i ett selskap i uker — dette tallet gjør det
                    # ikke.
                    "_storst": (størst / verdi) if verdi > 0 else 0.0}
        if marked.ref and marked.ref[i]:
            rad["_ref"] = marked.ref[i]
        equity.append(rad)

    for r in equity:
        r["Andel_Kapital"] = round(float(r.pop("_investert", 0.0)), 4)
        r["Storste_Vekt"] = round(float(r.pop("_storst", 0.0)), 4)
    forste_ref = next((r.get("_ref") for r in equity if r.get("_ref")), None)
    for r in equity:
        rk = r.pop("_ref", None)
        r["Referanse_NOK"] = (round(rk / forste_ref * opp.startkapital, 2)
                              if (forste_ref and rk) else "")

    # Holdings and performance refer to the same final trading session.
    beholdning: List[Rad] = []
    siste = marked.dager[-1] if marked.dager else -1
    sist_eid = dict(bok)
    if siste >= 0 and sist_eid:
        # Vekten regnes av HELE porteføljen, kontantene inkludert. Ellers står
        # det 100 % på en posisjon som er en femtedel av kapitalen.
        i_aksjer = sum(pos.antall * (marked.kurs[t][siste] or 0.0)
                       for t, pos in sist_eid.items())
        total = float(equity[siste - marked.dager[0]]["Verdi_NOK"]) or i_aksjer or 1.0
        for t, pos in sorted(sist_eid.items(),
                             key=lambda x: -x[1].antall * (marked.kurs[x[0]][siste] or 0.0)):
            k = marked.kurs[t][siste]
            verdi = pos.antall * (k or 0.0)
            beholdning.append({
                "Strategi": st.navn, "Dato": iso(marked.kalender[siste]),
                "Ticker": t,
                "Antall": round(pos.antall, 2),
                "Inn_Dato": iso(marked.kalender[pos.inn_i]),
                "Inn_Kurs": round(pos.inn_kurs, 4),
                "Siste_Kurs": round(k, 4) if k else "",
                "Verdi_NOK": round(verdi, 0),
                "Andel_Pst": round(100.0 * verdi / total, 1),
                "Avk_Pst": (round((k / pos.inn_kurs - 1) * 100, 2)
                            if k and pos.inn_kurs else ""),
                "Dager": siste - pos.inn_i,
            })
        kontanter_da = max(0.0, total - i_aksjer)
        if kontanter_da > 1.0:
            beholdning.append({
                "Strategi": st.navn, "Dato": iso(marked.kalender[siste]),
                "Ticker": "(kontanter)", "Antall": "", "Inn_Dato": "",
                "Inn_Kurs": "", "Siste_Kurs": "",
                "Verdi_NOK": round(kontanter_da, 0),
                "Andel_Pst": round(100.0 * kontanter_da / total, 1),
                "Avk_Pst": "", "Dager": ""})
    if not beholdning and equity:
        beholdning = [{"Strategi": st.navn, "Dato": equity[-1]["Dato"],
                       "Ticker": "(kontanter)", "Verdi_NOK": equity[-1]["Verdi_NOK"],
                       "Andel_Pst": 100.0}]
    return equity, handler, nedskrevet, beholdning


def _sett_portefolje(marked: Marked, bok: Dict[str, Posisjon],
                     mål: Sequence[Tuple[str, float]], i: int, dag: date,
                     kontanter: float, kostnad_sats: float, st: Strategi,
                     opp: Oppsett, handler: List[Rad]) -> float:
    """Setter porteføljen til nøyaktig `mål`. Gir tilbake kontantbeholdningen."""
    tidligere = {t: Posisjon(p.antall, p.inn_kurs, p.inn_i) for t, p in bok.items()}
    verdi = kontanter + sum(p.antall * (marked.kurs[t][i] or 0.0)
                            for t, p in bok.items())
    navn = [t for t, _ in mål]
    if not navn:
        for t in list(bok):
            p, k = bok[t], marked.kurs[t][i]
            if k:
                brutto = p.antall * k
                handler.append({"Dato": iso(dag), "Ticker": t, "Type": "SELG",
                                "Verdi_NOK": round(brutto, 2),
                                "Kostnad_NOK": round(brutto * kostnad_sats, 2)})
            bok.pop(t)
        return kontanter + (verdi - kontanter) * (1 - kostnad_sats)

    if st.vekting == "score":
        # Score 50 er nøytralt. Vi vekter etter overskuddet OVER nøytralt,
        # ellers ville en score på 51 og en på 90 fått nesten samme vekt.
        rå = {t: max(1.0, v - 50.0) for t, v in mål}
    else:
        rå = {t: 1.0 for t, _ in mål}
    sum_vekt = sum(rå.values()) or 1.0
    ønsket = {t: verdi * (v / sum_vekt) for t, v in rå.items()}

    # Taket. Med færre enn `min_navn` kvalifiserte navn blir ikke resten
    # investert — den blir kontanter. Det er hele poenget: en portefølje som
    # står 100 % i én aksje fordi det var den eneste som kvalifiserte, måler
    # den aksjen og ikke strategien.
    min_navn = st.min_navn or opp.min_navn_portefolje
    if min_navn > 0:
        tak = verdi / float(min_navn)
        ønsket = {t: min(v, tak) for t, v in ønsket.items()}

    omsetning = 0.0
    for t in sorted(set(list(bok) + navn)):
        k = marked.kurs.get(t, [None])[i] if t in marked.kurs else None
        før = bok[t].antall * (k or 0.0) if t in bok else 0.0
        etter = ønsket.get(t, 0.0) if k else 0.0
        omsetning += abs(etter - før)
        if abs(etter - før) > 1.0:
            handler.append({"Dato": iso(dag), "Ticker": t,
                            "Type": ("KJØP" if etter > før else
                                     ("SELG" if etter <= 0 else "TRIMM")),
                            "Verdi_NOK": round(abs(etter - før), 2),
                            "Kostnad_NOK": round(abs(etter - før) * kostnad_sats, 2)})
        if etter > 0 and k:
            gammel = tidligere.get(t)
            bok[t] = Posisjon(etter / k, gammel.inn_kurs if gammel else k,
                              gammel.inn_i if gammel else i)
        else:
            bok.pop(t, None)

    # Friksjonen tas ut av kassen, ikke bare rapportert. Ellers er kostnaden
    # et tall i en tabell og ikke penger ut av porteføljen.
    kostnad = omsetning * kostnad_sats
    investert = sum(p.antall * (marked.kurs[t][i] or 0.0) for t, p in bok.items())
    kontanter_etter = verdi - kostnad - investert
    if kontanter_etter < 0:
        # Kostnaden spiste mer enn kontantene. Da skaleres posisjonene ned,
        # så regnskapet går opp uansett.
        faktor = max(0.0, (verdi - kostnad)) / investert if investert > 0 else 0.0
        for t in list(bok):
            bok[t] = Posisjon(bok[t].antall * faktor, bok[t].inn_kurs, bok[t].inn_i)
        kontanter_etter = 0.0
    # Kostpris er gjennomsnittlig faktisk inngang, ikke dagens sluttkurs.
    # Bruk endelig antall ETTER eventuell kostnadsskalering. Trimming lar
    # kostprisen stå; bare nye aksjer får dagens kurs. Ingen endring i
    # handelsregler eller equity, men beholdningsavkastningen blir riktig.
    for t, pos in bok.items():
        gammel = tidligere.get(t)
        if gammel is None:
            continue
        tillegg = max(0.0, pos.antall - gammel.antall)
        if tillegg > 0:
            pos.inn_kurs = ((gammel.antall * gammel.inn_kurs
                            + tillegg * marked.kurs[t][i]) / pos.antall)
        else:
            pos.inn_kurs = gammel.inn_kurs
    return kontanter_etter


HOVEDSTRATEGI = VARIANTER[0]


def portefolje(kjop: Sequence[Rad], opp: Oppsett,
               logger: logging.Logger) -> Tuple[List[Rad], List[Rad], int]:
    """Hovedstrategien — den samme motoren, kjørt på den første varianten."""
    marked = Marked(kjop, opp)
    if not marked:
        logger.warning("   Ingen kalender, kurser eller kjøp — porteføljen kan ikke "
                       "simuleres.")
        return [], [], 0
    equity, handler, nedskrevet, _ = kjor_strategi(marked, HOVEDSTRATEGI, opp)
    if nedskrevet:
        logger.warning(
            f"   ⚠️  {nedskrevet} posisjoner mistet kursdata og ble skrevet ned til "
            f"null. Det er den ærlige behandlingen av en avnotering, men tallet er "
            f"også et mål på hvor mye kursdata som mangler.")
    return equity, handler, nedskrevet


# ── SAMMENLIKNINGEN ──────────────────────────────────────────────────────

BEHOLDNING_KOLONNER = ["Strategi", "Dato", "Ticker", "Antall", "Inn_Dato", "Inn_Kurs",
                       "Siste_Kurs", "Verdi_NOK", "Andel_Pst", "Avk_Pst", "Dager"]

STRATEGI_KOLONNER = ["Strategi", "Hvorfor", "CAGR_Pst", "Sharpe", "Sortino",
                     "MaxDD_Pst", "Inn_CAGR_Pst", "Inn_Sharpe", "Ut_CAGR_Pst",
                     "Ut_Sharpe", "Andel_I_Marked_Pst", "Andel_Kapital_Pst",
                     "Omsetning_Per_Ar_Pst", "Drag_Ved_15_Pst", "Snitt_Navn",
                     "Median_Navn", "Maks_Vekt_Pst", "Dager_I_Kontanter_Pst",
                     "Handler", "Nedskrevet"]

# Satsen strategiene måles mot når friksjonen er skrudd av: 1,5 % spread
# (halve hver vei) og 0,05 % kurtasje. Det er der Oslo Børs ligger for en
# aksje som omsettes normalt, og tallet er der for å svare på ett spørsmål:
# overlever meravkastningen at noen skal betale for handlene?
DEFAULT_FRIKSJON = (1.5 / 2.0 + 0.05) / 100.0


def _del_equity(equity: Sequence[Rad], slutt: str) -> Tuple[List[float], List[float]]:
    inn = [float(r["Verdi_NOK"]) for r in equity if str(r.get("Dato")) <= slutt]
    ut = [float(r["Verdi_NOK"]) for r in equity if str(r.get("Dato")) > slutt]
    return inn, inn[-1:] + ut


def sammenlikn_strategier(kjop: Sequence[Rad], opp: Oppsett, logger: logging.Logger
                          ) -> Tuple[List[Rad], Dict[str, List[Rad]],
                                     List[Rad], List[Rad]]:
    """
    Kjører alle variantene på de samme dataene.

    (tabell, equity per navn, beholdning på siste dag, alle handler).
    De to siste er det mailen sender ut — nøkkeltall alene sier ikke hva
    strategien faktisk EIER i dag.
    """
    marked = Marked(kjop, opp)
    if not marked:
        return [], {}, [], []

    logger.info(f"\n🔁 Prøver {len(VARIANTER)} strategier på de samme "
                f"{len(marked.signaler)} signalene …")
    tabell: List[Rad] = []
    kurver: Dict[str, List[Rad]] = {}
    beholdninger: List[Rad] = []
    alle_handler: List[Rad] = []
    for st in VARIANTER:
        equity, handler, nedskrevet, beholdning = kjor_strategi(marked, st, opp)
        if len(equity) < 40:
            continue
        kurver[st.navn] = equity
        beholdninger.extend(beholdning)
        alle_handler.extend(dict(h, Strategi=st.navn) for h in handler)
        verdier = [float(r["Verdi_NOK"]) for r in equity]
        m = nokkeltall(verdier, opp.risikofri_pst)
        inn, ut = _del_equity(equity, opp.inn_utvalg_slutt)
        m_inn = nokkeltall(inn, opp.risikofri_pst) if len(inn) > 40 else {}
        m_ut = nokkeltall(ut, opp.risikofri_pst) if len(ut) > 40 else {}

        i_marked = sum(1 for r in equity if int(r.get("Antall_Navn") or 0) > 0)
        # Andelen av KAPITALEN som står i markedet. «85 % av dagene med minst
        # én posisjon» kan godt bety at 90 % av pengene lå i kontanter hele
        # tiden — og da måler du kontantdrag, ikke signal.
        kapital = sum(float(r.get("Andel_Kapital") or 0.0) for r in equity) / len(equity)
        navn_per_dag = [int(r.get("Antall_Navn") or 0) for r in equity]
        med_navn = sorted(n for n in navn_per_dag if n > 0)
        median_navn = median(med_navn) if med_navn else 0.0
        # Dager helt i kontanter. Etter at porteføljen ble «hel eller tom» er
        # det DETTE tallet som forteller hvor ofte strategien ikke fant nok
        # selskaper til å spre risikoen på.
        i_kontanter = sum(1 for n in navn_per_dag if n == 0)
        maks_vekt = max((float(r.get("Storste_Vekt") or 0.0) for r in equity),
                        default=0.0)
        oms = sum(tolk_maskin(h.get("Verdi_NOK")) or 0.0 for h in handler)
        ar = max(0.5, len(equity) / 252.0)
        snitt_kap = sum(verdier) / len(verdier)

        def pst(x: Optional[float]) -> Any:
            return round(x * 100, 2) if x is not None and x == x else ""

        tabell.append({
            "Strategi": st.navn, "Hvorfor": st.hvorfor,
            "CAGR_Pst": pst(m.get("CAGR")),
            "Sharpe": round(m.get("Sharpe", NAN), 2) if m.get("Sharpe") == m.get("Sharpe") else "",
            "Sortino": round(m.get("Sortino", NAN), 2) if m.get("Sortino") == m.get("Sortino") else "",
            "MaxDD_Pst": pst(m.get("MaxDD")),
            "Inn_CAGR_Pst": pst(m_inn.get("CAGR")),
            "Inn_Sharpe": round(m_inn.get("Sharpe", NAN), 2) if m_inn.get("Sharpe") == m_inn.get("Sharpe") else "",
            "Ut_CAGR_Pst": pst(m_ut.get("CAGR")),
            "Ut_Sharpe": round(m_ut.get("Sharpe", NAN), 2) if m_ut.get("Sharpe") == m_ut.get("Sharpe") else "",
            "Andel_I_Marked_Pst": round(100.0 * i_marked / len(equity), 1),
            "Andel_Kapital_Pst": round(100.0 * kapital, 1),
            "Omsetning_Per_Ar_Pst": round(100.0 * oms / ar / max(1.0, snitt_kap), 0),
            "Drag_Ved_15_Pst": round(100.0 * (oms / ar / max(1.0, snitt_kap))
                                     * DEFAULT_FRIKSJON, 1),
            "Snitt_Navn": round(sum(navn_per_dag) / len(equity), 1),
            "Median_Navn": round(median_navn, 1),
            "Maks_Vekt_Pst": round(100.0 * maks_vekt, 1),
            "Dager_I_Kontanter_Pst": round(100.0 * i_kontanter / len(equity), 1),
            "Handler": len(handler), "Nedskrevet": nedskrevet,
        })
        logger.info(f"   {st.navn:<14} CAGR {tabell[-1]['CAGR_Pst'] or '—':>7} %  "
                    f"Sharpe {tabell[-1]['Sharpe'] or '—':>6}  "
                    f"kapital ute {tabell[-1]['Andel_Kapital_Pst']:>5} %")
    if tabell:
        from insider_selection import build_insider_selection
        build_insider_selection(opp, logger, market=marked, stats=tabell,
                                curves=kurver, trades=alle_handler)
    return tabell, kurver, beholdninger, alle_handler


def strategi_dom(tabell: Sequence[Rad], opp: Oppsett) -> List[str]:
    """
    Hva tabellen faktisk tillater deg å si.

    Dette er det viktigste avsnittet i hele steget, og det sier nesten alltid
    «mindre enn du håpet». Tolv forsøk på de samme dataene gjør den beste
    raden bedre enn den fortjener, og forskjellen mellom nummer én og
    medianen er som regel innenfor det flaks alene klarer.
    """
    if len(tabell) < 2:
        return []
    med_inn = [r for r in tabell if r.get("Inn_Sharpe") != ""]
    med_ut = [r for r in tabell if r.get("Ut_Sharpe") != ""]
    ut: List[str] = [
        f"{len(tabell)} strategier er prøvd på de samme dataene. Den beste raden "
        f"er derfor delvis heldig, ikke bare god."]
    if not med_inn or not med_ut:
        ut.append(f"For lite historikk til å dele i inn- og ut-utvalg ved "
                  f"{opp.inn_utvalg_slutt}. Da er ingen av radene etterprøvd, og "
                  f"tabellen er en beskrivelse av fortiden — ikke en prediksjon.")
        return ut

    beste_inn = max(med_inn, key=lambda r: float(r["Inn_Sharpe"]))
    ut.append(f"Best på INN-utvalget (til {opp.inn_utvalg_slutt}): "
              f"«{beste_inn['Strategi']}», Sharpe {beste_inn['Inn_Sharpe']}.")
    egen = next((r for r in med_ut if r["Strategi"] == beste_inn["Strategi"]), None)
    if egen:
        ut.append(f"Den samme strategien på UT-utvalget: Sharpe {egen['Ut_Sharpe']}, "
                  f"CAGR {egen['Ut_CAGR_Pst']} %. Det er tallet som teller — "
                  f"valget ble tatt før det ble lest.")
        beste_ut = max(med_ut, key=lambda r: float(r["Ut_Sharpe"]))
        if beste_ut["Strategi"] != beste_inn["Strategi"]:
            ut.append(f"En annen strategi («{beste_ut['Strategi']}», Sharpe "
                      f"{beste_ut['Ut_Sharpe']}) gjorde det bedre på ut-utvalget. "
                      f"Å bytte til den NÅ er å velge på ut-utvalget, og da er det "
                      f"ikke lenger et ut-utvalg. La den stå som en observasjon.")
    # Omsetningen er ikke en detalj når friksjonen er slått av. En strategi
    # som bytter porteføljen tjue ganger i året er gratis på papiret og dyr i
    # virkeligheten, og forskjellen er ofte hele meravkastningen.
    if opp.spread_pst <= 0 and opp.kurtasje_pst <= 0:
        drept = [r for r in tabell
                 if r.get("CAGR_Pst") != "" and r.get("Drag_Ved_15_Pst") != ""
                 and float(r["Drag_Ved_15_Pst"]) >= float(r["CAGR_Pst"])]
        verst = max((float(r["Drag_Ved_15_Pst"]) for r in tabell
                     if r.get("Drag_Ved_15_Pst") != ""), default=0.0)
        ut.append(f"Friksjonen er slått av (spread og kurtasje = 0), så tallene er "
                  f"FØR kostnader. Ved 1,5 % spread ville handlingen kostet opptil "
                  f"{verst:.0f} % i året"
                  + (f", og {len(drept)} av {len(tabell)} strategier ville da tapt "
                     f"hele avkastningen sin." if drept else "."))

    aldri = [r["Strategi"] for r in tabell
             if float(r.get("Andel_Kapital_Pst") or 0) < 1.0]
    if aldri:
        ut.append(f"{', '.join(aldri)} kom aldri i markedet. Porteføljen er hel "
                  f"eller tom — finnes det ikke nok kvalifiserte selskaper til å "
                  f"spre risikoen, kjøpes ingenting. Det er ikke en feil i "
                  f"koden, det er svaret: filteret er for stramt til å drives "
                  f"som en portefølje.")

    # Konsentrasjon er ikke en detalj. En «strategi» som sto 100 % i én aksje
    # måler den aksjen, ikke signalet, og da er hele raden en anekdote.
    trange = [r for r in tabell
              if tolk_maskin(r.get("Maks_Vekt_Pst")) is not None
              and float(r["Maks_Vekt_Pst"]) > 99.0]
    if trange:
        ut.append(f"{len(trange)} av {len(tabell)} strategier hadde minst én dag "
                  f"med hele kapitalen i ÉN aksje "
                  f"({', '.join(r['Strategi'] for r in trange[:4])}"
                  + (" …" if len(trange) > 4 else "") +
                  "). Da måler den raden det selskapet, ikke signalet. "
                  "Sett min_navn høyere, eller les tallet som en anekdote.")

    sharper = sorted(float(r["Ut_Sharpe"]) for r in med_ut)
    if len(sharper) >= 3:
        spenn = sharper[-1] - sharper[len(sharper) // 2]
        if spenn < 0.5:
            ut.append(f"Spennet fra median til best på ut-utvalget er {spenn:.2f} i "
                      f"Sharpe. Det er innenfor det tilfeldigheter alene klarer med "
                      f"{len(tabell)} forsøk — behandle variantene som likeverdige.")
    return ut

DAGENS_KOLONNER = ["Strategi", "Ticker", "Selskap", "Score", "Signaldato",
                   "Dager_Siden", "Rolle", "Verdi_NOK"]


def dagens_kandidater(rader: Sequence[Rad], opp: Oppsett,
                      logger: logging.Logger) -> List[Rad]:
    """
    Hva hver strategi ville kjøpt på SISTE kursdag.

    Backtesten kan ikke si dette. Den krever at det finnes kurser langt nok
    fram til å måle en melding, og de ferskeste meldingene har ikke det — de
    faller ut som FOR_NY. Resultatet er at beholdningen i rapporten er
    måneder gammel, mens meldingene øverst i mailen er fra i går.

    Denne listen bruker de samme reglene på det samme markedet, men med ALLE
    meldingene som har en handelsdag — også de som er for ferske til å ha en
    fasit. Det er en signalliste, ikke et resultat: ingen av disse navnene har
    vært gjennom en eneste dag med etterprøving.
    """
    brede = velg(rader, opp, "KJOP", krev_kurs=False)
    if not brede:
        return []
    marked = Marked(brede, opp)
    if not marked or not marked.dager:
        return []

    i = marked.dager[-1]
    dag = marked.kalender[i]
    # Slår opp meldingen bak hvert signal, så listen kan si HVEM som kjøpte.
    per_ticker: Dict[str, Rad] = {}
    for r in sorted(brede, key=lambda x: str(x.get("Handelsdag_0"))):
        per_ticker[rens(r.get("Ticker")).upper()] = r

    ut: List[Rad] = []
    for st in VARIANTER:
        for ticker, poeng in _kandidater(marked, st, opp, i):
            kilde = per_ticker.get(ticker, {})
            signaldato = fra_iso(kilde.get("Handelsdag_0"))
            ut.append({
                "Strategi": st.navn, "Ticker": ticker,
                "Selskap": rens(kilde.get("Selskap"))[:30],
                "Score": round(poeng, 1),
                "Signaldato": rens(kilde.get("Handelsdag_0")),
                "Dager_Siden": (dag - signaldato).days if signaldato else "",
                "Rolle": rens(kilde.get("Rolle")),
                "Verdi_NOK": rens(kilde.get("Verdi_NOK")),
            })
    if ut:
        logger.info(f"📌 Dagens liste per {dag}: "
                    f"{len({r['Ticker'] for r in ut})} ulike selskaper "
                    f"fordelt på {len({r['Strategi'] for r in ut})} strategier")
    return ut


def bt_maal(equity: Sequence[Rad], opp: Oppsett) -> Dict[str, Dict[str, float]]:
    ut: Dict[str, Dict[str, float]] = {}
    if not equity:
        return ut
    ut["Strategi"] = nokkeltall([float(r["Verdi_NOK"]) for r in equity], opp.risikofri_pst)
    ref = [v for v in (tolk_maskin(r.get("Referanse_NOK")) for r in equity) if v]
    if len(ref) > 2:
        ut["Referanse"] = nokkeltall(ref, opp.risikofri_pst)
    return ut


def friksjonsregnskap(handler: Sequence[Rad], equity: Sequence[Rad],
                      m: Dict[str, Dict[str, float]], opp: Oppsett) -> List[str]:
    """
    Hva koster handlingen, i året, mot hva strategien tjener?

    Uten dette regnestykket er «Sharpe 0,07» bare et skuffende tall. Med det
    ser du HVORFOR: en portefølje som byttes helt ut hver måned omsetter
    200 % i måneden, og med 1,5 % spread er det rundt 20 % i året rett ut av
    kassen. Da spiller det ingen rolle hvor pen event studyen er.
    """
    kostnad = sum(tolk_maskin(h.get("Kostnad_NOK")) or 0.0 for h in handler)
    sats = (opp.spread_pst / 2.0 + opp.kurtasje_pst) / 100.0
    ut = [f"Friksjon totalt: {kostnad:,.0f} kr  (sats {sats*100:.2f} % hver vei)"]

    verdier = [v for v in (tolk_maskin(r.get("Verdi_NOK")) or 0.0 for r in equity) if v > 0]
    ar = len(verdier) / 252.0
    if verdier and ar > 0.5:
        snitt_kapital = sum(verdier) / len(verdier)
        drag = kostnad / ar / snitt_kapital
        ut.append(f"Friksjon per år: {drag*100:.1f} % av gjennomsnittlig kapital")
        netto = m.get("Strategi", {}).get("CAGR", NAN)
        if netto == netto:
            ut.append(f"Brutto ≈ {(netto + drag)*100:+.1f} %  −  friksjon "
                      f"{drag*100:.1f} %  =  netto {netto*100:+.1f} % i året")
        if drag > 0.10:
            ut.append("⚠️  Friksjonen alene spiser over 10 % i året. En portefølje som "
                      "byttes helt ut hver måned omsetter 200 % i måneden. Lengre "
                      "holdeperiode eller strengere likviditetskrav er eneste vei ut "
                      "— ikke et bedre signal.")
    return ut


def _brekk(tekst: str, bredde: int) -> List[str]:
    ord_, linjer, linje = str(tekst).split(), [], ""
    for o in ord_:
        if len(linje) + len(o) + 1 > bredde:
            linjer.append(linje); linje = o
        else:
            linje = f"{linje} {o}".strip()
    if linje:
        linjer.append(linje)
    return linjer


def skriv_rapport(opp: Oppsett, dom: Dict[str, Any], kjop_tabell: Sequence[Rad],
                  salg_tabell: Sequence[Rad], kurve: Sequence[Rad],
                  score_tabell: Sequence[Rad], score_tekst: str,
                  grupper: Sequence[Rad], equity: Sequence[Rad],
                  m: Dict[str, Dict[str, float]], antall_kjop: int, antall_salg: int,
                  nedskrevet: int, kontrolltekst: str, friksjon: Optional[Sequence[str]],
                  logger: logging.Logger, strategier: Sequence[Rad] = (),
                  kurver: Optional[Dict[str, List[Rad]]] = None,
                  strategi_raad: Sequence[str] = ()) -> None:
    d: List[str] = [HODE]
    d.append(f"<h1>Innsidehandel på Oslo Børs</h1>"
             f"<p class='undertittel'>Kjørt {datetime.now():%Y-%m-%d %H:%M} · "
             f"{antall_kjop} kjøp og {antall_salg} salg med kurshistorikk · "
             f"måler {trygg(opp.avkastningstype())} · "
             f"inn-utvalg til og med {trygg(opp.inn_utvalg_slutt)}</p>")

    klasse = "apen" if dom.get("apen") else "stengt"
    d.append(f"<div class='dom {klasse}'><h2>{trygg(dom.get('kort'))}</h2>"
             f"<p>{trygg(dom.get('tekst'))}</p></div>")

    # ── virker scoren? ───────────────────────────────────────────────────
    d.append("<h2>Virker bullishness-scoren?</h2>")
    d.append("<p>Alle vurderte meldinger sorteres på scoren fra steg 3 og deles i "
             "like store bøtter. Er scoren informativ, skal meravkastningen stige "
             "fra nederste til øverste bøtte. Er kurven flat, måler scoren "
             "ingenting — og da er den pynt, ikke informasjon.</p>")
    d.append(f"<p style='color:var(--ink)'><b>{trygg(score_tekst)}</b></p>")
    if score_tabell:
        d.append("<div class='graf'>" + svg_stolper(
            [str(r["Bøtte"]) for r in score_tabell],
            [float(r["Snitt_Meravk_Pst"]) for r in score_tabell],
            y_etikett=f"snitt meravkastning, {opp.event_horisont} dager (%)") + "</div>")
        d.append(tabell_html(score_tabell))

    # ── kontrollen ───────────────────────────────────────────────────────
    d.append("<h2>Kontroll: hva gjorde salgene?</h2>")
    d.append("<p>Kjøp bør slå børsen, salg bør ligge under. Ser de to like ut, er det "
             "ikke et resultat — det er et varsel om at noe lenger oppe i røret er "
             "galt, uansett hvor pent kjøpstallet er.</p>")
    d.append(f"<p style='color:var(--ink)'><b>{trygg(kontrolltekst)}</b></p>")

    # ── forbeholdene ─────────────────────────────────────────────────────
    d.append("<div class='varsel'><h2>Les dette før tallene</h2><ul>")
    d.append("<li><b>Overlevelsesskjevhet.</b> Selskapslisten er dagens noterte "
             "selskaper. De som gikk konkurs eller ble strøket i perioden mangler helt, "
             "og det er nettopp deres innsidekjøp som skulle trukket avkastningen ned. "
             "Skjevheten kan ikke fjernes i ettertid.</li>")
    d.append("<li><b>Avnoteringer teller.</b> Posisjoner som mister kursdata regnes på "
             "siste observerte kurs og skrives ned til null i porteføljen — de "
             "forsvinner ikke ut av gjennomsnittet."
             + (f" {nedskrevet} posisjoner ble skrevet ned." if nedskrevet else "") + "</li>")
    d.append(f"<li><b>Friksjon.</b> {opp.spread_pst:.2f} % spread (halve hver vei) og "
             f"{opp.kurtasje_pst:.2f} % kurtasje trekkes løpende, ikke til slutt.</li>")
    d.append(f"<li><b>Målestokk.</b> Aksje og referanse leses fra samme kursfelt "
             f"({trygg(opp.kursfelt_navn())}), så utbytte kan ikke lekke inn som falsk "
             f"meravkastning.</li>")
    d.append("<li><b>Scoren er valgt, ikke funnet.</b> Vektene i steg 3 er satt av "
             "skjønn, ikke tilpasset dataene. Det er med vilje: en score som er "
             "optimert på det samme utvalget den testes på, måler bare hvor godt den "
             "husker.</li>")
    d.append("</ul></div>")

    if kjop_tabell:
        d.append("<h2>Event study — kjøp</h2>")
        d.append("<p>Meravkastning mot referansen, i handledager fra kjøpsdagen. "
                 "Negative horisonter er dagene før. Standardfeilen er klynget på både "
                 "selskap og dato, så gjentatte kjøp i samme selskap og felles "
                 "børsdager ikke telles som uavhengige.</p>")
        d.append(tabell_html(kjop_tabell))
    if kurve and len(kurve) >= 2:
        punkter = [(float(r["Horisont"]), float(r["Snitt_Pst"])) for r in kurve]
        d.append("<div class='graf'>" + svg_linje({"Meravkastning %": punkter},
                                                  y_etikett="%") + "</div>")
        d.append("<p class='fot'>Kurven er normalisert til kjøpsdagen: dag 0 er null, "
                 "og dagene før viser opptakten.</p>")
    if salg_tabell:
        d.append("<h2>Event study — salg (kontrollgruppe)</h2>")
        d.append(tabell_html([r for r in salg_tabell if r.get("Utvalg") == "alt"]))
    if grupper:
        d.append(f"<h2>Undergrupper ({opp.event_horisont} dager)</h2>")
        d.append("<p>«Etter stengetid», «Nærstående» og «Tillit» er kontroller, ikke "
                 "hypoteser: store forskjeller der er varsler om at "
                 "handelsdagsregelen eller uttrekket svikter.</p>")
        d.append(tabell_html(grupper))

    if m:
        d.append("<h2>Portefølje</h2>")
        d.append(f"<p>Månedlig rebalansert, likevektet, inntil {opp.maks_navn} navn med "
                 f"høyest score de siste {opp.signal_vindu_dager} dagene.</p>")
        rader = ["<div class='tabell'><table><thead><tr><th>Nøkkeltall</th>"
                 + "".join(f"<th>{trygg(k)}</th>" for k in m) + "</tr></thead><tbody>"]
        for felt, etikett, prosent in (
                ("CAGR", "CAGR", True), ("Sharpe", "Sharpe", False),
                ("Sortino", "Sortino", False), ("Volatilitet", "Volatilitet", True),
                ("MaxDD", "Max drawdown", True), ("AndelDagerOpp", "Andel dager opp", True)):
            celler = []
            for k in m:
                v = m[k].get(felt, NAN)
                celler.append("<td>—</td>" if v != v else
                              (f"<td>{v*100:+.1f} %</td>" if prosent else f"<td>{v:.2f}</td>"))
            rader.append(f"<tr><td>{etikett}</td>" + "".join(celler) + "</tr>")
        rader.append("</tbody></table></div>")
        d.append("".join(rader))

    if equity and friksjon:
        d.append("<h3>Hva koster handlingen?</h3><ul class='fot'>"
                 + "".join(f"<li>{trygg(l)}</li>" for l in friksjon) + "</ul>")

    if equity and len(equity) > 2:
        serier = {"Strategi": [(i, float(r["Verdi_NOK"])) for i, r in enumerate(equity)]}
        ref = [(i, tolk_maskin(r.get("Referanse_NOK"))) for i, r in enumerate(equity)
               if tolk_maskin(r.get("Referanse_NOK"))]
        if len(ref) > 2:
            serier["Referanse"] = ref
        d.append("<div class='graf'>" + svg_linje(serier, hoyde=320, null_linje=False,
                                                  y_etikett="NOK") + "</div>")
        d.append(f"<p class='fot'>Equity-kurve, {len(equity)} handledager fra "
                 f"{trygg(equity[0]['Dato'])} til {trygg(equity[-1]['Dato'])}. "
                 f"Startkapital {opp.startkapital:,.0f} kr. X-aksen er handledager.</p>")

    if strategier:
        d.append("<h2>Strategiene, side om side</h2>")
        d.append("<p>Alle radene er kjørt på nøyaktig de samme signalene og de "
                 "samme kursene. Det eneste som skiller dem, er når og hvordan "
                 "det handles.</p>")
        d.append(tabell_html(strategier, [
            "Strategi", "Hvorfor", "CAGR_Pst", "Sharpe", "MaxDD_Pst",
            "Inn_Sharpe", "Ut_Sharpe", "Andel_Kapital_Pst",
            "Omsetning_Per_Ar_Pst", "Drag_Ved_15_Pst", "Median_Navn",
            "Maks_Vekt_Pst"]))
        if strategi_raad:
            d.append("<div class='varsel'><h2>Hva tabellen tillater deg å si</h2><ul>"
                     + "".join(f"<li>{trygg(x)}</li>" for x in strategi_raad)
                     + "</ul></div>")
        if kurver:
            # Tre kurver, ikke tolv: dagens oppsett, den beste på inn-utvalget,
            # og referansen. Tolv linjer i én graf er et garnnøste.
            valgte = [HOVEDSTRATEGI.navn]
            med_inn = [r for r in strategier if r.get("Inn_Sharpe") != ""]
            if med_inn:
                b = max(med_inn, key=lambda r: float(r["Inn_Sharpe"]))["Strategi"]
                if b not in valgte:
                    valgte.append(b)
            serier: Dict[str, Sequence[Tuple[float, float]]] = {}
            for navn in valgte:
                e = kurver.get(navn) or []
                if len(e) > 2:
                    serier[navn] = [(i, float(r["Verdi_NOK"])) for i, r in enumerate(e)]
            grunn = kurver.get(valgte[0]) or []
            ref = [(i, tolk_maskin(r.get("Referanse_NOK")))
                   for i, r in enumerate(grunn) if tolk_maskin(r.get("Referanse_NOK"))]
            if len(ref) > 2:
                serier["Referanse"] = ref
            if serier:
                d.append("<div class='graf'>"
                         + svg_linje(serier, hoyde=320, null_linje=False,
                                     y_etikett="NOK") + "</div>")
                d.append(f"<p class='fot'>{trygg(', '.join(valgte))} mot referansen. "
                         f"Alle kurvene ligger i {trygg(opp.strategi_equity_csv.name)} "
                         f"hvis du vil tegne dem selv.</p>")

    d.append(FOT)
    opp.rapport_html.parent.mkdir(parents=True, exist_ok=True)
    opp.rapport_html.write_text("".join(d), encoding="utf-8")
    logger.info(f"💾 Rapport: {opp.rapport_html}")


def steg6_backtest(opp: Oppsett, logger: logging.Logger) -> Dict[str, Any]:
    opp.lag_mapper()
    rader = les_csv(opp.merget_csv)
    if not rader:
        return {"status": "HOPPET",
                "detaljer": f"ingen {opp.merget_csv.name} — kjør steg 5 først"}
    logger.info(f"📂 {len(rader)} sammenslåtte hendelser fra {opp.merget_csv.name}")

    avvist: Dict[str, int] = {}
    kjop = velg(rader, opp, "KJOP", avvist)
    salg = velg(rader, opp, "SALG")
    logger.info(f"🎯 {len(kjop)} kjøp og {len(salg)} salg egnet til analyse "
                f"(tillit HØY/MIDDELS"
                + (", én per klynge" if opp.kun_primaer else "")
                + f", beløp ≥ {opp.min_verdi_nok:,.0f} kr)")
    if not kjop:
        logger.warning("\n   Hvorfor ingen kjøp kom gjennom:")
        for grunn, antall in sorted(avvist.items(), key=lambda x: -x[1])[:8]:
            logger.warning(f"      {antall:>6}  {grunn}")
        verste = max(avvist.items(), key=lambda x: x[1], default=("", 0))[0]
        raad = ["se listen over: det er den øverste linjen som tømte utvalget"]
        if verste.startswith("kurs:"):
            raad = ["kursene er problemet, ikke uttrekket — "
                    "kjør: --steg 4,5,6 --full"]
        elif verste.startswith("tillit:") or verste.startswith("klasse"):
            raad = ["meldingene ble ikke lest — feilen sitter i steg 2/3",
                    "kjør: --steg 2,3 --tving-tekst"]
        return {"status": "FEIL", "raad": raad,
                "detaljer": f"ingen kjøp å analysere — flest avvist på «{verste}»"}

    kjop_tabell = event_study(kjop, opp, "kjøp")
    salg_tabell = event_study(salg, opp, "salg") if len(salg) >= 20 else []
    kurve = event_kurve(kjop)
    score_tabell = test_scoren(kjop, salg, opp)
    score_tekst = score_dom(score_tabell)
    grupper = undergrupper(kjop, opp)
    dom = vurder(kjop_tabell, opp)
    kontrolltekst = kontroll_salg(kjop_tabell, salg_tabell, opp)

    port_kjop = velg(rader, opp, "KJOP", krev_kurs=False)
    equity, handler, nedskrevet = portefolje(port_kjop, opp, logger)
    m = bt_maal(equity, opp)
    friksjon = friksjonsregnskap(handler, equity, m, opp) if handler else None

    strategier, kurver, beholdninger, strategi_handler = \
        ([], {}, [], []) if opp.kun_hovedstrategi else \
        sammenlikn_strategier(port_kjop, opp, logger)
    dagens = [] if opp.kun_hovedstrategi else dagens_kandidater(rader, opp, logger)
    strategi_raad = strategi_dom(strategier, opp)

    skriv_csv(opp.event_study_csv, kjop_tabell + salg_tabell)
    skriv_csv(opp.event_kurve_csv, kurve)
    if score_tabell:
        skriv_csv(opp.score_test_csv, score_tabell)
    if grupper:
        skriv_csv(opp.undergrupper_csv, grupper)
    if equity:
        skriv_csv(opp.equity_csv, equity, ["Dato", "Verdi_NOK", "Antall_Navn",
                                           "Referanse_NOK"])
    if handler:
        skriv_csv(opp.handler_csv, handler, ["Dato", "Ticker", "Type", "Verdi_NOK",
                                             "Kostnad_NOK"])
    if strategier:
        skriv_csv(opp.strategier_csv, strategier, STRATEGI_KOLONNER)
        # Alle kurvene i én lang fil, så du kan tegne dem selv i Excel.
        lange = [{"Strategi": navn, "Dato": r["Dato"], "Verdi_NOK": r["Verdi_NOK"],
                  "Antall_Navn": r.get("Antall_Navn", "")}
                 for navn, e in kurver.items() for r in e]
        skriv_csv(opp.strategi_equity_csv, lange,
                  ["Strategi", "Dato", "Verdi_NOK", "Antall_Navn"])
        skriv_csv(opp.beholdning_csv, beholdninger, BEHOLDNING_KOLONNER)
        # Bare de siste handlene per strategi — hele loggen er hundretusener
        # av rader og hjelper ingen som skal lese en mail.
        siste: List[Rad] = []
        for navn in {str(h.get("Strategi")) for h in strategi_handler}:
            egne = [h for h in strategi_handler if h.get("Strategi") == navn]
            siste.extend(sorted(egne, key=lambda h: str(h.get("Dato")))[-40:])
        skriv_csv(opp.strategi_handler_csv, siste,
                  ["Strategi", "Dato", "Ticker", "Type", "Verdi_NOK", "Kostnad_NOK"])
    if dagens:
        skriv_csv(opp.dagens_liste_csv, dagens, DAGENS_KOLONNER)
    skriv_rapport(opp, dom, kjop_tabell, salg_tabell, kurve, score_tabell, score_tekst,
                  grupper, equity, m, len(kjop), len(salg), nedskrevet, kontrolltekst,
                  friksjon, logger, strategier, kurver, strategi_raad)
    _skriv_ut_backtest(opp, dom, kjop_tabell, salg_tabell, score_tabell, score_tekst,
                       m, handler, equity, kontrolltekst, logger)
    _skriv_ut_strategier(strategier, strategi_raad, logger)

    cagr = m.get("Strategi", {}).get("CAGR", NAN)
    sharpe = m.get("Strategi", {}).get("Sharpe", NAN)
    detaljer = f"{dom.get('kort')} · {len(kjop)} kjøp"
    if cagr == cagr:
        detaljer += f" · CAGR {cagr*100:+.1f} %, Sharpe {sharpe:.2f}"
    return {"status": "OK", "dom": dom.get("kort"), "kjop": len(kjop),
            "apen": dom.get("apen"), "detaljer": detaljer}


def _skriv_ut_strategier(strategier: Sequence[Rad], raad: Sequence[str],
                         logger: logging.Logger) -> None:
    if not strategier:
        return
    logger.info(f"\n{'─' * 74}")
    logger.info("STRATEGIENE, SIDE OM SIDE  (samme signaler, samme kurser)")
    logger.info(f"{'─' * 74}")
    logger.info(f"    {'Strategi':<14}{'CAGR':>8}{'Sharpe':>8}{'MaxDD':>8}"
                f"{'inn Sh':>8}{'ut Sh':>8}{'kapital':>9}{'oms/år':>8}"
                f"{'drag':>7}{'navn':>6}{'maks v':>8}")
    for r in strategier:
        logger.info(f"    {str(r['Strategi']):<14}"
                    f"{str(r['CAGR_Pst'] or '—'):>7} %"
                    f"{str(r['Sharpe'] or '—'):>8}"
                    f"{str(r['MaxDD_Pst'] or '—'):>7} %"
                    f"{str(r['Inn_Sharpe'] or '—'):>8}"
                    f"{str(r['Ut_Sharpe'] or '—'):>8}"
                    f"{str(r['Andel_Kapital_Pst']):>8} %"
                    f"{str(r['Omsetning_Per_Ar_Pst']):>7} %"
                    f"{str(r['Drag_Ved_15_Pst']):>6} %"
                    f"{str(r['Median_Navn']):>6}"
                    f"{str(r['Maks_Vekt_Pst']):>7} %")
    tomme = [r["Strategi"] for r in strategier
             if float(r.get("Andel_Kapital_Pst") or 0) < 1.0]
    if tomme:
        logger.info(f"    ({', '.join(tomme)} kom aldri i markedet: filteret "
                    f"fant aldri nok selskaper til å fylle en portefølje)")
    logger.info("")
    for linje in raad:
        for bit in _brekk(linje, 68):
            logger.info(f"    {bit}")
        logger.info("")


def _skriv_ut_backtest(opp: Oppsett, dom: Dict[str, Any], kjop_tabell: Sequence[Rad],
                       salg_tabell: Sequence[Rad], score_tabell: Sequence[Rad],
                       score_tekst: str, m: Dict[str, Dict[str, float]],
                       handler: Sequence[Rad], equity: Sequence[Rad],
                       kontrolltekst: str, logger: logging.Logger) -> None:
    logger.info(f"\n{'═' * 74}")
    logger.info("EVENT STUDY")
    logger.info(f"{'═' * 74}")
    for utvalg in ("inn-utvalg", "ut-utvalg", "alt"):
        del_ = [r for r in kjop_tabell if r.get("Utvalg") == utvalg]
        if not del_:
            continue
        logger.info(f"\n  KJØP — {utvalg.upper()}")
        for r in del_:
            if r.get("Snitt_Pst") in (None, ""):
                logger.info(f"    {int(r['Horisont']):>4} dager   n={int(r['N']):>5}"
                            f"   (for få til å regne på)")
                continue
            ki = ""
            if r.get("KI_Lav_Pst") not in (None, ""):
                ki = (f"   95 % KI [{float(r['KI_Lav_Pst']):+.2f}, "
                      f"{float(r['KI_Hoy_Pst']):+.2f}]"
                      + ("  krysser null" if r.get("KI_Krysser_Null") == "JA" else ""))
            logger.info(f"    {int(r['Horisont']):>4} dager   n={int(r['N']):>5}   "
                        f"snitt {float(r['Snitt_Pst']):+6.2f} %   "
                        f"t={str(r.get('t','')):>7}{ki}")

    if salg_tabell:
        logger.info("\n  SALG — KONTROLLGRUPPE (alt)")
        for r in salg_tabell:
            if r.get("Utvalg") != "alt" or r.get("Snitt_Pst") in (None, ""):
                continue
            logger.info(f"    {int(r['Horisont']):>4} dager   n={int(r['N']):>5}   "
                        f"snitt {float(r['Snitt_Pst']):+6.2f} %")
    logger.info(f"\n  {kontrolltekst}")

    if score_tabell:
        logger.info(f"\n{'─' * 74}")
        logger.info(f"VIRKER SCOREN?  (meravkastning på {opp.event_horisont} dager "
                    f"per score-bøtte)")
        logger.info(f"{'─' * 74}")
        logger.info(f"    {'Bøtte':<7} {'Score':<14} {'N':>6}  {'Snitt':>8}  "
                    f"{'Andel opp':>10}  {'t':>7}")
        for r in score_tabell:
            spenn = f"{float(r['Score_fra']):.0f}-{float(r['Score_til']):.0f}"
            logger.info(f"    {str(r['Bøtte']):<7} {spenn:<14} "
                        f"{int(r['N']):>6}  {float(r['Snitt_Meravk_Pst']):+7.2f} %  "
                        f"{float(r['Andel_Opp_Pst']):>9.1f} %  {str(r.get('t','')):>7}")
        for linje in _brekk(score_tekst, 70):
            logger.info(f"  {linje}")

    logger.info(f"\n{'─' * 74}")
    logger.info(f"  {dom.get('kort')}")
    for linje in _brekk(dom.get("tekst", ""), 70):
        logger.info(f"  {linje}")
    logger.info(f"{'─' * 74}")

    if m:
        logger.info("\n  PORTEFØLJE")
        for navn, tall in m.items():
            logger.info(f"    {navn:<11} CAGR {tall.get('CAGR', NAN)*100:+6.1f} %   "
                        f"Sharpe {tall.get('Sharpe', NAN):5.2f}   "
                        f"Sortino {tall.get('Sortino', NAN):5.2f}   "
                        f"MaxDD {tall.get('MaxDD', NAN)*100:6.1f} %")
        if handler:
            for linje in friksjonsregnskap(handler, equity, m, opp):
                logger.info(f"    {linje}")
    logger.info(f"{'═' * 74}")


# ══════════════════════════════════════════════════════════════════════════
# DEL J — STATUSTAVLEN: HVA GIKK BRA, OG HVA GIKK IKKE?
# ══════════════════════════════════════════════════════════════════════════
# DEL K — RESULTATET PÅ MAIL
# ══════════════════════════════════════════════════════════════════════════
#
# Én mail på slutten av kjøringen: statusen for de seks stegene, strategiene
# side om side, og for HVER strategi som er beholdt — nøkkeltallene, hva den
# eier i dag, og de siste handlene.
#
# Mailen bygges av filene steg 6 skrev, ikke av tall som ligger i minnet.
# Det er et bevisst valg: da kan den sendes på nytt uten å kjøre backtesten
# om igjen (`--steg 6 --mail` eller bare `--mail`), og den kan aldri vise noe
# annet enn det som faktisk står i filene du åpner etterpå.
#
# ADVARSEL OM PASSORDET. App-passordet står i klartekst i Oppsett, som i
# resten av kodebasen din. Det ligger dermed i git, og alle som har lest
# tilgang til repoet kan sende mail som deg. Bytt det i Google-kontoen din og
# sett det heller som miljøvariabel:  setx AKSJE_MAIL_APP_PASSWORD "…"

EPOST_STIL = """
body { font-family:'Segoe UI',Arial,sans-serif; margin:0; padding:20px;
       background:#f0f2f5; color:#222; }
.beholder { max-width:1060px; margin:0 auto; }
.topp { background:linear-gradient(135deg,#12494f 0%,#1f5c63 100%); color:#fff;
        padding:26px 30px; border-radius:12px 12px 0 0; }
.topp h1 { margin:0; font-size:22px; }
.topp p { margin:6px 0 0; opacity:.85; font-size:13px; }
.kort { background:#fff; padding:20px 25px; border-bottom:1px solid #e8e8e8; }
.kort:last-of-type { border-bottom:none; border-radius:0 0 12px 12px; }
.kort h2 { margin:0 0 4px; color:#12494f; font-size:17px; }
.kort h3 { margin:16px 0 2px; color:#12494f; font-size:14px; }
p.sub { color:#666; font-size:12px; margin:0 0 10px; }
table { border-collapse:collapse; width:100%; margin-top:8px; font-size:12.5px; }
th { background:#f5f5f5; color:#333; padding:8px 10px; text-align:left;
     font-weight:600; border-bottom:2px solid #e0e0e0; white-space:nowrap; }
td { padding:6px 10px; border-bottom:1px solid #f0f0f0; }
.h { text-align:right; }
.merke { background:#e8eaf6; color:#283593; padding:3px 10px; border-radius:12px;
         font-size:11px; font-weight:600; }
.opp { color:#2e7d32; font-weight:600; }
.ned { color:#c62828; font-weight:600; }
.rute { background:#f8f9fa; border:1px solid #e0e0e0; border-radius:8px;
        padding:10px; margin:10px 0; }
.tall { display:inline-block; min-width:104px; text-align:center; padding:6px 8px; }
.tall .lab { font-size:10px; color:#888; text-transform:uppercase;
             letter-spacing:.5px; }
.tall .verdi { font-size:17px; font-weight:bold; margin-top:2px; }
.advarsel { background:#fff8e1; border:1px solid #ffe082; border-radius:6px;
            padding:10px 12px; margin-top:12px; font-size:11.5px; color:#5d4037;
            line-height:1.55; }
.fot { text-align:center; color:#999; font-size:11px; padding:16px 0; }
"""


def _e_tall(v: Any, d: int = 2, sfx: str = "", fortegn: bool = False) -> str:
    x = tolk_maskin(v)
    if x is None:
        return '<span style="color:#bbb;">—</span>'
    return (f"{x:+.{d}f}" if fortegn else f"{x:.{d}f}") + sfx


def _e_farge(v: Any, d: int = 1, sfx: str = " %") -> str:
    x = tolk_maskin(v)
    if x is None:
        return '<span style="color:#bbb;">—</span>'
    return f'<span class="{"opp" if x > 0 else "ned"}">{x:+.{d}f}{sfx}</span>'


def _e_rute(lab: str, verdi: str, farge: str = "#333") -> str:
    return (f'<div class="tall"><div class="lab">{trygg(lab)}</div>'
            f'<div class="verdi" style="color:{farge};">{verdi}</div></div>')


def _e_alder(sti: Path) -> str:
    if not sti.exists():
        return "mangler"
    m = datetime.fromtimestamp(sti.stat().st_mtime)
    timer = (datetime.now() - m).total_seconds() / 3600.0
    if timer < 1:
        return f"{m:%Y-%m-%d %H:%M} ({int(timer * 60)} min siden)"
    if timer < 48:
        return f"{m:%Y-%m-%d %H:%M} ({int(timer)} t siden)"
    return f"{m:%Y-%m-%d %H:%M} ({int(timer / 24)} dager siden)"


def valgt_innsidestrategi(opp):
    path = opp.s6_dir / "selected_variant.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"Variant": HOVEDSTRATEGI.navn, "Reason": "Saved baseline result"}


def _e_strategikort(opp: Oppsett, rad: Rad, beholdning: Sequence[Rad],
                    handler: Sequence[Rad], dagens: Sequence[Rad] = ()) -> str:
    navn = str(rad.get("Strategi"))
    hoved = " &nbsp;<span class='merke'>valgt strategi</span>" if navn == valgt_innsidestrategi(opp)["Variant"] else ""
    cagr = tolk_maskin(rad.get("CAGR_Pst"))
    grønn, rød = "#2e7d32", "#c62828"

    ruter = "".join([
        _e_rute("CAGR", _e_tall(rad.get("CAGR_Pst"), 1, " %", True),
                grønn if (cagr or 0) > 0 else rød),
        _e_rute("Sharpe", _e_tall(rad.get("Sharpe"))),
        _e_rute("Max drawdown", _e_tall(rad.get("MaxDD_Pst"), 1, " %"), rød),
        _e_rute("Sharpe ut-utvalg", _e_tall(rad.get("Ut_Sharpe"))),
        _e_rute("Kapital ute", _e_tall(rad.get("Andel_Kapital_Pst"), 0, " %")),
        _e_rute("Navn (median)", _e_tall(rad.get("Median_Navn"), 1)),
        _e_rute("Største posisjon", _e_tall(rad.get("Maks_Vekt_Pst"), 0, " %"),
                rød if (tolk_maskin(rad.get("Maks_Vekt_Pst")) or 0) > 90 else "#333"),
        _e_rute("Omsetning/år", _e_tall(rad.get("Omsetning_Per_Ar_Pst"), 0, " %")),
        _e_rute("Drag ved 1,5 %", _e_tall(rad.get("Drag_Ved_15_Pst"), 1, " %"), rød),
    ])

    if beholdning:
        sum_verdi = sum(tolk_maskin(b.get("Verdi_NOK")) or 0.0 for b in beholdning)
        dato = trygg(beholdning[0].get("Dato"))
        rader = "".join(
            f'<tr><td><strong>{trygg(b.get("Ticker"))}</strong></td>'
            f'<td class="h">{_e_tall(b.get("Antall"), 0)}</td>'
            f'<td>{trygg(b.get("Inn_Dato"))}</td>'
            f'<td class="h">{_e_tall(b.get("Inn_Kurs"))}</td>'
            f'<td class="h">{_e_tall(b.get("Siste_Kurs"))}</td>'
            f'<td class="h">{_e_tall(b.get("Verdi_NOK"), 0)}</td>'
            f'<td class="h">{_e_tall(b.get("Andel_Pst"), 1, " %")}</td>'
            f'<td class="h">{_e_farge(b.get("Avk_Pst"))}</td>'
            f'<td class="h">{trygg(b.get("Dager"))}</td></tr>'
            for b in beholdning)
        beholdning_html = (
            '<table><tr><th>Ticker</th><th class="h">Antall</th><th>Kjøpt</th>'
            '<th class="h">Inngang</th><th class="h">Siste</th>'
            '<th class="h">Verdi</th><th class="h">Vekt</th><th class="h">Avk.</th>'
            f'<th class="h">Dager</th></tr>{rader}'
            f'<tr style="background:#e8f1ef;font-weight:bold;"><td colspan="5">'
            f'{len(beholdning)} posisjon{"er" if len(beholdning) != 1 else ""} '
            f'per {dato}</td>'
            f'<td class="h">{sum_verdi:,.0f}</td><td colspan="3"></td></tr></table>'
            .replace(",", " "))
    else:
        beholdning_html = (
            '<p class="sub"><em>Strategien står i kontanter på siste '
            'kursdag i beregningen.</em></p>')

    if handler:
        siste = sorted(handler, key=lambda h: str(h.get("Dato")))[-10:][::-1]
        rader = "".join(
            f'<tr><td>{trygg(h.get("Dato"))}</td>'
            f'<td class="{"opp" if str(h.get("Type")) == "KJØP" else "ned"}">'
            f'{trygg(h.get("Type"))}</td>'
            f'<td><strong>{trygg(h.get("Ticker"))}</strong></td>'
            f'<td class="h">{_e_tall(h.get("Verdi_NOK"), 0)}</td>'
            f'<td class="h">{_e_tall(h.get("Kostnad_NOK"), 0)}</td></tr>'
            for h in siste)
        handler_html = ('<table><tr><th>Dato</th><th>Type</th><th>Ticker</th>'
                        '<th class="h">Beløp</th><th class="h">Kostnad</th></tr>'
                        f'{rader}</table>')
    else:
        handler_html = '<p class="sub"><em>Ingen handler i loggen.</em></p>'

    beholdning_dato = (f" per {trygg(beholdning[0].get('Dato'))}"
                       if beholdning else "")
    if dagens:
        rader = "".join(
            f'<tr><td><strong>{trygg(d.get("Ticker"))}</strong></td>'
            f'<td>{trygg(d.get("Selskap"))}</td>'
            f'<td>{trygg(d.get("Rolle"))}</td>'
            f'<td class="h">{_e_tall(d.get("Verdi_NOK"), 0)}</td>'
            f'<td class="h">{_e_tall(d.get("Score"), 1)}</td>'
            f'<td>{trygg(d.get("Signaldato"))}</td>'
            f'<td class="h">{trygg(d.get("Dager_Siden"))}</td></tr>'
            for d in dagens)
        dagens_html = (
            '<table><tr><th>Ticker</th><th>Selskap</th><th>Rolle</th>'
            '<th class="h">Beløp</th><th class="h">Score</th><th>Signaldato</th>'
            f'<th class="h">Dager siden</th></tr>{rader}</table>')
    else:
        dagens_html = ('<p class="sub"><em>Ingen selskaper kvalifiserer på '
                       'siste kursdag — strategien ville stått i kontanter.</em></p>')

    return f"""
<div class="kort">
    <h2>{trygg(navn)}{hoved}</h2>
    <p class="sub">{trygg(rad.get("Hvorfor"))}</p>
    <div class="rute">{ruter}</div>
    <h3>Kvalifiserer nå &nbsp;<span style="font-weight:400;font-size:11px;
        color:#999;">signalliste, ikke etterprøvd</span></h3>
    {dagens_html}
    <h3>Beholdning{beholdning_dato}</h3>
    {beholdning_html}
    <h3>Siste handler</h3>
    {handler_html}
</div>"""


def bygg_epost(opp: Oppsett, resultater: Sequence["Stegresultat"]) -> Optional[str]:
    """HTML-en for mailen, bygget av filene steg 6 skrev. None uten data."""
    strategier = les_csv(opp.strategier_csv)
    if not strategier:
        return None
    valg = valgt_innsidestrategi(opp)
    strategier.sort(key=lambda r: r.get("Strategi") != valg["Variant"])
    beholdning = [b for b in les_csv(opp.beholdning_csv)
                  if str(b.get("Ticker", "")).upper() not in ("", "KONTANTER", "(KONTANTER)", "CASH")]
    handler = les_csv(opp.strategi_handler_csv)

    status_rader = "".join(
        f'<tr><td>{r.nr} {trygg(r.navn)}</td>'
        f'<td class="{"opp" if r.status == "OK" else ("ned" if r.status == "FEIL" else "")}">'
        f'{trygg(r.status)}</td><td>{trygg(r.detaljer)}</td></tr>'
        for r in resultater if r.status != "IKKE_VALGT")

    sammenlikning = "".join(
        f'<tr><td><strong>{trygg(r.get("Strategi"))}</strong></td>'
        f'<td class="h">{_e_farge(r.get("CAGR_Pst"))}</td>'
        f'<td class="h">{_e_tall(r.get("Sharpe"))}</td>'
        f'<td class="h">{_e_tall(r.get("Ut_Sharpe"))}</td>'
        f'<td class="h">{_e_tall(r.get("MaxDD_Pst"), 1, " %")}</td>'
        f'<td class="h">{_e_tall(r.get("Andel_Kapital_Pst"), 0, " %")}</td>'
        f'<td class="h">{_e_tall(r.get("Median_Navn"), 1)}</td>'
        f'<td class="h">{_e_tall(r.get("Maks_Vekt_Pst"), 0, " %")}</td>'
        f'<td class="h">{_e_tall(r.get("Drag_Ved_15_Pst"), 1, " %")}</td></tr>'
        for r in strategier)

    # De ferskeste kjøpene. Det er de som er handlebare i morgen — resten av
    # mailen er historikk.
    ferske = [h for h in les_csv(opp.hendelser_csv) if h.get("Klasse") == "KJOP"]
    ferske.sort(key=lambda h: (str(h.get("Dato")), str(h.get("Klokkeslett"))),
                reverse=True)
    signal_rader = "".join(
        f'<tr><td>{trygg(h.get("Dato"))}</td>'
        f'<td><strong>{trygg(h.get("Ticker"))}</strong></td>'
        f'<td>{trygg(h.get("Selskap"))[:28]}</td>'
        f'<td>{trygg(h.get("Rolle"))}</td>'
        f'<td class="h">{_e_tall(h.get("Verdi_NOK"), 0)}</td>'
        f'<td class="h">{_e_tall(h.get("Bullish_Score"), 1)}</td>'
        f'<td>{trygg(h.get("Signal"))}</td></tr>'
        for h in ferske[:12])

    etterslep = ""
    selection_html = (
        '<p><strong>Valgt strategi: ' + trygg(valg["Variant"]) + '</strong><br>'
        + trygg(valg.get("Reason", "")) + '<br>Treningsperiode til '
        + trygg(valg.get("Selection_Cutoff", "—"))
        + ' · CAGR trening ' + _e_tall(valg.get("Train_CAGR_Pst"), 1, " %")
        + ' · CAGR senere periode ' + _e_tall(valg.get("Test_CAGR_Pst"), 1, " %")
        + '</p>')

    dagens = les_csv(opp.dagens_liste_csv)
    kort = "".join(
        _e_strategikort(
            opp, r,
            [b for b in beholdning if b.get("Strategi") == r.get("Strategi")],
            [h for h in handler if h.get("Strategi") == r.get("Strategi")],
            [d for d in dagens if d.get("Strategi") == r.get("Strategi")])
        for r in strategier)

    kilder = "".join(
        f'<tr><td>{trygg(navn)}</td>'
        f'<td style="font-family:monospace;font-size:11px;">{trygg(sti.name)}</td>'
        f'<td>{trygg(_e_alder(sti))}</td></tr>'
        for navn, sti in (("Artikkelindeks", opp.indeks_csv),
                          ("Tekstindeks", opp.tekst_indeks_csv),
                          ("Hendelser", opp.hendelser_csv),
                          ("Børskalender", opp.kalender_csv),
                          ("Sammenslått", opp.merget_csv),
                          ("Strategier", opp.strategier_csv)))

    return f"""<html><head><meta charset="utf-8"><style>{EPOST_STIL}</style></head>
<body><div class="beholder">

<div class="topp">
    <h1>Innsidehandel på Oslo Børs</h1>
    <p>{len(strategier)} strategier · {len(beholdning)} åpne posisjoner ·
       bygget {datetime.now():%Y-%m-%d %H:%M}</p>
</div>

<div class="kort">
    <h2>Kjøringen</h2>
    <table><tr><th>Steg</th><th>Status</th><th>Resultat</th></tr>
    {status_rader}</table>
</div>

<div class="kort">
    <h2>Strategiene side om side</h2>
    {selection_html}
    <p class="sub">Samme signaler, samme kurser. Det eneste som skiller dem er
       når og hvordan det handles.</p>
    <table><tr><th>Strategi</th><th class="h">CAGR</th><th class="h">Sharpe</th>
        <th class="h">Sharpe ut</th><th class="h">Max DD</th>
        <th class="h">Kapital ute</th><th class="h">Navn</th>
        <th class="h">Største pos.</th><th class="h">Drag v/1,5 %</th></tr>
    {sammenlikning}</table>
    <div class="advarsel">
        <strong>Les den nest siste kolonnen før den første.</strong>
        «Kapital ute» sier hvor mye av pengene som faktisk står i markedet —
        en strategi med 12 % der måler kontantdrag, ikke signal. «Drag v/1,5 %»
        er hva handlingen ville kostet med normal spread på Oslo Børs; tallene
        i tabellen er FØR kostnader. Og siden alle radene er prøvd på de samme
        dataene, er den beste av dem delvis heldig — «Sharpe ut» er den eneste
        kolonnen som er etterprøvd.
    </div>
</div>

<div class="kort">
    <h2>Ferskeste innsidekjøp</h2>
    <p class="sub">De tolv nyeste meldingene som ble lest som rene kjøp.</p>
    <table><tr><th>Dato</th><th>Ticker</th><th>Selskap</th><th>Rolle</th>
        <th class="h">Beløp</th><th class="h">Score</th><th>Signal</th></tr>
    {signal_rader}</table>
    {etterslep}
</div>

{kort}

<div class="kort">
    <h2>Datagrunnlag</h2>
    <table><tr><th>Fil</th><th>Navn</th><th>Sist skrevet</th></tr>{kilder}</table>
</div>

<div class="fot">
    <p>Alt over er backtester på historiske data, ikke en live portefølje.</p>
    <p>innsidehandel_pipeline · {datetime.now():%Y-%m-%d %H:%M:%S}</p>
</div>

</div></body></html>"""


def send_epost(opp: Oppsett, html: str, emne: str, logger: logging.Logger) -> bool:
    """
    Sender mailen. Feiler aldri kjøringen — en mail er ikke analysen.

    Prøver hvert passord vi kjenner, ikke bare det første. Et gammelt passord
    i mail_passord.txt skal ikke kunne skygge for et gyldig i miljøvariabelen:
    535 fra Gmail betyr «feil nøkkel», ikke «gi opp». Andre SMTP-feil —
    nettverk, ukjent mottaker — er ikke passordets skyld, og da stopper vi med
    én gang i stedet for å hamre på med de samme opplysningene.
    """
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    mottakere = [m.strip() for m in str(opp.epost_til).split(",") if m.strip()]
    kandidater = opp.passord_kandidater()
    if not kandidater or not mottakere:
        mangler = ("mottaker" if kandidater else "app-passord")
        logger.warning(
            f"   ✉️  Mangler {mangler} — mailen ble IKKE sendt.\n"
            + passord_leteforklaring(opp.base_dir))
        return False

    def _bygg() -> "MIMEMultipart":
        melding = MIMEMultipart("alternative")
        melding["Subject"] = emne
        melding["From"] = opp.epost_fra
        melding["To"] = ", ".join(mottakere)
        melding.attach(MIMEText(html, "html", "utf-8"))
        return melding

    avvist: List[str] = []
    for nr, (kilde, passord) in enumerate(kandidater, start=1):
        try:
            with smtplib.SMTP(opp.smtp_vert, opp.smtp_port, timeout=45) as tjener:
                tjener.starttls()
                tjener.login(opp.epost_fra, passord)
                tjener.send_message(_bygg())
        except smtplib.SMTPAuthenticationError as e:
            # Feil nøkkel. Si hvilken, så brukeren vet hvilken fil som er utdatert.
            avvist.append(kilde)
            logger.info(f"   ✉️  Passord {nr}/{len(kandidater)} avvist av Gmail "
                        f"({kilde}): {feiltekst(e)[:70]}")
            continue
        except Exception as e:
            logger.warning(f"   ✉️  Sending feilet: {feiltekst(e)}")
            return False
        if avvist:
            logger.info(f"   ✉️  Kom inn med passordet fra {kilde}. Utdatert i: "
                        f"{'; '.join(avvist)} — rydd der.")
        logger.info(f"   ✉️  Mail sendt til {', '.join(mottakere)}")
        return True

    logger.warning(
        f"   ✉️  Alle {len(kandidater)} passordene ble avvist av Gmail (535).\n"
        f"       Prøvd: {'; '.join(avvist)}\n"
        f"       Lag et nytt app-passord på https://myaccount.google.com/apppasswords\n"
        + passord_leteforklaring(opp.base_dir))
    return False


def epost_rapport(opp: Oppsett, resultater: Sequence["Stegresultat"],
                  logger: logging.Logger, send: bool = True) -> Optional[Path]:
    """Bygger mailen, lagrer en kopi, og sender den. Stien til kopien."""
    try:
        html = bygg_epost(opp, resultater)
    except Exception as e:
        logger.warning(f"   ✉️  Kunne ikke bygge mailen: {feiltekst(e)}")
        return None
    if not html:
        logger.info(f"   ✉️  Ingen {opp.strategier_csv.name} å sende — "
                    f"kjør steg 6 først.")
        return None

    kopi = opp.s6_dir / f"mail_{datetime.now():%Y%m%d_%H%M%S}.html"
    try:
        kopi.parent.mkdir(parents=True, exist_ok=True)
        kopi.write_text(html, encoding="utf-8")
        logger.info(f"   ✉️  Kopi av mailen: {kopi}")
    except OSError as e:
        logger.debug(f"Kunne ikke lagre mailkopi: {feiltekst(e)}")

    strategier = les_csv(opp.strategier_csv)
    valg = valgt_innsidestrategi(opp)
    beholdning = [r for r in les_csv(opp.beholdning_csv)
                  if r.get("Strategi") == valg["Variant"]
                  and r.get("Ticker") != "(kontanter)"]
    hoved = next((r for r in strategier
                  if r.get("Strategi") == valg["Variant"]), None)
    emne = (f"Innsidehandel Oslo Børs — {len(strategier)} strategier, "
            f"{len(beholdning)} posisjoner")
    if hoved and tolk_maskin(hoved.get("CAGR_Pst")) is not None:
        emne += f" · {valg['Variant']} CAGR {tolk_maskin(hoved['CAGR_Pst']):+.1f} %"
    emne += f" — {datetime.now():%Y-%m-%d}"

    if send:
        if not send_epost(opp, html, emne, logger):
            raise RuntimeError(f"Email delivery failed; report saved at {kopi}")
    else:
        logger.info("   ✉️  --mail-kladd: mailen ble bygget, ikke sendt.")
    return kopi


# ══════════════════════════════════════════════════════════════════════════
#
# Det viktigste i hele fila for deg som kjører den.
#
# Hvert steg er pakket inn i sin egen try/except. Feiler steg 4, blir steg 4
# markert som FEIL — og steg 5 og 6 kjører videre på det som allerede ligger
# på disk fra forrige gang. Ingenting kaster deg ut av programmet, og til
# slutt står det svart på hvitt hvilke steg som gikk og hvilke som ikke gikk.
#
# Det er nettopp dette som manglet før: en kjøring som stoppet i steg 1 sa
# ingenting om at steg 2 og 3 hadde data fra i går som fortsatt var brukbare.

STEGNAVN = {
    1: "Nedlasting fra Euronext",
    2: "Tekstuttrekk",
    3: "Score og rangering",
    4: "Aksjekurser (yfinance)",
    5: "Sammenslåing",
    6: "Backtest",
}

# Rekkefølgen betyr noe: OK er best, AVBRUTT verst.
STATUSMERKE = {
    "OK": ("✅", "OK"),
    "DELVIS": ("🟡", "DELVIS"),
    "HOPPET": ("⏭️", "HOPPET OVER"),
    "IKKE_VALGT": ("· ", "ikke valgt"),
    "FEIL": ("❌", "FEIL"),
    "AVBRUTT": ("⏹️", "AVBRUTT"),
}


@dataclass
class Stegresultat:
    nr: int
    navn: str
    status: str = "IKKE_VALGT"
    sekunder: float = 0.0
    detaljer: str = ""
    feil: str = ""
    sporing: str = ""
    raad: Tuple[str, ...] = ()

    def som_rad(self) -> Rad:
        return {"Steg": self.nr, "Navn": self.navn, "Status": self.status,
                "Sekunder": round(self.sekunder, 1), "Detaljer": self.detaljer,
                "Feil": self.feil}


def kjor_steg(nr: int, funksjon: Callable[[], Dict[str, Any]],
              logger: logging.Logger) -> Stegresultat:
    """
    Kjører ett steg og fanger ALT som kan gå galt.

    Én ting slipper gjennom: Ctrl+C. Det er en beskjed fra deg, ikke en feil
    i programmet, og da skal kjøringen stanse — men den skal fortsatt rekke å
    skrive statustavlen på vei ut.
    """
    res = Stegresultat(nr=nr, navn=STEGNAVN[nr])
    logger.info(f"\n{'━' * 74}")
    logger.info(f"STEG {nr} — {STEGNAVN[nr].upper()}")
    logger.info(f"{'━' * 74}")
    start = time.time()
    try:
        svar = funksjon() or {}
        res.status = str(svar.get("status", "OK"))
        res.detaljer = str(svar.get("detaljer", ""))
        res.raad = tuple(str(x) for x in (svar.get("raad") or ()))
    except KeyboardInterrupt:
        res.status = "AVBRUTT"
        res.detaljer = "avbrutt med Ctrl+C"
        res.sekunder = time.time() - start
        logger.warning(f"\n⏹️  Steg {nr} avbrutt.")
        raise
    except ImportError as e:
        res.status = "FEIL"
        res.feil = feiltekst(e)
        res.detaljer = "manglende pakke"
        logger.error(f"❌ Steg {nr} kan ikke kjøre — {res.feil}")
    except Exception as e:
        res.status = "FEIL"
        res.feil = feiltekst(e)[:300]
        res.sporing = traceback.format_exc()
        res.detaljer = "se feilmeldingen"
        logger.error(f"❌ Steg {nr} stoppet — {res.feil}")
        logger.debug(res.sporing)
    res.sekunder = time.time() - start
    logger.info(f"\n   Steg {nr} ferdig på {_varighet(res.sekunder)} — "
                f"{STATUSMERKE.get(res.status, ('', res.status))[1]}")
    return res


def _vis_bredde(s: str) -> int:
    """
    Hvor mange KOLONNER tar teksten i terminalen?

    len() duger ikke: «✅» er ett tegn i Python, men tegnes to kolonner
    bredt, og «⏭️» er to tegn (ikon + variantvelger) som tegnes to kolonner.
    Uten dette blir høyrekanten i statustavlen ujevn.
    """
    b = 0
    for c in s:
        if unicodedata.combining(c) or c in ("\ufe0f", "\ufe0e"):
            continue
        o = ord(c)
        bred = (unicodedata.east_asian_width(c) in ("W", "F")
                or 0x1F300 <= o <= 0x1FAFF or 0x2600 <= o <= 0x27BF)
        b += 2 if bred else 1
    return b


def _rammelinje(innhold: str, bredde: int = 72) -> str:
    """Én linje inni rammen, alltid like bred uansett emoji."""
    tekst = " " + innhold
    mens = _vis_bredde(tekst)
    while mens > bredde:                  # klipp tegn for tegn, ikke byte
        tekst = tekst[:-1]
        mens = _vis_bredde(tekst)
    return "║" + tekst + " " * (bredde - mens) + "║"


def _varighet(sekunder: float) -> str:
    if sekunder < 90:
        return f"{sekunder:.0f} s"
    if sekunder < 5400:
        return f"{sekunder/60:.1f} min"
    return f"{sekunder/3600:.1f} t"


def skriv_statustavle(resultater: Sequence[Stegresultat], opp: Oppsett,
                      logger: logging.Logger, total: float) -> None:
    """Den siste tingen du ser. Én linje per steg, og aldri noe skjult."""
    logger.info("")
    logger.info("╔" + "═" * 72 + "╗")
    logger.info(_rammelinje(" STATUS FOR KJØRINGEN"))
    logger.info("╠" + "═" * 72 + "╣")
    logger.info(_rammelinje(f"   {'STEG':<26} {'STATUS':<13} {'TID':>8}"))
    logger.info("╟" + "─" * 72 + "╢")

    for r in resultater:
        ikon, tekst = STATUSMERKE.get(r.status, ("  ", r.status))
        tid = _varighet(r.sekunder) if r.sekunder >= 0.05 else "—"
        navn = f"{r.nr} {r.navn}"
        logger.info(_rammelinje(f"{ikon} {navn:<26} {tekst:<13} {tid:>8}"))
        detalj = r.feil or r.detaljer
        if detalj:
            for bit in _brekk(detalj, 62)[:3]:
                logger.info(_rammelinje(f"       {bit}"))
    logger.info("╠" + "═" * 72 + "╣")

    ok = sum(1 for r in resultater if r.status == "OK")
    delvis = sum(1 for r in resultater if r.status == "DELVIS")
    feil = sum(1 for r in resultater if r.status in ("FEIL", "AVBRUTT"))
    hoppet = sum(1 for r in resultater if r.status == "HOPPET")
    sammendrag = (f"{ok} OK · {delvis} delvis · {hoppet} hoppet over · {feil} feilet"
                  f"   ·   totalt {_varighet(total)}")
    logger.info(_rammelinje(" " + sammendrag))
    logger.info("╚" + "═" * 72 + "╝")

    if feil:
        logger.info("\n   Stegene som feilet, og hva du kan gjøre:")
        for r in resultater:
            if r.status not in ("FEIL", "AVBRUTT"):
                continue
            logger.info(f"     STEG {r.nr} ({r.navn}): {r.feil or r.detaljer}")
            for råd in _rad_om_feil(r):
                logger.info(f"        → {råd}")

    # De viktigste filene, med en gang, så du slipper å lete.
    logger.info("\n   Filene:")
    for sti, hva in ((opp.indeks_csv, "steg 1  artikkelindeks"),
                     (opp.tekst_indeks_csv, "steg 2  tekstindeks"),
                     (opp.hendelser_xlsx, "steg 3  score  ← åpne denne i Excel"),
                     (opp.merget_xlsx, "steg 5  score + kurs  ← og denne"),
                     (opp.rapport_html, "steg 6  rapport  ← åpne i nettleser")):
        merke = "✓" if sti.exists() else "·"
        logger.info(f"     {merke} {hva:<38} {sti}")

    try:
        skriv_atomisk(opp.status_json, lambda p: p.write_text(json.dumps({
            "tidspunkt": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "versjon": VERSJON, "sekunder": round(total, 1),
            "steg": [r.som_rad() for r in resultater]},
            ensure_ascii=False, indent=1), encoding="utf-8"))
    except OSError as e:
        logger.debug(f"Kunne ikke skrive status.json: {feiltekst(e)}")


def _rad_om_feil(r: Stegresultat) -> List[str]:
    """Konkrete neste skritt, ikke «noe gikk galt»."""
    if r.raad:
        return list(r.raad)                    # steget vet best selv
    f = (r.feil or "").lower()
    if "playwright" in f:
        return ["pip install playwright", "playwright install chromium"]
    if "yfinance" in f:
        return ["pip install yfinance",
                "eller kjør videre uten: Yahoo kalles direkte som reserve"]
    if "aksjeliste" in f or "isin" in f:
        return ["last ned lista for hånd fra "
                "https://live.euronext.com/nb/markets/oslo/equities/list",
                "legg .xlsx-fila i datamappen, eller bruk --aksjeliste \"sti\""]
    if r.nr == 1:
        return ["kjør med --synlig for å se hva nettleseren faktisk gjør",
                "kjør med --feilsok for full sporing i loggen"]
    if r.nr in (5, 6):
        return [f"steg {r.nr - 1} må ha kjørt først — sjekk linjen over"]
    return ["kjør med --feilsok for full sporing i loggen"]


def status_paa_disk(opp: Oppsett, logger: logging.Logger) -> int:
    """--status: hva ligger der, og hvor gammelt er det? Henter ingenting."""
    opp.lag_mapper()
    vm = Vannmerke(opp.vannmerke_json, logger)
    logger.info(f"\n{'═' * 74}")
    logger.info(f"HVA LIGGER PÅ DISK — {opp.base_dir}")
    logger.info(f"{'═' * 74}")

    for gruppe, hva in ((GRUPPE_ARTIKLER, "selskaper med artikler"),
                        (GRUPPE_KURSER, "tickere med kurser")):
        o = vm.oppsummering(gruppe)
        if not o["antall"]:
            logger.info(f"  {hva:<28} —  ingenting hentet ennå")
            continue
        if o["nyeste"] is None:
            # Poster finnes, men ingen av dem har lyktes ennå — bare feil.
            logger.info(f"  {hva:<28} {o['antall']:>5}   ingen fullført ennå"
                        + (f"   ⚠️  {o['med_feil']} med feil" if o["med_feil"] else ""))
            continue
        etterslep = (date.today() - o["nyeste"]).days
        logger.info(f"  {hva:<28} {o['antall']:>5}   komplett til {o['eldste']} … "
                    f"{o['nyeste']}"
                    + (f"  ({etterslep} dager siden nyeste)" if etterslep else "")
                    + (f"   ⚠️  {o['med_feil']} med feil" if o["med_feil"] else ""))

    for sti, hva in ((opp.indeks_csv, "1  artikkelindeks"),
                     (opp.tekst_indeks_csv, "2  tekstindeks"),
                     (opp.hendelser_csv, "3  hendelser med score"),
                     (opp.merget_csv, "5  score + kurs"),
                     (opp.equity_csv, "6  equity-kurve")):
        logger.info(f"  {hva:<28} " + (f"{len(les_csv(sti)):>5} rader   {sti.name}"
                                       if sti.exists() else "—  ikke laget ennå"))

    for mappe, hva in ((opp.artikkel_dir, "rå HTML-filer"),
                       (opp.pdf_dir, "PDF-vedlegg"),
                       (opp.tekst_dir, "tekstfiler"),
                       (opp.s4_dir, "kursfiler")):
        monster = "*.csv" if mappe == opp.s4_dir else ("*.pdf" if mappe == opp.pdf_dir
                                                       else ("*.html" if mappe == opp.artikkel_dir
                                                             else "*.txt"))
        antall = len(list(mappe.glob(monster))) if mappe.exists() else 0
        logger.info(f"  {hva:<28} {antall:>5}")

    liste = finn_aksjeliste(opp)
    if liste is None:
        logger.info(f"  {'aksjeliste':<28} —  ingen funnet")
    else:
        alder = aksjeliste_alder(liste)
        merke = ("  ⚠️  gammel" if alder is not None
                 and alder > max(7, opp.aksjeliste_maks_alder_dager) else "")
        logger.info(f"  {'aksjeliste':<28} {liste.name}"
                    + (f"   ({alder} dager gammel)" if alder is not None else "") + merke)

    if opp.status_json.exists():
        try:
            forrige = json.loads(opp.status_json.read_text(encoding="utf-8"))
            logger.info(f"\n  Forrige kjøring: {forrige.get('tidspunkt')}")
            for s in forrige.get("steg", []):
                ikon = STATUSMERKE.get(str(s.get("Status")), ("  ",))[0]
                logger.info(f"     {ikon} {s.get('Steg')} {str(s.get('Navn')):<26} "
                            f"{s.get('Status'):<8} {s.get('Detaljer', '')[:40]}")
        except (OSError, ValueError):
            pass
    logger.info(f"{'═' * 74}")
    return 0


# ══════════════════════════════════════════════════════════════════════════
# DEL K — KOMMANDOLINJEN
# ══════════════════════════════════════════════════════════════════════════

def bygg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="innsidehandel_pipeline",
        description="Innsidehandel på Oslo Børs — seks steg fra nedlasting til backtest",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Stegene:
  1  last ned artiklene fra Euronext (rå HTML)      krever playwright
  2  trekk meldingsteksten ut av HTML-en → .txt     offline
  3  les dato, hvem, hvor mye — og ranger på bullishness   offline
  4  hent aksjekursene med yfinance
  5  slå sammen score og kurs til én fil            offline
  6  backtest: virker signalet, og virker scoren?   offline

Eksempler:
  python innsidehandel_pipeline.py                  alle seks steg
  python innsidehandel_pipeline.py --steg 2,3       les tekstene og score på nytt
  python innsidehandel_pipeline.py --steg 4,5,6     kurser, sammenslåing, backtest
  python innsidehandel_pipeline.py --offline        rør ikke nettet (steg 2,3,5,6)
  python innsidehandel_pipeline.py --status         hva ligger på disk?
  python innsidehandel_pipeline.py --steg 1 --selskap EQNR --synlig
  python innsidehandel_pipeline.py --tving-tekst --steg 2,3   les all HTML på nytt
""")
    p.add_argument("--steg", metavar="N[,N]",
                   help="hvilke steg som skal kjøre (1-6). Standard: alle.")
    p.add_argument("--mappe", metavar="STI", help="hvor dataene ligger (standard: ./data)")
    p.add_argument("--offline", action="store_true",
                   help="rør ikke nettet — bruk det som allerede er lastet ned")
    p.add_argument("--full", action="store_true",
                   help="se bort fra vannmerkene og hent alt på nytt")
    p.add_argument("--status", action="store_true",
                   help="vis hva som ligger på disk, og avslutt")
    p.add_argument("--ingen-mail", action="store_true",
                   help="ikke send resultatmail til slutt")
    p.add_argument("--mail-kladd", action="store_true",
                   help="bygg mailen og lagre kopien, men ikke send den")
    p.add_argument("--mail-til", metavar="ADRESSE",
                   help="mottaker(e), kommaskilt")
    p.add_argument("--feilsok", action="store_true",
                   help="skriv DEBUG-linjer: hvilken feil ble hoppet over, og hvor")
    p.add_argument("--stopp-ved-feil", action="store_true",
                   help="avbryt hele kjeden når et steg feiler (standard: fortsett)")

    s1 = p.add_argument_group("steg 1 — nedlasting")
    s1.add_argument("--selskap", metavar="NAVN", help="bare ett selskap (delstreng)")
    s1.add_argument("--aksjeliste", metavar="STI",
                    help="bruk DENNE aksjelista i stedet for å hente en fersk")
    s1.add_argument("--fersk-liste", action="store_true",
                    help="hent aksjelista på nytt selv om dagens ligger på disk")
    s1.add_argument("--behold-liste", action="store_true",
                    help="ikke hent aksjeliste automatisk")
    s1.add_argument("--ar", type=int, metavar="N", help="års historikk (10)")
    s1.add_argument("--synlig", action="store_true", help="vis nettleservinduet")
    s1.add_argument("--nettleser", metavar="STI", help="sti til chrome/chromium")
    s1.add_argument("--uten-pdf", action="store_true",
                    help="ikke last ned PDF-vedlegg")

    s2 = p.add_argument_group("steg 2 — tekst")
    s2.add_argument("--tving-tekst", action="store_true",
                    help="les all HTML på nytt, også der teksten alt er skrevet")
    s2.add_argument("--sidemal-andel", type=float, metavar="ANDEL",
                    help="hvor stor andel av artiklene en tekstblokk må stå i før "
                         "den regnes som sidemal (0.20)")

    s3 = p.add_argument_group("steg 3 — score")
    s3.add_argument("--ta-med-emisjoner", action="store_true",
                    help="regn tegning i emisjon som et innsidekjøp")
    s3.add_argument("--min-verdi", type=float, metavar="NOK",
                    help="minste handelsbeløp som teller (50000)")
    s3.add_argument("--klyngedager", type=int, metavar="N",
                    help="handler i samme selskap innenfor N dager er én klynge (30)")

    s4 = p.add_argument_group("steg 4 — kurser")
    s4.add_argument("--alle", action="store_true",
                    help="hent kurser for hele aksjelista, ikke bare selskaper "
                         "med meldinger")
    s4.add_argument("--referanse", metavar="TICKER", help="referanseindeks (OSEBX.OL)")
    s4.add_argument("--totalavkastning", action="store_true",
                    help="bruk utbyttejustert kurs for BÅDE aksje og referanse. "
                         "Krever at referansen er en gross-indeks (…GI), ellers får "
                         "du utbyttet som falsk meravkastning.")
    s4.add_argument("--overlapp", type=int, metavar="N",
                    help="dager som hentes om igjen bakover hver gang (10)")

    s5 = p.add_argument_group("steg 5 — sammenslåing")
    s5.add_argument("--horisonter", metavar="N,N,N",
                    help="avkastningsvinduer i handledager "
                         "(-20,-5,-1,1,5,10,20,60,120). Negative gir dagene før.")

    s6 = p.add_argument_group("steg 6 — backtest")
    s6.add_argument("--event-horisont", type=int, metavar="N",
                    help="horisonten dommen hviler på (20)")
    s6.add_argument("--inn-utvalg-slutt", metavar="ÅÅÅÅ-MM-DD",
                    help="siste dag i inn-utvalget (2021-12-31)")
    s6.add_argument("--alle-i-klynge", action="store_true",
                    help="tell hvert kjøp for seg i stedet for ett per klynge")
    s6.add_argument("--min-score", type=float, metavar="N",
                    help="laveste score som slipper inn i porteføljen (60)")
    s6.add_argument("--maks-navn", type=int, metavar="N", help="navn i porteføljen (20)")
    s6.add_argument("--min-navn", type=int, metavar="N",
                    help="minste antall posisjoner risikoen deles på; "
                         "taket blir 1/N per aksje (5, 0 = av)")
    s6.add_argument("--signal-vindu", type=int, metavar="N",
                    help="hvor mange dager et innsidekjøp teller (30)")
    s6.add_argument("--min-omsetning", type=float, metavar="NOK",
                    help="likviditetsgulv (500000)")
    s6.add_argument("--spread", type=float, metavar="PST", help="full spread i %% (standard: 0; kostnadsstress rapporteres separat)")
    s6.add_argument("--kurtasje", type=float, metavar="PST", help="kurtasje i %% (standard: 0)")
    s6.add_argument("--bootstrap", type=int, metavar="N", help="bootstrap-runder (2000)")
    s6.add_argument("--kun-hovedstrategi", action="store_true",
                    help="hopp over sammenlikningen av strategivarianter")
    return p


# argparse tolker «-5» som et flagg. Skriv om «--horisonter -5,1» til
# «--horisonter=-5,1» før parsing, ellers må brukeren huske likhetstegnet og
# får en feilmelding som ikke forklarer noe.
_KAN_HA_MINUS = ("--horisonter",)


def tal_minus(argv: List[str]) -> List[str]:
    ut: List[str] = []
    hopp = False
    for i, bit in enumerate(argv):
        if hopp:
            hopp = False
            continue
        if bit in _KAN_HA_MINUS and i + 1 < len(argv) and argv[i + 1].startswith("-"):
            ut.append(f"{bit}={argv[i + 1]}")
            hopp = True
        else:
            ut.append(bit)
    return ut


def lag_oppsett(args) -> Oppsett:
    base = Path(args.mappe).expanduser() if args.mappe else SKRIPTMAPPE / "data"
    o = Oppsett(base_dir=base)
    o.inn_utvalg_slutt = os.environ.get("AKSJE_SELECTION_CUTOFF", o.inn_utvalg_slutt)
    o.offline = bool(args.offline)
    o.full = bool(args.full)

    if args.ar:
        o.historikk_ar = max(1, args.ar)
    if args.synlig:
        o.headless = False
    if args.nettleser:
        o.browser_sti = args.nettleser
    if args.behold_liste:
        o.hent_aksjeliste = False
    if args.uten_pdf:
        o.last_ned_pdf = False
    if args.sidemal_andel is not None:
        o.sidemal_andel = min(0.95, max(0.02, args.sidemal_andel))
    if args.referanse:
        o.referanse_ticker = args.referanse
    if args.totalavkastning:
        o.kursfelt = "adjclose"
    if args.overlapp is not None:
        o.overlapp_dager = max(0, args.overlapp)
    if args.ta_med_emisjoner:
        o.ta_med_emisjoner = True
    if args.min_verdi is not None:
        o.min_verdi_nok = max(0.0, args.min_verdi)
    if args.klyngedager is not None:
        o.klynge_dager = max(0, args.klyngedager)
    if args.horisonter:
        try:
            o.horisonter = tuple(sorted({int(x) for x in args.horisonter.split(",")
                                         if x.strip() and int(x) != 0}))
        except ValueError:
            raise SystemExit(f"Ugyldige horisonter: {args.horisonter}")
    if args.event_horisont:
        o.event_horisont = args.event_horisont
    if args.inn_utvalg_slutt:
        o.inn_utvalg_slutt = args.inn_utvalg_slutt
    if args.alle_i_klynge:
        o.kun_primaer = False
    if getattr(args, "kun_hovedstrategi", False):
        o.kun_hovedstrategi = True
    if getattr(args, "ingen_mail", False):
        o.send_epost_ved_slutt = False
    if getattr(args, "mail_til", None):
        o.epost_til = args.mail_til
    if args.min_score is not None:
        o.min_score_portefolje = args.min_score
    if args.maks_navn:
        o.maks_navn = max(1, args.maks_navn)
    if getattr(args, "min_navn", None) is not None:
        o.min_navn_portefolje = max(0, args.min_navn)
    if args.signal_vindu:
        o.signal_vindu_dager = max(1, args.signal_vindu)
    if args.min_omsetning is not None:
        o.min_omsetning_nok = max(0.0, args.min_omsetning)
    if args.spread is not None:
        o.spread_pst = max(0.0, args.spread)
    if args.kurtasje is not None:
        o.kurtasje_pst = max(0.0, args.kurtasje)
    if args.bootstrap:
        o.bootstrap_runder = max(100, args.bootstrap)

    # Event-horisonten må finnes blant horisontene, ellers har steg 6
    # ingen kolonne å hvile dommen på.
    if o.event_horisont not in o.horisonter:
        o.horisonter = tuple(sorted(set(o.horisonter) | {o.event_horisont}))
    return o


def velg_steg(args) -> List[int]:
    if not args.steg:
        return [1, 2, 3, 4, 5, 6]
    ut = []
    for bit in str(args.steg).replace(" ", "").split(","):
        if "-" in bit and not bit.startswith("-"):
            a, _, b = bit.partition("-")
            if a.isdigit() and b.isdigit():
                ut.extend(range(int(a), int(b) + 1))
                continue
        if bit.isdigit() and 1 <= int(bit) <= 6:
            ut.append(int(bit))
    return sorted({n for n in ut if 1 <= n <= 6})


def banner(logger: logging.Logger, opp: Oppsett, steg: Sequence[int]) -> None:
    logger.info("╔" + "═" * 72 + "╗")
    logger.info(_rammelinje(f" INNSIDEHANDEL PÅ OSLO BØRS  ·  versjon {VERSJON}"))
    logger.info("╚" + "═" * 72 + "╝")
    for n in sorted(STEGNAVN):
        merke = "✓" if n in steg else "·"
        logger.info(f"   {merke} {n}  {STEGNAVN[n]}")
    modus = ("offline (rører ikke nettet)" if opp.offline else
             "full henting (ser bort fra vannmerker)" if opp.full else
             "tilvekst (henter bare det som mangler)")
    logger.info(f"\n   Modus ........ {modus}")
    logger.info(f"   Mappe ........ {opp.base_dir}")
    logger.info(f"   Måler ........ {opp.avkastningstype()} mot {opp.referanse_ticker}")
    logger.info(f"   Stengetid .... {opp.stengetid}  "
                f"(melding etter dette handles først neste dag)")


def main(argv: Optional[List[str]] = None) -> int:
    from runtime_config import configure_console
    configure_console()
    argv = tal_minus(list(sys.argv[1:] if argv is None else argv))
    args = bygg_parser().parse_args(argv)
    opp = lag_oppsett(args)
    try:
        opp.lag_mapper()
    except OSError as e:
        print(f"❌ Fikk ikke laget datamappen {opp.base_dir} — {feiltekst(e)}")
        return 1
    logger = lag_logger(opp.logg_fil, feilsok=args.feilsok)

    if args.status:
        return status_paa_disk(opp, logger)

    steg = velg_steg(args)
    if not steg:
        logger.error("❌ Ingen gyldige steg valgt. Bruk --steg 1,2,3 eller --steg 1-6.")
        return 1
    banner(logger, opp, steg)

    handlinger: Dict[int, Callable[[], Dict[str, Any]]] = {
        1: lambda: steg1_nedlasting(opp, logger, kun=args.selskap or "",
                                    aksjeliste=args.aksjeliste or "",
                                    fersk_liste=bool(args.fersk_liste)),
        2: lambda: steg2_tekst(opp, logger, tving=bool(args.tving_tekst)),
        3: lambda: steg3_score(opp, logger),
        4: lambda: steg4_kurser(opp, logger, alle=bool(args.alle)),
        5: lambda: steg5_merge(opp, logger),
        6: lambda: steg6_backtest(opp, logger),
    }

    resultater: List[Stegresultat] = [
        Stegresultat(nr=n, navn=STEGNAVN[n],
                     status="OK" if n in steg else "IKKE_VALGT",
                     detaljer="" if n in steg else "kjørte ikke denne gangen")
        for n in sorted(STEGNAVN)]
    plass = {r.nr: i for i, r in enumerate(resultater)}
    start = time.time()
    avbrutt = False

    for n in steg:
        try:
            resultater[plass[n]] = kjor_steg(n, handlinger[n], logger)
        except KeyboardInterrupt:
            avbrutt = True
            resultater[plass[n]] = Stegresultat(
                nr=n, navn=STEGNAVN[n], status="AVBRUTT", detaljer="avbrutt med Ctrl+C")
            for m in steg:
                if m > n:
                    resultater[plass[m]] = Stegresultat(
                        nr=m, navn=STEGNAVN[m], status="IKKE_VALGT",
                        detaljer="rakk ikke å kjøre — kjøringen ble avbrutt")
            break
        if ((args.stopp_ved_feil and resultater[plass[n]].status == "FEIL")
                or (n in (1, 4, 5) and resultater[plass[n]].status != "OK")):
            logger.error(f"\n⏹️  --stopp-ved-feil: stanser etter steg {n}.")
            for m in steg:
                if m > n:
                    resultater[plass[m]] = Stegresultat(
                        nr=m, navn=STEGNAVN[m], status="IKKE_VALGT",
                        detaljer=f"stanset fordi steg {n} feilet")
            break

    skriv_statustavle(resultater, opp, logger, time.time() - start)

    # Send only a freshly completed backtest; incomplete downloads stop it.
    mail_failed = False
    if (opp.send_epost_ved_slutt and not avbrutt and 6 in steg
            and resultater[plass[6]].status == "OK"
            and not any(r.status in ("FEIL", "HOPPET", "AVBRUTT")
                        or (r.nr in (1, 4, 5) and r.status != "OK")
                        for r in resultater if r.nr in steg)):
        try:
            if epost_rapport(opp, resultater, logger, send=not args.mail_kladd) is None:
                mail_failed = True
        except Exception as exc:
            logger.error("Email failed: %s", exc)
            mail_failed = True

    kjørte = [r for r in resultater if r.nr in steg]
    if avbrutt:
        return 130
    if mail_failed:
        return 3
    if any(r.status in ("FEIL", "AVBRUTT") for r in kjørte):
        return 1
    if any(r.status in ("DELVIS", "HOPPET") for r in kjørte):
        return 2
    return 0


# ══════════════════════════════════════════════════════════════════════════
# INNGANG FOR ET SAMLESCRIPT
# ══════════════════════════════════════════════════════════════════════════
#
#     from innsidehandel_pipeline import steg1, steg2, steg3, steg4, steg5, steg6
#     steg1(); steg2(); steg3()
#
# Argumentene er de samme flaggene som på kommandolinjen, ett per flagg. Tom
# liste videre til main(), aldri None: ellers leser argparse sys.argv, altså
# flaggene til samlescriptet som kalte oss, og stopper på første ukjente.

def _kjor(nr: str, *argumenter: str) -> int:
    return main(["--steg", nr, *argumenter])


def steg1(*a: str) -> int:
    """Last ned artiklene fra Euronext."""
    return _kjor("1", *a)


def steg2(*a: str) -> int:
    """Trekk meldingsteksten ut av HTML-en."""
    return _kjor("2", *a)


def steg3(*a: str) -> int:
    """Les dato, hvem og hvor mye — og ranger på bullishness."""
    return _kjor("3", *a)


def steg4(*a: str) -> int:
    """Hent aksjekursene."""
    return _kjor("4", *a)


def steg5(*a: str) -> int:
    """Slå sammen score og kurs."""
    return _kjor("5", *a)


def steg6(*a: str) -> int:
    """Backtest."""
    return _kjor("6", *a)


def kjor_alt(*a: str) -> int:
    """Hele kjeden, alle seks steg."""
    return main(list(a))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n⏹️  Avbrutt.")
        sys.exit(130)
