# -*- coding: utf-8 -*-
"""Bygg grunnlagsfilene masteren tidligere bare KONTROLLERTE at fantes.

HVORFOR DENNE FINNES
--------------------
master.py sjekket at tre filer lå der, og avbrøt hvis de ikke gjorde det.
Ingenting i repoet lagde dem:

    Data_BT/AllTickers_OSEBX_TW_260428.xlsx     -> PBROE_All3.load_tickers()
                                                   SentimentManagement
    Data_BT1/FinancialData/Stock_Prices_*.xlsx  -> SentimentMomentumV31
    DataNLP/Step4_Sentiment_Changes_*.xlsx      -> SentimentMomentumV31

Alt som trengs for å bygge dem lastes allerede ned av denne pakken:

  * Euronext-aksjelista  -> innsidehandel_pipeline.sikre_aksjeliste
  * daglige kurser       -> innsidehandel_pipeline.steg4_kurser (yfinance)
  * FinBERT-artikkelscore -> SentimentManagement skriver
                             DataNLP/NLP_Sentiment_Detail_*.xlsx

De tre filene er altså omforminger av data masterkjøringen allerede har.

TO RETTELSER MOT 2026-09-18-UTGAVEN
-----------------------------------
1. **Tickerfila må hete nøyaktig `AllTickers_OSEBX_TW_260428.xlsx`.**
   `PBROE_All3` leser en *fast* sti (linje 278 i Only_260820.py), ikke et
   glob-mønster, og `SentimentManagement` gjør det samme fire steder.
   2026-09-18-utgaven skrev `AllTickers_OSEBX_TW_<dagens dato>.xlsx`. Den fila
   leses aldri av noen. PB-ROE ville fortsatt ha lest aprilfila — eller stoppet.
   Begge funksjonene er hash-beskyttet og kan ikke endres, så fila må bære
   navnet de spør etter. En datert kopi skrives ved siden av for sporbarhet.

2. **En dårligere fil får aldri overskrive en god.** Halvveis nedlasting ga før
   en tynn kursfil som så fersk ut. Nå sammenlignes den nye fila med den som
   ligger der; er den vesentlig tynnere eller slutter tidligere, beholdes den
   gamle og statusraden sier DEGRADERT. Da blir strategien utelatt på alder,
   som er riktig utfall — i stedet for å backteste på en fil med 10 % av
   tickerne uten at noen ser det.

De hash-beskyttede strategiene røres ikke: dette skriver filene de leser, i
formatet de allerede forventer.

STRUKTUR
--------
Radbygging er ren Python og enhetstestet. pandas og yfinance finnes bare i
IO-laget nederst.
"""
from __future__ import annotations

import math
import re
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

# load_tickers() gjør df.drop(df.columns[0], axis=1) og leser så df["Company"],
# så Company må overleve droppet. index=True legger den navnløse indeksen
# først, og det er nøyaktig kolonnen som droppes.
TICKER_COLUMNS = ["Company", "Ticker", "ISIN", "Name", "Market"]

# Navnet PBROE_All3 og SentimentManagement leser. Det er ikke en dato, det er
# en nøkkel: fire faste strenger i hash-beskyttet kode peker hit.
TICKER_FILENAME = "AllTickers_OSEBX_TW_260428.xlsx"

# DataLoader.load_all() krever Date, Close, Company og Ticker. Resten bæres med
# fordi det er gratis og gjør fila lesbar for hånd.
PRICE_COLUMNS = ["Date", "Company", "Ticker", "Close", "AdjClose", "Volume"]

# DataLoader leser Article_Date, Company, Article_Title, Sentiment_Change og
# Final_Score. SignalBuilder bruker Sentiment_Change og Final_Score.
STEP4_COLUMNS = ["Company", "Ticker", "Article_Date", "Article_Title",
                 "Final_Score", "Sentiment_Change", "Previous_Score",
                 "Positive_Score", "Neutral_Score", "Negative_Score",
                 "Article_URL", "Report_Index"]

PLACEHOLDER_TITLE = "INGEN ARTIKLER"

# Hvor mye tynnere en ny fil får være før den regnes som et halvferdig
# nedlastingsresultat i stedet for en oppdatering.
MIN_KEEP_RATIO = 0.80

# Kurshistorikken pipelinen selv henter er historikk_ar + kurs_ekstra_ar = 11 år.
DEFAULT_HISTORY_YEARS = 10


# ---------------------------------------------------------------------------
# Rene hjelpere
# ---------------------------------------------------------------------------

def _text(value) -> str:
    return "" if value is None else str(value).strip()


def _number(value) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def parse_date(value) -> Optional[date]:
    """Godta de flere datoformene de skrapede artikkelradene kommer i."""
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    text = text.split("T")[0].split(" ")[0]
    for pattern in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    match = re.match(r"(\d{4})-(\d{2})-(\d{2})", text)
    if match:
        try:
            return date(*(int(g) for g in match.groups()))
        except ValueError:
            return None
    return None


def bare_symbol(ticker: str) -> str:
    """EQNR.OL -> EQNR. TradingView adresseres som OSL-<bart symbol>."""
    return _text(ticker).upper().replace(".OL", "").strip()


def stamp(day: Optional[date] = None) -> str:
    return f"{day or date.today():%y%m%d}"


def retry(handling, *, forsok: int = 3, pause: float = 2.0, logger=None,
          navn: str = "", sov=time.sleep):
    """Kjør `handling` med eksponentiell pause. Siste feil kastes videre.

    Nedlasting mot Euronext og Yahoo feiler forbigående. Ett forsøk er ikke
    robust; uendelig mange skjuler at kilden faktisk er nede.
    """
    siste = None
    for nummer in range(1, max(1, forsok) + 1):
        try:
            return handling()
        except KeyboardInterrupt:
            raise
        except Exception as exc:                       # noqa: BLE001
            siste = exc
            if nummer >= forsok:
                break
            if logger is not None:
                logger.warning("   ⚠️  %s feilet (forsøk %d/%d): %s — prøver igjen om %.0f s",
                               navn or "Nedlasting", nummer, forsok, exc, pause)
            sov(pause)
            pause *= 2
    raise siste


# ---------------------------------------------------------------------------
# Radbyggere - rene, enhetstestet
# ---------------------------------------------------------------------------

def ticker_workbook_rows(companies: Iterable[Dict[str, object]]) -> List[Dict[str, object]]:
    """Rader til AllTickers_OSEBX_TW_260428.xlsx fra pipelinens selskapsliste.

    `Company` holder det bare symbolet, fordi PBROE bygger
    https://www.tradingview.com/symbols/OSL-<Company>/ av det.
    """
    rows, seen = [], set()
    for company in companies:
        symbol = bare_symbol(company.get("Symbol") or company.get("Ticker") or "")
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        rows.append({"Company": symbol,
                     "Ticker": symbol + ".OL",
                     "ISIN": _text(company.get("ISIN")),
                     "Name": _text(company.get("Selskap")) or symbol,
                     "Market": _text(company.get("Marked"))})
    return sorted(rows, key=lambda r: r["Company"])


def price_workbook_rows(series: Dict[str, Dict[date, Dict[str, Optional[float]]]],
                        names: Optional[Dict[str, str]] = None,
                        *, start: Optional[date] = None) -> List[Dict[str, object]]:
    """Langform kursrader til Stock_Prices_*.xlsx.

    `names` kobler bart symbol -> selskapsnavn så Company matcher navnene i
    Step4; DataLoader._map_tickers skjøter de to filene på nettopp det feltet.
    """
    names = names or {}
    rows: List[Dict[str, object]] = []
    for raw_ticker, points in sorted(series.items()):
        symbol = bare_symbol(raw_ticker)
        if not symbol or raw_ticker.startswith("^") or raw_ticker.startswith("IDX_"):
            continue
        company = names.get(symbol) or symbol
        for day, values in sorted(points.items()):
            if start is not None and day < start:
                continue
            close = _number(values.get("close"))
            if close is None or close <= 0:
                continue
            rows.append({"Date": day, "Company": company, "Ticker": symbol + ".OL",
                         "Close": close, "AdjClose": _number(values.get("adjclose")),
                         "Volume": _number(values.get("volum"))})
    return rows


def sentiment_change_rows(detail: Iterable[Dict[str, object]],
                          *, tickers: Optional[Dict[str, str]] = None
                          ) -> List[Dict[str, object]]:
    """Gjør FinBERT-score per artikkel om til Step4-endringsrader.

    Sentiment_Change er bevegelsen fra selskapets FORRIGE artikkel til denne,
    som er det strategien handler på: «kjøper på endringen fra forrige rapport».
    Første artikkel for et selskap har ingen forgjenger, får 0,0 og kan ikke
    utløse et signal alene.

    Plassholderrader skrevet for selskaper uten artikler forkastes.
    """
    tickers = tickers or {}
    cleaned: List[Tuple[date, str, Dict[str, object]]] = []
    for row in detail:
        company = _text(row.get("Company"))
        title = _text(row.get("Article_Title"))
        day = parse_date(row.get("Article_Date"))
        score = _number(row.get("Final_Score"))
        if not company or day is None or score is None:
            continue
        if title.upper() == PLACEHOLDER_TITLE:
            continue
        cleaned.append((day, company, row))

    # Stabil kronologisk rekkefølge per selskap; likhet beholder inndata-orden.
    cleaned.sort(key=lambda item: (item[1], item[0]))

    out: List[Dict[str, object]] = []
    previous_company, previous_score, index = None, None, 0
    for day, company, row in cleaned:
        score = float(_number(row.get("Final_Score")))
        if company != previous_company:
            previous_company, previous_score, index = company, None, 0
        index += 1
        change = 0.0 if previous_score is None else score - previous_score
        symbol = bare_symbol(tickers.get(company, "") or "")
        out.append({
            "Company": company,
            "Ticker": (symbol + ".OL") if symbol else "",
            "Article_Date": day,
            "Article_Title": _text(row.get("Article_Title")),
            "Final_Score": round(score, 6),
            "Sentiment_Change": round(change, 6),
            "Previous_Score": None if previous_score is None else round(previous_score, 6),
            "Positive_Score": _number(row.get("Positive_Score")),
            "Neutral_Score": _number(row.get("Neutral_Score")),
            "Negative_Score": _number(row.get("Negative_Score")),
            "Article_URL": _text(row.get("Article_URL")),
            "Report_Index": index,
        })
        previous_score = score
    out.sort(key=lambda r: (r["Article_Date"], r["Company"]))
    return out


def needs_refresh(path: Optional[Path], as_of: date, max_age_days: int) -> Tuple[bool, str]:
    """Om en eksisterende arbeidsbok er for gammel til å stole på."""
    if path is None:
        return True, "mangler"
    try:
        written = datetime.fromtimestamp(Path(path).stat().st_mtime).date()
    except OSError:
        return True, "uleselig"
    age = (as_of - written).days
    if age > max_age_days:
        return True, f"{age} dager gammel (grense {max_age_days})"
    return False, f"{age} dager gammel"


def latest(folder: Path, pattern: str) -> Optional[Path]:
    paths = [p for p in Path(folder).glob(pattern)
             if not p.name.startswith("~$") and "BEFORE_FIX" not in p.name]
    return max(paths, key=lambda p: (p.stat().st_mtime_ns, p.name)) if paths else None


def replacement_is_safe(new_rows: int, new_last: Optional[date],
                        old_rows: Optional[int], old_last: Optional[date],
                        *, min_ratio: float = MIN_KEEP_RATIO) -> Tuple[bool, str]:
    """Skal den nye fila få erstatte den gamle?

    Nei hvis den er vesentlig tynnere eller slutter tidligere: det er en
    halvferdig nedlasting, ikke en oppdatering. Å beholde den gamle gjør
    strategien foreldet, og foreldet er synlig. En tynn fil er det ikke.
    """
    if new_rows <= 0:
        return False, "den nye fila er tom"
    if old_rows is None:
        return True, "ingen tidligere fil"
    if old_rows > 0 and new_rows < old_rows * min_ratio:
        return False, (f"{new_rows} rader mot {old_rows} tidligere "
                       f"(under {min_ratio:.0%}) — ser ut som en halvferdig nedlasting")
    if new_last is not None and old_last is not None and new_last < old_last:
        return False, (f"slutter {new_last}, tidligere fil slutter {old_last} "
                       "— den nye dekker mindre historikk")
    return True, "ny fil er minst like komplett"


# ---------------------------------------------------------------------------
# IO-lag - pandas / yfinance / innsidepipelinen
# ---------------------------------------------------------------------------

def write_workbook(path: Path, rows: Sequence[Dict[str, object]],
                   columns: Sequence[str], *, index: bool = False) -> Path:
    """Skriv atomisk: en halvskrevet arbeidsbok må aldri se ut som inndata."""
    import pandas as pd

    if not rows:
        raise ValueError(f"Nekter å skrive en tom arbeidsbok: {path.name}")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows, columns=list(columns))
    temporary = path.with_name(path.name + ".tmp")
    frame.to_excel(temporary, index=index)
    temporary.replace(path)
    return path


def workbook_shape(path: Optional[Path], date_column: str) -> Tuple[Optional[int], Optional[date]]:
    """(antall rader, siste dato) for en eksisterende arbeidsbok, eller (None, None)."""
    if path is None or not Path(path).is_file():
        return None, None
    try:
        import pandas as pd
        frame = pd.read_excel(path)
        rows = int(len(frame))
        if date_column and date_column in frame.columns:
            days = [parse_date(v) for v in frame[date_column].tolist()]
            days = [d for d in days if d is not None]
            return rows, (max(days) if days else None)
        return rows, None
    except Exception:                                  # noqa: BLE001
        # En uleselig fil er ikke et vern verdt å beholde.
        return None, None


def read_nlp_detail(nlp_dir: Path) -> Tuple[List[Dict[str, object]], Optional[Path]]:
    """Nyeste NLP_Sentiment_Detail_*.xlsx, som rene dict-rader."""
    import pandas as pd

    path = latest(Path(nlp_dir), "NLP_Sentiment_Detail_*.xlsx")
    if path is None:
        return [], None
    frame = pd.read_excel(path)
    return frame.to_dict("records"), path


def company_names(companies: Iterable[Dict[str, object]]) -> Dict[str, str]:
    return {bare_symbol(c.get("Symbol") or c.get("Ticker") or ""):
            _text(c.get("Selskap")) or bare_symbol(c.get("Symbol") or "")
            for c in companies if bare_symbol(c.get("Symbol") or c.get("Ticker") or "")}


def ensure_stock_list(opp, logger, *, forsok: int = 3) -> List[Dict[str, object]]:
    """Last ned Euronext-aksjelista om nødvendig og returner selskapene."""
    import innsidehandel_pipeline as ip

    companies = ip.les_selskaper(opp)
    if companies:
        return companies

    def hent():
        ip.sikre_aksjeliste(opp, logger)
        funnet = ip.bygg_selskaper(opp, logger)
        if not funnet:
            raise RuntimeError("Euronext-lista kom tom tilbake")
        return funnet

    return retry(hent, forsok=forsok, logger=logger, navn="Euronext-aksjelista")


def ensure_prices(opp, logger, companies: Sequence[Dict[str, object]], *, forsok: int = 3):
    """Se til at pipelinens kursbok dekker hvert notert selskap."""
    import innsidehandel_pipeline as ip

    book = ip.Kursbok(opp.s4_dir).last()
    wanted = {bare_symbol(c.get("Symbol") or c.get("Ticker") or "") for c in companies}
    wanted.discard("")
    have = {bare_symbol(t) for t in book.serier}
    if not wanted - have:
        return book
    logger.info("   Kurser: henter %d tickere som mangler i kursboka.", len(wanted - have))
    retry(lambda: ip.steg4_kurser(opp, logger, alle=True),
          forsok=forsok, logger=logger, navn="Kursnedlasting")
    return ip.Kursbok(opp.s4_dir).last()


ALL_STEPS = ("tickers", "prices", "step4")


def build_all(excel_dir: Path, opp, logger, *, as_of: Optional[date] = None,
              max_age_days: int = 5, force: bool = False,
              history_years: int = DEFAULT_HISTORY_YEARS,
              forsok: int = 3,
              steps: Sequence[str] = ALL_STEPS) -> List[Dict[str, object]]:
    """Bygg de etterspurte grunnlagsfilene. Én statusrad per kilde.

    `steps` finnes fordi Step4 avhenger av FinBERT-skrapingen, som kjører inne i
    analysesteget. master.py bygger derfor tickerliste og kurser før analysene,
    og step4 rett etter skrapingen.

    Statusradene bærer Handling (SKREVET / GJENBRUKT / DEGRADERT / HOPPET /
    FEIL), radantall og siste dato, slik at datastatusblokken i mailen kan si
    om hver strategi faktisk fikk ferske data.
    """
    unknown = [s for s in steps if s not in ALL_STEPS]
    if unknown:
        raise ValueError(f"Ukjent hentesteg: {', '.join(unknown)}")
    excel_dir = Path(excel_dir)
    as_of = as_of or date.today()
    start = date(as_of.year - history_years, as_of.month, 1)
    results: List[Dict[str, object]] = []

    def record(name, path, action, detail="", *, rows=None, last=None):
        results.append({"Kilde": name, "Fil": "" if path is None else str(path),
                        "Handling": action, "Merknad": detail,
                        "Rader": rows, "Siste": None if last is None else str(last)})

    try:
        companies = ensure_stock_list(opp, logger, forsok=forsok)
    except Exception as exc:                           # noqa: BLE001
        companies = []
        record("Aksjeliste", None, "FEIL", f"Euronext-lista utilgjengelig: {exc}")
    if not companies:
        if not results:
            record("Aksjeliste", None, "FEIL", "Euronext-lista utilgjengelig")
        return results
    record("Aksjeliste", opp.selskapsliste, "OK", f"{len(companies)} selskaper",
           rows=len(companies))

    # 1. Tickerarbeidsboka til PB-ROE og SentimentManagement.
    #    Fast filnavn: de leser en konstant sti, ikke et mønster.
    if "tickers" in steps:
        folder = excel_dir / "Data_BT"
        fast = folder / TICKER_FILENAME
        refresh, why = needs_refresh(fast if fast.is_file() else None, as_of, 90)
        if force or refresh:
            rows = ticker_workbook_rows(companies)
            old_rows, _ = workbook_shape(fast if fast.is_file() else None, "")
            safe, hvorfor = replacement_is_safe(len(rows), None, old_rows, None)
            if not safe:
                record("PB-ROE tickerliste", fast, "DEGRADERT",
                       f"beholdt eksisterende fil: {hvorfor}", rows=old_rows)
            else:
                write_workbook(fast, rows, TICKER_COLUMNS, index=True)
                # Datert kopi ved siden av, bare for sporbarhet. Ingen leser den.
                try:
                    write_workbook(folder / f"AllTickers_OSEBX_TW_{stamp(as_of)}.xlsx",
                                   rows, TICKER_COLUMNS, index=True)
                except Exception as exc:               # noqa: BLE001
                    logger.debug("Datert tickerkopi ikke skrevet: %s", exc)
                record("PB-ROE tickerliste", fast, "SKREVET",
                       f"{len(rows)} tickere ({why}); skrevet som {TICKER_FILENAME}, "
                       "navnet PBROE_All3 og SentimentManagement leser", rows=len(rows))
        else:
            old_rows, _ = workbook_shape(fast, "")
            record("PB-ROE tickerliste", fast, "GJENBRUKT", why, rows=old_rows)

    # 2. Kursarbeidsboka til Sentiment Momentum.
    if "prices" in steps:
        folder = excel_dir / "Data_BT1" / "FinancialData"
        existing = latest(folder, "Stock_Prices_*.xlsx")
        refresh, why = needs_refresh(existing, as_of, max_age_days)
        if force or refresh:
            try:
                book = ensure_prices(opp, logger, companies, forsok=forsok)
                rows = price_workbook_rows(book.serier, company_names(companies), start=start)
            except Exception as exc:                   # noqa: BLE001
                rows = []
                logger.warning("   ⚠️  Kursnedlasting feilet: %s", exc)
                record("Kursdata", existing, "FEIL", f"nedlasting feilet: {exc}")
            if rows:
                new_last = max(r["Date"] for r in rows)
                old_rows, old_last = workbook_shape(existing, "Date")
                safe, hvorfor = replacement_is_safe(len(rows), new_last, old_rows, old_last)
                if not safe:
                    record("Kursdata", existing, "DEGRADERT",
                           f"beholdt eksisterende fil: {hvorfor}",
                           rows=old_rows, last=old_last)
                else:
                    path = write_workbook(folder / f"Stock_Prices_{stamp(as_of)}.xlsx",
                                          rows, PRICE_COLUMNS)
                    record("Kursdata", path, "SKREVET",
                           f"{len(rows)} rader, siste kurs {new_last} ({why})",
                           rows=len(rows), last=new_last)
            elif not any(r["Kilde"] == "Kursdata" for r in results):
                record("Kursdata", existing, "FEIL", "kursboka ga ingen brukbare rader")
        else:
            old_rows, old_last = workbook_shape(existing, "Date")
            record("Kursdata", existing, "GJENBRUKT", why, rows=old_rows, last=old_last)

    # 3. Step4-sentimentendringer, fra FinBERT-scorene som allerede ligger der.
    if "step4" not in steps:
        return results
    folder = excel_dir / "DataNLP"
    existing = latest(folder, "Step4_Sentiment_Changes_*.xlsx")
    refresh, why = needs_refresh(existing, as_of, max_age_days)
    if force or refresh:
        try:
            detail, source = read_nlp_detail(folder)
        except Exception as exc:                       # noqa: BLE001
            detail, source = [], None
            logger.warning("   ⚠️  Kunne ikke lese NLP_Sentiment_Detail: %s", exc)
        if not detail:
            record("Sentimentendringer", existing, "HOPPET",
                   "ingen NLP_Sentiment_Detail_*.xlsx i DataNLP; kjør "
                   "artikkelskrapingen først (masteren gjør det uten --ingen-nlp-hent)")
        else:
            tickers = {name: symbol for symbol, name in company_names(companies).items()}
            rows = sentiment_change_rows(detail, tickers=tickers)
            if not rows:
                record("Sentimentendringer", existing, "FEIL",
                       f"{source.name if source else '?'} hadde ingen scorebare artikler")
            else:
                new_last = max(r["Article_Date"] for r in rows)
                old_rows, old_last = workbook_shape(existing, "Article_Date")
                safe, hvorfor = replacement_is_safe(len(rows), new_last, old_rows, old_last)
                if not safe:
                    record("Sentimentendringer", existing, "DEGRADERT",
                           f"beholdt eksisterende fil: {hvorfor}",
                           rows=old_rows, last=old_last)
                else:
                    path = write_workbook(
                        folder / f"Step4_Sentiment_Changes_{as_of:%Y-%m-%d}.xlsx",
                        rows, STEP4_COLUMNS)
                    record("Sentimentendringer", path, "SKREVET",
                           f"{len(rows)} artikler fra {source.name if source else '?'}, "
                           f"siste {new_last} ({why})", rows=len(rows), last=new_last)
    else:
        old_rows, old_last = workbook_shape(existing, "Article_Date")
        record("Sentimentendringer", existing, "GJENBRUKT", why,
               rows=old_rows, last=old_last)
    return results
