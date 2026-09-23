# -*- coding: utf-8 -*-
"""
MANAGEMENT SENTIMENT - PRICE DOWNLOAD, STEP BY STEP

This is the part of SentimentHendelseLab() in Only_260820.py that stopped the
2026-09-23 run: reading the article list, downloading prices from Yahoo and
checking them. The download settings and the 4x price check are the lab's own.
What is new:

  * Every step prints OK, WARN or FAILED to the console. A failure names the
    function and the line it failed on, the error, and what to do about it.
  * One bad company no longer stops all the others. An exact x10/x100/x1000
    jump is a unit error from the data provider and is rescaled. Any other
    jump of 4x or more excludes that company, and price_issues.csv says why.
    --strict gives the lab's behaviour: any unresolved jump stops the run.
  * You can run 5 companies (any number, or named ones) instead of all.

USAGE
    python management_download.py            the COMPANIES setting below
    python management_download.py 5          the first 5 in the article list
    python management_download.py all        every company, as the lab does
    python management_download.py BSP EAM    named companies from the same list
                                             (write 2020.OL for 2020 Bulkers,
                                             since a bare 2020 is a count)

    --excel-dir PATH     ExcelData folder. Without it the script looks in
                         AKSJE_BASE_DIR, ExcelData next to the script and
                         the Desktop ExcelData (LEGACY_EXCEL_DIR), and uses
                         the first one that actually has the data.
    --start DATE         first price date, default 2019-01-01 as in the lab
    --strict             stop at any unresolved price jump, as the lab does
    --accept T1,T2       tickers whose jumps you have checked and accept
    --batch-size N       tickers per Yahoo request, default 50
    --retries N          attempts per request, default 3
    --no-articles        skip the article download (step 4) and use the
                         articles already in DataNLP

STEPS
    1  Check setup           Python packages and folders
    2  Read company list     the articles in DataNLP; without them, the
                             OSEBX ticker list the scraper itself reads
    3  Select companies      5, all, or named - from that same list
    4  Download articles     only articles newer than those in DataNLP,
                             for the chosen companies (Euronext, can be slow)
    5  Download prices       Yahoo Finance, in batches, with retries
    6  Check price quality   the lab's 4x rule; repair, exclude or stop
    7  Build indicators      ATR20, SMA10, SMA50, EMA20, market index
    8  Save results          CSV files, then summary.json and a log

Exit code: 0 every step OK, 2 finished with warnings, 1 a step failed.
Output:    ExcelData/StrategyResults_v5_Sentiment_Exit/management_download/
           all/ for a full run, subset/ for 5 or named companies.

The lab itself is not changed. It still downloads and checks its own prices.
"""

from __future__ import annotations

import argparse
import ast
import importlib
import importlib.util
import json
import linecache
import logging
import math
import os
import re
import sys
import time
import traceback
import warnings
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

THIS_FILE = Path(__file__).resolve()
# Where the log goes when the output folder could not be made (step 1 failed).
FALLBACK_LOG_DIR = THIS_FILE.parent

# Which companies to run when none are given on the command line: "all", a
# number such as "5", or tickers such as "BSP EAM". Handy when the script is
# started from an editor rather than a terminal.
COMPANIES = "all"

LEGACY_EXCEL_DIR = r"C:\Users\ander\Desktop\Python_K4\ExcelData"
NLP_DIR = "DataNLP"
# The list SentimentManagement() scrapes articles for. Used when there are no
# articles yet, so prices can still be downloaded.
TICKER_LIST = Path("Data_BT") / "AllTickers_OSEBX_TW_260428.xlsx"
OUTPUT_DIR = "StrategyResults_v5_Sentiment_Exit"
OSLO_SUFFIX = ".OL"
PRICE_START = "2019-01-01"          # hent_kurser() in the lab

# The lab's price check: a move of 4x or more between two actual observations
# needs verification before it may become a return.
UPPER_RATIO = 4.0
LOWER_RATIO = 0.25
# A jump this close to an exact power of ten is a unit change at the provider
# (ore/krone), not a price move. Same rule and tolerance as price_repair.py.
UNIT_FACTORS = (1000.0, 100.0, 10.0, 0.1, 0.01, 0.001)
UNIT_TOLERANCE = 0.005
# One bad day: a jump followed by the jump back. When the two ratios multiply
# to within 10 % of 1, the price in between is a bad print, not a move.
SPIKE_TOLERANCE = 0.10
# A ticker where more than this share of the prices are zero, negative or
# not numbers is not a usable series, whatever is left after removing them.
MAX_INVALID_SHARE = 0.05

# Indicator settings, as in the lab's Config.
ATR_DAYS = 20
SMA_DAYS = 50
MIN_HISTORY_DAYS = 120              # the lab skips signals with less history

FIELDS = ("Close", "High", "Low")
TOTAL_STEPS = 8
WIDE = "=" * 74
THIN = "-" * 74

# Replaced by the tests, so retries do not really wait.
_sleep = time.sleep


# ══════════════════════════════════════════════════════════════════════════
# SETTINGS AND REPORTING
# ══════════════════════════════════════════════════════════════════════════

@dataclass
class Settings:
    base_dir: Path
    companies: List[str]
    start: str = PRICE_START
    batch_size: int = 50
    retries: int = 3
    pause: float = 2.0
    strict: bool = False
    accept: Tuple[str, ...] = ()
    searched: Tuple[str, ...] = ()
    articles: bool = True

    @property
    def nlp_dir(self) -> Path:
        return self.base_dir / NLP_DIR

    @property
    def ticker_list(self) -> Path:
        return self.base_dir / TICKER_LIST

    @property
    def full_run(self) -> bool:
        return [c.lower() for c in self.companies] == ["all"]

    @property
    def out_dir(self) -> Path:
        # A five-company test must never overwrite the files of a full run.
        return (self.base_dir / OUTPUT_DIR / "management_download"
                / ("all" if self.full_run else "subset"))


class StepError(Exception):
    """A failure the console can explain: what happened, and what to do."""

    def __init__(self, message: str, hint: str = ""):
        super().__init__(message)
        self.hint = hint


class Step:
    """What a step function gets: somewhere to report progress and warnings."""

    def __init__(self, report: "Report", number: int, title: str):
        self.report, self.number, self.title = report, number, title
        self.warnings: List[str] = []
        self.summary = ""

    def info(self, text: str) -> None:
        self.report.say("    " + text)

    def warn(self, text: str) -> None:
        self.warnings.append(text)
        self.report.say("    WARNING: " + text)


def locate(exc: BaseException) -> str:
    """
    Where an exception came from, as «function() -> function(), line N».

    The chain lists the functions in this file the error passed through, so
    the console says which step function and which helper failed. If the
    error was raised inside a library (pandas, yfinance), that is named too.
    """
    frames = traceback.extract_tb(exc.__traceback__)
    if not frames:
        return "unknown location"
    own = [f for f in frames if _same_file(f.filename)]
    text = ""
    if own:
        chain = [f"{f.name}()" for f in own if f.name not in ("run", "<module>", "main")]
        text = (" -> ".join(chain) or f"{own[-1].name}()") + \
            f", {THIS_FILE.name} line {own[-1].lineno}"
    deepest = frames[-1]
    if not own or not _same_file(deepest.filename):
        text += ("; " if text else "") + (f"raised inside {Path(deepest.filename).name} "
                                          f"line {deepest.lineno}, in {deepest.name}()")
    return text


def _same_file(name: str) -> bool:
    try:
        return Path(name).resolve() == THIS_FILE
    except (OSError, ValueError):
        return False


def describe(exc: Optional[BaseException]) -> str:
    if exc is None:
        return "no error recorded"
    text = str(exc).strip().splitlines()[0] if str(exc).strip() else ""
    name = type(exc).__name__
    return text if isinstance(exc, StepError) else (f"{name}: {text}" if text else name)


def hint_for(exc: BaseException) -> str:
    """Plain advice for the errors that have one obvious cause."""
    if isinstance(exc, ModuleNotFoundError):
        return f"Install the missing package: pip install {exc.name or '<package>'}"
    if isinstance(exc, ImportError):
        return "A package is installed but broken or too old: pip install -U <package>"
    if isinstance(exc, PermissionError):
        return ("The file is open in another program (often Excel) or the folder is "
                "read-only. Close it and run again.")
    if isinstance(exc, FileNotFoundError):
        return "Check the path. Use --excel-dir to point at your ExcelData folder."
    if isinstance(exc, MemoryError):
        return "Too much data at once. Test with fewer companies: python management_download.py 5"
    if isinstance(exc, (ConnectionError, TimeoutError)) or "curl" in str(exc).lower():
        return ("Network problem. Check the internet connection, proxy or firewall, "
                "then run again.")
    if isinstance(exc, KeyError):
        return "A column or ticker the code expects is missing from the data."
    return ""


class Report:
    """Runs the steps, prints each result, and keeps everything for the log."""

    def __init__(self) -> None:
        self.lines: List[str] = []
        self.steps: List[Dict[str, Any]] = []
        self.failed_step: Optional[int] = None
        self.interrupted = False
        self.facts: Dict[str, Any] = {}

    def say(self, text: str = "") -> None:
        print(text, flush=True)
        self.lines.append(text)

    def log_only(self, text: str) -> None:
        self.lines.append(text)

    def run(self, number: int, title: str, func: Callable[..., Any], *args: Any) -> Any:
        head = f"[STEP {number}/{TOTAL_STEPS}]"
        if self.failed_step is not None or self.interrupted:
            reason = ("stopped by the user" if self.interrupted
                      else f"step {self.failed_step} failed")
            self.say(f"{head} {title} - SKIPPED ({reason})")
            self.steps.append({"step": number, "title": title, "status": "SKIPPED",
                               "seconds": 0.0, "summary": reason})
            return None

        self.say()
        self.say(f"{head} {title}")
        step = Step(self, number, title)
        start = time.perf_counter()
        try:
            value = func(step, *args)
        except KeyboardInterrupt:
            seconds = time.perf_counter() - start
            self.say(f"{head} INTERRUPTED after {seconds:.1f} s")
            self.steps.append({"step": number, "title": title, "status": "INTERRUPTED",
                               "seconds": round(seconds, 1), "summary": "Ctrl+C"})
            self.interrupted = True
            raise
        except Exception as exc:        # every step failure ends up here
            seconds = time.perf_counter() - start
            where = locate(exc)
            hint = getattr(exc, "hint", "") or hint_for(exc)
            self.say(f"{head} FAILED  ({seconds:.1f} s)")
            self.say(f"    Where : {where}")
            self.say(f"    Error : {describe(exc)}")
            if hint:
                self.say(f"    Hint  : {hint}")
            self.say("    The full traceback is in management_download.log.")
            self.log_only(f"--- traceback, step {number} ({title}) ---")
            self.log_only("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
            self.steps.append({"step": number, "title": title, "status": "FAILED",
                               "seconds": round(seconds, 1), "summary": describe(exc),
                               "where": where, "hint": hint})
            self.failed_step = number
            return None

        seconds = time.perf_counter() - start
        status = "WARN" if step.warnings else "OK"
        self.say(f"{head} {status}  ({seconds:.1f} s)"
                 + (f" - {step.summary}" if step.summary else ""))
        self.steps.append({"step": number, "title": title, "status": status,
                           "seconds": round(seconds, 1), "summary": step.summary,
                           "warnings": list(step.warnings)})
        return value

    def exit_code(self) -> int:
        if self.interrupted:
            return 130
        if self.failed_step is not None:
            return 1
        return 2 if any(s["status"] == "WARN" for s in self.steps) else 0

    def finish(self, settings: Settings) -> int:
        code = self.exit_code()
        self.say()
        self.say(WIDE)
        self.say(" SUMMARY")
        self.say(WIDE)
        for s in self.steps:
            self.say(f"  {s['step']}  {s['title']:<34} {s['status']:<11} "
                     f"{s['seconds']:>6.1f} s  {str(s.get('summary', ''))[:60]}")
        self.say(THIN)
        if self.interrupted:
            verdict = "STOPPED by the user"
        elif self.failed_step is not None:
            failed = next(s for s in self.steps if s["status"] == "FAILED")
            verdict = f"FAILED at step {failed['step']} ({failed['title']})"
        elif code == 2:
            verdict = "FINISHED WITH WARNINGS - read the WARNING lines above"
        else:
            verdict = "FINISHED - every step OK"
        self.say(f" RESULT : {verdict} - exit code {code}")

        # Without an output folder (step 1 failed) the log goes next to the script.
        folder = settings.out_dir if settings.out_dir.is_dir() else FALLBACK_LOG_DIR
        log_path = folder / "management_download.log"
        self.say(f" LOG    : {log_path}")
        self.say(WIDE)
        summary = {"finished": datetime.now().isoformat(timespec="seconds"),
                   "exit_code": code, "result": verdict,
                   "companies_argument": settings.companies,
                   "excel_dir": str(settings.base_dir), "strict": settings.strict,
                   "accepted": list(settings.accept), "steps": self.steps, **self.facts}
        for path, text in (
                (folder / "summary.json",
                 json.dumps(summary, indent=2, ensure_ascii=False, default=str)),
                (log_path, "\n".join(self.lines) + "\n")):
            try:
                path.write_text(text, encoding="utf-8")
            except OSError as exc:
                print(f" Could not write {path}: {describe(exc)}", flush=True)
        return code


# ══════════════════════════════════════════════════════════════════════════
# STEP 1 - CHECK SETUP
# ══════════════════════════════════════════════════════════════════════════

def check_setup(step: Step, s: Settings) -> Dict[str, Any]:
    step.info(f"Python     : {sys.version.split()[0]}")
    modules: Dict[str, Any] = {}
    missing: List[str] = []
    for name in ("pandas", "numpy", "yfinance", "openpyxl"):
        try:
            modules[name] = importlib.import_module(name)
            step.info(f"{name:<11}: {getattr(modules[name], '__version__', 'installed')}")
        except Exception as exc:
            missing.append(name)
            step.info(f"{name:<11}: MISSING ({describe(exc)})")
    if missing:
        raise StepError(f"Missing Python package(s): {', '.join(missing)}",
                        hint="Install with: pip install " + " ".join(missing)
                             + "   (or run SETUP.cmd)")

    # yfinance only needs scipy for repair=True, which the lab uses. Without
    # scipy that repair fails for every ticker, so it is switched off instead.
    try:
        scipy = importlib.import_module("scipy")
        repair = True
        step.info(f"scipy      : {getattr(scipy, '__version__', 'installed')} "
                  f"(Yahoo price repair on, as in the lab)")
    except Exception:
        repair = False
        step.warn("scipy is not installed, so Yahoo's own price repair (repair=True in "
                  "the lab) is switched off. Install it with: pip install scipy")

    # yfinance prints its own «Failed download» lines. They are caught here
    # instead, so each missing ticker is reported once, with its reason.
    yahoo_log = YahooLog()
    logger = logging.getLogger("yfinance")
    for old in [h for h in logger.handlers if isinstance(h, YahooLog)]:
        logger.removeHandler(old)
    logger.addHandler(yahoo_log)
    logger.setLevel(logging.ERROR)
    logger.propagate = False

    for line in s.searched:
        step.info(f"searched   : {line}")
    if not s.base_dir.is_dir():
        raise StepError(f"ExcelData folder not found: {s.base_dir}",
                        hint="Use --excel-dir PATH, or set AKSJE_BASE_DIR.")
    step.info(f"ExcelData  : {s.base_dir}")
    has_articles = bool(article_files(s.nlp_dir)) if s.nlp_dir.is_dir() else False
    if has_articles:
        step.info(f"Articles   : {s.nlp_dir}")
    elif s.ticker_list.is_file():
        step.warn(f"No article files in {s.nlp_dir}. Prices are downloaded for the "
                  f"ticker list {TICKER_LIST} instead (the list the scraper reads).")
    else:
        raise StepError(
            f"Neither articles ({s.nlp_dir}) nor the ticker list ({s.ticker_list}) "
            f"exist, so there is no list of companies to download",
            hint="Point --excel-dir at the ExcelData folder that has DataNLP or "
                 "Data_BT, e.g. --excel-dir " + LEGACY_EXCEL_DIR)
    try:
        s.out_dir.mkdir(parents=True, exist_ok=True)
        probe = s.out_dir / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        raise StepError(f"Cannot write to the output folder {s.out_dir}: {describe(exc)}",
                        hint="Check that the folder is not read-only or locked by "
                             "OneDrive or antivirus.") from exc
    step.info(f"Output     : {s.out_dir}")
    step.summary = (f"pandas {modules['pandas'].__version__}, "
                    f"yfinance {getattr(modules['yfinance'], '__version__', '?')}")
    return {"pd": modules["pandas"], "np": modules["numpy"],
            "yf": modules["yfinance"], "repair": repair, "yahoo_log": yahoo_log}


# ══════════════════════════════════════════════════════════════════════════
# STEP 2 - READ ARTICLE FILES
# ══════════════════════════════════════════════════════════════════════════

REQUIRED_ARTICLE_COLUMNS = ("Company", "Article_Date", "Final_Score")


def article_files(folder: Path) -> List[Path]:
    """The same files les_artikler() in the lab reads."""
    def wanted(p: Path) -> bool:
        tail = p.stem.rsplit("_", 1)[-1]
        return (not p.name.startswith("~$")
                and ("_FINAL" in p.name or not any(ch.isdigit() for ch in tail)
                     or len(tail) <= 8))
    return sorted(p for p in folder.glob("NLP_Sentiment_Detail_*.xlsx") if wanted(p))


def parse_article_dates(pd: Any, column: Any) -> Any:
    raw = column.astype(str).str.replace(r"\n.*$", "", regex=True).str.strip()
    first = pd.to_datetime(raw, format="%d %b %Y", errors="coerce")
    try:
        rest = pd.to_datetime(raw, format="mixed", errors="coerce")
    except (TypeError, ValueError):     # pandas older than 2.0 has no «mixed»
        rest = pd.to_datetime(raw, errors="coerce")
    return first.fillna(rest)


def clean_company(value: Any) -> str:
    # Excel can store the ticker 2020 as the number 2020.0.
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = str(value).strip() if value is not None else ""
    return "" if text.lower() in ("", "nan", "none", "nat") else text


def read_ticker_list(step: Step, s: Settings, mods: Dict[str, Any]) -> Any:
    """The OSEBX list, read as PBROE_All3() and SentimentManagement() read it."""
    pd = mods["pd"]
    try:
        df = pd.read_excel(s.ticker_list)
    except PermissionError as exc:
        raise StepError(f"{s.ticker_list.name} cannot be opened: {describe(exc)}",
                        hint="Close it in Excel and run again.") from exc
    if "Company" not in df.columns:
        raise StepError(f"{s.ticker_list.name} has no Company column "
                        f"(columns: {', '.join(map(str, df.columns))})")
    companies = sorted({clean_company(c) for c in df["Company"]} - {""})
    if not companies:
        raise StepError(f"{s.ticker_list.name} lists no companies")
    step.info(f"read {s.ticker_list}: {len(companies)} companies")
    step.summary = f"{len(companies)} companies from {s.ticker_list.name}"
    return pd.DataFrame({"Company": companies})


def read_articles(step: Step, s: Settings, mods: Dict[str, Any]) -> Any:
    pd = mods["pd"]
    files = article_files(s.nlp_dir) if s.nlp_dir.is_dir() else []
    if not files:
        step.info(f"no article files in {s.nlp_dir}; using the ticker list")
        return read_ticker_list(step, s, mods)
    step.info(f"{len(files)} article file(s) found")

    parts = []
    for f in files:
        try:
            d = pd.read_excel(f)
        except PermissionError as exc:
            step.warn(f"{f.name}: cannot be opened ({describe(exc)}). Is it open in "
                      f"Excel? Skipped.")
            continue
        except Exception as exc:
            step.warn(f"{f.name}: cannot be read ({describe(exc)}). Skipped.")
            continue
        if d.empty:
            step.warn(f"{f.name}: the sheet is empty. Skipped.")
            continue
        absent = [c for c in REQUIRED_ARTICLE_COLUMNS if c not in d.columns]
        if absent:
            step.warn(f"{f.name}: missing column(s) {', '.join(absent)}. Skipped.")
            continue
        d["_file"] = f.name
        parts.append(d)
        step.info(f"  read {f.name}: {len(d)} rows")
    if not parts:
        raise StepError("None of the article files could be used (see the warnings above)",
                        hint="Close the files in Excel, or run SentimentManagement() "
                             "again to rewrite them.")

    df = pd.concat(parts, ignore_index=True)
    total = len(df)
    raw_dates = df["Article_Date"].astype(str)
    df["Article_Date"] = parse_article_dates(pd, df["Article_Date"])
    no_date = int(df["Article_Date"].isna().sum())
    if no_date:
        examples = raw_dates[df["Article_Date"].isna()].str.strip().drop_duplicates().head(5)
        step.info("dates that could not be read, e.g.: "
                  + " | ".join(repr(x[:40]) for x in examples))
    df = df.dropna(subset=["Article_Date"])
    no_text = 0
    if "Text_Length" in df.columns:
        length = pd.to_numeric(df["Text_Length"], errors="coerce")
        no_text = int((~(length > 0)).sum())
        df = df[length > 0]
    df["Final_Score"] = pd.to_numeric(df["Final_Score"], errors="coerce")
    no_score = int(df["Final_Score"].isna().sum())
    df = df.dropna(subset=["Final_Score"])
    df["Company"] = df["Company"].map(clean_company)
    no_company = int((df["Company"] == "").sum())
    df = df[df["Company"] != ""]
    keys = [k for k in ("Company", "Article_Date", "Article_Title") if k in df.columns]
    before = len(df)
    df = df.sort_values("_file").drop_duplicates(subset=keys, keep="last")
    duplicates = before - len(df)
    df = df.sort_values(["Company", "Article_Date"]).reset_index(drop=True)

    dropped = {"date could not be read": no_date, "no text": no_text,
               "no Final_Score": no_score, "no company": no_company,
               "duplicate": duplicates}
    step.info(f"{total} rows read; removed: "
              + ", ".join(f"{n} {why}" for why, n in dropped.items()))
    if df.empty:
        raise StepError("No usable articles left after cleaning",
                        hint="Every row lacked a readable date, a score or a company. "
                             "Open one of the files and check the columns "
                             + ", ".join(REQUIRED_ARTICLE_COLUMNS) + ".")
    if total and len(df) < 0.5 * total:
        step.warn(f"Only {len(df)} of {total} rows are usable. Check the article files.")

    reports = df.groupby("Company").size()
    step.info(f"{len(df)} articles, {len(reports)} companies, "
              f"{df['Article_Date'].min().date()} -> {df['Article_Date'].max().date()}")
    step.info(f"{int((reports >= 2).sum())} companies have two or more reports "
              f"(a signal needs a previous report to compare with)")
    step.summary = f"{len(df)} articles, {len(reports)} companies"
    return df


# ══════════════════════════════════════════════════════════════════════════
# STEP 3 - SELECT COMPANIES
# ══════════════════════════════════════════════════════════════════════════

def to_ticker(company: str) -> str:
    company = company.strip()
    return company if company.upper().endswith(OSLO_SUFFIX) else company + OSLO_SUFFIX


def select_companies(step: Step, s: Settings, articles: Any) -> List[str]:
    names = sorted({clean_company(c) for c in articles["Company"].unique()} - {""})
    if not names:
        raise StepError("The article list has no company names")
    wanted = [w.strip() for w in s.companies if w.strip()]

    if [w.lower() for w in wanted] == ["all"]:
        chosen = names
        step.info(f"all {len(names)} companies in the article list")
    elif len(wanted) == 1 and wanted[0].isdigit():
        n = int(wanted[0])
        if n <= 0:
            raise StepError("The number of companies must be 1 or more",
                            hint="For example: python management_download.py 5")
        if n > len(names):
            step.warn(f"Asked for {n} companies, but the list has {len(names)}. Using all "
                      f"of them."
                      + (f" To run the company {wanted[0]}, write {wanted[0]}{OSLO_SUFFIX}."
                         if wanted[0] in names else ""))
        chosen = names[:n]
        step.info(f"the first {len(chosen)} of {len(names)} companies (alphabetical)")
    else:
        lookup: Dict[str, str] = {}
        for name in names:
            lookup[name.upper()] = name
            lookup[to_ticker(name).upper()] = name
        chosen, unknown = [], []
        for w in wanted:
            hit = lookup.get(w.upper())
            if hit is None:
                unknown.append(w)
            elif hit not in chosen:
                chosen.append(hit)
        if unknown:
            step.warn(f"Not in the article list, ignored: {', '.join(unknown)}")
        if not chosen:
            raise StepError("None of the named companies are in the article list",
                            hint="Names come from the Company column. Examples: "
                                 + ", ".join(names[:12]))
        step.info(f"{len(chosen)} named companies")

    tickers = [to_ticker(n) for n in chosen]
    shown = tickers if len(tickers) <= 20 else tickers[:10] + ["..."] + tickers[-5:]
    step.info("tickers: " + ", ".join(shown))
    step.summary = f"{len(tickers)} of {len(names)} companies"
    return tickers


# ══════════════════════════════════════════════════════════════════════════
# STEP 4 - DOWNLOAD NEW ARTICLES
# ══════════════════════════════════════════════════════════════════════════

def article_snapshot(pd: Any, folder: Path) -> Tuple[set, str]:
    """(one key per article the lab can read, newest article date)."""
    keys: set = set()
    dates = []
    for f in (article_files(folder) if folder.is_dir() else []):
        try:
            d = pd.read_excel(f)
        except Exception:
            continue
        if "Company" not in d.columns or "Article_Date" not in d.columns:
            continue
        d = d.reindex(columns=["Company", "Article_Date", "Article_Title"])
        keys.update(tuple(clean_company(v) for v in r) for r in d.itertuples(index=False))
        dates.append(parse_article_dates(pd, d["Article_Date"]).max())
    dates = [x for x in dates if x == x and x is not None]
    return keys, (str(max(dates).date()) if dates else "-")


# The changes that make the v4.1 scraper fetch only new articles: pairs of
# (text in the old Only_260820.py, text it becomes). Taken from the
# difference between the original file and the fixed one, and checked
# against the original in test_management_download.py.
SCRAPER_PATCHES: List[Tuple[str, str]] = [
    # 1
    (r'''            force_rerun: bool       = True''',
     r'''            force_rerun: bool       = True
            # Bare nye artikler: hvert selskap blas bare fram til første side der
            # alt allerede ligger i DataNLP. AKSJE_NLP_ALLE=1 henter alt på nytt.
            incremental: bool       = not _miljo_paa("AKSJE_NLP_ALLE")
            # Kommaseparert utvalg, f.eks. "BSP,EAM". Tomt = hele Excel-lista.
            only_companies: str     = os.environ.get("AKSJE_NLP_SELSKAPER", "")'''),
    # 2
    (r'''
        async def collect_all_article_rows(page, config: Config, sl: StepLogger) -> List[dict]:''',
     r'''
        # ─────────────────────────────────────────────────────────────────────────────
        # BARE NYE ARTIKLER
        # ─────────────────────────────────────────────────────────────────────────────

        def _selskapsnokkel(company) -> str:
            # Excel kan lagre tickeren 2020 som tallet 2020.0.
            if isinstance(company, float) and company.is_integer():
                company = int(company)
            return str(company).strip().upper()

        def _artikkel_url(row: dict, config: Config) -> str:
            """Den samme Article_URL som scrape_company skriver for raden."""
            nid, href = row.get("nid", "") or "", row.get("href", "") or ""
            url = config.euronext_base + href if href.startswith("/") else href
            return url or (f"modal://{nid}" if nid else "")

        def _er_kjent(row: dict, kjente: Set, config: Config) -> bool:
            url = _artikkel_url(row, config)
            if url and ("url", url) in kjente:
                return True
            return ("tittel", str(row.get("title", "")).strip(),
                    str(row.get("date", "")).strip()) in kjente

        def load_known_articles(config: Config):
            """
            (kjente nøkler per selskap, alle lagrede rader uten duplikater).

            Leser hver NLP_Sentiment_Detail_*.xlsx i DataNLP. En fil som ikke kan
            leses hoppes over med en advarsel; det koster bare at artiklene i
            den hentes på nytt.
            """
            deler = []
            for f in sorted(config.nlp_dir.glob("NLP_Sentiment_Detail_*.xlsx")):
                if f.name.startswith("~$"):
                    continue
                try:
                    d = pd.read_excel(f)
                except Exception as e:
                    log.warning("  Hoppet over %s: %s", f.name, e)
                    continue
                if not d.empty and "Company" in d.columns:
                    deler.append(d)
            if not deler:
                return {}, []
            df = pd.concat(deler, ignore_index=True).dropna(subset=["Company"])
            df["Company"] = df["Company"].map(
                lambda c: int(c) if isinstance(c, float) and c.is_integer() else c)
            if "Article_Title" in df.columns:
                df = df[df["Article_Title"].astype(str) != "INGEN ARTIKLER"]
            nokler = [k for k in ("Company", "Article_Date", "Article_Title") if k in df.columns]
            df = df.drop_duplicates(subset=nokler, keep="last")
            rader = df.to_dict("records")
            kjente = {}
            for r in rader:
                s = kjente.setdefault(_selskapsnokkel(r["Company"]), set())
                url = str(r.get("Article_URL") or "").strip()
                if url and url.lower() != "nan" and url != "modal://":
                    s.add(("url", url))
                s.add(("tittel", str(r.get("Article_Title") or "").strip(),
                       str(r.get("Article_Date") or "").strip()))
            return kjente, rader
        async def collect_all_article_rows(page, config: Config, sl: StepLogger,
                                           kjente: Optional[Set] = None,
                                           stats: Optional[dict] = None) -> List[dict]:'''),
    # 3
    (r'''                sl.info(f"  Side {page_num}: {len(rows)} rader, {new_count} nye → totalt {len(all_rows)}")''',
     r'''                sl.info(f"  Side {page_num}: {len(rows)} rader, {new_count} nye → totalt {len(all_rows)}")
                # Bare nye artikler: de nyeste står øverst, så når en hel side
                # allerede ligger i DataNLP, gjør resten av sidene det også.
                if kjente is not None and new_count:
                    denne_siden = all_rows[-new_count:]
                    ukjente = sum(1 for r in denne_siden if not _er_kjent(r, kjente, config))
                    if stats is not None:
                        stats["kjente"] = stats.get("kjente", 0) + new_count - ukjente
                    if ukjente == 0:
                        sl.info("  Hele siden ligger allerede i DataNLP — stopper bladingen")
                        break'''),
    # 4
    (r'''            is_first: bool,''',
     r'''            is_first: bool,
            kjente: Optional[Set] = None,
            stats: Optional[dict] = None,'''),
    # 5
    (r'''
            row_data = await collect_all_article_rows(page, config, sl)''',
     r'''
            row_data = await collect_all_article_rows(page, config, sl, kjente, stats)
            if kjente is not None:
                row_data = [r for r in row_data if not _er_kjent(r, kjente, config)]'''),
    # 6
    (r'''                    sl.info(f"  ... og {len(row_data)-3} til")''',
     r'''                    sl.info(f"  ... og {len(row_data)-3} til")
            elif stats is not None and stats.get("kjente"):
                sl.ok(f"Ingen nye artikler — {stats['kjente']} ligger allerede i DataNLP")
                stats["oppdatert"] = True
                try:
                    await page.goto(config.start_url, wait_until="networkidle",
                                    timeout=config.page_timeout)
                    await page.wait_for_timeout(1_500)
                except Exception:
                    pass
                return articles'''),
    # 7
    (r'''            companies = load_companies(config)''',
     r'''            companies = load_companies(config)
            if config.only_companies.strip():
                valgt = {_selskapsnokkel(w).removesuffix(".OL")
                         for w in config.only_companies.split(",") if w.strip()}
                companies = [c for c in companies if _selskapsnokkel(c) in valgt]
                print(f"   Utvalg fra AKSJE_NLP_SELSKAPER: {len(companies)} selskaper")'''),
    # 8
    (r'''            print(f"   ✅ STEG C FERDIG: {len(remaining)} selskaper gjenstår")''',
     r'''            print(f"   ✅ STEG C FERDIG: {len(remaining)} selskaper gjenstår")
            # STEG C2: Bare nye artikler
            known, existing_rows = {}, []
            if config.incremental:
                print(f"\n📚 STEG C2: Leser artiklene som allerede ligger i DataNLP...")
                try:
                    known, existing_rows = load_known_articles(config)
                    print(f"   ✅ STEG C2 FERDIG: {len(existing_rows)} lagrede artikler for "
                          f"{len(known)} selskaper — bare nye hentes og analyseres")
                except Exception as e:
                    print(f"   ⚠️  STEG C2 FEILET ({type(e).__name__}: {e}) — henter alle "
                          f"artikler på nytt")
                    known, existing_rows = {}, []
                    config.incremental = False
            else:
                print(f"\n📚 STEG C2: AKSJE_NLP_ALLE=1 — henter alle artikler på nytt")

            def kjente_for(company):
                return known.get(_selskapsnokkel(company)) if config.incremental else None'''),
    # 9
    (r'''                failed_companies = []''',
     r'''                failed_companies = []
                oppdatert = []'''),
    # 10
    (r'''                    try:
                        articles = await scrape_company(page, company, config, is_first)''',
     r'''                    stats = {}
                    try:
                        articles = await scrape_company(page, company, config, is_first,
                                                        kjente_for(company), stats)'''),
    # 11
    (r'''                    if not articles:
                        # A loaded page with no parsed articles may be a failed navigation.''',
     r'''                    if not articles and stats.get("oppdatert"):
                        oppdatert.append(company)
                        mark_company_complete(company, config, today)
                        print(f"  ✓ {company}: ingen nye artikler — allerede oppdatert")
                        continue
                    if not articles:
                        # A loaded page with no parsed articles may be a failed navigation.'''),
    # 12
    (r'''                                try:
                                    articles = await scrape_company(page, company, config, False)''',
     r'''                                try:
                                    articles = await scrape_company(page, company, config, False,
                                                                    kjente_for(company), stats)'''),
    # 13
    (r'''            print(f"{'='*80}")
            save_results(all_results, config, today, final=not failed_companies)''',
     r'''            print(f"{'='*80}")
            # Filen får både det som lå der og det nye, så den nyeste filen alene
            # er hele datagrunnlaget (data_acquisition.py leser bare den). Den er
            # _FINAL også når noen selskaper feilet: den inneholder alt fra før,
            # og en fil med tidsstempel leses ikke av ledelses-laben.
            save_results(existing_rows + all_results, config, today,
                         final=not failed_companies or config.incremental)'''),
    # 14
    (r'''            print(f"  Artikler analysert:      {arts_total}")''',
     r'''            print(f"  Artikler analysert:      {arts_total}")
            if config.incremental:
                print(f"  Allerede oppdatert:      {len(oppdatert)} selskaper (ingen nye artikler)")
                print(f"  Lagret fra før:          {len(existing_rows)} artikler (tatt med i filen)")'''),
]

# ── Loading the scraper ───────────────────────────────────────────────────
#
# Only_260820.py stays exactly as it is on disk. It is read, fixed in memory
# and run from there, so this works with the file you already have:
#
#   1. Every scraper ends with «if __name__ == "__main__": asyncio.run(main())».
#      Started from another script, __name__ is «Only_260820», and the scraper
#      returned without downloading anything. The check is replaced by a call.
#   2. The v4.1 scraper gets «only new articles» (SCRAPER_PATCHES below). If
#      your file differs where a change goes, none of them are applied: the
#      scraper still runs, but downloads every article again, and step 4 warns
#      and lists every change that did not match.
#   3. The scraper reads its companies from a list in Data_BT. When that file
#      is missing, or only some companies are chosen (5, or named ones), the
#      chosen companies are written to this script's own output folder and
#      the scraper reads that list instead. Data_BT is not touched.

SCRAPER_FILE = "Only_260820.py"
# What the article scraper needs: the browser, the language model and its
# sentence splitter.
SCRAPER_PACKAGES = ("playwright", "transformers", "torch", "nltk")
SCRAPER_START = "    def NLP_Euronext_Quarter4_v41():"
SCRAPER_END = "    def NlpSentimentTrader4_v41():"
MAIN_GUARD = re.compile(r'^([ \t]+)if __name__ == ["\']__main__["\']:[ \t]*\n'
                        r'\1[ \t]+asyncio\.run\(main\(\)\)[ \t]*$', re.M)
GUARD_COMMENT = (
    "# Kjøres også når fila importeres, slik master.py gjør. En sperre med",
    "# «if __name__ == \"__main__\"» her gjorde at skrapingen stille ble hoppet",
    "# over: da er __name__ «Only_260820», og ingen artikler ble hentet.")
KJOR_ASYNC = """


def _kjor_async(coro):
    # Added by management_download.py: asyncio.run, also where a loop runs.
    import asyncio
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop is None:
        return asyncio.run(coro)
    import nest_asyncio
    nest_asyncio.apply()
    return asyncio.get_event_loop().run_until_complete(coro)
"""


def patch_scraper_source(text: str) -> Tuple[str, List[str], List[str]]:
    """(fixed source, what was changed, what could not be changed)."""
    text = text.replace("\r\n", "\n")
    if "def _kjor_async" in text:
        return text, ["already the fixed version, used as it is"], []
    done: List[str] = []
    missing: List[str] = []
    text, guards = MAIN_GUARD.subn(lambda m: "".join(
        m.group(1) + line + "\n" for line in GUARD_COMMENT) + m.group(1)
        + "_kjor_async(main())", text)
    if guards:
        done.append(f"scraper start fixed in {guards} place(s)")
    else:
        missing.append("the scraper start («if __name__ ... asyncio.run(main())») was "
                       "not found")
    text += KJOR_ASYNC

    start = text.find(SCRAPER_START)
    end = text.find(SCRAPER_END, start + 1) if start >= 0 else -1
    if start < 0 or end < 0:
        missing.append("the v4.1 scraper was not found, so every article is downloaded "
                       "again (slow)")
        return text, done, missing
    part = text[start:end]
    unmatched = []
    for number, (old, _) in enumerate(SCRAPER_PATCHES, 1):
        if part.count(old + "\n") != 1:
            last = next((x.strip() for x in reversed(old.splitlines()) if x.strip()), "")
            unmatched.append(f"{number} (near «{last[:70]}»)")
    if unmatched:
        missing.append(f"{len(unmatched)} of {len(SCRAPER_PATCHES)} changes do not match "
                       f"your file, so every article is downloaded again (slow). "
                       f"Not matching: " + "; ".join(unmatched))
        return text, done, missing
    for old, new in SCRAPER_PATCHES:
        part = part.replace(old + "\n", new + "\n", 1)
    done.append(f"only new articles: all {len(SCRAPER_PATCHES)} changes applied")
    return text[:start] + part + text[end:], done, missing


TICKERS_FILE = re.compile(r'^([ \t]+tickers_file:[^=\n]*=[ \t]*)r?(["\'])([^"\'\n]*)\2',
                          re.M)


def point_at_company_list(step: Step, s: Settings, text: str, names: List[str]) -> str:
    """
    Make the v4.1 scraper read the chosen companies, when that is needed.

    Kept as it is: a full run whose own list exists. Otherwise the chosen
    companies go to <output>/scraper_companies.xlsx, and the scraper's
    tickers_file points there - in memory; Data_BT is not touched.
    """
    start = text.find(SCRAPER_START)
    end = text.find(SCRAPER_END, start + 1) if start >= 0 else -1
    found = TICKERS_FILE.search(text, start, end) if start >= 0 and end > 0 else None
    if found is None:
        step.warn("scraper: its company list setting (tickers_file) was not found, so "
                  "it uses its own list" + ("" if s.full_run else
                                            " - and may scrape more than the chosen companies"))
        return text
    own = s.base_dir / found.group(3).replace("\\", "/")
    if s.full_run and own.is_file():
        step.info(f"scraper: company list {own}")
        return text
    target = s.out_dir / "scraper_companies.xlsx"
    import pandas as pd
    # Same layout as AllTickers_OSEBX_TW_*.xlsx: an index column, then Company.
    # Readers that drop the first column and readers that drop «Unnamed»
    # columns both find Company.
    pd.DataFrame({"Company": names}).to_excel(target)
    why = (f"{own.name} is missing" if not own.is_file() else "only the chosen companies")
    (step.warn if not own.is_file() else step.info)(
        f"scraper: {why} - it reads {len(names)} companies from {target} instead")
    return text[:found.start()] + found.group(1) + repr(str(target)) + text[found.end():]


def find_scraper_file() -> Optional[Path]:
    for folder in [THIS_FILE.parent] + [Path(p) for p in sys.path if p]:
        candidate = folder / SCRAPER_FILE
        if candidate.is_file():
            return candidate
    return None


def load_scraper(step: Step, s: Optional[Settings] = None,
                 names: Optional[List[str]] = None) -> Any:
    """Only_260820 as a module, fixed in memory. The file is never written."""
    if "Only_260820" in sys.modules:
        module = sys.modules["Only_260820"]
        step.info(f"scraper file: {getattr(module, '__file__', '?')} (already loaded)")
        if not hasattr(module, "_kjor_async"):
            raise StepError(
                f"{getattr(module, '__file__', SCRAPER_FILE)} is the old version and was "
                f"loaded before this step, so it cannot be fixed now",
                hint="Start this script on its own, not from a program that already "
                     "imported Only_260820.")
        return module
    path = find_scraper_file()
    if path is None:
        raise StepError(f"{SCRAPER_FILE} not found next to {THIS_FILE.name}",
                        hint=f"Put {SCRAPER_FILE} in {THIS_FILE.parent}.")
    step.info(f"scraper file: {path}")
    try:
        raw = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raw = path.read_text(encoding="cp1252")
    text, done, missing = patch_scraper_source(raw)
    for line in done:
        step.info(f"scraper: {line}")
    for line in missing:
        step.warn(f"scraper: {line}")
    if s is not None and names:
        text = point_at_company_list(step, s, text, names)
    if "_kjor_async(main())" not in text:
        raise StepError("the scraper cannot be started from here: its start was not found",
                        hint=f"Send me the last 20 lines of NLP_Euronext_Quarter4_v41() "
                             f"in {path.name}.")

    spec = importlib.util.spec_from_loader("Only_260820", loader=None, origin=str(path))
    module = importlib.util.module_from_spec(spec)
    module.__file__ = str(path)
    # Tracebacks then show the fixed lines that actually ran.
    linecache.cache[str(path)] = (len(text), None, text.splitlines(True), str(path))
    sys.modules["Only_260820"] = module
    try:
        exec(compile(text, str(path), "exec", dont_inherit=True), module.__dict__)
    except BaseException:
        sys.modules.pop("Only_260820", None)
        raise
    return module


def download_articles(step: Step, s: Settings, mods: Dict[str, Any],
                      tickers: List[str]) -> Optional[int]:
    """
    Run the article scraper, SentimentManagement() in Only_260820.py.

    For each company it only opens articles newer than those already in
    DataNLP, and it saves one new file holding the old and the new articles.
    If it fails, the articles already saved are still valid: the step warns,
    and the prices are downloaded anyway.
    """
    if not s.articles:
        step.info("skipped (--no-articles): using the articles already in DataNLP")
        step.summary = "skipped"
        return None
    pd = mods["pd"]
    before, newest_before = article_snapshot(pd, s.nlp_dir)
    step.info(f"on disk now: {len(before)} articles, newest {newest_before}")

    # Without FinBERT the scraper does not stop: it gives every new article
    # a neutral default score, saves it, and later runs skip it as known.
    # So nothing is started unless everything it needs is installed.
    absent = [name for name in SCRAPER_PACKAGES if importlib.util.find_spec(name) is None]
    if absent:
        step.warn(f"Article download skipped: the scraper needs {', '.join(absent)}, which "
                  f"is not installed (without it, new articles would get a fake neutral "
                  f"score). Install with: pip install {' '.join(absent)}, then run "
                  f"'python -m playwright install chromium' once.")
        step.summary = "skipped - packages missing"
        return None
    names = [t[:-len(OSLO_SUFFIX)] if t.upper().endswith(OSLO_SUFFIX) else t
             for t in tickers]
    step.info(("all companies" if s.full_run else f"{len(names)} companies")
              + " - only articles newer than those saved are opened. The scraper "
                "prints its own progress below; this can take a long time.")

    settings_env = {"AKSJE_BASE_DIR": str(s.base_dir), "AKSJE_NLP_HENT": "1",
                    "AKSJE_NLP_ONLY_DOWNLOAD": "1",
                    "AKSJE_NLP_SELSKAPER": "" if s.full_run else ",".join(names)}
    previous = {k: os.environ.get(k) for k in settings_env}
    os.environ.update(settings_env)
    error = ""
    try:
        if str(THIS_FILE.parent) not in sys.path:
            sys.path.insert(0, str(THIS_FILE.parent))
        models = load_scraper(step, s, names)
        try:
            from runtime_config import configure_paths
            configure_paths(models.__dict__, s.base_dir)
        except ImportError:
            step.info("runtime_config.py not found: the scraper uses its own ExcelData path")
        models.SentimentManagement()
    except SystemExit as exc:           # the scraper calls sys.exit when its list is missing
        error = (f"the scraper stopped with exit code {exc.code} (its own message is "
                 f"just above)")
    except StepError as exc:
        error = describe(exc) + (f". {exc.hint}" if exc.hint else "")
    except Exception as exc:
        hint = hint_for(exc)
        error = f"{describe(exc)} at {locate(exc)}" + (f". {hint}" if hint else "")
    finally:
        for k, v in previous.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    after, newest_after = article_snapshot(pd, s.nlp_dir)
    new = len(after - before)
    if error:
        step.warn(f"Article download failed: {error}. Continuing with the articles "
                  f"already saved" + (f" ({new} new ones were saved first)" if new else "")
                  + ".")
    step.info(f"{new} new article(s); newest article is now {newest_after}")
    step.summary = f"{new} new articles, newest {newest_after}"
    return new


# ══════════════════════════════════════════════════════════════════════════
# STEP 5 - DOWNLOAD PRICES
# ══════════════════════════════════════════════════════════════════════════

def normalise_index(pd: Any, index: Any) -> Any:
    idx = pd.to_datetime(index)
    if getattr(idx, "tz", None) is not None:
        idx = idx.tz_localize(None)
    return idx.normalize()


def extract_fields(pd: Any, data: Any, batch: Sequence[str]) -> Dict[str, Any]:
    """
    Close, High and Low as one column per ticker, whatever shape Yahoo sent.

    yfinance returns (field, ticker) columns, sometimes (ticker, field), and
    for one ticker in older versions just flat field names.
    """
    out: Dict[str, Any] = {}
    if data is None or getattr(data, "empty", True):
        return {f: pd.DataFrame() for f in FIELDS}
    cols = data.columns
    for f in FIELDS:
        if isinstance(cols, pd.MultiIndex):
            if f in cols.get_level_values(0):
                x = data.xs(f, axis=1, level=0)
            elif cols.nlevels > 1 and f in cols.get_level_values(1):
                x = data.xs(f, axis=1, level=1)
            else:
                x = pd.DataFrame(index=data.index)
        elif f in cols:
            if len(batch) != 1:
                raise ValueError(f"Yahoo returned one flat table for {len(batch)} tickers, "
                                 f"so the prices cannot be matched to tickers")
            x = data[[f]].copy()
            x.columns = [batch[0]]
        else:
            x = pd.DataFrame(index=data.index)
        if isinstance(x, pd.Series):
            x = x.to_frame(batch[0])
        x = x.apply(pd.to_numeric, errors="coerce")
        x.columns = [str(c) for c in x.columns]
        x.index = normalise_index(pd, x.index)
        out[f] = x[~x.index.duplicated(keep="last")].sort_index()
    return out


def with_prices(close: Any, tickers: Sequence[str]) -> List[str]:
    return [t for t in tickers if t in close.columns and close[t].notna().any()]


class YahooLog(logging.Handler):
    """
    yfinance's own reason per failed ticker, from its log.

    yfinance 1.x keeps the reasons only in its log. Two kinds of line matter:
    «Failed to get ticker 'BSP.OL' reason: <cause>», and the summary
    «['BSP.OL', 'EAM.OL']: <error>». The summary can say «possibly delisted»
    when the real cause is a blocked network, so the cause line wins. Older
    versions also keep them in yf.shared._ERRORS; yahoo_reasons() reads both.
    """

    CAUSE = "Failed to get ticker '"

    def __init__(self) -> None:
        super().__init__(logging.ERROR)
        self.reasons: Dict[str, str] = {}
        self.causes: Dict[str, str] = {}

    def clear(self) -> None:
        self.reasons.clear()
        self.causes.clear()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            text = record.getMessage().strip()
            if text.startswith(self.CAUSE):
                ticker, _, cause = text[len(self.CAUSE):].partition("' reason: ")
                self.causes[ticker.upper()] = cause.strip()
                return
            head, sep, reason = text.partition("]: ")
            if sep and head.startswith("["):
                for t in ast.literal_eval(head + "]"):
                    self.reasons[str(t).upper()] = reason.strip()
        except Exception:
            pass        # an unexpected log line must never break a download


def yahoo_reasons(mods: Dict[str, Any], tickers: Sequence[str]) -> Dict[str, str]:
    """yfinance's own reason per failed ticker, from whichever place has it."""
    found: Dict[str, str] = {}
    try:
        shared = getattr(getattr(mods["yf"], "shared", None), "_ERRORS", None) or {}
        found.update({str(t).upper(): str(e) for t, e in shared.items()})
    except Exception:
        pass
    log = mods.get("yahoo_log")
    if log is not None:
        found.update(log.reasons)
        found.update(log.causes)
    # curl appends «See https://curl.se/...»; the cause is what comes before.
    return {t: found[t.upper()].strip().splitlines()[0].split(" See http")[0][:160]
            for t in tickers if found.get(t.upper(), "").strip()}


def fetch(step: Step, s: Settings, mods: Dict[str, Any], batch: Sequence[str],
          label: str, attempts: int, repair: Optional[bool] = None
          ) -> Tuple[Optional[Dict[str, Any]], Optional[BaseException]]:
    """One Yahoo request, retried with a doubling pause. Never raises."""
    pd, yf = mods["pd"], mods["yf"]
    last: Optional[BaseException] = None
    for attempt in range(1, attempts + 1):
        if mods.get("yahoo_log") is not None:
            mods["yahoo_log"].clear()
        try:
            data = yf.download(list(batch), start=s.start, auto_adjust=True,
                               repair=mods["repair"] if repair is None else repair,
                               progress=False, threads=True)
            fields = extract_fields(pd, data, batch)
            if with_prices(fields["Close"], batch):
                if attempt > 1:
                    step.info(f"{label}: succeeded on attempt {attempt}")
                return fields, None
            reasons = yahoo_reasons(mods, batch)
            last = StepError("Yahoo returned no prices"
                             + (f" ({next(iter(reasons.values()))})" if reasons else ""))
        except Exception as exc:
            last = exc
        if attempt < attempts:
            wait = s.pause * 2 ** (attempt - 1)
            step.info(f"{label}: attempt {attempt}/{attempts} failed ({describe(last)}); "
                      f"waiting {wait:.0f} s")
            _sleep(wait)
    return None, last


def combine(pd: Any, frames: Sequence[Any]) -> Any:
    frames = [f for f in frames if len(f.columns)]
    if not frames:
        return pd.DataFrame()
    x = pd.concat(frames, axis=1)
    # A ticker retried on its own comes last, so its column wins.
    return x.loc[:, ~x.columns.duplicated(keep="last")].sort_index()


def download_prices(step: Step, s: Settings, mods: Dict[str, Any],
                    tickers: List[str]) -> Dict[str, Any]:
    pd = mods["pd"]
    batches = [tickers[i:i + s.batch_size] for i in range(0, len(tickers), s.batch_size)]
    step.info(f"{len(tickers)} tickers in {len(batches)} batch(es) of up to {s.batch_size}; "
              f"from {s.start}, auto_adjust=True, repair={mods['repair']}")

    frames: Dict[str, List[Any]] = {f: [] for f in FIELDS}
    reasons: Dict[str, str] = {}
    last_error: Optional[BaseException] = None
    for no, batch in enumerate(batches, 1):
        label = f"batch {no}/{len(batches)}"
        fields, exc = fetch(step, s, mods, batch, label, s.retries)
        if fields is None:
            last_error = exc
            step.warn(f"{label} FAILED after {s.retries} attempt(s): {describe(exc)}")
            reasons.update({t: describe(exc) for t in batch})
            continue
        for f in FIELDS:
            frames[f].append(fields[f])
        got = with_prices(fields["Close"], batch)
        reasons.update(yahoo_reasons(mods, [t for t in batch if t not in got]))
        step.info(f"{label}: {len(got)}/{len(batch)} tickers with prices")

    close = combine(pd, frames["Close"])
    have = with_prices(close, tickers)
    if not have:
        raise StepError(
            f"Yahoo Finance returned no prices for any of the {len(tickers)} tickers. "
            f"Last error: {describe(last_error)}",
            hint="Check the internet connection, proxy or firewall. Yahoo may also be "
                 "rate limiting: wait 15-60 minutes. Updating yfinance often helps: "
                 "pip install -U yfinance. Test quickly with: "
                 "python management_download.py 5")

    missing = [t for t in tickers if t not in have]
    if missing:
        step.info(f"retrying {len(missing)} ticker(s) without prices, one at a time")
        for t in missing:
            fields, exc = fetch(step, s, mods, [t], t, 1)
            how = "on its own"
            if fields is None and mods["repair"]:
                # Some tickers fail inside yfinance's own repair (for example
                # «Period 'max' is invalid» or «Cannot convert non-finite
                # values»). One try without it; the price check still runs.
                fields, exc = fetch(step, s, mods, [t], t, 1, repair=False)
                how = "without Yahoo's price repair"
            if fields is not None:
                for f in FIELDS:
                    frames[f].append(fields[f])
                reasons.pop(t, None)
                step.info(f"{t}: prices found {how}")
            else:
                reasons[t] = (yahoo_reasons(mods, [t]).get(t)
                              or reasons.get(t) or describe(exc))
        close = combine(pd, frames["Close"])
        have = with_prices(close, tickers)

    close = close[have].copy()
    high = combine(pd, frames["High"]).reindex(index=close.index, columns=have)
    low = combine(pd, frames["Low"]).reindex(index=close.index, columns=have)
    no_prices = {t: reasons.get(t, "Yahoo returned no prices") for t in tickers
                 if t not in have}
    if no_prices:
        step.warn(f"{len(no_prices)} of {len(tickers)} ticker(s) have no prices and are "
                  f"left out (often delisted or renamed):")
        for t, why in list(no_prices.items())[:15]:
            step.info(f"  {t:<12} {why}")
        if len(no_prices) > 15:
            step.info(f"  ... and {len(no_prices) - 15} more, see ticker_status.csv")
    no_range = [t for t in have if high[t].isna().all() or low[t].isna().all()]
    if no_range:
        step.warn(f"No High/Low prices for {', '.join(no_range[:10])}"
                  f"{' ...' if len(no_range) > 10 else ''}: ATR stops cannot work for them")

    step.info(f"prices: {len(have)} tickers, {close.index[0].date()} -> "
              f"{close.index[-1].date()}, {len(close.index)} trading days")
    step.summary = f"{len(have)}/{len(tickers)} tickers with prices"
    return {"close": close, "high": high, "low": low, "no_prices": no_prices,
            "requested": list(tickers)}


# ══════════════════════════════════════════════════════════════════════════
# STEP 6 - CHECK PRICE QUALITY
# ══════════════════════════════════════════════════════════════════════════

def unit_factor(ratio: float) -> Optional[float]:
    """The power of ten a jump matches within UNIT_TOLERANCE, or None."""
    if not math.isfinite(ratio) or ratio <= 0:
        return None
    for f in UNIT_FACTORS:
        if abs(ratio / f - 1.0) <= UNIT_TOLERANCE:
            return f
    return None


def find_jumps(pd: Any, np: Any, series: Any) -> Tuple[Any, Any]:
    """(invalid prices, flagged jumps) exactly as kontroller_priser() finds them."""
    prices = pd.to_numeric(series, errors="coerce").dropna()
    invalid = prices[~np.isfinite(prices) | (prices <= 0)]
    good = prices[np.isfinite(prices) & (prices > 0)]
    previous = good.shift(1)
    ratio = good / previous
    hit = (ratio >= UPPER_RATIO) | (ratio <= LOWER_RATIO)
    jumps = pd.DataFrame({"previous_price": previous[hit], "price": good[hit],
                          "ratio": ratio[hit]})
    return invalid, jumps


def find_spikes(pd: Any, np: Any, series: Any) -> List[Tuple[Any, float, float, float]]:
    """(day, price before, price, price after) for each one-day bad print."""
    good = pd.to_numeric(series, errors="coerce")
    good = good[np.isfinite(good) & (good > 0)]
    values = good.to_numpy(dtype=float)
    found = []
    i = 1
    while i < len(values) - 1:
        up = values[i] / values[i - 1]
        back = values[i + 1] / values[i]
        flagged = (up >= UPPER_RATIO or up <= LOWER_RATIO) and \
            (back >= UPPER_RATIO or back <= LOWER_RATIO)
        if flagged and abs(up * back - 1.0) <= SPIKE_TOLERANCE:
            found.append((good.index[i], float(values[i - 1]), float(values[i]),
                          float(values[i + 1])))
            i += 2
            continue
        i += 1
    return found


def check_one(pd: Any, np: Any, ticker: str, close: Any, high: Any, low: Any
              ) -> Dict[str, Any]:
    """
    Check one ticker. Returns the (possibly repaired) columns and the issues.

    Invalid prices (zero, negative, infinite) are not prices; they are removed,
    which leaves a gap the lab already knows how to handle. Unit jumps are
    rescaled BACKWARDS, so the newest prices - the ones open positions are
    valued at - never change. Everything else is left for the caller to decide.
    """
    rows: List[Dict[str, Any]] = []
    invalid, jumps = find_jumps(pd, np, close)
    observations = int(pd.to_numeric(close, errors="coerce").notna().sum())
    for day, price in invalid.items():
        rows.append({"ticker": ticker, "date": str(day.date()),
                     "issue": "non_positive_or_non_finite", "price": float(price)})
    if len(invalid):
        close, high, low = close.copy(), high.copy(), low.copy()
        close[invalid.index] = np.nan
        high[invalid.index] = np.nan
        low[invalid.index] = np.nan

    # One bad day: remove that price, instead of taking either jump as real.
    spikes = find_spikes(pd, np, close)
    for day, before, price, after in spikes:
        rows.append({"ticker": ticker, "date": str(day.date()), "issue": "single_day_spike",
                     "previous_price": before, "price": price,
                     "ratio": price / before, "note": f"next price {after:.6g}"})
    if spikes:
        days = [d for d, *_ in spikes]
        close, high, low = close.copy(), high.copy(), low.copy()
        close[days] = np.nan
        high[days] = np.nan
        low[days] = np.nan
        _, jumps = find_jumps(pd, np, close)

    units = [(day, r, unit_factor(float(r["ratio"]))) for day, r in jumps.iterrows()]
    units = [(day, r, f) for day, r, f in units if f is not None]
    if units:
        multiplier = pd.Series(1.0, index=close.index)
        for day, _, f in units:
            multiplier[multiplier.index < day] *= f
        close, high, low = close * multiplier, high * multiplier, low * multiplier
        for day, r, f in units:
            rows.append({"ticker": ticker, "date": str(day.date()),
                         "issue": "unit_scale_artifact",
                         "previous_price": float(r["previous_price"]),
                         "price": float(r["price"]), "ratio": float(r["ratio"]),
                         "factor": f})
        # Verify rather than assume: check the repaired series again.
        _, jumps = find_jumps(pd, np, close)

    unresolved = []
    for day, r in jumps.iterrows():
        row = {"ticker": ticker, "date": str(day.date()),
               "issue": "unverified_adjusted_price_discontinuity",
               "previous_price": float(r["previous_price"]),
               "price": float(r["price"]), "ratio": float(r["ratio"])}
        rows.append(row)
        unresolved.append(row)
    return {"close": close, "high": high, "low": low, "rows": rows,
            "invalid": len(invalid), "spikes": len(spikes), "units": len(units),
            "unresolved": unresolved,
            "mostly_invalid": observations > 0
            and len(invalid) > MAX_INVALID_SHARE * observations,
            "observations": observations}


def check_prices(step: Step, s: Settings, mods: Dict[str, Any],
                 prices: Dict[str, Any]) -> Dict[str, Any]:
    pd, np = mods["pd"], mods["np"]
    close, high, low = prices["close"].copy(), prices["high"].copy(), prices["low"].copy()
    accepted = {a.strip().upper() for a in s.accept if a.strip()}
    accepted |= {to_ticker(a).upper() for a in accepted}
    step.info(f"rule: a move of {UPPER_RATIO:g}x or more between two observations needs "
              f"verification; an exact x10/x100/x1000 jump is rescaled")

    issues: List[Dict[str, Any]] = []
    status: Dict[str, str] = {}
    blocked: List[str] = []
    for t in list(close.columns):
        try:
            r = check_one(pd, np, t, close[t], high[t], low[t])
        except Exception as exc:
            # A problem in one ticker must not stop the others.
            issues.append({"ticker": t, "issue": "check_failed",
                           "action": "ticker_excluded", "note": describe(exc)})
            status[t] = "excluded: the price check itself failed"
            step.warn(f"{t}: the price check failed ({describe(exc)}) at {locate(exc)}. "
                      f"Ticker excluded.")
            continue
        close[t], high[t], low[t] = r["close"], r["high"], r["low"]
        notes = []
        for row in r["rows"]:
            if row["issue"] == "unit_scale_artifact":
                row["action"] = f"earlier_prices_rescaled_x{row['factor']:g}"
                notes.append(f"{row['date']} ratio {row['ratio']:.4g} -> earlier prices "
                             f"x{row['factor']:g}")
            elif row["issue"] == "non_positive_or_non_finite":
                row["action"] = ("ticker_excluded" if r["mostly_invalid"] else
                                 "blocks_run" if s.strict else "observation_removed")
            elif row["issue"] == "single_day_spike":
                row["action"] = "observation_removed"
            elif t.upper() in accepted:
                row["action"] = "accepted_by_user"
            else:
                row["action"] = "blocks_run" if s.strict else "ticker_excluded"
            issues.append(row)
        if r["units"]:
            step.info(f"{t:<12} repaired unit error: " + "; ".join(notes))
        if r["spikes"]:
            step.info(f"{t:<12} removed {r['spikes']} one-day bad price(s) (jump there "
                      f"and straight back)")
        if r["mostly_invalid"]:
            step.warn(f"{t:<12} {r['invalid']} of {r['observations']} prices are zero, "
                      f"negative or not numbers - ticker excluded")
            status[t] = "excluded: mostly invalid prices"
            continue
        if r["invalid"]:
            (step.warn if not s.strict else step.info)(
                f"{t:<12} {r['invalid']} zero/negative/invalid price(s)"
                + (" removed" if not s.strict else ""))
        if r["unresolved"] and t.upper() in accepted:
            step.warn(f"{t:<12} {len(r['unresolved'])} large jump(s) kept, accepted "
                      f"with --accept")
            status[t] = "accepted"
        elif r["unresolved"] or (s.strict and r["invalid"]):
            blocked.append(t)
            status[t] = "blocked" if s.strict else "excluded: unverified price jump"
        else:
            status[t] = "repaired" if (r["units"] or r["invalid"] or r["spikes"]) else "ok"

    if blocked:
        (step.info if s.strict else step.warn)(
            f"{len(blocked)} ticker(s) need verification (a jump of {UPPER_RATIO:g}x or "
            f"more that is not a unit error)" + ("" if s.strict else " - excluded:"))
        for t in blocked[:20]:
            first = next(i for i in issues if i["ticker"] == t and i.get("action")
                         in ("ticker_excluded", "blocks_run"))
            where = (f"{first.get('previous_price', float('nan')):.4g} -> "
                     f"{first.get('price', float('nan')):.4g} "
                     f"(x{first.get('ratio', float('nan')):.3g})"
                     if "ratio" in first else first["issue"])
            step.info(f"  {t:<12} {first.get('date', '')}  {where}")
        if len(blocked) > 20:
            step.info(f"  ... and {len(blocked) - 20} more")

    issue_file = s.out_dir / "price_issues.csv"
    columns = ["ticker", "date", "issue", "previous_price", "price", "ratio",
               "factor", "action", "note"]
    try:
        pd.DataFrame(issues, columns=columns).to_csv(issue_file, index=False)
        step.info(f"{len(issues)} issue(s) written to {issue_file.name}")
    except Exception as exc:
        step.warn(f"Could not write {issue_file.name}: {describe(exc)}")

    if s.strict and blocked:
        raise StepError(
            f"--strict: {len(blocked)} ticker(s) need verification: "
            + ", ".join(blocked[:8]) + (" ..." if len(blocked) > 8 else ""),
            hint=f"Check the dates in {issue_file.name} on another source. "
                 f"Accept checked tickers with --accept T1,T2, or run without --strict "
                 f"to exclude them and continue.")

    keep = [t for t in close.columns if not status.get(t, "").startswith("excluded")]
    if not keep:
        raise StepError("Every ticker failed the price check, so there is nothing to use",
                        hint=f"Open {issue_file.name}. If the jumps are real, accept them "
                             f"with --accept.")
    counts = {k: sum(1 for v in status.values() if v.startswith(k))
              for k in ("ok", "repaired", "accepted", "excluded")}
    step.summary = ", ".join(f"{n} {k}" for k, n in counts.items() if n)
    return {"close": close[keep], "high": high[keep], "low": low[keep],
            "status": status, "no_prices": prices["no_prices"],
            "requested": prices["requested"], "issues": issues}


# ══════════════════════════════════════════════════════════════════════════
# STEP 7 - BUILD INDICATORS
# ══════════════════════════════════════════════════════════════════════════

def build_indicators(step: Step, s: Settings, mods: Dict[str, Any],
                     checked: Dict[str, Any]) -> Dict[str, Any]:
    """The same indicators hent_kurser() builds, with the same settings."""
    pd, np = mods["pd"], mods["np"]
    close, high, low = checked["close"], checked["high"], checked["low"]

    try:
        previous = close.shift(1)
        # fmax skips a missing value instead of warning about it, as nanmax does.
        tr = np.fmax(np.fmax((high - low).abs().to_numpy(),
                             (high - previous).abs().to_numpy()),
                     (low - previous).abs().to_numpy())
        tr = pd.DataFrame(tr, index=close.index, columns=close.columns)
        atr20 = tr.rolling(ATR_DAYS, min_periods=max(5, ATR_DAYS // 2)).mean()
    except Exception as exc:
        raise StepError(f"ATR{ATR_DAYS} could not be calculated: {describe(exc)}",
                        hint="High/Low prices may be missing or misaligned with Close.") from exc
    try:
        sma10 = close.rolling(10).mean()
        sma50 = close.rolling(SMA_DAYS).mean()
        ema20 = close.ewm(span=20, adjust=False, min_periods=20).mean()
    except Exception as exc:
        raise StepError(f"Moving averages could not be calculated: {describe(exc)}") from exc
    try:
        daily = close.pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan)
        market_index = (1.0 + daily.mean(axis=1).fillna(0.0)).cumprod()
    except Exception as exc:
        raise StepError(f"The market index could not be calculated: {describe(exc)}") from exc

    if not np.isfinite(market_index.to_numpy()).all() or (market_index <= 0).any():
        step.warn("The equal-weight market index has invalid values; check the prices.")
    history = close.notna().sum()
    short = history[history < MIN_HISTORY_DAYS]
    if len(short):
        step.info(f"{len(short)} ticker(s) have under {MIN_HISTORY_DAYS} days of prices, "
                  f"so the lab cannot use them for a signal yet: "
                  + ", ".join(short.index[:10]) + (" ..." if len(short) > 10 else ""))
    with_sma = int(sma50.iloc[-1].notna().sum()) if len(sma50) else 0
    step.info(f"ATR{ATR_DAYS}, SMA10, SMA{SMA_DAYS}, EMA20 for {len(close.columns)} "
              f"tickers; SMA{SMA_DAYS} available today for {with_sma}")
    step.info(f"market index: {market_index.iloc[-1]:.3f} on "
              f"{market_index.index[-1].date()} (1.000 on {market_index.index[0].date()})")

    last = pd.DataFrame({
        "ticker": close.columns,
        "last_date": [str(close[t].last_valid_index().date())
                      if close[t].last_valid_index() is not None else ""
                      for t in close.columns],
        "close": close.ffill().iloc[-1].to_numpy(),
        "sma10": sma10.iloc[-1].to_numpy(), "sma50": sma50.iloc[-1].to_numpy(),
        "ema20": ema20.iloc[-1].to_numpy(), "atr20": atr20.iloc[-1].to_numpy(),
        "observations": history.to_numpy()})
    step.summary = f"{len(close.columns)} tickers"
    return {"last": last, "market_index": market_index}


# ══════════════════════════════════════════════════════════════════════════
# STEP 8 - SAVE RESULTS
# ══════════════════════════════════════════════════════════════════════════

def save_results(step: Step, s: Settings, mods: Dict[str, Any], checked: Dict[str, Any],
                 indicators: Dict[str, Any]) -> List[Path]:
    pd = mods["pd"]
    close = checked["close"]

    rows = []
    for t in checked["requested"]:
        if t in checked["no_prices"]:
            rows.append({"ticker": t, "status": "no_prices", "note": checked["no_prices"][t]})
            continue
        state = checked["status"].get(t, "ok")
        series = close[t].dropna() if t in close.columns else None
        rows.append({"ticker": t, "status": state.split(":")[0],
                     "first_date": str(series.index[0].date()) if series is not None and len(series) else "",
                     "last_date": str(series.index[-1].date()) if series is not None and len(series) else "",
                     "observations": int(len(series)) if series is not None else 0,
                     "note": state.split(": ", 1)[1] if ": " in state else ""})

    jobs = [
        ("management_prices_close.csv", lambda p: checked["close"].to_csv(p, index_label="Date")),
        ("management_prices_high.csv", lambda p: checked["high"].to_csv(p, index_label="Date")),
        ("management_prices_low.csv", lambda p: checked["low"].to_csv(p, index_label="Date")),
        ("indicators_last.csv", lambda p: indicators["last"].to_csv(p, index=False)),
        ("market_index.csv", lambda p: indicators["market_index"].rename("market_index")
         .to_csv(p, index_label="Date")),
        ("ticker_status.csv", lambda p: pd.DataFrame(rows).to_csv(p, index=False)),
    ]
    written: List[Path] = []
    failed: List[str] = []
    for name, write in jobs:
        path = s.out_dir / name
        try:
            write(path)
        except PermissionError:
            # Almost always the file is open in Excel. Keep the result anyway.
            alt = path.with_name(f"{path.stem}_{datetime.now():%Y%m%d_%H%M%S}{path.suffix}")
            try:
                write(alt)
                step.warn(f"{name} is locked (open in Excel?); wrote {alt.name} instead")
                path = alt
            except Exception as exc:
                failed.append(f"{name} ({describe(exc)})")
                continue
        except Exception as exc:
            failed.append(f"{name} ({describe(exc)} at {locate(exc)})")
            continue
        written.append(path)
        step.info(f"wrote {path.name}")
    if failed:
        raise StepError(f"{len(failed)} file(s) could not be written: " + "; ".join(failed),
                        hint="Close the files in Excel and check free disk space.")
    step.info(f"folder: {s.out_dir}")
    step.summary = f"{len(written)} files in {s.out_dir.name}/"
    return written


# ══════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════

def has_data(folder: Path) -> bool:
    try:
        return bool(article_files(folder / NLP_DIR)) or (folder / TICKER_LIST).is_file()
    except OSError:
        return False


def find_excel_dir(explicit: Optional[str]) -> Tuple[Path, Tuple[str, ...]]:
    """
    (ExcelData folder, what was searched).

    --excel-dir is used as given. Otherwise the first candidate that actually
    has articles or the ticker list wins. An empty ExcelData folder next to
    the script must not hide the real one on the Desktop.
    """
    if explicit:
        return Path(explicit).expanduser().resolve(), ()
    candidates: List[Path] = []
    if os.environ.get("AKSJE_BASE_DIR"):
        candidates.append(Path(os.environ["AKSJE_BASE_DIR"]).expanduser())
    candidates += [THIS_FILE.parent / "ExcelData", Path(LEGACY_EXCEL_DIR)]
    searched = []
    for c in candidates:
        found = has_data(c)
        searched.append(f"{c} - {'has data' if found else 'no articles or ticker list'}")
        if found:
            return c.resolve(), tuple(searched)
    first = next((c for c in candidates if c.is_dir()), candidates[-1])
    return first.resolve(), tuple(searched)


def parse_args(argv: Optional[Sequence[str]]) -> Settings:
    p = argparse.ArgumentParser(
        prog="management_download",
        description="Management sentiment: download and check prices, step by step.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="examples:\n"
               "  python management_download.py 5\n"
               "  python management_download.py all\n"
               "  python management_download.py BSP EAM 2020.OL\n"
               "  python management_download.py all --strict\n"
               "  python management_download.py all --accept BSP.OL,EAM.OL")
    p.add_argument("companies", nargs="*",
                   help='"all", a number such as 5, or companies from the article list')
    p.add_argument("--excel-dir", metavar="PATH", help="the ExcelData folder")
    p.add_argument("--start", default=PRICE_START, metavar="YYYY-MM-DD",
                   help=f"first price date (default {PRICE_START}, as in the lab)")
    p.add_argument("--strict", action="store_true",
                   help="stop at any unverified price jump, as the lab does")
    p.add_argument("--accept", default="", metavar="T1,T2",
                   help="comma-separated tickers whose price jumps you have checked")
    p.add_argument("--batch-size", type=int, default=50, metavar="N")
    p.add_argument("--retries", type=int, default=3, metavar="N")
    p.add_argument("--no-articles", action="store_true",
                   help="skip the article download and use the articles in DataNLP")
    p.add_argument("--pause", type=float, default=2.0, metavar="SECONDS",
                   help="wait before the first retry; doubles each time")
    a = p.parse_args(list(argv) if argv is not None else None)

    try:
        date.fromisoformat(a.start)
    except ValueError:
        p.error(f"--start must be a date like 2019-01-01, not {a.start!r}")
    if a.batch_size < 1 or a.retries < 1 or a.pause < 0:
        p.error("--batch-size and --retries must be 1 or more, --pause 0 or more")
    companies = [c for arg in (a.companies or [COMPANIES])
                 for c in str(arg).replace(",", " ").split()] or ["all"]
    base_dir, searched = find_excel_dir(a.excel_dir)
    return Settings(base_dir=base_dir, searched=searched, companies=companies,
                    start=a.start, batch_size=a.batch_size, retries=a.retries,
                    pause=a.pause, strict=a.strict, articles=not a.no_articles,
                    accept=tuple(x for x in a.accept.replace(" ", ",").split(",") if x))


def configure_console() -> None:
    """Keep the console readable when Windows redirects output to a file."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def main(argv: Optional[Sequence[str]] = None) -> int:
    configure_console()
    warnings.filterwarnings("ignore", category=FutureWarning)
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    settings = parse_args(argv)
    report = Report()

    report.say(WIDE)
    report.say(" MANAGEMENT SENTIMENT - PRICE DOWNLOAD  (from SentimentHendelseLab)")
    report.say(WIDE)
    report.say(f" Started   : {datetime.now():%Y-%m-%d %H:%M:%S}")
    report.say(f" Companies : {' '.join(settings.companies)}")
    report.say(f" ExcelData : {settings.base_dir}")
    report.say(" Price jump: " + ("--strict, any unverified jump stops the run"
                                  if settings.strict else
                                  "unverified jumps exclude that company, the rest continue"))
    if settings.accept:
        report.say(f" Accepted  : {', '.join(settings.accept)}")

    try:
        mods = report.run(1, "Check setup", check_setup, settings)
        articles = report.run(2, "Read company list", read_articles, settings, mods)
        tickers = report.run(3, "Select companies", select_companies, settings, articles)
        report.run(4, "Download new articles", download_articles, settings, mods, tickers)
        prices = report.run(5, "Download prices from Yahoo", download_prices,
                            settings, mods, tickers)
        checked = report.run(6, "Check price quality", check_prices, settings, mods, prices)
        indicators = report.run(7, "Build indicators", build_indicators,
                                settings, mods, checked)
        report.run(8, "Save results", save_results, settings, mods, checked, indicators)
        if checked:
            report.facts = {
                "tickers_with_prices": len(checked["close"].columns),
                "tickers_without_prices": sorted(checked["no_prices"]),
                "tickers_excluded": sorted(t for t, v in checked["status"].items()
                                           if v.startswith("excluded")),
                "tickers_repaired": sorted(t for t, v in checked["status"].items()
                                           if v == "repaired")}
    except KeyboardInterrupt:
        report.interrupted = True
        report.say()
        report.say("Stopped by the user (Ctrl+C).")
    return report.finish(settings)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as exc:    # a bug in the reporting itself
        print(f"\nINTERNAL ERROR in {THIS_FILE.name} at {locate(exc)}: {describe(exc)}",
              file=sys.stderr, flush=True)
        traceback.print_exc()
        sys.exit(1)
