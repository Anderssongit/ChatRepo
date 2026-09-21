"""Download the shared universe/prices and build the strategy input workbooks.

A successful reshape is not a successful download. Every result reports both
network provenance and usable coverage; cached data remain labelled as cached.
The NLP scrape itself belongs to SentimentManagement. Its article archive is
converted here only after that scrape, retaining history across separate runs.
"""
from __future__ import annotations

import math
import re
from copy import copy
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional, Sequence

TICKER_COLUMNS = ["Company", "Ticker", "ISIN", "Name", "Market"]
PRICE_COLUMNS = ["Date", "Company", "Ticker", "Close", "AdjClose", "Volume", "RawClose"]
STEP4_COLUMNS = ["Company", "Ticker", "Article_Date", "Article_Title", "Final_Score",
                 "Sentiment_Change", "Previous_Score", "Positive_Score",
                 "Neutral_Score", "Negative_Score", "Article_URL", "Report_Index"]
ALL_STEPS = ("tickers", "prices", "step4")
PLACEHOLDER_TITLE = "INGEN ARTIKLER"


def _text(value):
    text = "" if value is None else str(value).strip()
    return "" if text.lower() in {"nan", "nat", "none", "<na>"} else text


def _number(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def parse_date(value) -> Optional[date]:
    """Accept Excel dates and Euronext's English/Norwegian date strings."""
    text = _text(value)
    if not text:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = text.split("\n")[0].strip()
    numeric = re.match(r"^(\d{4})-(\d{2})-(\d{2})(?:$|[ T])", text)
    if numeric:
        try:
            return date(*(int(p) for p in numeric.groups()))
        except ValueError:
            return None
    # Avoid locale dependence: the scraper returns e.g. '18 Sep 2026'.
    months = {name: i for i, names in enumerate([
        ("jan", "january", "januar"), ("feb", "february", "februar"),
        ("mar", "march", "mars"), ("apr", "april"), ("may", "mai"),
        ("jun", "june", "juni"), ("jul", "july", "juli"),
        ("aug", "august"), ("sep", "sept", "september"),
        ("oct", "october", "okt", "oktober"), ("nov", "november"),
        ("dec", "december", "des", "desember")], 1) for name in names}
    match = re.match(r"^(\d{1,2})[ .-]+([A-Za-z]+)\.?[ -]+(\d{4})(?:$|\s)", text)
    if match and match[2].lower() in months:
        try:
            return date(int(match[3]), months[match[2].lower()], int(match[1]))
        except ValueError:
            return None
    for pattern in ("%d.%m.%Y", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(text.split()[0], pattern).date()
        except ValueError:
            pass
    return None


def bare_symbol(ticker):
    text = _text(ticker).upper()
    return text[:-3] if text.endswith(".OL") else text


def stamp(day=None):
    return f"{day or date.today():%y%m%d}"


def latest(folder, pattern):
    paths = [p for p in Path(folder).glob(pattern) if p.is_file()
             and not p.name.startswith("~$") and "BEFORE_FIX" not in p.name
             and ".tmp." not in p.name]
    return max(paths, key=lambda p: (p.stat().st_mtime_ns, p.name)) if paths else None


def needs_refresh(path, as_of, max_age_days):
    """File-age utility only; price freshness is checked from observations."""
    if path is None:
        return True, "missing"
    try:
        age = (as_of - datetime.fromtimestamp(Path(path).stat().st_mtime).date()).days
    except OSError:
        return True, "unreadable"
    return age < 0 or age > max_age_days, f"{age} days old"


def ticker_workbook_rows(companies):
    rows = {}
    for company in companies:
        symbol = bare_symbol(company.get("Symbol") or company.get("Ticker"))
        if not symbol or symbol.startswith("^"):
            continue
        rows[symbol] = {"Company": symbol, "Ticker": symbol + ".OL",
                        "ISIN": _text(company.get("ISIN")),
                        "Name": _text(company.get("Selskap")) or symbol,
                        "Market": _text(company.get("Marked"))}
    return [rows[key] for key in sorted(rows)]


def company_names(companies):
    return {r["Company"]: r["Name"] for r in ticker_workbook_rows(companies)}


def company_aliases(companies):
    aliases = {}
    ambiguous = set()
    for row in ticker_workbook_rows(companies):
        for name in (row["Company"], row["Ticker"], row["Name"]):
            key = name.casefold().strip()
            if key in aliases and aliases[key] != row["Company"]:
                ambiguous.add(key)
            aliases[key] = row["Company"]
    return {k: v for k, v in aliases.items() if k not in ambiguous}


def price_workbook_rows(series, names=None, *, start=None, as_of=None, wanted=None):
    """Company is the bare symbol used by BOTH ticker and NLP workbooks.

    The former adapter wrote a full company name here but symbols into NLP,
    leaving the consumer's substring matcher to guess identities. No guessing
    is necessary: the downloaded series already has an exact ticker.
    """
    rows = []
    for ticker, points in sorted(series.items()):
        symbol = bare_symbol(ticker)
        if not symbol or symbol.startswith(("^", "IDX_")):
            continue
        if wanted is not None and symbol not in wanted:
            continue
        for day, values in sorted(points.items()):
            day = parse_date(day)
            raw_close = _number(values.get("close"))
            close = _number(values.get("adjclose"))
            if (day is None or close is None or close <= 0
                    or (start and day < start) or (as_of and day >= as_of)):
                continue
            rows.append({"Date": day, "Company": symbol, "Ticker": symbol + ".OL",
                         "Close": close, "RawClose": raw_close, "AdjClose": close,
                         "Volume": _number(values.get("volum"))})
    return rows


def sentiment_change_rows(detail, *, tickers=None, as_of=None):
    """Difference from the previous published date's mean article score.

    Source dates have no reliable intraday ordering. Same-day articles use the
    same strictly earlier baseline, avoiding invented sequencing. A company's
    first publication date has zero change. Scores are on FinBERT's [-1, 1]
    scale (positive probability minus negative probability).
    """
    tickers = tickers or {}
    unique = {}
    for row in detail:
        company, title = _text(row.get("Company")), _text(row.get("Article_Title"))
        day, score = parse_date(row.get("Article_Date")), _number(row.get("Final_Score"))
        if (not company or not title or title.upper() == PLACEHOLDER_TITLE
                or day is None or score is None or not -1 <= score <= 1
                or (as_of and day > as_of)
                or ("Text_Length" in row and (_number(row["Text_Length"]) or 0) <= 0)):
            continue
        symbol = bare_symbol(tickers.get(company) or row.get("Ticker"))
        company = symbol or company
        key = (company, day, " ".join(title.casefold().split()))
        unique[key] = (row, score, symbol)
    grouped = {}
    for (company, day, title), item in unique.items():
        grouped.setdefault(company, {}).setdefault(day, []).append((title, item))
    out = []
    for company, days in sorted(grouped.items()):
        previous, index = None, 0
        for day, records in sorted(days.items()):
            for _, (row, score, symbol) in sorted(records):
                index += 1
                out.append({"Company": company, "Ticker": symbol + ".OL" if symbol else "",
                            "Article_Date": day, "Article_Title": _text(row.get("Article_Title")),
                            "Final_Score": round(score, 6),
                            "Sentiment_Change": round(score - previous, 6) if previous is not None else 0.0,
                            "Previous_Score": round(previous, 6) if previous is not None else None,
                            "Positive_Score": _number(row.get("Positive_Score")),
                            "Neutral_Score": _number(row.get("Neutral_Score")),
                            "Negative_Score": _number(row.get("Negative_Score")),
                            "Article_URL": _text(row.get("Article_URL")), "Report_Index": index})
            previous = sum(item[1][1] for item in records) / len(records)
    return sorted(out, key=lambda row: (row["Article_Date"], row["Company"], row["Article_Title"]))


def write_workbook(path, rows, columns, *, index=False):
    import pandas as pd
    if not rows:
        raise ValueError(f"Refusing to write empty input: {Path(path).name}")
    if len(rows) > 1_048_575:
        raise ValueError("Input exceeds Excel's single-sheet row limit; reduce history_years.")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.stem + ".tmp.xlsx")
    try:
        pd.DataFrame(rows, columns=list(columns)).to_excel(temporary, index=index, engine="openpyxl")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return path


def read_nlp_archive(nlp_dir):
    """Keep all archived reports; later files win duplicate article keys."""
    import pandas as pd
    paths = sorted((p for p in Path(nlp_dir).glob("NLP_Sentiment_Detail_*.xlsx")
                    if not p.name.startswith("~$") and ".tmp." not in p.name),
                   key=lambda p: (p.stat().st_mtime_ns, p.name))
    rows, readable, issues = [], [], []
    required = {"Company", "Article_Date", "Article_Title", "Final_Score"}
    for path in paths:
        try:
            frame = pd.read_excel(path)
            if not required.issubset(frame.columns):
                raise ValueError("missing columns: " + ", ".join(sorted(required - set(frame.columns))))
            rows.extend(frame.to_dict("records"))
            readable.append(path)
        except Exception as exc:
            issues.append(f"{path.name}: {type(exc).__name__}: {exc}")
    return rows, readable, issues


def read_nlp_detail(nlp_dir):
    rows, paths, _ = read_nlp_archive(nlp_dir)
    return rows, paths[-1] if paths else None


def _result(key, label, status, *, path=None, detail="", **metadata):
    row = {"source": key, "Kilde": label, "Fil": str(path or ""),
           "Handling": status, "Merknad": detail, "status": status,
           "network_attempted": False, "downloaded_count": 0, "cached_count": 0,
           "expected_count": 0, "usable_count": 0, "coverage_pct": 0.0,
           "latest_observation": None, "missing": [], "stale": [], "issues": []}
    row.update(metadata)
    row["downloaded_correctly"] = status == "DOWNLOADED" and not row["issues"]
    return row


def ensure_stock_list(opp, logger, *, download=True, force=False, as_of=None, with_status=False):
    import innsidehandel_pipeline as ip
    as_of = as_of or date.today()
    opp.lag_mapper()
    cached = ip.les_selskaper(opp)
    path, downloaded, attempted, issues = None, False, False, []
    if download and not opp.offline:
        attempted = True
        try:
            # sikre_aksjeliste() without a browser never makes a request.
            with ip.Nettleser(opp, logger) as browser:
                path = ip.last_ned_aksjeliste(opp, logger, browser)
            if path is not None:
                companies = ip.bygg_selskaper(opp, logger, str(path))
                downloaded = bool(companies)
            else:
                companies = []
            if not downloaded:
                issues.append("Euronext universe download returned no usable companies")
        except Exception as exc:
            companies = []
            issues.append(f"Euronext universe download: {type(exc).__name__}: {exc}")
    else:
        companies = []
    if not companies:
        companies = cached
    if not companies:
        try:
            path = ip.finn_aksjeliste(opp)
            companies = ip.bygg_selskaper(opp, logger, str(path)) if path else []
        except Exception as exc:
            issues.append(f"Cached universe: {type(exc).__name__}: {exc}")
    if not downloaded:
        path = Path(opp.selskapsliste) if companies else path
    observation = as_of if downloaded else (datetime.fromtimestamp(path.stat().st_mtime).date()
                                           if path and path.exists() else None)
    status = "DOWNLOADED" if downloaded else "CACHED" if companies else "FAILED"
    count = len(ticker_workbook_rows(companies))
    row = _result("tickers", "PB-ROE / shared universe", status, path=path,
                  detail=f"{count} companies; " + ("fresh Euronext download" if downloaded else "cached universe; no confirmed download"),
                  network_attempted=attempted, downloaded_count=count if downloaded else 0,
                  cached_count=0 if downloaded else count, expected_count=count,
                  usable_count=count, coverage_pct=100.0 if count else 0.0,
                  latest_observation=str(observation) if observation else None, issues=issues)
    return (companies, row) if with_status else companies


def ensure_prices(opp, logger, companies, *, download=True, force=False, with_status=False):
    import innsidehandel_pipeline as ip
    options = copy(opp)
    options.full = bool(force or opp.full)
    options.offline = bool(opp.offline or not download)
    result = {"status": "CACHED", "downloaded_count": 0, "cached_count": 0, "network_attempted": False}
    if not options.offline:
        result = ip.steg4_kurser(options, logger, alle=True)
    book = ip.Kursbok(opp.s4_dir).last()
    return (book, result) if with_status else book


def build_all(excel_dir: Path, opp, logger, *, as_of=None, max_age_days=5,
              force=False, history_years=6, steps: Sequence[str] = ALL_STEPS,
              download=True, source_status=None):
    """Initial call: steps=('tickers','prices'); after scrape: ('step4',).

    force=True forces a source refresh even if cached files were written today.
    Cached fallback remains usable for research, but never counts as downloaded.
    source_status is the article downloader's outcome from download_status.
    """
    unknown = set(steps) - set(ALL_STEPS)
    if unknown:
        raise ValueError(f"Unknown acquisition steps: {sorted(unknown)}")
    if not 1 <= history_years <= 30:
        raise ValueError("history_years must be between 1 and 30")
    as_of, excel_dir = as_of or date.today(), Path(excel_dir)
    start = date(as_of.year - history_years, as_of.month, 1)
    results = []

    def record(row):
        results.append(row)
        try:
            from download_status import record_source
            record_source(row["source"], status=row["status"], detail=row["Merknad"],
                          **{k: v for k, v in row.items() if k not in {"source", "status"}})
        except ImportError:
            pass

    try:
        companies, universe = ensure_stock_list(
            opp, logger, download=download and any(s in steps for s in ("tickers", "prices")),
            force=force, as_of=as_of, with_status=True)
    except Exception as exc:
        companies = []
        universe = _result("tickers", "PB-ROE / shared universe", "FAILED",
                           detail=f"{type(exc).__name__}: {exc}", issues=[str(exc)])
    wanted = {r["Company"] for r in ticker_workbook_rows(companies)}
    if "tickers" in steps:
        if companies:
            try:
                path = write_workbook(excel_dir / "Data_BT" / "AllTickers_OSEBX_TW_current.xlsx",
                                      ticker_workbook_rows(companies), TICKER_COLUMNS, index=True)
                universe["Fil"] = str(path)
            except Exception as exc:
                universe.update(status="FAILED", Handling="FAILED", downloaded_correctly=False)
                universe["issues"].append(f"Ticker workbook: {exc}")
        record(universe)

    if "prices" in steps:
        if not companies:
            record(_result("prices", "Shared stock prices", "FAILED", detail="No company universe available"))
        else:
            try:
                book, network = ensure_prices(opp, logger, companies, download=download,
                                               force=force, with_status=True)
                rows = price_workbook_rows(book.serier, start=start, as_of=as_of, wanted=wanted)
                tails = {}
                for row in rows:
                    tails[row["Company"]] = max(tails.get(row["Company"], date.min), row["Date"])
                missing = sorted(wanted - tails.keys())
                stale = sorted(t for t, day in tails.items() if (as_of - day).days > max_age_days)
                successful = int(network.get("downloaded_count", 0))
                issues = list(network.get("failed_tickers", []))
                if network.get("status") in {"FEIL", "DELVIS", "FAILED", "PARTIAL"}:
                    issues.append(network.get("detaljer", "Source download incomplete"))
                if missing:
                    issues.append(f"Missing prices: {', '.join(missing)}")
                if stale:
                    issues.append(f"Stale prices: {', '.join(stale)}")
                path = write_workbook(excel_dir / "Data_BT1" / "FinancialData" / f"Stock_Prices_{stamp(as_of)}.xlsx",
                                      rows, PRICE_COLUMNS) if rows else None
                status = ("FAILED" if not rows else "PARTIAL" if issues else
                          "DOWNLOADED" if successful else "CACHED")
                last = max(tails.values()) if tails else None
                record(_result("prices", "Shared stock prices", status, path=path,
                               detail=f"{len(tails)}/{len(wanted)} tickers; {successful} downloaded; "
                                      f"{len(stale)} stale; latest observation {last}",
                               network_attempted=bool(network.get("network_attempted", download and not opp.offline)),
                               downloaded_count=successful, cached_count=int(network.get("cached_count", 0)) if successful else len(tails),
                               expected_count=len(wanted), usable_count=len(tails) - len(stale),
                               coverage_pct=round(100 * (len(tails) - len(stale)) / len(wanted), 2),
                               latest_observation=str(last) if last else None,
                               earliest_observation=str(min(r["Date"] for r in rows)) if rows else None,
                               row_count=len(rows), missing=missing, stale=stale, issues=issues))
            except Exception as exc:
                record(_result("prices", "Shared stock prices", "FAILED", detail=f"{type(exc).__name__}: {exc}",
                               issues=[str(exc)], network_attempted=bool(download and not opp.offline)))

    if "step4" in steps:
        try:
            raw, files, issues = read_nlp_archive(excel_dir / "DataNLP")
            aliases = company_aliases(companies)
            ticker_map = {name: aliases[name.casefold()] for name in {_text(r.get("Company")) for r in raw}
                          if name.casefold() in aliases}
            rows = sentiment_change_rows(raw, tickers=ticker_map, as_of=as_of)
            unmapped = sorted({r["Company"] for r in rows if not r["Ticker"]})
            # Symbols absent from the current universe may be delisted. Keep the
            # archive but do not silently map them to another company's prices.
            if unmapped:
                issues.append("Unmapped article companies: " + ", ".join(unmapped))
            path = write_workbook(excel_dir / "DataNLP" / f"Step4_Sentiment_Changes_{as_of:%Y-%m-%d}.xlsx",
                                  rows, STEP4_COLUMNS) if rows else None
            last = max((r["Article_Date"] for r in rows), default=None)
            article_source = source_status or {}
            confirmed = article_source.get("status") == "DOWNLOADED"
            status = "FAILED" if not rows else "PARTIAL" if issues else "DERIVED" if confirmed else "CACHED"
            count = len({r["Ticker"] for r in rows if r["Ticker"]})
            record(_result("step4", "Sentiment changes", status, path=path,
                           detail=f"{len(rows)} articles from {len(files)} archives; latest article {last}; "
                                  + ("derived after confirmed article download" if confirmed else "derived from cache; no confirmed article download"),
                           expected_count=len(wanted), usable_count=count,
                           coverage_pct=round(100 * count / len(wanted), 2) if wanted else 0.0,
                           cached_count=len(rows) if not confirmed else 0, row_count=len(rows),
                           latest_observation=str(last) if last else None, issues=issues,
                           article_source_status=article_source.get("status", "UNKNOWN"),
                           source_files=[str(p) for p in files], missing=unmapped))
        except Exception as exc:
            record(_result("step4", "Sentiment changes", "FAILED", detail=f"{type(exc).__name__}: {exc}", issues=[str(exc)]))
    return results
