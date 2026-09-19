# -*- coding: utf-8 -*-
"""Produce the three upstream workbooks master.py used to only check for.

WHY THIS EXISTS
---------------
master.py verified that three files existed and aborted when they did not:

    Data_BT/AllTickers_OSEBX_TW_*.xlsx        -> PBROE_All3.load_tickers()
    Data_BT1/FinancialData/Stock_Prices_*.xlsx -> SentimentMomentumV31
    DataNLP/Step4_Sentiment_Changes_*.xlsx     -> SentimentMomentumV31

Nothing in the repository produced them. They came from a separate program the
README told you to keep running first, which is why Sentiment Momentum silently
ran on prices ending 2026-08-19: nobody had run that program since.

Every input needed to build all three is already downloaded by this package:

  * the Euronext equities list -> innsidehandel_pipeline.sikre_aksjeliste
  * daily prices               -> innsidehandel_pipeline.steg4_kurser (yfinance)
  * FinBERT article scores     -> SentimentManagement writes
                                  DataNLP/NLP_Sentiment_Detail_*.xlsx

So the three workbooks are reshapes of data the master run already has. This
module does that reshape, and master.py now calls it before the analyses.

The two hash-protected strategies are untouched: this writes the files they
read, in the schema they already expect.

STRUCTURE
---------
Row-building is pure Python and unit-tested. pandas and yfinance appear only
in the IO functions at the bottom.
"""
from __future__ import annotations

import math
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

# load_tickers() does df.drop(df.columns[0], axis=1) then reads df["Company"],
# so Company must survive the drop. Writing with index=True puts the unnamed
# index first, which is exactly the column that gets dropped.
TICKER_COLUMNS = ["Company", "Ticker", "ISIN", "Name", "Market"]

# DataLoader.load_all() requires Date, Close, Company and Ticker. The rest is
# carried through because it costs nothing and helps when reading by hand.
PRICE_COLUMNS = ["Date", "Company", "Ticker", "Close", "AdjClose", "Volume"]

# DataLoader reads Article_Date, Company, Article_Title, Sentiment_Change and
# Final_Score. SignalBuilder uses Sentiment_Change and Final_Score.
STEP4_COLUMNS = ["Company", "Ticker", "Article_Date", "Article_Title",
                 "Final_Score", "Sentiment_Change", "Previous_Score",
                 "Positive_Score", "Neutral_Score", "Negative_Score",
                 "Article_URL", "Report_Index"]

PLACEHOLDER_TITLE = "INGEN ARTIKLER"


# ---------------------------------------------------------------------------
# Pure helpers
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
    """Accept the several date shapes the scraped article rows arrive in."""
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
    """EQNR.OL -> EQNR. TradingView is addressed as OSL-<bare symbol>."""
    return _text(ticker).upper().replace(".OL", "").strip()


def stamp(day: Optional[date] = None) -> str:
    return f"{day or date.today():%y%m%d}"


# ---------------------------------------------------------------------------
# Row builders - pure, unit-tested
# ---------------------------------------------------------------------------

def ticker_workbook_rows(companies: Iterable[Dict[str, object]]) -> List[Dict[str, object]]:
    """Rows for AllTickers_OSEBX_TW_*.xlsx from the pipeline's selskaper.csv.

    `Company` holds the bare symbol because PBROE builds
    https://www.tradingview.com/symbols/OSL-<Company>/ from it.
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
    """Long-format price rows for Stock_Prices_*.xlsx.

    `names` maps bare symbol -> company name so the Company column matches the
    names in Step4; DataLoader._map_tickers joins the two files on it.
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
    """Turn per-article FinBERT scores into Step4 change rows.

    Sentiment_Change is the move from the company's PREVIOUS article to this
    one, which is what the strategy trades: "kjoper pa endringen fra forrige
    rapport". The first article for a company has no predecessor, so its change
    is 0.0 and it cannot generate a signal on its own.

    Placeholder rows written when a company had no articles are dropped.
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

    # Stable chronological order per company; ties keep input order.
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
    """Whether an existing workbook is too old to rely on."""
    if path is None:
        return True, "missing"
    try:
        written = datetime.fromtimestamp(Path(path).stat().st_mtime).date()
    except OSError:
        return True, "unreadable"
    age = (as_of - written).days
    if age > max_age_days:
        return True, f"{age} days old (limit {max_age_days})"
    return False, f"{age} days old"


def latest(folder: Path, pattern: str) -> Optional[Path]:
    paths = [p for p in Path(folder).glob(pattern)
             if not p.name.startswith("~$") and "BEFORE_FIX" not in p.name]
    return max(paths, key=lambda p: (p.stat().st_mtime_ns, p.name)) if paths else None


# ---------------------------------------------------------------------------
# IO layer - pandas / yfinance / the insider pipeline
# ---------------------------------------------------------------------------

def write_workbook(path: Path, rows: Sequence[Dict[str, object]],
                   columns: Sequence[str], *, index: bool = False) -> Path:
    """Write atomically: a half-written workbook must never look like input."""
    import pandas as pd

    if not rows:
        raise ValueError(f"Refusing to write an empty workbook: {path.name}")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows, columns=list(columns))
    temporary = path.with_name(path.name + ".tmp")
    frame.to_excel(temporary, index=index)
    temporary.replace(path)
    return path


def read_nlp_detail(nlp_dir: Path) -> Tuple[List[Dict[str, object]], Optional[Path]]:
    """Newest NLP_Sentiment_Detail_*.xlsx, as plain dict rows."""
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


def ensure_stock_list(opp, logger) -> List[Dict[str, object]]:
    """Download the Euronext equities list if needed and return the companies."""
    import innsidehandel_pipeline as ip

    companies = ip.les_selskaper(opp)
    if companies:
        return companies
    ip.sikre_aksjeliste(opp, logger)
    return ip.bygg_selskaper(opp, logger)


def ensure_prices(opp, logger, companies: Sequence[Dict[str, object]]):
    """Make sure the pipeline's price book covers every listed company."""
    import innsidehandel_pipeline as ip

    book = ip.Kursbok(opp.s4_dir).last()
    wanted = {bare_symbol(c.get("Symbol") or c.get("Ticker") or "") for c in companies}
    wanted.discard("")
    have = {bare_symbol(t) for t in book.serier}
    if not wanted - have:
        return book
    logger.info("Kurser: henter %d tickere som mangler i kursboka.", len(wanted - have))
    ip.steg4_kurser(opp, logger, alle=True)
    return ip.Kursbok(opp.s4_dir).last()


ALL_STEPS = ("tickers", "prices", "step4")


def build_all(excel_dir: Path, opp, logger, *, as_of: Optional[date] = None,
              max_age_days: int = 5, force: bool = False,
              history_years: int = 6,
              steps: Sequence[str] = ALL_STEPS) -> List[Dict[str, object]]:
    """Build the requested upstream workbooks. Returns one status row each.

    `steps` exists because Step4 depends on the FinBERT article scrape, which
    runs inside the analysis stage. master.py therefore builds tickers and
    prices before the analyses and step4 immediately after the scrape.
    """
    unknown = [s for s in steps if s not in ALL_STEPS]
    if unknown:
        raise ValueError(f"Unknown acquisition step(s): {', '.join(unknown)}")
    excel_dir = Path(excel_dir)
    as_of = as_of or date.today()
    start = date(as_of.year - history_years, as_of.month, 1)
    results: List[Dict[str, object]] = []

    def record(name, path, action, detail=""):
        results.append({"Kilde": name, "Fil": "" if path is None else str(path),
                        "Handling": action, "Merknad": detail})

    companies = ensure_stock_list(opp, logger)
    if not companies:
        record("Aksjeliste", None, "FEIL", "Euronext equities list unavailable")
        return results
    record("Aksjeliste", opp.selskapsliste, "OK", f"{len(companies)} selskaper")

    # 1. Ticker workbook for PB-ROE.
    if "tickers" in steps:
        folder = excel_dir / "Data_BT"
        existing = latest(folder, "AllTickers_OSEBX_TW_*.xlsx")
        refresh, why = needs_refresh(existing, as_of, max_age_days)
        if force or refresh:
            rows = ticker_workbook_rows(companies)
            path = write_workbook(folder / f"AllTickers_OSEBX_TW_{stamp(as_of)}.xlsx",
                                  rows, TICKER_COLUMNS, index=True)
            record("PB-ROE tickerliste", path, "SKREVET", f"{len(rows)} tickere ({why})")
        else:
            record("PB-ROE tickerliste", existing, "GJENBRUKT", why)

    # 2. Price workbook for Sentiment Momentum.
    if "prices" in steps:
        folder = excel_dir / "Data_BT1" / "FinancialData"
        existing = latest(folder, "Stock_Prices_*.xlsx")
        refresh, why = needs_refresh(existing, as_of, max_age_days)
        if force or refresh:
            book = ensure_prices(opp, logger, companies)
            rows = price_workbook_rows(book.serier, company_names(companies), start=start)
            if not rows:
                record("Kursdata", None, "FEIL", "price book produced no usable rows")
            else:
                path = write_workbook(folder / f"Stock_Prices_{stamp(as_of)}.xlsx",
                                      rows, PRICE_COLUMNS)
                last = max(r["Date"] for r in rows)
                record("Kursdata", path, "SKREVET",
                       f"{len(rows)} rader, siste kurs {last} ({why})")
        else:
            record("Kursdata", existing, "GJENBRUKT", why)

    # 3. Step4 sentiment changes, from the FinBERT scores already on disk.
    if "step4" not in steps:
        return results
    folder = excel_dir / "DataNLP"
    existing = latest(folder, "Step4_Sentiment_Changes_*.xlsx")
    refresh, why = needs_refresh(existing, as_of, max_age_days)
    if force or refresh:
        detail, source = read_nlp_detail(folder)
        if not detail:
            record("Sentimentendringer", existing, "HOPPET",
                   "no NLP_Sentiment_Detail_*.xlsx in DataNLP; run the article "
                   "scrape first (master does this unless --ingen-nlp-hent)")
        else:
            tickers = {name: symbol for symbol, name in company_names(companies).items()}
            rows = sentiment_change_rows(detail, tickers=tickers)
            if not rows:
                record("Sentimentendringer", existing, "FEIL",
                       f"{source.name if source else '?'} held no scorable articles")
            else:
                path = write_workbook(
                    folder / f"Step4_Sentiment_Changes_{as_of:%Y-%m-%d}.xlsx",
                    rows, STEP4_COLUMNS)
                last = max(r["Article_Date"] for r in rows)
                record("Sentimentendringer", path, "SKREVET",
                       f"{len(rows)} artikler fra {source.name if source else '?'}, "
                       f"siste {last} ({why})")
    else:
        record("Sentimentendringer", existing, "GJENBRUKT", why)
    return results
