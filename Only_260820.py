from runtime_config import LazyImport, configure_paths
from download_status import record_source
#Only working code - 26.08.18

# =========================
# Standard library
# =========================
import os
import sys
import re
import csv
import json
import ssl
import time
from time import sleep
import math
import glob
import shutil
import random
import io
import logging
import traceback
import statistics
import pickle
from pathlib import Path
from threading import Timer
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from email.message import EmailMessage
import smtplib

# Email helpers
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# =========================
# Warnings / asyncio fixes
# =========================
import warnings
# Deferred until a strategy is explicitly run.

# Fix for asyncio loop conflict with Playwright
nest_asyncio = LazyImport('nest_asyncio')
# Deferred until a strategy is explicitly run.

# =========================
# Third-party libraries
# =========================
np = LazyImport('numpy')
pd = LazyImport('pandas')
plt = LazyImport('matplotlib.pyplot')

# Finance / data
yf = LazyImport('yfinance')
fa = LazyImport('fredapi')
pdr = LazyImport('pandas_datareader')
web = LazyImport('pandas_datareader.data')
feedparser = LazyImport('feedparser')

# Web / scraping / automation
requests = LazyImport('requests')
BeautifulSoup = LazyImport('bs4', 'BeautifulSoup')
Article = LazyImport('newspaper', 'Article')
import webbrowser
schedule = LazyImport('schedule')
sync_playwright = LazyImport('playwright.sync_api', 'sync_playwright')

# Selenium (webdriver + helpers)
webdriver = LazyImport('selenium', 'webdriver')
Keys = LazyImport('selenium.webdriver.common.keys', 'Keys')
By = LazyImport('selenium.webdriver.common.by', 'By')
ActionChains = LazyImport('selenium.webdriver.common.action_chains', 'ActionChains')
Service = LazyImport('selenium.webdriver.chrome.service', 'Service')
Options = LazyImport('selenium.webdriver.chrome.options', 'Options')
WebDriverWait = LazyImport('selenium.webdriver.support.ui', 'WebDriverWait')
Select = LazyImport('selenium.webdriver.support.ui', 'Select')
EC = LazyImport('selenium.webdriver.support', 'expected_conditions')
NoSuchElementException = LazyImport('selenium.common.exceptions', 'NoSuchElementException')
ChromeDriverManager = LazyImport('webdriver_manager.chrome', 'ChromeDriverManager')

# Office / Excel
openpyxl = LazyImport('openpyxl')
load_workbook = LazyImport('openpyxl', 'load_workbook')
xlsxwriter = LazyImport('xlsxwriter')

# Images / OCR / CV
Image = LazyImport('PIL', 'Image')
cv2 = LazyImport('cv2')
fitz = LazyImport('fitz')
pytesseract = LazyImport('pytesseract')

# Text / NLP
nltk = LazyImport('nltk')
sent_tokenize = LazyImport('nltk.tokenize', 'sent_tokenize')
TextBlob = LazyImport('textblob', 'TextBlob')
detect = LazyImport('langdetect', 'detect')
unidecode = LazyImport('unidecode')

# Machine learning / transformers / torch / sklearn
torch = LazyImport('torch')
F = LazyImport('torch.nn.functional')
BertTokenizer = LazyImport('transformers', 'BertTokenizer')
BertForSequenceClassification = LazyImport('transformers', 'BertForSequenceClassification')
AutoTokenizer = LazyImport('transformers', 'AutoTokenizer')
AutoModelForSequenceClassification = LazyImport('transformers', 'AutoModelForSequenceClassification')
pipeline = LazyImport('transformers', 'pipeline')
RandomForestClassifier = LazyImport('sklearn.ensemble', 'RandomForestClassifier')
TfidfVectorizer = LazyImport('sklearn.feature_extraction.text', 'TfidfVectorizer')

# Misc third-party
chardet = LazyImport('chardet')
fredapi = LazyImport('fredapi')
feedparser = LazyImport('feedparser')
unidecode = LazyImport('unidecode')
Client = LazyImport('wordpress_xmlrpc', 'Client')
WordPressPost = LazyImport('wordpress_xmlrpc', 'WordPressPost')
ServerConnectionError = LazyImport('wordpress_xmlrpc.exceptions', 'ServerConnectionError')
InvalidCredentialsError = LazyImport('wordpress_xmlrpc.exceptions', 'InvalidCredentialsError')
pyautogui = LazyImport('pyautogui')

# =========================
# Optional / utilities
# =========================
import io

# =========================
# Downloads / setup
# =========================
# Deferred until a strategy is explicitly run.
# Deferred until a strategy is explicitly run.

# Add these imports after the existing imports in the scraper
matplotlib = LazyImport('matplotlib')
# Deferred until a strategy is explicitly run.
plt = LazyImport('matplotlib.pyplot')
mdates = LazyImport('matplotlib.dates')
from io import BytesIO
import base64
matplotlib = LazyImport('matplotlib')
# Deferred until a strategy is explicitly run.
plt = LazyImport('matplotlib.pyplot')
from io import BytesIO
import base64

import os
import re
import sys
import time
import json
import logging
import traceback
pd = LazyImport('pandas')
np = LazyImport('numpy')
from pathlib import Path
from datetime import datetime, timedelta, time as dt_time
from typing import Optional, Dict, List, Set, Tuple
pytz = LazyImport('pytz')


## Hvordan installere nye packages - C:/Users/ander/Desktop/Python_K4/venv/Scripts/python.exe -m pip install pyautogui

# Credentials belong in environment variables, never in source control.

# ══════════════════════════════════════════════════════════════════════════
# APP-PASSORDET TIL MAILEN
# ══════════════════════════════════════════════════════════════════════════
#
# Ingen passordverdi står i denne filen. Den sto her før — hardkodet, og
# dermed i git-historikken for alltid.
#
# Letingen bor i innsidehandel_pipeline.py, som ligger i samme mappe. Ligger
# den ikke der (du har bare kopiert Only-filen ut), faller vi tilbake på
# miljøvariabelen alene, og sier fra om hva som mangler.

def _miljo_paa(navn: str, standard: bool = False) -> bool:
    """
    En av/på-bryter fra miljøet. «1», «ja», «true», «on» er på.

    Poenget er at du skal slippe å redigere en 8000-linjers fil for å skru på
    en skraping. Er variabelen ikke satt, gjelder standardverdien.
    """
    v = os.environ.get(navn)
    if v is None or not str(v).strip():
        return standard
    return str(v).strip().lower() in ("1", "ja", "j", "true", "yes", "y", "on")


def _mail_passord(datamappe=None) -> str:
    """App-passordet, eller tom streng. Feiler aldri."""
    try:
        from innsidehandel_pipeline import finn_mail_passord
    except Exception:
        p = os.environ.get("AKSJE_MAIL_APP_PASSWORD", "").strip()
        if not p:
            print("  Fant ikke innsidehandel_pipeline.py ved siden av denne "
                  "filen, og AKSJE_MAIL_APP_PASSWORD er ikke satt.\n"
                  "  Legg de to filene i samme mappe, eller kjør:\n"
                  '     setx AKSJE_MAIL_APP_PASSWORD "xxxx xxxx xxxx xxxx"')
        return p
    return finn_mail_passord(datamappe)


##PB ROE
#Claude code 3 - #CAGR 25% - many parameters
# Hvor mange av de best rangerte selskapene som logges med score per
# rebalanseringsdato. Loggen er grunnlaget master.py bygger den samlede
# scoren på; halen av lista er uinteressant og ville doblet filstørrelsen.
SCORE_LOG_TOPP = 40


def PBROE_All3():

    #full liste med tickers - https://live.euronext.com/en/markets/oslo/equities/list

    #For flere versjoner gå på eldre versjon av denne 

    #Nyeste versjonen - funker kanskje best?
    def PB_ROE_Momentum_StrategyTrades6_1():
        """
        PB-ROE-Momentum STRATEGY  —  V6.1
        =================================
        V6.1 fixes the period-toggle click.

        Change vs V6:
            • The "Quarterly" tab on TradingView's stats page is not a
            <button> — it's a <span class="content-h5ZKzylb">Quarterly</span>
            inside a <span class="tabContent-nqU_VJml"> wrapper. V6's
            selectors looked for <button>, so the click silently no-op'd
            and we kept reading whatever default view (annual) was
            showing.
            • V6.1 clicks the actual "Quarterly" span by exact text, waits
            for the header row to update from "2024" / "FY '24" to a Qx
            pattern, and only then extracts.
            • If the toggle still fails (e.g. element not in DOM yet), the
            code falls back to reading whatever view is showing — same as
            before — but now logs WHICH view it ended up reading, so you
            can confirm.

        Everything else from V6 (period-regex includes "2024", locked cells
        → null placeholders, row container detection by walking up from
        label, etc.) is unchanged.

        FIX (2026-08-14): save_history() krasjet med
        "ValueError: Excel file format cannot be determined" fordi
        Master_PB_ROE_History.xlsx fantes, men var 0 bytes / ugyldig xlsx
        etter et avbrutt skriv. Se save_history() og run_pipeline().
        """

        import os
        import re
        import time
        import shutil
        import logging
        import calendar
        from datetime import datetime

        import pandas as pd
        import numpy as np

        # ──────────────────────────────────────────────────────
        # CONFIGURATION
        # ──────────────────────────────────────────────────────

        TICKER_FILE = r"C:\Users\ander\Desktop\Python_K4\ExcelData\Data_BT\AllTickers_OSEBX_TW_current.xlsx"
        #TICKER_FILE = r"C:\Users\ander\Desktop\Python_K4\ExcelData\Data_BT\AllTickers_OSEBX_Norbit.xlsx"

        BASE_DIR   = r"C:\Users\ander\Desktop\Python_K4\ExcelData\DataPB_ROE"
        PB_DIR     = os.path.join(BASE_DIR, "WorkingDataPB")
        ROE_DIR    = os.path.join(BASE_DIR, "WorkingDataROE")
        MCAP_DIR   = os.path.join(BASE_DIR, "WorkingDataMCap")
        IND_DIR    = os.path.join(BASE_DIR, "WorkingDataIndustry")
        MOM_DIR    = os.path.join(BASE_DIR, "WorkingDataMomentum")
        HIST_DIR   = os.path.join(BASE_DIR, "HistoricalData")
        MERGED_DIR = os.path.join(BASE_DIR, "MergedData")
        PORTF_DIR  = os.path.join(BASE_DIR, "Portfolio")
        BT_DIR     = os.path.join(BASE_DIR, "Backtest")
        DEBUG_DIR  = os.path.join(BASE_DIR, "Debug")

        DRIVER = "playwright"
        TOGGLE_TO_QUARTERLY = True   # click "Q" button before scraping

        N_PORTFOLIO         = 10
        SELL_RANK_THRESHOLD = 15
        MAX_PER_INDUSTRY    = 3

        W_PB        = 0.30
        W_ROE       = 0.30
        W_MOM       = 0.25
        W_ROE_TREND = 0.15

        FILTER_NEGATIVE_PB  = True
        FILTER_NEGATIVE_ROE = True
        FILTER_NEGATIVE_MOM = True
        MIN_ROE             = 0.0
        MAX_PB              = 10.0
        ROE_TREND_QUARTERS  = 4

        MOM_SKIP_RECENT_MONTHS = 1
        MOM_LOOKBACK_MONTHS    = 12

        PAGE_LOAD_WAIT  = 8
        ACTION_WAIT     = 1.5
        ELEMENT_TIMEOUT = 15

        DEBUG_DUMP_ON_FAILURE = True

        # ──────────────────────────────────────────────────────
        # LOGGING
        # ──────────────────────────────────────────────────────

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s  %(levelname)-8s  %(message)s",
            datefmt="%H:%M:%S",
        )
        log = logging.getLogger(__name__)

        for _d in (PB_DIR, ROE_DIR, MCAP_DIR, IND_DIR, MOM_DIR,
                HIST_DIR, MERGED_DIR, PORTF_DIR, BT_DIR, DEBUG_DIR):
            os.makedirs(_d, exist_ok=True)

        TODAY_STR = datetime.now().strftime("%Y-%m-%d")

        # ──────────────────────────────────────────────────────
        # UTILITIES
        # ──────────────────────────────────────────────────────

        def clean_tv_text(raw):
            if raw is None:
                return ""
            return (str(raw)
                    .replace("\u202a", "")
                    .replace("\u202c", "")
                    .replace("\u2212", "-")
                    .strip())

        def safe_float(text):
            if text in (None, "N/A", "", "—", "-"):
                return None
            try:
                return round(float(str(text).replace("%", "").replace("\u2212", "-").replace("\u00a0", "").replace(" ", "").replace(",", ".")), 4)
            except (ValueError, TypeError):
                return None

        def save_txt(folder, prefix, ticker, value):
            path = os.path.join(folder, f"{prefix}_{TODAY_STR}_{ticker}.txt")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(str(value))

        def archive_txt_files(folder):
            archive = os.path.join(folder, f"{TODAY_STR}_Archive")
            os.makedirs(archive, exist_ok=True)
            for fname in os.listdir(folder):
                if fname.endswith(".txt"):
                    shutil.move(os.path.join(folder, fname),
                                os.path.join(archive, fname))

        def rows_to_excel(rows, folder, suffix):
            df       = pd.DataFrame(rows)
            out_path = os.path.join(folder, f"{TODAY_STR}_{suffix}.xlsx")
            df.to_excel(out_path, index=False)
            log.info("Saved %d rows → %s", len(df), out_path)
            return out_path

        # ──────────────────────────────────────────────────────
        # PERIOD LABEL → DATE
        # ──────────────────────────────────────────────────────
        #
        # TradingView period labels we care about:
        #   "Q1 '26"          → quarter,  end of Mar 2026
        #   "Q1 '26|Mar 2026" → same, with subtitle baked in
        #   "FY '24"          → annual,   end of Dec 2024
        #   "2024"            → annual,   end of Dec 2024  (NEW in V6)
        #   "2024|Dec 2024"   → annual,   end of Dec 2024
        #   "Current" / "TTM" → today
        # ──────────────────────────────────────────────────────

        MONTH_MAP = {
            "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4,
            "May": 5, "Jun": 6, "Jul": 7, "Aug": 8,
            "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
        }

        def clean_period_label(label):
            if not label:
                return ""
            return str(label).split("|")[0].strip()

        def quarter_label_to_date(label):
            raw  = clean_tv_text(label)
            base = raw.split("|")[0].strip()

            # Pipe subtitle wins if present
            if "|" in raw:
                date_part = raw.split("|", 1)[1].strip()
                m = re.match(
                    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})",
                    date_part)
                if m:
                    month = MONTH_MAP[m.group(1)]
                    year  = int(m.group(2))
                    last  = calendar.monthrange(year, month)[1]
                    return datetime(year, month, last)

            # Quarter
            m = re.match(r"Q([1-4])\s*'?(\d{2,4})$", base)
            if m:
                q  = int(m.group(1))
                yr = int(m.group(2))
                if yr < 100:
                    yr += 2000
                end_month = q * 3
                last      = calendar.monthrange(yr, end_month)[1]
                return datetime(yr, end_month, last)

            # FY '24
            m = re.match(r"(?:FY|Annual)\s*'?(\d{2,4})$", base, re.IGNORECASE)
            if m:
                yr = int(m.group(1))
                if yr < 100:
                    yr += 2000
                return datetime(yr, 12, 31)

            # Plain "2024" (annual mode in TV stats page)
            m = re.match(r"^(20\d{2}|19\d{2})$", base)
            if m:
                return datetime(int(m.group(1)), 12, 31)

            if base in ("Current", "TTM"):
                return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

            return None

        # ──────────────────────────────────────────────────────
        # ROE TREND
        # ──────────────────────────────────────────────────────

        def compute_roe_trend(roe_history):
            vals = [safe_float(v) for _, v in roe_history if safe_float(v) is not None]
            if len(vals) < 2:
                return None
            vals = vals[-ROE_TREND_QUARTERS:]
            if len(vals) < 2:
                return None
            x     = np.arange(len(vals), dtype=float)
            slope = float(np.polyfit(x, vals, 1)[0])
            return round(slope, 4)

        # ──────────────────────────────────────────────────────
        # MOMENTUM
        # ──────────────────────────────────────────────────────

        def fetch_momentum(ticker):
            import yfinance as yf
            yf_ticker = ticker + ".OL"
            result    = {"Company Name": ticker, "Momentum": None, "Momentum_pct": None}
            try:
                total_months = MOM_LOOKBACK_MONTHS + MOM_SKIP_RECENT_MONTHS + 2
                hist = yf.download(
                    yf_ticker, period=f"{total_months}mo", interval="1mo",
                    progress=False, auto_adjust=True)
                if hist is None or len(hist) < MOM_LOOKBACK_MONTHS + MOM_SKIP_RECENT_MONTHS:
                    log.warning("Not enough price history for %s", ticker)
                    return result
                close = hist["Close"].dropna()
                if len(close) < MOM_LOOKBACK_MONTHS + MOM_SKIP_RECENT_MONTHS:
                    return result
                idx_recent   = -(1 + MOM_SKIP_RECENT_MONTHS)
                idx_past     = -(MOM_LOOKBACK_MONTHS + MOM_SKIP_RECENT_MONTHS)
                price_recent = float(close.iloc[idx_recent])
                price_past   = float(close.iloc[idx_past])
                if price_past <= 0:
                    return result
                mom = round((price_recent / price_past) - 1, 4)
                result["Momentum"]     = mom
                result["Momentum_pct"] = round(mom * 100, 2)
                log.info("Momentum %-10s → %+.1f%%", ticker, mom * 100)
            except Exception as exc:
                log.warning("fetch_momentum(%s): %s", ticker, exc)
            return result

        # ══════════════════════════════════════════════════════
        # JS EXTRACTORS — V6
        # ══════════════════════════════════════════════════════
        #
        # Two functions injected into the page:
        #
        #   1. JS_EXTRACT_TABLE
        #      Finds the stats table, returns:
        #         {
        #           headers:        [ "Q1 '26|Mar 2026", "Q4 '25|Dec 2025", ... ],
        #           row_containers: <opaque, used for diagnostics only>,
        #         }
        #      The table is identified by finding the smallest container that
        #      holds ≥4 leaf-cells whose top-level text matches a period
        #      pattern AND whose immediate parent contains many sibling rows
        #      with the same column count.
        #
        #   2. JS_EXTRACT_ROW (parameterised by label)
        #      Given a metric name (e.g. "Price to book ratio"), finds the
        #      row in the table with that label and returns its values
        #      column-by-column, using `null` for locked / em-dash cells so
        #      length matches the header row.
        #
        # ══════════════════════════════════════════════════════

        JS_EXTRACT_TABLE = r"""
        (() => {
            const clean = s => (s||'').replace(/[\u202a\u202c]/g,'')
                                    .replace(/\u2212/g,'-').trim();

            const QTR_RE      = /^Q[1-4]\s*'?\d{2,4}$/;
            const FY_RE       = /^(?:FY|Annual)\s*'?\d{2,4}$/i;
            const YEAR_RE     = /^(?:19|20)\d{2}$/;
            const MONTH_YR_RE = /^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}$/;
            const SPECIAL_RE  = /^(Current|TTM)$/i;

            const isPeriod = txt => QTR_RE.test(txt) || FY_RE.test(txt)
                || YEAR_RE.test(txt) || SPECIAL_RE.test(txt);

            // Top-level text of an element: text from direct text nodes plus
            // text from any inline children that are NOT subvalue/help-icon.
            const topText = el => {
                let t = '';
                for (const n of el.childNodes) {
                    if (n.nodeType === 3) t += n.textContent;
                    else if (n.nodeType === 1) {
                        const cls = n.getAttribute('class') || '';
                        if (cls.indexOf('subvalue-') !== -1) continue;
                        // skip help-icon spans (they often contain "?")
                        if (n.tagName === 'BUTTON') continue;
                        t += n.textContent;
                    }
                }
                return clean(t);
            };

            // For a header value-cell, find a "Mon YYYY" subtitle nearby.
            const findSubvalue = el => {
                // try descendants first
                const inside = el.querySelector('[class*="subvalue-"]');
                if (inside) {
                    const t = clean(inside.textContent);
                    if (MONTH_YR_RE.test(t)) return t;
                }
                // try parent's subvalue children
                if (el.parentElement) {
                    const sibs = el.parentElement.querySelectorAll('[class*="subvalue-"]');
                    for (const s of sibs) {
                        const t = clean(s.textContent);
                        if (MONTH_YR_RE.test(t)) return t;
                    }
                }
                // try next siblings
                let sib = el.nextElementSibling;
                for (let i = 0; i < 3 && sib; i++) {
                    const cls = sib.getAttribute('class') || '';
                    if (cls.indexOf('subvalue-') !== -1) {
                        const t = clean(sib.textContent);
                        if (MONTH_YR_RE.test(t)) return t;
                    }
                    sib = sib.nextElementSibling;
                }
                return '';
            };

            // 1) Find every leaf value-cell whose top text is a period label.
            const all = [...document.querySelectorAll('[class*="value-"]')];
            const periodCells = [];
            for (const el of all) {
                const cls = el.getAttribute('class') || '';
                if (cls.indexOf('subvalue-') !== -1) continue;
                // leaf only
                if (el.querySelector('[class*="value-"]:not([class*="subvalue-"])')) continue;
                const txt = topText(el);
                if (isPeriod(txt)) periodCells.push({el, txt});
            }
            if (periodCells.length < 2) return {headers: [], reason: 'no-period-cells'};

            // 2) Group cells by their nearest "row" ancestor — the ancestor
            //    where ALL of these period cells share the same parent or
            //    same grandparent. The ancestor with the most period cells
            //    as descendants is the header row.
            const ancestorScore = new Map();
            for (const pc of periodCells) {
                let p = pc.el.parentElement;
                for (let depth = 0; depth < 6 && p; depth++) {
                    const score = (ancestorScore.get(p) || 0) + 1;
                    ancestorScore.set(p, score);
                    p = p.parentElement;
                }
            }
            let headerRow = null, bestScore = 0;
            for (const [el, score] of ancestorScore) {
                // prefer the deepest (smallest) ancestor that holds ≥4 period cells
                if (score < 4) continue;
                if (score > bestScore || (score === bestScore && headerRow &&
                    el.contains(headerRow) === false &&
                    headerRow.contains(el))) {
                    headerRow = el;
                    bestScore = score;
                }
            }
            if (!headerRow) {
                // fallback: any ancestor with ≥2 period cells
                for (const [el, score] of ancestorScore) {
                    if (score >= 2 && score > bestScore) {
                        headerRow = el;
                        bestScore = score;
                    }
                }
            }
            if (!headerRow) return {headers: [], reason: 'no-header-row'};

            // 3) Within headerRow, collect period cells in DOM order and
            //    pair each with its subvalue.
            const headers = [];
            const headerCellEls = [];
            for (const pc of periodCells) {
                if (!headerRow.contains(pc.el)) continue;
                const sub = findSubvalue(pc.el);
                headers.push(sub ? `${pc.txt}|${sub}` : pc.txt);
                headerCellEls.push(pc.el);
            }

            // 4) Stash the headerRow on window so the row extractor can find
            //    its sibling data rows. We use a unique attribute.
            headerRow.setAttribute('data-tv-header-row', '1');

            return {
                headers: headers,
                n_cells: headerCellEls.length,
                row_score: bestScore,
            };
        })()
        """

        def _make_js_extract_row(label_text):
            # Escape for inclusion as JS string literal.
            safe = label_text.replace("\\", "\\\\").replace("'", "\\'")
            return r"""
            (() => {
                const LABEL = '""" + safe + r"""';
                const clean = s => (s||'').replace(/[\u202a\u202c]/g,'')
                                        .replace(/\u2212/g,'-').trim();
                const NUMERIC_RE = /^-?[\d.,]+\s*[BMKT%]?$/;
                const DASH_RE    = /^[\u2014\u2013\-]$/;     // — – -
                const LOCK_HINTS = ['lock', 'paywall', 'premium'];

                // Same topText helper as the table extractor.
                const topText = el => {
                    let t = '';
                    for (const n of el.childNodes) {
                        if (n.nodeType === 3) t += n.textContent;
                        else if (n.nodeType === 1) {
                            const cls = n.getAttribute('class') || '';
                            if (cls.indexOf('subvalue-') !== -1) continue;
                            if (n.tagName === 'BUTTON') continue;
                            t += n.textContent;
                        }
                    }
                    return clean(t);
                };

                // 1) Find the cell whose TOP-LEVEL text is exactly LABEL.
                //    (Top-level so the help-icon ? sibling doesn't pollute.)
                let labelEl = null;
                const candidates = document.querySelectorAll(
                    'span, div, td, [class*="title-"], [class*="label-"]');
                for (const el of candidates) {
                    if (topText(el) === LABEL) {
                        // prefer the deepest matching node
                        let inner = el;
                        while (inner.children.length === 1 &&
                            topText(inner.children[0]) === LABEL) {
                            inner = inner.children[0];
                        }
                        labelEl = inner;
                        break;
                    }
                }
                if (!labelEl) return {found: false, values: [], reason: 'label-not-found'};

                // 2) Walk up from labelEl until we hit an ancestor that ALSO
                //    contains numeric/lock value-cells as its OTHER descendants.
                //    The first such ancestor is the row container for this metric.
                const NUMERIC_OR_DASH = (txt) => NUMERIC_RE.test(txt) || DASH_RE.test(txt);

                const isLocked = el => {
                    // Lock cells in TV typically render as an SVG icon and have
                    // no text. We treat any value-cell with empty text and a
                    // child SVG as locked.
                    if (clean(el.textContent) !== '') return false;
                    if (el.querySelector('svg')) return true;
                    const cls = el.getAttribute('class') || '';
                    return LOCK_HINTS.some(h => cls.toLowerCase().indexOf(h) !== -1);
                };

                let row = labelEl;
                let valueCells = [];
                for (let depth = 0; depth < 10 && row; depth++) {
                    row = row.parentElement;
                    if (!row) break;

                    // collect candidate value-cells inside row (leaves only)
                    const cells = [...row.querySelectorAll('[class*="value-"]')]
                        .filter(v => {
                            const cls = v.getAttribute('class') || '';
                            if (cls.indexOf('subvalue-') !== -1) return false;
                            if (v.querySelector(
                                '[class*="value-"]:not([class*="subvalue-"])')) return false;
                            return true;
                        });

                    // we want cells that are NUMERIC, DASH, or LOCKED — and
                    // we want at least 2 of them to confirm we're in a data row
                    let nData = 0;
                    for (const c of cells) {
                        const t = topText(c);
                        if (NUMERIC_OR_DASH(t) || isLocked(c)) nData++;
                    }
                    if (nData >= 2 && nData <= 30) {
                        // accept this ancestor as the row container
                        valueCells = cells;
                        break;
                    }
                }
                if (valueCells.length === 0) {
                    return {found: true, values: [], reason: 'no-value-cells'};
                }

                // 3) Convert each cell to its value, using null for locks / dashes.
                const values = valueCells.map(c => {
                    const t = topText(c);
                    if (NUMERIC_RE.test(t)) return t;
                    if (DASH_RE.test(t)) return null;       // em-dash → no data
                    if (t === '') return null;              // locked / empty
                    if (isLocked(c)) return null;
                    // anything else (period label etc.) — return null too,
                    // alignment is what matters
                    return null;
                });

                return {found: true, values: values};
            })()
            """

        # ══════════════════════════════════════════════════════
        # PLAYWRIGHT SCRAPER
        # ══════════════════════════════════════════════════════

        class PlaywrightScraper:
            def __init__(self):
                from playwright.sync_api import sync_playwright
                self._pw      = sync_playwright().start()
                self._browser = self._pw.chromium.launch(
                    headless=False, args=["--start-maximized"])
                ctx        = self._browser.new_context(no_viewport=True)
                self._page = ctx.new_page()
                self._page.set_default_timeout(ELEMENT_TIMEOUT * 1000)

            def _dump_debug(self, ticker, suffix="headers"):
                if not DEBUG_DUMP_ON_FAILURE:
                    return
                try:
                    html = self._page.content()
                    path = os.path.join(DEBUG_DIR,
                                        f"debug_{suffix}_{ticker}_{TODAY_STR}.html")
                    with open(path, "w", encoding="utf-8") as fh:
                        fh.write(html)
                    log.warning("Debug HTML dumped → %s", path)
                except Exception as exc:
                    log.debug("Debug dump failed: %s", exc)

            def open_company(self, ticker, first=False):
                try:
                    url = f"https://www.tradingview.com/symbols/OSL-{ticker.upper()}/"
                    self._page.goto(url, wait_until="domcontentloaded", timeout=20000)
                    time.sleep(PAGE_LOAD_WAIT)
                    current_url = self._page.url
                    if "/symbols/OSL-" not in current_url:
                        log.warning("open_company(%s): redirected to %s",
                                    ticker, current_url)
                        return False
                    # Quick check that the symbol resolved (404 page won't have
                    # the standard symbol header)
                    try:
                        title = self._page.title() or ""
                        if "Page not found" in title or "404" in title:
                            log.warning("open_company(%s): 404 — wrong ticker symbol?",
                                        ticker)
                            return False
                    except Exception:
                        pass
                    return True
                except Exception as exc:
                    log.error("open_company(%s) failed: %s", ticker, exc)
                    return False

            def navigate_to_statistics(self):
                try:
                    current_url = self._page.url.rstrip("/")
                    m = re.search(r"(/symbols/OSL-[^/]+)", current_url)
                    if not m:
                        log.error("navigate_to_statistics: no OSL- segment")
                        return False
                    symbol_root = current_url.split("/symbols/")[0] + m.group(1)
                    stats_url   = symbol_root + "/financials-statistics-and-ratios/"
                    self._page.goto(stats_url, wait_until="domcontentloaded",
                                    timeout=20000)
                    time.sleep(3)
                    return True
                except Exception as exc:
                    log.error("navigate_to_statistics failed: %s", exc)
                    return False

            def _toggle_quarterly_view(self):
                """
                Click the "Quarterly" tab on TV's stats page.

                DOM structure (as of 2026-05):
                    <span aria-hidden="false" class="tabContent-nqU_VJml">
                        <span class="content-h5ZKzylb">Quarterly</span>
                    </span>

                We target the inner span by exact text. Playwright will click
                on its hit-target (the parent <span> or <button> wrapper that
                actually has the click handler) automatically.

                Returns True if the click succeeded AND the table headers
                switched from annual labels (2024 / FY '24) to quarterly
                labels (Q1 '26 etc.); False otherwise.
                """
                if not TOGGLE_TO_QUARTERLY:
                    return False

                # Selectors to try, in order of specificity.
                # The first one matches the exact DOM you pasted.
                # Subsequent ones are fallbacks in case TV rotates class hashes.
                selectors = [
                    'span.content-h5ZKzylb:text-is("Quarterly")',
                    'span:text-is("Quarterly")',
                    '[class*="content-"]:text-is("Quarterly")',
                    'button:has-text("Quarterly")',
                    'div[role="tab"]:has-text("Quarterly")',
                ]

                clicked = False
                for sel in selectors:
                    try:
                        loc = self._page.locator(sel).first
                        # Wait briefly for it to be there, but don't fail hard
                        loc.wait_for(state="visible", timeout=4000)
                        loc.scroll_into_view_if_needed(timeout=2000)
                        loc.click(timeout=4000)
                        log.info("Clicked Quarterly tab via: %s", sel)
                        clicked = True
                        break
                    except Exception as exc:
                        log.debug("Selector failed (%s): %s", sel, exc)
                        continue

                if not clicked:
                    log.warning("Could not click Quarterly tab — "
                                "will read whatever view is showing")
                    return False

                # Wait for the header row to repaint with quarterly labels.
                # We poll the JS extractor and check for any "Qn 'YY" header.
                import time as _t
                deadline = _t.time() + 8
                while _t.time() < deadline:
                    try:
                        result = self._page.evaluate(JS_EXTRACT_TABLE)
                        headers = result.get("headers", []) if result else []
                        if any(re.match(r"Q[1-4]\s*'?\d{2,4}",
                                        clean_period_label(h)) for h in headers):
                            log.info("Quarterly view confirmed (%d headers)",
                                    len(headers))
                            return True
                    except Exception:
                        pass
                    _t.sleep(0.4)

                log.warning("Clicked Quarterly but headers still look annual — "
                            "extraction will proceed anyway")
                return False

            def _scroll_table_into_view(self):
                try:
                    self._page.evaluate("window.scrollBy(0, 400)"); time.sleep(0.8)
                    self._page.evaluate("window.scrollBy(0, 600)"); time.sleep(0.8)
                    self._page.evaluate("window.scrollBy(0, 600)"); time.sleep(0.8)
                except Exception:
                    pass

            def _get_headers(self, ticker=""):
                try:
                    result = self._page.evaluate(JS_EXTRACT_TABLE)
                    if result and result.get("headers"):
                        headers = [clean_tv_text(h) for h in result["headers"]]
                        sample = []
                        for h in headers[:5]:
                            d = quarter_label_to_date(h)
                            sample.append(
                                f"{clean_period_label(h)}→"
                                f"{d.strftime('%Y-%m-%d') if d else '?'}")
                        log.info("Headers (%d): %s", len(headers), sample)
                        return headers
                    log.warning("Headers: extraction returned empty for %s "
                                "(reason=%s)",
                                ticker, result.get("reason") if result else "?")
                except Exception as exc:
                    log.debug("_get_headers: %s", exc)
                self._dump_debug(ticker, "headers")
                return []

            def _get_row(self, label_text):
                """Returns list of strings/None aligned to header columns, or []."""
                try:
                    js     = _make_js_extract_row(label_text)
                    result = self._page.evaluate(js)
                    if not result:
                        return []
                    if not result.get("found"):
                        return []
                    vals = result.get("values") or []
                    return vals
                except Exception as exc:
                    log.debug("_get_row('%s'): %s", label_text, exc)
                    return []

            def _row_for_any_label(self, labels):
                for lbl in labels:
                    row = self._get_row(lbl)
                    if row:
                        return lbl, row
                return None, []

            def _align_row_to_headers(self, row_values, headers):
                """
                Pair each header with the corresponding row value.
                If lengths match, zip directly. If row is shorter (locked
                cells dropped by site), right-align (most recent on the right).
                """
                if not headers:
                    return []
                n_h = len(headers)
                n_r = len(row_values)
                if n_r == n_h:
                    aligned = list(row_values)
                elif n_r < n_h:
                    aligned = [None] * (n_h - n_r) + list(row_values)
                else:
                    aligned = list(row_values[-n_h:])
                return list(zip(headers, aligned))

            def scrape_statistics(self, ticker):
                # 1) Scroll the stats table into view first — the Quarterly
                #    tab is part of the table header, not always visible above
                #    the fold on first load.
                self._scroll_table_into_view()
                # 2) Click the Quarterly tab (waits until headers actually
                #    repaint as Qx 'YY before returning).
                self._toggle_quarterly_view()
                # 3) Extract.
                headers = self._get_headers(ticker)

                # Diagnostic: report which view we actually ended up reading.
                view_kind = "unknown"
                if headers:
                    qn = sum(1 for h in headers
                            if re.match(r"Q[1-4]", clean_period_label(h)))
                    yn = sum(1 for h in headers
                            if re.match(r"^(?:19|20)\d{2}$|^FY\s*'?\d{2,4}$",
                                        clean_period_label(h)))
                    if qn >= yn and qn > 0:
                        view_kind = "quarterly"
                    elif yn > 0:
                        view_kind = "annual"
                log.info("Reading %s view (%d period columns) for %s",
                        view_kind, len(headers), ticker)

                # Current value: rightmost numeric cell of each row
                pb_label, pb_row = self._row_for_any_label(
                    ("Price to book ratio", "Price to book", "P/B ratio", "PB ratio"))
                roe_label, roe_row = self._row_for_any_label(
                    ("Return on equity %", "Return on equity", "ROE %", "ROE"))

                def rightmost_numeric(row):
                    for v in reversed(row):
                        if v is not None:
                            s = clean_tv_text(str(v))
                            if re.match(r'^-?[\d.,]+\s*[BMKT%]?$', s):
                                return s
                    return "N/A"

                pb_current  = rightmost_numeric(pb_row)
                roe_current = rightmost_numeric(roe_row)

                pb_aligned  = self._align_row_to_headers(pb_row, headers) if pb_row else []
                roe_aligned = self._align_row_to_headers(roe_row, headers) if roe_row else []

                # Build per-period history
                history_rows = []
                pb_dict      = {h: v for h, v in pb_aligned if v is not None}
                roe_dict     = {h: v for h, v in roe_aligned if v is not None}
                all_periods  = list(dict.fromkeys(
                    [h for h, _ in pb_aligned] + [h for h, _ in roe_aligned]))

                for raw_period in all_periods:
                    period_date = quarter_label_to_date(raw_period)
                    period_str  = clean_period_label(raw_period)
                    pb_val      = pb_dict.get(raw_period)
                    roe_val     = roe_dict.get(raw_period)
                    if pb_val is None and roe_val is None:
                        continue
                    history_rows.append({
                        "Company Name": ticker,
                        "Period"      : period_str,
                        "Period_Date" : period_date.strftime("%Y-%m-%d") if period_date else None,
                        "PB"          : clean_tv_text(pb_val) if pb_val else None,
                        "ROE"         : clean_tv_text(roe_val) if roe_val else None,
                        "Scraped_date": TODAY_STR,
                    })

                # ROE_trend over the most recent quarters (excluding "Current")
                roe_for_trend = [(h, v) for h, v in roe_aligned
                                if v is not None
                                and clean_period_label(h) not in ("Current", "TTM")]
                roe_trend = compute_roe_trend(roe_for_trend)

                current_row = {
                    "Company Name": ticker,
                    "PB Number"   : pb_current,
                    "ROE Number"  : roe_current,
                    "ROE_trend"   : roe_trend,
                }

                sample = [
                    (clean_period_label(h),
                    pb_dict.get(h, "?"),
                    roe_dict.get(h, "?"))
                    for h in all_periods[:4]
                ]
                log.info("Stats %-10s → PB=%s  ROE=%s  trend=%s  (%d periods) %s",
                        ticker, pb_current, roe_current, roe_trend,
                        len(history_rows), sample)
                return current_row, history_rows

            def scrape_overview(self, ticker):
                mcap, industry = "N/A", "N/A"
                try:
                    js_mcap = r"""
                    (() => {
                        let el = document.querySelector('[data-field="market_cap_calc"]');
                        if (el) {
                            const v = el.querySelector('span[class*="value"]')
                                || el.querySelector('span:last-child');
                            if (v && /[\d]/.test(v.textContent))
                                return v.textContent.trim();
                            if (/[\d]/.test(el.textContent))
                                return el.textContent.trim();
                        }
                        for (const e of [...document.querySelectorAll('span,div')]) {
                            if (['Market cap','Market capitalization']
                                    .includes(e.textContent.trim())) {
                                const sib = e.nextElementSibling;
                                if (sib && /[\d]/.test(sib.textContent))
                                    return sib.textContent.trim();
                            }
                        }
                        return null;
                    })()
                    """
                    r = self._page.evaluate(js_mcap)
                    if r:
                        mcap = clean_tv_text(r)
                except Exception as exc:
                    log.warning("MCap(%s): %s", ticker, exc)

                try:
                    js_ind = r"""
                    (() => {
                        let el = document.querySelector('[data-field="industry"]');
                        if (el) {
                            const a = el.querySelector('a');
                            return a ? a.textContent.trim() : el.textContent.trim();
                        }
                        for (const e of [...document.querySelectorAll('span,div,dt')]) {
                            if (e.textContent.trim() === 'Industry') {
                                const sib = e.nextElementSibling;
                                if (sib) {
                                    const a = sib.querySelector('a');
                                    if (a) return a.textContent.trim();
                                    const t = sib.textContent.trim();
                                    if (t && t !== 'Industry') return t;
                                }
                            }
                        }
                        return null;
                    })()
                    """
                    r = self._page.evaluate(js_ind)
                    if r:
                        industry = clean_tv_text(r)
                except Exception as exc:
                    log.warning("Industry(%s): %s", ticker, exc)

                log.info("Overview %-10s → MCap=%s  Industry=%s",
                        ticker, mcap, industry)
                return {"Company Name": ticker,
                        "MCap Number": mcap, "Industry": industry}

            def quit(self):
                try:
                    self._browser.close()
                    self._pw.stop()
                except Exception:
                    pass

        # ──────────────────────────────────────────────────────
        # MERGE / HISTORY / FILTER / SCORE / STRATEGY
        # ──────────────────────────────────────────────────────

        def merge_all(stats_rows, overview_rows, momentum_rows):
            df_s = pd.DataFrame(stats_rows)
            df_o = pd.DataFrame(overview_rows)
            df_m = pd.DataFrame(momentum_rows)
            merged = (df_s
                    .merge(df_o, on="Company Name", how="outer")
                    .merge(df_m, on="Company Name", how="outer"))
            merged.drop_duplicates(subset=["Company Name"], inplace=True)
            out = os.path.join(MERGED_DIR, f"Merged_{TODAY_STR}.xlsx")
            merged.to_excel(out, index=False)
            log.info("Merged → %s (%d rows)", out, len(merged))
            return out

        def save_history(all_history_rows):
                    """
                    Skriver historikk til Master_PB_ROE_History.xlsx.

                    Robust mot 0-byte / korrupt master: validerer ZIP-signaturen
                    (PK\\x03\\x04) før read_excel, og flytter ugyldig fil til side.

                    NB tmp-filnavn: pandas velger Excel-engine ut fra FILENDELSEN.
                    "....xlsx.tmp" gir ValueError: No engine for filetype: 'tmp'.
                    Derfor må tmp-filen også ende på .xlsx, og vi setter engine
                    eksplisitt.
                    """
                    master = os.path.join(HIST_DIR, "Master_PB_ROE_History.xlsx")
                    tmp    = os.path.join(HIST_DIR, "Master_PB_ROE_History.tmp.xlsx")

                    today_df = pd.DataFrame(all_history_rows)
                    if today_df.empty:
                        log.warning("save_history: ingen rader å skrive — hopper over")
                        return master

                    if "Period_Date" in today_df.columns:
                        today_df["Period_Date"] = pd.to_datetime(
                            today_df["Period_Date"], errors="coerce")

                    # Rydd bort en eventuell tmp fra et avbrutt run
                    if os.path.exists(tmp):
                        try:
                            os.remove(tmp)
                        except Exception:
                            pass

                    # ── Valider eksisterende master før lesing ────────────────────
                    existing = None
                    if os.path.exists(master):
                        try:
                            size = os.path.getsize(master)
                            with open(master, "rb") as fh:
                                head = fh.read(4)
                        except Exception as exc:
                            size, head = -1, b""
                            log.error("Kunne ikke inspisere master: %s", exc)

                        if not (size > 0 and head.startswith(b"PK")):
                            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            bad   = master.replace(".xlsx", f"_CORRUPT_{stamp}.bak")
                            try:
                                shutil.move(master, bad)
                                log.error("Master var ugyldig (%d bytes, head=%r) → "
                                        "flyttet til %s. Bygger ny master.",
                                        size, head, os.path.basename(bad))
                            except Exception as exc:
                                log.error("Kunne ikke flytte korrupt master: %s", exc)
                        else:
                            try:
                                existing = pd.read_excel(master, engine="openpyxl")
                            except Exception as exc:
                                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                bad   = master.replace(".xlsx", f"_UNREADABLE_{stamp}.bak")
                                try:
                                    shutil.move(master, bad)
                                except Exception:
                                    pass
                                log.error("Kunne ikke lese master (%s) → bygger ny.", exc)
                                existing = None

                    # ── Slå sammen ────────────────────────────────────────────────
                    if existing is not None and not existing.empty:
                        if "Period_Date" in existing.columns:
                            existing["Period_Date"] = pd.to_datetime(
                                existing["Period_Date"], errors="coerce")
                        if "Scraped_date" in existing.columns:
                            existing = existing[
                                existing["Scraped_date"].astype(str).str[:10] != TODAY_STR]
                        combined = pd.concat([existing, today_df], ignore_index=True)
                    else:
                        combined = today_df

                    # ── Atomisk skriv: .tmp.xlsx → os.replace ─────────────────────
                    combined.to_excel(tmp, index=False, engine="openpyxl")
                    os.replace(tmp, master)

                    # ── Datert backup ─────────────────────────────────────────────
                    try:
                        bdir = os.path.join(HIST_DIR, "Backups")
                        os.makedirs(bdir, exist_ok=True)
                        shutil.copy2(master, os.path.join(
                            bdir, f"Master_PB_ROE_History_{TODAY_STR}.xlsx"))
                    except Exception as exc:
                        log.warning("Backup feilet (ikke kritisk): %s", exc)

                    log.info("History master → %s (%d total rows)", master, len(combined))
                    if "Period_Date" in combined.columns:
                        dated = combined["Period_Date"].notna().sum()
                        total = len(combined)
                        log.info("Period_Date coverage: %d / %d (%.0f%%)",
                                dated, total, 100 * dated / total if total else 0)
                    return master


        def filter_data(file_path):
            df = pd.read_excel(file_path)
            for col in ("PB Number", "ROE Number", "Momentum", "ROE_trend"):
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            before = len(df)
            mask   = pd.Series([True] * len(df))
            for col in ("PB Number", "ROE Number", "Momentum"):
                if col in df.columns:
                    mask &= df[col].notna()
            if FILTER_NEGATIVE_PB and "PB Number" in df.columns:
                mask &= df["PB Number"] >= 0
            if FILTER_NEGATIVE_ROE and "ROE Number" in df.columns:
                mask &= df["ROE Number"] >= MIN_ROE
            if FILTER_NEGATIVE_MOM and "Momentum" in df.columns:
                mask &= df["Momentum"] >= 0
            if "PB Number" in df.columns:
                mask &= df["PB Number"] <= MAX_PB
            df_f = df[mask].copy()
            out  = file_path.replace(".xlsx", "_Filtered.xlsx")
            df_f.to_excel(out, index=False)
            log.info("Filter: %d → %d rows (removed %d)",
                    before, len(df_f), before - len(df_f))
            return out

        def calculate_scores(file_path):
            df = pd.read_excel(file_path)
            for col in ("PB Number", "ROE Number", "Momentum"):
                df[col] = pd.to_numeric(df[col], errors="coerce")
            if "ROE_trend" in df.columns:
                df["ROE_trend"] = pd.to_numeric(df["ROE_trend"], errors="coerce")
            industry_col = next(
                (c for c in df.columns if "industry" in c.lower()), None)

            def _score(group):
                g = group.copy()
                if len(g) < 3:
                    return g
                g["PB_percentile"]  = 1 - g["PB Number"].rank(pct=True)
                g["ROE_percentile"] = g["ROE Number"].rank(pct=True)
                g["MOM_percentile"] = g["Momentum"].rank(pct=True)
                if "ROE_trend" in g.columns and g["ROE_trend"].notna().sum() >= 2:
                    g["ROET_percentile"] = g["ROE_trend"].rank(pct=True)
                else:
                    g["ROET_percentile"] = 0.5
                g["Combined_score"] = (
                    W_PB        * g["PB_percentile"]  +
                    W_ROE       * g["ROE_percentile"] +
                    W_MOM       * g["MOM_percentile"] +
                    W_ROE_TREND * g["ROET_percentile"])
                return g

            if industry_col:
                df = df.groupby(industry_col, group_keys=False).apply(_score)
            if "Combined_score" not in df.columns:
                df["Combined_score"] = np.nan
            unscored = df["Combined_score"].isna()
            if unscored.any():
                sub = df[unscored].copy()
                sub["PB_percentile"]   = 1 - sub["PB Number"].rank(pct=True)
                sub["ROE_percentile"]  = sub["ROE Number"].rank(pct=True)
                sub["MOM_percentile"]  = sub["Momentum"].rank(pct=True)
                sub["ROET_percentile"] = (sub["ROE_trend"].rank(pct=True)
                                        if "ROE_trend" in sub.columns else 0.5)
                sub["Combined_score"] = (
                    W_PB        * sub["PB_percentile"]  +
                    W_ROE       * sub["ROE_percentile"] +
                    W_MOM       * sub["MOM_percentile"] +
                    W_ROE_TREND * sub["ROET_percentile"])
                df.update(sub)
            df["Momentum_pct"] = (df["Momentum"] * 100).round(2)
            df.sort_values("Combined_score", ascending=False, inplace=True)
            df.reset_index(drop=True, inplace=True)
            df.insert(0, "Score_Rank", df.index + 1)
            out = os.path.join(MERGED_DIR, f"Scored_{TODAY_STR}.xlsx")
            df.to_excel(out, index=False)
            log.info("Scored file: %s", out)
            return out

        def apply_strategy(scored_path):
            df           = pd.read_excel(scored_path)
            industry_col = next(
                (c for c in df.columns if "industry" in c.lower()), None)
            selected, ind_counts = [], {}
            for _, row in df.iterrows():
                if len(selected) >= N_PORTFOLIO:
                    break
                ind = row.get(industry_col, "Unknown") if industry_col else "Unknown"
                ind_counts[ind] = ind_counts.get(ind, 0)
                if ind_counts[ind] >= MAX_PER_INDUSTRY:
                    continue
                selected.append(row)
                ind_counts[ind] += 1
            if not selected:
                log.warning("No stocks selected — check filters")
                return None
            n_pos        = len(selected)
            weight       = round(1.0 / n_pos, 4)
            portfolio_df = pd.DataFrame(selected).copy()
            portfolio_df["Weight_pct"] = round(weight * 100, 2)
            portfolio_df["Date"]       = TODAY_STR
            portfolio_df["Signal"]     = "HOLD"

            prev_path    = os.path.join(PORTF_DIR, "Current_Portfolio.xlsx")
            prev_tickers = set()
            if os.path.exists(prev_path):
                prev_df      = pd.read_excel(prev_path)
                prev_tickers = set(prev_df["Company Name"].tolist())
                log.info("Previous portfolio: %d positions", len(prev_tickers))

            current_tickers = set(portfolio_df["Company Name"].tolist())
            new_buys        = current_tickers - prev_tickers
            sells           = prev_tickers    - current_tickers
            holds           = current_tickers & prev_tickers

            portfolio_df.loc[portfolio_df["Company Name"].isin(new_buys), "Signal"] = "BUY"
            portfolio_df.loc[portfolio_df["Company Name"].isin(holds),    "Signal"] = "HOLD"

            sell_rows = []
            if sells:
                sell_df               = df[df["Company Name"].isin(sells)].copy()
                sell_df["Signal"]     = "SELL"
                sell_df["Weight_pct"] = 0.0
                sell_df["Date"]       = TODAY_STR
                sell_rows             = sell_df.to_dict("records")

            all_instructions = pd.concat([
                portfolio_df, pd.DataFrame(sell_rows)
            ], ignore_index=True) if sell_rows else portfolio_df

            cols_order = [
                "Signal", "Company Name", "Weight_pct",
                "Score_Rank", "Combined_score",
                "PB Number", "ROE Number", "Momentum_pct",
                "ROE_trend", "MCap Number",
                industry_col if industry_col else "Industry",
                "Date",
            ]
            cols_order       = [c for c in cols_order if c in all_instructions.columns]
            all_instructions = all_instructions[cols_order]

            out_path = os.path.join(PORTF_DIR, f"Portfolio_{TODAY_STR}.xlsx")
            all_instructions.to_excel(out_path, index=False)
            portfolio_df.to_excel(prev_path, index=False)

            changes_log = os.path.join(PORTF_DIR, "Portfolio_Changes_Log.xlsx")
            if os.path.exists(changes_log):
                old_log = pd.read_excel(changes_log)
                new_log = pd.concat([old_log, all_instructions], ignore_index=True)
            else:
                new_log = all_instructions
            new_log.to_excel(changes_log, index=False)

            log.info("=" * 55)
            log.info("  PORTFOLIO INSTRUCTIONS  (%s)", TODAY_STR)
            log.info("  Positions: %d  |  Weight each: %.1f%%", n_pos, weight * 100)
            for sig in ("BUY", "HOLD", "SELL"):
                group = all_instructions[all_instructions["Signal"] == sig]
                if group.empty:
                    continue
                log.info("  -- %s --", sig)
                for _, r in group.iterrows():
                    mom  = r.get("Momentum_pct", "?")
                    roe  = r.get("ROE Number",   "?")
                    pb   = r.get("PB Number",    "?")
                    rank = r.get("Score_Rank",   "?")
                    log.info("    %-10s  Rank:%-3s  PB:%-5s  ROE:%-6s  Mom:%+.1f%%",
                            r["Company Name"], rank, pb, roe,
                            float(mom) if mom not in ("?", None) else 0.0)
            log.info("=" * 55)
            return out_path

        # ──────────────────────────────────────────────────────
        # MAIN PIPELINE
        # ──────────────────────────────────────────────────────

        def load_tickers():
            df = pd.read_excel(TICKER_FILE)
            df.drop(df.columns[0], axis=1, inplace=True)
            tickers = [str(t).strip() for t in df["Company"].tolist()]
            log.info("Loaded %d tickers", len(tickers))
            return tickers

        def make_scraper():
            return PlaywrightScraper()

        def run_pipeline():
            log.info("=" * 55)
            log.info("  PB-ROE-Momentum STRATEGY V6 — %s", TODAY_STR)
            log.info("  Weights: PB=%.2f  ROE=%.2f  MOM=%.2f  ROET=%.2f",
                    W_PB, W_ROE, W_MOM, W_ROE_TREND)
            log.info("  Buy top %d  |  Sell rank>%d  |  Max %d/industry",
                    N_PORTFOLIO, SELL_RANK_THRESHOLD, MAX_PER_INDUSTRY)
            log.info("=" * 55)

            tickers       = load_tickers()
            stats_rows    = []
            overview_rows = []
            momentum_rows = []
            all_hist_rows = []
            scraper       = make_scraper()
            failed_tickers = []
            record_source("pbroe_data", status="FAILED", detail="Download started; not yet validated",
                          network_attempted=True, expected_count=len(tickers))

            try:
                for i, ticker in enumerate(tickers):
                    log.info("--- [%d/%d]  %s ---", i + 1, len(tickers), ticker)
                    try:
                        if not scraper.open_company(ticker, first=(i == 0)):
                            log.warning("Skipping %s (open_company failed)", ticker)
                            failed_tickers.append(ticker)
                            continue
                        ov = scraper.scrape_overview(ticker)
                        overview_rows.append(ov)
                        save_txt(MCAP_DIR, "MCap",     ticker, ov["MCap Number"])
                        save_txt(IND_DIR,  "Industry", ticker, ov["Industry"])
                        if scraper.navigate_to_statistics():
                            st, hist = scraper.scrape_statistics(ticker)
                            stats_rows.append(st)
                            all_hist_rows.extend(hist)
                            save_txt(PB_DIR,  "PB",  ticker, st["PB Number"])
                            save_txt(ROE_DIR, "ROE", ticker, st["ROE Number"])
                        else:
                            log.warning("Could not reach Statistics for %s", ticker)
                            failed_tickers.append(ticker)
                    except Exception as exc:
                        failed_tickers.append(ticker)
                        log.error("Error on %s: %s", ticker, exc)
            finally:
                scraper.quit()

            log.info("=== Fetching momentum (yfinance) ===")
            for ticker in tickers:
                row_m = fetch_momentum(ticker)
                momentum_rows.append(row_m)
                save_txt(MOM_DIR, "Momentum", ticker,
                        row_m.get("Momentum_pct", "N/A"))

            rows_to_excel(stats_rows,    MERGED_DIR, "Raw_Stats")
            rows_to_excel(overview_rows, MERGED_DIR, "Raw_Overview")
            rows_to_excel(momentum_rows, MERGED_DIR, "Raw_Momentum")

            # FIX: historikk er ren bokføring — merge/filter/score/portefølje
            # bruker IKKE denne filen. En feil her skal aldri drepe hele runet
            # etter ~290 scrapede tickere (slik den gjorde 2026-08-14).
            if all_hist_rows:
                try:
                    save_history(all_hist_rows)
                except Exception as exc:
                    raise RuntimeError("PB-ROE history could not be saved") from exc
            usable = [r for r in stats_rows if safe_float(r.get("PB Number")) is not None
                      and safe_float(r.get("ROE Number")) is not None]
            usable_tickers = {str(r.get("Company Name", "")) for r in usable}
            failed_tickers = sorted(set(failed_tickers) | (set(tickers) - usable_tickers))
            record_source("pbroe_data", status="PARTIAL" if failed_tickers or not all_hist_rows else "DOWNLOADED",
                          detail="Fundamental observations downloaded; historical availability starts at observation date",
                          network_attempted=True, expected_count=len(tickers), usable_count=len(usable),
                          downloaded_count=len(usable), cached_count=0, issues=failed_tickers)
            if failed_tickers or not all_hist_rows:
                raise RuntimeError("PB-ROE fundamental download incomplete: " + ", ".join(failed_tickers)
                                   + ("; no history rows" if not all_hist_rows else ""))
            for d in (PB_DIR, ROE_DIR, MCAP_DIR, IND_DIR, MOM_DIR):
                archive_txt_files(d)

            log.info("=== Merging, Filtering, Scoring ===")
            merged_path   = merge_all(stats_rows, overview_rows, momentum_rows)
            filtered_path = filter_data(merged_path)
            scored_path   = calculate_scores(filtered_path)

            log.info("=== Applying Strategy Rules ===")
            portfolio_path = apply_strategy(scored_path)

            log.info("=== All done. ===")
            log.info("  Scored    : %s", os.path.basename(scored_path))
            log.info("  Portfolio : %s",
                    os.path.basename(portfolio_path) if portfolio_path else "none")
            log.info("  History   : Master_PB_ROE_History.xlsx")

        run_pipeline()
    PB_ROE_Momentum_StrategyTrades6_1()


    #skal være samme som over, med large cap filter(fjerner euronext growth selskaper )
    def DETAILED_BACKTEST_v3():
        """
        DETAILED BACKTEST v3 — Empirically Enhanced Live-Strategy Replica
        ==================================================================

        NEW i denne revisjonen:
        * EURONEXT GROWTH FILTER — ekskluderer alle tickere som er listet
            i EuronextGrowth_Exclude.xlsx (én kolonne 'Ticker'). Filtreringen
            skjer i select_at() før scoring, slik at Growth-selskaper aldri
            kommer inn i porteføljen.
            Av/på via flagget EXCLUDE_EURONEXT_GROWTH.

        Forbedringer over v2, basert på akademisk evidens:

        1. INVERSE VOLATILITY WEIGHTING (Choueifaty & Coignard 2008)
        2. 52-WEEK HIGH MOMENTUM (George & Hwang 2004)
        3. QUALITY FILTER — Earnings Stability (Novy-Marx 2013)
        4. DRAWDOWN STOP (Faber 2007)
        5. SEPTEMBER SEASONAL AVOIDANCE
        6. MIN LIQUIDITY FILTER
        7. TREND FILTER PÅ BENCHMARK
        """

        import os, re, logging, warnings
        from datetime import datetime, timedelta
        from glob import glob
        import pandas as pd
        import numpy as np

        warnings.filterwarnings("ignore")

        # ── Paths ─────────────────────────────────────────────────────────────────
        BASE_DIR    = r"C:\Users\ander\Desktop\Python_K4\ExcelData\DataPB_ROE"
        MERGED_DIR  = os.path.join(BASE_DIR, "MergedData")
        HIST_DIR    = os.path.join(BASE_DIR, "HistoricalData")
        BT_DIR      = os.path.join(BASE_DIR, "Backtest")
        PORTF_DIR   = os.path.join(BASE_DIR, "Portfolio")
        GROWTH_FILE = os.path.join(BASE_DIR, "EuronextGrowth_Exclude.xlsx")

        # ── Strategy parameters ───────────────────────────────────────────────────
        N_PORTFOLIO          = 5
        MAX_PER_INDUSTRY     = 3

        # Score weights (sum = 1.0)
        W_PB                 = 0.25
        W_ROE                = 0.25
        W_MOM12              = 0.20
        W_MOM52              = 0.10
        W_ROE_TREND          = 0.12
        W_ROE_STAB           = 0.08   # stability (lav vol = bra)

        # Filters
        MIN_ROE              = 0.0
        MAX_PB               = 10.0
        FILTER_NEGATIVE_PB   = True
        FILTER_NEGATIVE_ROE  = True
        FILTER_NEGATIVE_MOM  = True    # filtrer ut negativ 12-1 momentum

        # Euronext Growth filter
        EXCLUDE_EURONEXT_GROWTH = True   # sett False for å skru av

        # Momentum
        MOM_SKIP_MONTHS      = 1
        MOM_LOOKBACK_MONTHS  = 12
        ROE_TREND_QUARTERS   = 4

        # Inv-vol weighting
        VOL_WINDOW_DAYS      = 63
        MAX_WEIGHT_CAP       = 0.25

        # Stop-loss
        DRAWDOWN_STOP_PCT    = 0.20

        # Trend filter
        BENCHMARK_SMA_DAYS   = 200
        BEAR_EXPOSURE        = 0.50

        # Seasonal filter
        AVOID_SEPTEMBER      = True

        # Liquidity
        MIN_PRICE_DAYS       = 60

        # Backtest
        BT_START_CAPITAL     = 1_000_000.0
        BT_TRANSACTION_COST  = 0.000
        BENCHMARK_TICKER     = "OSEBX.OL"

        # ── Logging ───────────────────────────────────────────────────────────────
        logging.basicConfig(level=logging.INFO,
                            format="%(asctime)s  %(levelname)-8s  %(message)s",
                            datefmt="%H:%M:%S")
        log = logging.getLogger("BT_v3")
        for d in (BT_DIR, PORTF_DIR):
            os.makedirs(d, exist_ok=True)
        TODAY_STR = datetime.now().strftime("%Y-%m-%d")

        # =========================================================================
        # HELPERS
        # =========================================================================

        def find_latest_file(folder, pattern):
            files = glob(os.path.join(folder, pattern))
            return sorted(files, reverse=True)[0] if files else None

        def period_to_date(period_str, scraped_date=None):
            if not isinstance(period_str, str):
                return None
            s = period_str.strip()
            if s.upper() in ("TTM", "ANNUAL"):
                return None
            m = re.match(r"Q([1-4])\s*'(\d{2})$", s, re.IGNORECASE)
            if m:
                q, yr2 = int(m.group(1)), int(m.group(2))
                yr = 2000 + yr2 if yr2 < 70 else 1900 + yr2
                try:
                    return pd.Timestamp(year=yr, month=q * 3, day=1) + pd.offsets.MonthEnd(0)
                except:
                    return None
            m2 = re.match(r"(?:FY|Annual)\s*'?(\d{2})$", s, re.IGNORECASE)
            if m2:
                yr = 2000 + int(m2.group(1)) if int(m2.group(1)) < 70 else 1900 + int(m2.group(1))
                try:
                    return pd.Timestamp(year=yr, month=12, day=31)
                except:
                    return None
            m3 = re.match(r"Q-(\d+)$", s)
            if m3:
                offset = int(m3.group(1))
                anchor = pd.Timestamp(scraped_date) if scraped_date else pd.Timestamp(datetime.now())
                cq = (anchor.month - 1) // 3 + 1
                total = (anchor.year * 4 + cq) - offset
                ty = (total - 1) // 4
                tq = total - ty * 4
                if tq <= 0:
                    tq += 4
                    ty -= 1
                try:
                    return pd.Timestamp(year=ty, month=tq * 3, day=1) + pd.offsets.MonthEnd(0)
                except:
                    return None
            return None

        def price_at(prices, ticker, dt):
            """Siste tilgjengelige pris på eller før dt."""
            if ticker not in prices.columns:
                return None
            p = prices[ticker].dropna()
            # Orders and valuations require this session's actual observation.
            if dt not in p.index:
                return None
            value = float(p.loc[dt])
            return value if np.isfinite(value) and value > 0 else None

        def compute_roe_trend(roe_series: pd.Series) -> float:
            vals = roe_series.dropna().values
            if len(vals) < 2:
                return np.nan
            vals = vals[-ROE_TREND_QUARTERS:]
            if len(vals) < 2:
                return np.nan
            x = np.arange(len(vals), dtype=float)
            return float(np.polyfit(x, vals, 1)[0])

        def compute_roe_stability(roe_series: pd.Series) -> float:
            vals = roe_series.dropna().values
            if len(vals) < 2:
                return np.nan
            vals = vals[-ROE_TREND_QUARTERS:]
            std = float(np.std(vals, ddof=1)) if len(vals) >= 2 else np.nan
            return -std

        def compute_momentum(monthly_prices, ticker, as_of_date):
            if ticker not in monthly_prices.columns:
                return None
            p = monthly_prices[ticker].dropna()
            # The explicit skip below excludes this month's execution close.
            # Excluding it twice would silently change 12-minus-1 momentum.
            p = p[p.index <= as_of_date]
            need = MOM_LOOKBACK_MONTHS + MOM_SKIP_MONTHS
            if len(p) < need:
                return None
            price_recent = float(p.iloc[-(1 + MOM_SKIP_MONTHS)])
            price_past   = float(p.iloc[-(MOM_LOOKBACK_MONTHS + MOM_SKIP_MONTHS)])
            if price_past <= 0:
                return None
            return round((price_recent / price_past) - 1, 6)

        def compute_52wk_high_ratio(daily_prices, ticker, as_of_date):
            if ticker not in daily_prices.columns:
                return None
            p = daily_prices[ticker].dropna()
            p = p[p.index < as_of_date]
            if len(p) < 252:
                if len(p) < 60:
                    return None
            window = p.iloc[-252:] if len(p) >= 252 else p
            high = float(window.max())
            current = float(p.iloc[-1])
            if high <= 0:
                return None
            return round(current / high, 6)

        def compute_inv_vol_weights(daily_prices, tickers, as_of_date, vol_window=VOL_WINDOW_DAYS):
            vols = {}
            for t in tickers:
                if t not in daily_prices.columns:
                    continue
                p = daily_prices[t].dropna()
                p = p[p.index < as_of_date]
                if len(p) < 20:
                    continue
                window = p.iloc[-vol_window:]
                ret = window.pct_change().dropna()
                if len(ret) < 10:
                    continue
                v = float(ret.std())
                if v > 0:
                    vols[t] = v

            if not vols:
                n = len(tickers)
                return {t: min(1.0 / n, MAX_WEIGHT_CAP) for t in tickers} if n else {}

            med_vol = float(np.median(list(vols.values())))
            for t in tickers:
                if t not in vols:
                    vols[t] = med_vol

            inv_vols = {t: 1.0 / v for t, v in vols.items()}
            total_inv = sum(inv_vols.values())
            raw_weights = {t: inv_vols[t] / total_inv for t in tickers}

            from runtime_config import capped_weights
            return capped_weights(raw_weights, MAX_WEIGHT_CAP)

        def check_drawdown_stop(daily_prices, ticker, as_of_date, lookback_days=126):
            if ticker not in daily_prices.columns:
                return False
            p = daily_prices[ticker].dropna()
            p = p[p.index < as_of_date]
            if len(p) < lookback_days:
                return False
            window = p.iloc[-lookback_days:]
            peak = float(window.max())
            current = float(p.iloc[-1])
            if peak <= 0:
                return False
            drawdown = (current - peak) / peak
            return drawdown < -DRAWDOWN_STOP_PCT

        def is_benchmark_above_sma(daily_prices, as_of_date):
            bname = BENCHMARK_TICKER.replace(".OL", "")
            if BENCHMARK_TICKER not in daily_prices.columns and bname not in daily_prices.columns:
                return None
            col = BENCHMARK_TICKER if BENCHMARK_TICKER in daily_prices.columns else bname
            p = daily_prices[col].dropna()
            p = p[p.index < as_of_date]
            if len(p) < BENCHMARK_SMA_DAYS:
                return None
            current = float(p.iloc[-1])
            sma = float(p.iloc[-BENCHMARK_SMA_DAYS:].mean())
            return current > sma

        def is_liquid(daily_prices, ticker, as_of_date, min_days=MIN_PRICE_DAYS):
            if ticker not in daily_prices.columns:
                return False
            p = daily_prices[ticker].dropna()
            p = p[p.index < as_of_date]
            if p.empty:
                return False
            days_since_last = (as_of_date - p.index[-1]).days
            return days_since_last <= min_days and len(p) >= min_days

        # =========================================================================
        # DATA LOADING
        # =========================================================================

        def load_industry_map():
            merged = find_latest_file(MERGED_DIR, "Merged_*.xlsx")
            if merged:
                df = pd.read_excel(merged)
            else:
                ov = find_latest_file(MERGED_DIR, "*_Raw_Overview.xlsx")
                if not ov:
                    raise FileNotFoundError("No merged/overview data in %s" % MERGED_DIR)
                df = pd.read_excel(ov)
            ic = next((c for c in df.columns if "industry" in c.lower()), None)
            if not ic:
                return {r["Company Name"]: "Unknown" for _, r in df.iterrows()}
            return dict(zip(df["Company Name"], df[ic]))

        def load_growth_exclusions():
            """
            Last set av tickere som skal ekskluderes (Euronext Growth Oslo).
            Returnerer tom set hvis filtrering er av eller filen mangler.
            """
            if not EXCLUDE_EURONEXT_GROWTH:
                log.info("Euronext Growth filter: DISABLED")
                return set()
            if not os.path.exists(GROWTH_FILE):
                log.warning("Growth exclusion file not found: %s — no filtering applied",
                            GROWTH_FILE)
                return set()
            try:
                df = pd.read_excel(GROWTH_FILE)
                col = next((c for c in df.columns if "ticker" in c.lower()), df.columns[0])
                tickers = {str(t).strip().upper() for t in df[col].dropna()}
                log.info("Euronext Growth filter: %d tickers loaded from %s",
                        len(tickers), os.path.basename(GROWTH_FILE))
                return tickers
            except Exception as exc:
                log.warning("Could not load growth exclusions: %s", exc)
                return set()

        def load_fundamentals():
            master = os.path.join(HIST_DIR, "Master_PB_ROE_History.xlsx")
            if not os.path.exists(master):
                raise FileNotFoundError(master)
            df = pd.read_excel(master)
            df["Scraped_date"] = pd.to_datetime(df["Scraped_date"], errors="coerce")
            df["PB"]  = pd.to_numeric(df["PB"],  errors="coerce")
            df["ROE"] = pd.to_numeric(df["ROE"], errors="coerce")
            df["period_date"] = df.apply(
                lambda r: period_to_date(r["Period"], r["Scraped_date"]), axis=1)
            df = df[df["period_date"].notna()].copy()
            # A scraped accounting period is not its publication timestamp.
            # Keep every observed version, so later revisions cannot rewrite the past.
            df["AvailableDate"] = df["Scraped_date"]
            df = df.dropna(subset=["AvailableDate"])
            df.sort_values(["AvailableDate", "period_date"], inplace=True)
            df.drop_duplicates(subset=["Company Name", "period_date", "AvailableDate"],
                               keep="last", inplace=True)

            fund = {}
            for t, g in df.groupby("Company Name"):
                g2 = g.set_index("period_date")[["PB", "ROE", "AvailableDate"]].sort_index()
                if g2["PB"].notna().any() or g2["ROE"].notna().any():
                    fund[t] = g2
            log.info("Fundamentals loaded: %d tickers", len(fund))
            return fund

        def download_prices(tickers):
            import yfinance as yf
            end   = datetime.now()
            start = end - timedelta(days=500 + 365 * 3)
            yft   = [t + ".OL" for t in tickers] + [BENCHMARK_TICKER]
            log.info("Downloading prices for %d tickers ...", len(tickers))
            record_source("pbroe_prices", "FAILED", "Price download started; not yet validated", network_attempted=True)
            raw = yf.download(
                yft,
                start=start.strftime("%Y-%m-%d"),
                end=end.strftime("%Y-%m-%d"),
                interval="1d",
                auto_adjust=True,
                progress=False,
            )
            if isinstance(raw.columns, pd.MultiIndex):
                daily = raw["Close"].copy()
            else:
                daily = raw[["Close"]].copy()
            daily.rename(columns={t + ".OL": t for t in tickers}, inplace=True)
            daily.index = pd.to_datetime(daily.index)
            daily.sort_index(inplace=True)
            from runtime_config import validate_price_frame, observed_month_ends
            validate_price_frame(daily, tickers + [BENCHMARK_TICKER], "PB-ROE prices")
            record_source("pbroe_prices", "DOWNLOADED", "All required PB-ROE and benchmark prices validated",
                          network_attempted=True, expected_count=len(yft), usable_count=len(yft),
                          downloaded_count=len(yft), latest_observation=str(daily.index.max().date()))
            monthly = observed_month_ends(daily, end)
            log.info("Daily: %d rows | Completed monthly sessions: %d rows", len(daily), len(monthly))
            return daily, monthly

        # =========================================================================
        # SELECTION — 6-faktor scoring
        # =========================================================================

        def select_at(fund, ind_map, growth_excl, monthly, daily, tickers, dt):
            """
            Scorer og rangerer alle kvalifiserte tickers med 6-faktor modell.
            Returnerer (liste_av_valgte, scoret_DataFrame).
            """
            rows = []
            for t in tickers:
                if t not in fund:
                    continue

                # ── Euronext Growth filter ────────────────────────────────────────
                if t.upper() in growth_excl:
                    continue

                from runtime_config import historical_fundamentals
                ff = historical_fundamentals(fund[t], dt)
                if ff.empty:
                    continue

                # ── Liquidity filter ──────────────────────────────────────────────
                if not is_liquid(daily, t, dt):
                    continue

                # ── Fundamentals ──────────────────────────────────────────────────
                lat = ff.iloc[-1]
                pb  = float(lat["PB"])  if pd.notna(lat["PB"])  else None
                roe = float(lat["ROE"]) if pd.notna(lat["ROE"]) else None

                if pb is None or roe is None:
                    continue
                if FILTER_NEGATIVE_PB  and pb  < 0:    continue
                if FILTER_NEGATIVE_ROE and roe < MIN_ROE: continue
                if pb > MAX_PB:                          continue

                # ── 12-1 momentum ─────────────────────────────────────────────────
                mom12 = compute_momentum(monthly, t, dt)
                if FILTER_NEGATIVE_MOM and (mom12 is None or mom12 < 0):
                    continue
                if mom12 is None:
                    continue

                # ── 52-week high ratio ────────────────────────────────────────────
                mom52 = compute_52wk_high_ratio(daily, t, dt)

                # ── ROE trend & stability ─────────────────────────────────────────
                roe_trend = compute_roe_trend(ff["ROE"])
                roe_stab  = compute_roe_stability(ff["ROE"])

                rows.append({
                    "ticker"   : t,
                    "PB"       : pb,
                    "ROE"      : roe,
                    "MOM12"    : mom12,
                    "MOM52"    : mom52,
                    "ROE_trend": roe_trend,
                    "ROE_stab" : roe_stab,
                    "Industry" : ind_map.get(t, "Unknown"),
                })

            if not rows:
                return [], pd.DataFrame()

            df = pd.DataFrame(rows)

            for col in ["MOM52", "ROE_trend", "ROE_stab"]:
                med = df[col].median()
                df[col] = df[col].fillna(med)

            def score_group(group):
                g = group.copy()
                if len(g) < 3:
                    for c in ["PB_pct","ROE_pct","MOM12_pct","MOM52_pct","ROET_pct","STAB_pct"]:
                        g[c] = 0.5
                else:
                    g["PB_pct"]    = 1 - g["PB"].rank(pct=True)
                    g["ROE_pct"]   = g["ROE"].rank(pct=True)
                    g["MOM12_pct"] = g["MOM12"].rank(pct=True)
                    g["MOM52_pct"] = g["MOM52"].rank(pct=True)
                    g["ROET_pct"]  = g["ROE_trend"].rank(pct=True) \
                                    if g["ROE_trend"].notna().sum() >= 2 else 0.5
                    g["STAB_pct"]  = g["ROE_stab"].rank(pct=True)
                g["Combined_score"] = (
                    W_PB       * g["PB_pct"]    +
                    W_ROE      * g["ROE_pct"]   +
                    W_MOM12    * g["MOM12_pct"] +
                    W_MOM52    * g["MOM52_pct"] +
                    W_ROE_TREND* g["ROET_pct"]  +
                    W_ROE_STAB * g["STAB_pct"]
                )
                return g

            df = df.groupby("Industry", group_keys=False).apply(score_group)

            if "Combined_score" not in df.columns or df["Combined_score"].isna().any():
                mask = df["Combined_score"].isna() \
                    if "Combined_score" in df.columns \
                    else pd.Series([True] * len(df), index=df.index)
                sub = df[mask].copy()
                sub["PB_pct"]    = 1 - sub["PB"].rank(pct=True)
                sub["ROE_pct"]   = sub["ROE"].rank(pct=True)
                sub["MOM12_pct"] = sub["MOM12"].rank(pct=True)
                sub["MOM52_pct"] = sub["MOM52"].rank(pct=True)
                sub["ROET_pct"]  = sub["ROE_trend"].rank(pct=True) \
                                if sub["ROE_trend"].notna().sum() >= 2 else 0.5
                sub["STAB_pct"]  = sub["ROE_stab"].rank(pct=True)
                sub["Combined_score"] = (
                    W_PB       * sub["PB_pct"]    +
                    W_ROE      * sub["ROE_pct"]   +
                    W_MOM12    * sub["MOM12_pct"] +
                    W_MOM52    * sub["MOM52_pct"] +
                    W_ROE_TREND* sub["ROET_pct"]  +
                    W_ROE_STAB * sub["STAB_pct"]
                )
                df.update(sub)

            df.sort_values("Combined_score", ascending=False, inplace=True)
            df.reset_index(drop=True, inplace=True)

            selected  = []
            ind_count = {}
            _scoret_df = df
            for _, row in df.iterrows():
                if len(selected) >= N_PORTFOLIO:
                    break
                ind = row["Industry"]
                ind_count[ind] = ind_count.get(ind, 0)
                if ind_count[ind] >= MAX_PER_INDUSTRY:
                    continue
                selected.append(row["ticker"])
                ind_count[ind] += 1

            sel_df = df[df["ticker"].isin(selected)].copy()

            # Scoren for HVER kandidat, ikke bare de valgte, og med datoen.
            # Uten denne loggen finnes Combined_score bare for i dag, og en
            # samlet backtest på tvers av strategiene kan ikke bygges: den
            # trenger å vite hva modellen mente den gangen, ikke hva den
            # mener nå. Vi tar toppen av lista — halen er uinteressant og
            # ville doblet filstørrelsen.
            try:
                for _rang, (_, _r) in enumerate(
                        _scoret_df.head(SCORE_LOG_TOPP).iterrows(), start=1):
                    score_log.append({
                        "date": pd.Timestamp(dt).strftime("%Y-%m-%d"),
                        "ticker": str(_r["ticker"]),
                        "score": float(_r["Combined_score"]),
                        "rank": _rang,
                        "valgt": "JA" if _r["ticker"] in selected else "NEI",
                    })
            except Exception as _e:
                # Én advarsel, ikke én per måned — men den SKAL komme. En
                # debug-linje her betydde at arket bare uteble, og at
                # master.py meldte «filen mangler Score_Log» i evighet.
                if not getattr(select_at, "_score_log_advart", False):
                    select_at._score_log_advart = True
                    log.warning("Score-loggen feiler (%s) — arket Score_Log blir "
                                "tomt, og master.py mister PB-ROE som kilde.", _e)
            return selected, sel_df

        # =========================================================================
        # MAIN BACKTEST LOOP
        # =========================================================================

        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        import matplotlib.ticker as mticker

        log.info("=" * 75)
        log.info("  DETAILED BACKTEST v3 — Empirically Enhanced")
        log.info("  Weights: PB=%.0f%%  ROE=%.0f%%  MOM12=%.0f%%  MOM52=%.0f%%  ROET=%.0f%%  STAB=%.0f%%",
                W_PB*100, W_ROE*100, W_MOM12*100, W_MOM52*100, W_ROE_TREND*100, W_ROE_STAB*100)
        log.info("  Inv-vol weighting (cap %.0f%%)  |  Drawdown stop %.0f%%  |  Sept-filter: %s",
                MAX_WEIGHT_CAP*100, DRAWDOWN_STOP_PCT*100, AVOID_SEPTEMBER)
        log.info("  Benchmark trend filter: %d-day SMA  |  Bear exposure: %.0f%%",
                BENCHMARK_SMA_DAYS, BEAR_EXPOSURE*100)
        log.info("  Exclude Euronext Growth: %s", EXCLUDE_EURONEXT_GROWTH)
        log.info("=" * 75)

        ind_map        = load_industry_map()
        growth_excl    = load_growth_exclusions()
        fund           = load_fundamentals()
        tickers        = list(fund.keys())

        # Sjekk hvor mange tickers i universet som faktisk vil bli filtrert ut
        if growth_excl:
            n_excluded = sum(1 for t in tickers if t.upper() in growth_excl)
            log.info("Universe: %d total tickers, %d match Growth exclusion list",
                    len(tickers), n_excluded)

        daily, monthly = download_prices(tickers)

        all_dates = []
        for f in fund.values():
            all_dates.extend(pd.to_datetime(f["AvailableDate"]).tolist())
        if not all_dates:
            raise RuntimeError("PB-ROE has no dated observed fundamentals.")
        bt_start = min(all_dates)
        bt_end   = pd.Timestamp(TODAY_STR)

        rdates = []
        dt = bt_start.replace(day=1)
        while dt <= bt_end:
            idx = monthly.index[
                (monthly.index.year  == dt.year) &
                (monthly.index.month == dt.month)
            ]
            if len(idx) > 0 and idx[0] > bt_start:
                rdates.append(idx[0])
            dt += pd.offsets.MonthBegin(1)
        if not rdates:
            raise RuntimeError("PB-ROE: no completed monthly execution session after the first "
                               "observed fundamentals. Historical publication dates cannot "
                               "be inferred from today's scraped ratios.")
        log.info("Rebalance dates: %d", len(rdates))

        bn = pd.Series(dtype=float)
        if BENCHMARK_TICKER in monthly.columns:
            b = monthly[BENCHMARK_TICKER].dropna()
            if not b.empty:
                bn = (b / b.iloc[0]) * BT_START_CAPITAL

        cash          = BT_START_CAPITAL
        holdings      = {}
        equity_curve  = []
        trade_log     = []
        monthly_log   = []
        # Én rad per (dato, ticker, score). Grunnlaget for den samlede
        # scoren i master.py — se kommentaren i select_at().
        score_log     = []
        stop_log      = []

        for rebal_dt in rdates:
            missing_held = [t for t in holdings if price_at(monthly, t, rebal_dt) is None]
            if missing_held:
                raise RuntimeError("PB-ROE held prices missing on " + str(rebal_dt.date())
                                   + ": " + ", ".join(missing_held))

            # ── Seasonal filter: hold cash i September ────────────────────────────
            if AVOID_SEPTEMBER and rebal_dt.month == 9:
                for tkr in list(holdings.keys()):
                    p = price_at(monthly, tkr, rebal_dt)
                    if p and holdings.get(tkr, 0) > 0:
                        proceeds = holdings[tkr] * p
                        cash    += proceeds * (1 - BT_TRANSACTION_COST)
                        trade_log.append({
                            "date": rebal_dt.strftime("%Y-%m-%d"), "ticker": tkr,
                            "action": "SELL_SEASONAL", "shares": round(holdings[tkr], 4),
                            "price": round(p, 2), "value": round(proceeds, 0),
                            "industry": ind_map.get(tkr, "?"),
                        })
                holdings.clear()
                pv = cash
                equity_curve.append({"date": rebal_dt, "value": pv})
                monthly_log.append({
                    "date": rebal_dt.strftime("%Y-%m"), "portfolio_value": round(pv, 0),
                    "cash": round(cash, 0), "n_holdings": 0,
                    "holdings": "CASH — September filter", "buys": "", "sells": "ALL",
                    "industries": 0, "market_regime": "SEASONAL_AVOID",
                })
                log.info("%s  $%.0f  SEPTEMBER FILTER — all cash", rebal_dt.strftime("%Y-%m"), pv)
                continue

            pv_before = cash + sum(
                holdings.get(t, 0) * (price_at(monthly, t, rebal_dt) or 0)
                for t in holdings
            )

            # Drawdown stop
            stopped_out = set()
            for tkr in list(holdings.keys()):
                if check_drawdown_stop(daily, tkr, rebal_dt):
                    p = price_at(monthly, tkr, rebal_dt)
                    if p and holdings.get(tkr, 0) > 0:
                        proceeds = holdings[tkr] * p
                        cash    += proceeds * (1 - BT_TRANSACTION_COST)
                        stop_log.append({
                            "date": rebal_dt.strftime("%Y-%m-%d"), "ticker": tkr,
                            "stop_price": round(p, 2), "proceeds": round(proceeds, 0),
                        })
                        trade_log.append({
                            "date": rebal_dt.strftime("%Y-%m-%d"), "ticker": tkr,
                            "action": "STOP_LOSS", "shares": round(holdings[tkr], 4),
                            "price": round(p, 2), "value": round(proceeds, 0),
                            "industry": ind_map.get(tkr, "?"),
                        })
                        del holdings[tkr]
                        stopped_out.add(tkr)
                        log.info("  STOP-LOSS: %s triggered at $%.2f", tkr, p)

            pv_before = cash + sum(
                holdings.get(t, 0) * (price_at(monthly, t, rebal_dt) or 0)
                for t in holdings
            )

            bull_market = is_benchmark_above_sma(daily, rebal_dt)
            if bull_market is None:
                bull_market = True
            market_regime = "BULL" if bull_market else "BEAR"

            investable = pv_before * (1.0 if bull_market else BEAR_EXPOSURE)

            target_tickers, sel_df = select_at(
                fund, ind_map, growth_excl, monthly, daily, tickers, rebal_dt)
            target_tickers = [t for t in target_tickers
                              if t not in stopped_out and price_at(monthly, t, rebal_dt) is not None]

            if not target_tickers:
                for tkr in list(holdings):
                    p = price_at(monthly, tkr, rebal_dt)
                    proceeds = holdings.pop(tkr) * p
                    cash += proceeds
                    trade_log.append({"date": rebal_dt.strftime("%Y-%m-%d"),
                                      "ticker": tkr, "action": "SELL_NO_SIGNAL",
                                      "price": p, "value": proceeds})
                equity_curve.append({"date": rebal_dt, "value": cash})
                monthly_log.append({
                    "date": rebal_dt.strftime("%Y-%m"), "portfolio_value": round(pv_before, 0),
                    "cash": round(cash, 0), "n_holdings": len(holdings),
                    "holdings": "CASH — no signal", "buys": "", "sells": "",
                    "industries": 0, "market_regime": market_regime,
                })
                log.info("%s  $%.0f  CASH (no signal) [%s]",
                        rebal_dt.strftime("%Y-%m"), pv_before, market_regime)
                continue

            target_set  = set(target_tickers)
            current_set = set(holdings.keys())
            sells_set   = current_set - target_set
            buys_set    = target_set  - current_set
            holds_set   = current_set & target_set

            for tkr in sells_set:
                p = price_at(monthly, tkr, rebal_dt)
                if p and holdings.get(tkr, 0) > 0:
                    proceeds = holdings[tkr] * p
                    cash    += proceeds * (1 - BT_TRANSACTION_COST)
                    trade_log.append({
                        "date": rebal_dt.strftime("%Y-%m-%d"), "ticker": tkr,
                        "action": "SELL", "shares": round(holdings[tkr], 4),
                        "price": round(p, 2), "value": round(proceeds, 0),
                        "industry": ind_map.get(tkr, "?"),
                    })
                    del holdings[tkr]

            weights = compute_inv_vol_weights(daily, target_tickers, rebal_dt)

            # Reduce positions before funding buys; no borrowing or negative cash.
            target_tickers = sorted(target_tickers, key=lambda t:
                investable * weights.get(t, 0) - holdings.get(t, 0) * price_at(monthly, t, rebal_dt))
            for tkr in target_tickers:
                p = price_at(monthly, tkr, rebal_dt)
                if not p or p <= 0:
                    continue
                w  = weights.get(tkr, 0.0)
                tv = investable * w
                cs = holdings.get(tkr, 0)
                ts = tv / p
                diff = ts - cs

                if abs(diff * p) < 1:
                    continue

                if diff > 0:
                    diff = min(diff, max(0.0, cash) / p)
                    if diff * p < 1:
                        continue
                    cost = diff * p
                    txn  = 0.0
                    cash -= cost + txn
                    holdings[tkr] = cs + diff
                    action = "BUY" if tkr in buys_set else "REBAL_BUY"
                    trade_log.append({
                        "date": rebal_dt.strftime("%Y-%m-%d"), "ticker": tkr,
                        "action": action, "shares": round(diff, 4),
                        "price": round(p, 2), "value": round(cost, 0),
                        "industry": ind_map.get(tkr, "?"),
                        "weight": round(w, 4),
                    })
                else:
                    ss       = abs(diff)
                    proceeds = ss * p
                    txn      = proceeds * BT_TRANSACTION_COST
                    cash    += proceeds - txn
                    holdings[tkr] = max(cs - ss, 0)
                    trade_log.append({
                        "date": rebal_dt.strftime("%Y-%m-%d"), "ticker": tkr,
                        "action": "REBAL_SELL", "shares": round(ss, 4),
                        "price": round(p, 2), "value": round(proceeds, 0),
                        "industry": ind_map.get(tkr, "?"),
                        "weight": round(w, 4),
                    })

            port_after = cash + sum(
                holdings.get(t, 0) * (price_at(monthly, t, rebal_dt) or 0)
                for t in holdings
            )

            stock_lines = []
            for tkr in sorted(holdings.keys()):
                p = price_at(monthly, tkr, rebal_dt)
                if p:
                    val = holdings[tkr] * p
                    w   = weights.get(tkr, 0)
                    pb_str, roe_str, mom_str, score_str, m52_str = "?","?","?","?","?"
                    if not sel_df.empty and tkr in sel_df["ticker"].values:
                        row      = sel_df[sel_df["ticker"] == tkr].iloc[0]
                        pb_str   = "%.2f" % row["PB"]
                        roe_str  = "%.1f" % row["ROE"]
                        mom_str  = "%+.1f%%" % (row["MOM12"] * 100)
                        m52_str  = "%.2f" % row["MOM52"] if pd.notna(row["MOM52"]) else "?"
                        score_str= "%.3f" % row["Combined_score"]
                    stock_lines.append(
                        "%-6s  $%-8.0f  w:%.1f%%  PB:%-5s  ROE:%-6s  Mom12:%-7s  52wH:%-5s  Score:%s  [%s]"
                        % (tkr, val, w*100, pb_str, roe_str, mom_str, m52_str, score_str,
                        ind_map.get(tkr, "?"))
                    )

            equity_curve.append({"date": rebal_dt, "value": port_after})
            industries_held = set(ind_map.get(t, "?") for t in holdings.keys())

            monthly_log.append({
                "date"           : rebal_dt.strftime("%Y-%m"),
                "portfolio_value": round(port_after, 0),
                "cash"           : round(cash, 0),
                "n_holdings"     : len(holdings),
                "holdings"       : ", ".join(sorted(holdings.keys())),
                "buys"           : ", ".join(sorted(buys_set)),
                "sells"          : ", ".join(sorted(sells_set)),
                "stops"          : ", ".join(sorted(stopped_out)),
                "industries"     : len(industries_held),
                "market_regime"  : market_regime,
            })

            pct_change = ""
            if len(equity_curve) >= 2:
                prev_val = equity_curve[-2]["value"]
                if prev_val > 0:
                    ret = (port_after / prev_val - 1) * 100
                    pct_change = " (%+.1f%%)" % ret

            log.info("")
            log.info("--- %s  $%.0f%s  [%s] ---",
                    rebal_dt.strftime("%Y-%m"), port_after, pct_change, market_regime)
            if buys_set:
                log.info("  BUY:  %s", ", ".join(sorted(buys_set)))
            if sells_set:
                log.info("  SELL: %s", ", ".join(sorted(sells_set)))
            if stopped_out:
                log.info("  STOP: %s", ", ".join(sorted(stopped_out)))
            if holds_set:
                log.info("  HOLD: %s", ", ".join(sorted(holds_set)))
            for line in stock_lines:
                log.info("    %s", line)
            log.info("  Cash: $%.0f  |  %d stocks  |  %d industries",
                    cash, len(holdings), len(industries_held))

        # =========================================================================
        # TRADE-LEVEL P&L
        # =========================================================================

        def compute_trade_pnl(trade_log):
            if not trade_log:
                return []
            tl   = pd.DataFrame(trade_log)
            tl["date"] = pd.to_datetime(tl["date"])
            sells = tl[tl["action"].isin(["SELL", "STOP_LOSS"])].copy()
            buys  = tl[tl["action"].isin(["BUY", "REBAL_BUY"])].copy()
            returns = []
            for _, sell in sells.iterrows():
                prior = buys[
                    (buys["ticker"] == sell["ticker"]) &
                    (buys["date"]   <  sell["date"])
                ].sort_values("date", ascending=False)
                if not prior.empty and prior.iloc[0]["price"] > 0:
                    returns.append(
                        (sell["price"] / prior.iloc[0]["price"] - 1) * 100)
            return returns

        trade_returns = compute_trade_pnl(trade_log)

        # =========================================================================
        # METRICS
        # =========================================================================

        if not equity_curve:
            log.warning("No equity curve generated.")
            return

        ec   = pd.DataFrame(equity_curve).set_index("date")["value"]
        rets = ec.pct_change().dropna()

        if len(rets) < 2:
            log.warning("Not enough data points for metrics.")
            return

        total_ret = (ec.iloc[-1] / ec.iloc[0]) - 1
        n_years   = max((ec.index[-1] - ec.index[0]).days / 365.25, 0.01)
        cagr      = (ec.iloc[-1] / ec.iloc[0]) ** (1 / n_years) - 1
        vol       = rets.std() * np.sqrt(12)
        sharpe    = (cagr - 0.03) / vol if vol > 0 else 0
        mdd       = ((ec - ec.cummax()) / ec.cummax()).min()
        wr        = (rets > 0).sum() / len(rets)
        ds        = rets[rets < 0]
        dv        = ds.std() * np.sqrt(12) if len(ds) > 0 else 0
        sortino   = (cagr - 0.03) / dv if dv > 0 else 0
        calmar    = cagr / abs(mdd) if mdd != 0 else 0

        n_stops = sum(1 for t in trade_log if t.get("action") == "STOP_LOSS")

        log.info("")
        log.info("=" * 65)
        log.info("  RESULTS — v3 Enhanced (PB+ROE+MOM12+MOM52+ROET+STAB + inv-vol)")
        log.info("=" * 65)
        log.info("  Start Value      : $%.0f", ec.iloc[0])
        log.info("  End Value        : $%.0f", ec.iloc[-1])
        log.info("  Total Return     : %.1f%%", total_ret * 100)
        log.info("  CAGR             : %.1f%%", cagr * 100)
        log.info("  Sharpe           : %.2f", sharpe)
        log.info("  Sortino          : %.2f", sortino)
        log.info("  Max Drawdown     : %.1f%%", mdd * 100)
        log.info("  Calmar           : %.2f", calmar)
        log.info("  Win Rate         : %.0f%%", wr * 100)
        log.info("  Volatility       : %.1f%%", vol * 100)
        log.info("  Total Trades     : %d", len(trade_log))
        log.info("  Stop-loss events : %d", n_stops)
        if trade_returns:
            profitable = sum(1 for r in trade_returns if r > 0)
            log.info("  Avg trade return : %+.2f%%", np.mean(trade_returns))
            log.info("  Median trade ret : %+.2f%%", np.median(trade_returns))
            log.info("  Best trade       : %+.2f%%", np.max(trade_returns))
            log.info("  Worst trade      : %+.2f%%", np.min(trade_returns))
            log.info("  Closed trades    : %d", len(trade_returns))
            log.info("  Trade Win Rate   : %.1f%%", profitable / len(trade_returns) * 100)

        bcagr      = None
        excess_ret = None
        if not bn.empty:
            bc = bn.reindex(ec.index, method="ffill").dropna()
            if len(bc) >= 2:
                bcagr      = (bc.iloc[-1] / bc.iloc[0]) ** (1 / n_years) - 1
                excess_ret = cagr - bcagr
                log.info("  Benchmark CAGR   : %.1f%%", bcagr * 100)
                log.info("  Excess Return    : %+.1f%%", excess_ret * 100)
        log.info("=" * 65)

        # =========================================================================
        # CHARTS
        # =========================================================================

        fig, axes = plt.subplots(
            5, 1, figsize=(16, 26),
            gridspec_kw={"height_ratios": [3, 1.2, 1.2, 1, 0.8]}
        )
        growth_tag = "  |  Growth-filter ON" if EXCLUDE_EURONEXT_GROWTH else ""
        fig.suptitle(
            "PB/ROE/MOM12/MOM52/ROE-trend/Stability — v3 Enhanced  |"
            "  Inv-vol weights  |  Stop-loss %.0f%%  |  Top %d  |  Max %d/ind%s"
            % (DRAWDOWN_STOP_PCT*100, N_PORTFOLIO, MAX_PER_INDUSTRY, growth_tag),
            fontsize=12, fontweight="bold", y=0.998
        )
        fig.patch.set_facecolor("#f8f9fa")

        ax1 = axes[0]
        ax1.plot(ec.index, ec.values,
                color="#1565C0", linewidth=2.2, label="Strategy v3", zorder=3)
        ax1.fill_between(ec.index, BT_START_CAPITAL, ec.values,
                        color="#1565C0", alpha=0.07, zorder=1)

        if not bn.empty:
            bp = bn.reindex(ec.index, method="ffill").dropna()
            if not bp.empty:
                bs = (bp / bp.iloc[0]) * BT_START_CAPITAL
                ax1.plot(bs.index, bs.values,
                        color="#FF9800", linewidth=1.8, linestyle="--",
                        label="OSEBX", alpha=0.85, zorder=2)

        dd      = (ec - ec.cummax()) / ec.cummax()
        dd_fill = dd.copy()
        dd_fill[dd_fill >= 0] = 0
        ax1_dd = ax1.twinx()
        ax1_dd.fill_between(dd.index, 0, dd_fill.values,
                            color="#E53935", alpha=0.13, zorder=0)
        ax1_dd.set_ylim(-0.6, 0)
        ax1_dd.set_ylabel("Drawdown", fontsize=10, color="#999")
        ax1_dd.yaxis.set_major_formatter(
            mticker.FuncFormatter(lambda x, _: "%.0f%%" % (x * 100)))
        ax1_dd.tick_params(axis="y", labelsize=9, colors="#999")

        ax1.annotate(
            "$%s" % f"{ec.iloc[-1]:,.0f}",
            xy=(ec.index[-1], ec.iloc[-1]),
            xytext=(10, 8), textcoords="offset points",
            fontsize=11, fontweight="bold", color="#1565C0",
            arrowprops=dict(arrowstyle="-", color="#1565C0", lw=0.8),
        )

        if stop_log:
            sl_df = pd.DataFrame(stop_log)
            sl_df["date"] = pd.to_datetime(sl_df["date"])
            for _, sl in sl_df.iterrows():
                matching = ec[ec.index >= sl["date"]]
                if not matching.empty:
                    ax1.axvline(sl["date"], color="#E53935", linewidth=0.4,
                                alpha=0.4, linestyle=":")

        metrics_text = (
            "CAGR: %.1f%%  |  Sharpe: %.2f  |  Sortino: %.2f\n"
            "Max DD: %.1f%%  |  Win Rate: %.0f%%  |  Trades: %d  |  Stops: %d"
            % (cagr*100, sharpe, sortino, mdd*100, wr*100, len(trade_log), n_stops)
        )
        if trade_returns:
            profitable = sum(1 for r in trade_returns if r > 0)
            metrics_text += (
                "\nAvg trade: %+.1f%%  |  Median: %+.1f%%  |  Trade WR: %.0f%%"
                % (np.mean(trade_returns), np.median(trade_returns),
                profitable / len(trade_returns) * 100)
            )
        if bcagr is not None:
            metrics_text += (
                "\nBenchmark CAGR: %.1f%%  |  Excess: %+.1f%%"
                % (bcagr * 100, excess_ret * 100)
            )
        ax1.text(0.02, 0.97, metrics_text, transform=ax1.transAxes,
                fontsize=9.5, verticalalignment="top",
                bbox=dict(boxstyle="round,pad=0.5", facecolor="white",
                        edgecolor="#ddd", alpha=0.9))

        ax1.set_title("Portfolio value over time", fontweight="bold", fontsize=12, pad=10)
        ax1.legend(loc="upper left", fontsize=10, framealpha=0.9)
        ax1.grid(True, alpha=0.25)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax1.yaxis.set_major_formatter(
            mticker.FuncFormatter(lambda x, _: "$%s" % f"{x:,.0f}"))
        ax1.set_facecolor("#ffffff")
        ax1.axhline(BT_START_CAPITAL, color="#888", linewidth=0.5, linestyle=":")
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)

        ax2    = axes[1]
        m_rets = ec.pct_change().dropna() * 100
        cols   = ["#43A047" if r > 0 else "#E53935" for r in m_rets.values]
        ax2.bar(m_rets.index, m_rets.values, color=cols, width=20, alpha=0.8)
        ax2.axhline(0, color="black", linewidth=0.8)
        ax2.set_title("Monthly returns (%)", fontweight="bold", fontsize=11)
        ax2.grid(True, alpha=0.25, axis="y")
        ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax2.yaxis.set_major_formatter(
            mticker.FuncFormatter(lambda x, _: "%.0f%%" % x))
        ax2.set_facecolor("#ffffff")
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)

        ax3        = axes[2]
        roll_strat = ec.pct_change(6).dropna() * 100
        ax3.plot(roll_strat.index, roll_strat.values,
                color="#1565C0", linewidth=1.5, label="Strategy v3 (6m rolling)")
        if not bn.empty:
            bn_ec = bn.reindex(ec.index, method="ffill").dropna()
            if len(bn_ec) > 6:
                roll_bench = bn_ec.pct_change(6).dropna() * 100
                ax3.plot(roll_bench.index, roll_bench.values,
                        color="#FF9800", linewidth=1.2, linestyle="--",
                        label="OSEBX (6m rolling)")
        ax3.axhline(0, color="black", linewidth=0.8)
        ax3.set_title("Rolling 6-month return", fontweight="bold", fontsize=11)
        ax3.legend(fontsize=9)
        ax3.grid(True, alpha=0.25, axis="y")
        ax3.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax3.yaxis.set_major_formatter(
            mticker.FuncFormatter(lambda x, _: "%.0f%%" % x))
        ax3.set_facecolor("#ffffff")
        plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45)

        ax4 = axes[3]
        if monthly_log:
            ml = pd.DataFrame(monthly_log)
            ml["date_ts"] = pd.to_datetime(ml["date"])
            ax4.bar(ml["date_ts"], ml["n_holdings"],
                    color="#1565C0", alpha=0.7, width=20, label="Holdings")
            ax4.bar(ml["date_ts"], ml["industries"],
                    color="#FF9800", alpha=0.5, width=15, label="Industries")
        ax4.set_title("Holdings & industry count", fontweight="bold", fontsize=11)
        ax4.legend(fontsize=9)
        ax4.grid(True, alpha=0.25, axis="y")
        ax4.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax4.set_facecolor("#ffffff")
        plt.setp(ax4.xaxis.get_majorticklabels(), rotation=45)

        ax5 = axes[4]
        if monthly_log:
            ml2 = pd.DataFrame(monthly_log)
            ml2["date_ts"] = pd.to_datetime(ml2["date"])
            bull_vals = [1 if r == "BULL" else 0 for r in ml2["market_regime"]]
            ax5.fill_between(ml2["date_ts"], 0, bull_vals,
                            color="#43A047", alpha=0.6, label="Bull")
            ax5.fill_between(ml2["date_ts"], bull_vals, 1,
                            color="#E53935", alpha=0.3, label="Bear / Seasonal")
        ax5.set_yticks([0, 1])
        ax5.set_yticklabels(["Bear", "Bull"])
        ax5.set_title("Market regime (OSEBX vs 200d SMA)", fontweight="bold", fontsize=11)
        ax5.legend(fontsize=9)
        ax5.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax5.set_facecolor("#ffffff")
        plt.setp(ax5.xaxis.get_majorticklabels(), rotation=45)

        plt.tight_layout()
        chart_path = os.path.join(BT_DIR, "BT_v3_Enhanced_%s.png" % TODAY_STR)
        plt.savefig(chart_path, dpi=150, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        plt.close()
        log.info("Chart saved: %s", chart_path)

        # =========================================================================
        # SAVE EXCEL
        # =========================================================================

        out_path = os.path.join(BT_DIR, "BT_v3_Enhanced_%s.xlsx" % TODAY_STR)
        with pd.ExcelWriter(out_path, engine="openpyxl") as writer:

            if monthly_log:
                pd.DataFrame(monthly_log).to_excel(
                    writer, sheet_name="Monthly_Holdings", index=False)

            # Arket skrives ALLTID. Et manglende ark betyr «gammel fil», et
            # tomt ark betyr «kjørt, men ingenting å logge» — master.py sier
            # forskjellige ting om de to, og da må de være forskjellige.
            (pd.DataFrame(score_log) if score_log else pd.DataFrame(
                columns=["date", "ticker", "score", "rank", "valgt"])
             ).to_excel(writer, sheet_name="Score_Log", index=False)
            if not score_log:
                log.warning("Score_Log er TOM — master.py teller da PB-ROE som "
                            "en kilde uten mening om noe selskap.")

            ec_df = ec.reset_index()
            ec_df.columns = ["Date", "Strategy_v3"]
            if not bn.empty:
                ec_df["Benchmark"] = bn.reindex(ec.index, method="ffill").values
            ec_df.to_excel(writer, sheet_name="Equity_Curve", index=False)

            if trade_log:
                pd.DataFrame(trade_log).to_excel(
                    writer, sheet_name="Trade_Log", index=False)

            if stop_log:
                pd.DataFrame(stop_log).to_excel(
                    writer, sheet_name="Stop_Loss_Log", index=False)

            metrics_rows = [
                ("Start Value",       f"${ec.iloc[0]:,.0f}"),
                ("End Value",         f"${ec.iloc[-1]:,.0f}"),
                ("Total Return",      f"{total_ret*100:.1f}%"),
                ("CAGR",              f"{cagr*100:.1f}%"),
                ("Sharpe",            f"{sharpe:.2f}"),
                ("Sortino",           f"{sortino:.2f}"),
                ("Max Drawdown",      f"{mdd*100:.1f}%"),
                ("Calmar",            f"{calmar:.2f}"),
                ("Win Rate",          f"{wr*100:.0f}%"),
                ("Volatility",        f"{vol*100:.1f}%"),
                ("Total Trades",      str(len(trade_log))),
                ("Stop-loss events",  str(n_stops)),
            ]
            if trade_returns:
                profitable = sum(1 for r in trade_returns if r > 0)
                metrics_rows += [
                    ("Avg trade return",  f"{np.mean(trade_returns):+.2f}%"),
                    ("Median trade ret",  f"{np.median(trade_returns):+.2f}%"),
                    ("Best trade",        f"{np.max(trade_returns):+.2f}%"),
                    ("Worst trade",       f"{np.min(trade_returns):+.2f}%"),
                    ("Trade Win Rate",    f"{profitable/len(trade_returns)*100:.1f}%"),
                ]
            if bcagr is not None:
                metrics_rows += [
                    ("Benchmark CAGR",  f"{bcagr*100:.1f}%"),
                    ("Excess Return",   f"{excess_ret*100:+.1f}%"),
                ]

            params_rows = [
                ("N_PORTFOLIO",             str(N_PORTFOLIO)),
                ("MAX_PER_INDUSTRY",        str(MAX_PER_INDUSTRY)),
                ("W_PB",                    f"{W_PB:.0%}"),
                ("W_ROE",                   f"{W_ROE:.0%}"),
                ("W_MOM12",                 f"{W_MOM12:.0%}"),
                ("W_MOM52",                 f"{W_MOM52:.0%}"),
                ("W_ROE_TREND",             f"{W_ROE_TREND:.0%}"),
                ("W_ROE_STAB",              f"{W_ROE_STAB:.0%}"),
                ("MAX_WEIGHT_CAP",          f"{MAX_WEIGHT_CAP:.0%}"),
                ("DRAWDOWN_STOP_PCT",       f"{DRAWDOWN_STOP_PCT:.0%}"),
                ("AVOID_SEPTEMBER",         str(AVOID_SEPTEMBER)),
                ("BENCHMARK_SMA_DAYS",      str(BENCHMARK_SMA_DAYS)),
                ("BEAR_EXPOSURE",           f"{BEAR_EXPOSURE:.0%}"),
                ("MOM_LOOKBACK_MONTHS",     str(MOM_LOOKBACK_MONTHS)),
                ("MOM_SKIP_MONTHS",         str(MOM_SKIP_MONTHS)),
                ("VOL_WINDOW_DAYS",         str(VOL_WINDOW_DAYS)),
                ("MIN_PRICE_DAYS",          str(MIN_PRICE_DAYS)),
                ("EXCLUDE_EURONEXT_GROWTH", str(EXCLUDE_EURONEXT_GROWTH)),
                ("Growth list size",        str(len(growth_excl))),
            ]

            pd.DataFrame(metrics_rows, columns=["Metric", "Value"]).to_excel(
                writer, sheet_name="Metrics", index=False)
            pd.DataFrame(params_rows, columns=["Parameter", "Value"]).to_excel(
                writer, sheet_name="Parameters", index=False)

        log.info("Excel saved: %s", out_path)
        log.info("=== Backtest v3 complete ===")
    # ── Kjør ───────────────────────────────────────────────────────────────────────
    DETAILED_BACKTEST_v3()


    def send_pb_roe_backtest_email():
        """
        Send email with PB/ROE + SMA50 backtest results and current portfolio holdings.
        Reads the latest backtest output files from DataPB_ROE/Backtest/ and Portfolio/.
        Only sends if the portfolio changed since the last email.
        
        Metrics match the backtest log: CAGR, Sharpe, Sortino, Max DD, Win Rate, etc.
        """
        import smtplib
        import pandas as pd
        import numpy as np
        from pathlib import Path
        from datetime import datetime
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        # ── Configuration ─────────────────────────────────────
        BASE_DIR    = Path(r"C:\Users\ander\Desktop\Python_K4\ExcelData\DataPB_ROE")
        BT_DIR      = BASE_DIR / "Backtest"
        EMAIL_USER  = os.environ.get("AKSJE_MAIL_USER", "andyxcx@gmail.com")
        # Passordet sto hardkodet her. Det er nå fjernet fra koden og leses i
        # stedet fra miljøvariabelen eller mail_passord.txt — se
        # finn_mail_passord() i innsidehandel_pipeline.py.
        #
        # Den gamle verdien ligger fortsatt i git-historikken og må regnes som
        # kjent av alle med tilgang til repoet. Lag et nytt app-passord på
        # https://myaccount.google.com/apppasswords, legg det i
        # <ExcelData>\mail_passord.txt, og slett det gamle hos Google.
        EMAIL_PASSWORD = _mail_passord()
        EMAIL_RECIPIENTS = ["andyxcx@gmail.com", "lynnvictoria08@gmail.com"]

        print("\n" + "=" * 70)
        print("📧 PB/ROE BACKTEST EMAIL: Checking for results...")
        print("=" * 70)

        # ── Find latest backtest Excel file ───────────────────
        bt_files = sorted(BT_DIR.glob("Detailed_SMA*_*.xlsx"),
                        key=lambda p: p.stat().st_mtime, reverse=True)
        if not bt_files:
            print("⚠️  No backtest results found — skipping email")
            return

        bt_file = bt_files[0]
        print(f"📁 Latest backtest: {bt_file.name}")

        # ── Load backtest data ────────────────────────────────
        try:
            monthly_df = pd.read_excel(bt_file, sheet_name="Monthly_Holdings")
            equity_df  = pd.read_excel(bt_file, sheet_name="Equity_Curve")
            trade_df   = pd.read_excel(bt_file, sheet_name="Trade_Log")
        except Exception as e:
            print(f"❌ Could not read backtest file: {e}")
            return

        if monthly_df.empty or equity_df.empty:
            print("⚠️  Backtest data is empty — skipping email")
            return

        # ── Extract current holdings from latest month ────────
        latest_month = monthly_df.iloc[-1]
        holdings_str = latest_month.get("holdings", "")
        n_holdings   = latest_month.get("n_holdings", 0)
        portfolio_value = latest_month.get("portfolio_value", 0)
        cash = latest_month.get("cash", 0)
        date_str = latest_month.get("date", "")

        if holdings_str and holdings_str != "CASH — no signal":
            current_tickers = sorted([t.strip() for t in holdings_str.split(",") if t.strip()])
        else:
            current_tickers = []

        # ── Check if portfolio changed vs last sent ───────────
        last_sent_file = BT_DIR / "_last_emailed_holdings.txt"
        previous_tickers = []
        if last_sent_file.exists():
            try:
                previous_tickers = last_sent_file.read_text().strip().split(",")
                previous_tickers = [t.strip() for t in previous_tickers if t.strip()]
            except:
                pass

        if sorted(current_tickers) == sorted(previous_tickers):
            print(f"⏭️  SKIPPING EMAIL: Portfolio unchanged ({current_tickers})")
            return

        print(f"✅ Portfolio changed!")
        print(f"   Previous: {previous_tickers}")
        print(f"   Current:  {current_tickers}")

        # ── Calculate metrics (matching backtest log exactly) ─
        equity_df["Date"] = pd.to_datetime(equity_df["Date"])
        ec = equity_df.set_index("Date")["Strategy"]
        rets = ec.pct_change().dropna()

        start_value = ec.iloc[0]
        end_value   = ec.iloc[-1]
        total_return = (end_value / start_value - 1) * 100
        n_years = max((ec.index[-1] - ec.index[0]).days / 365.25, 0.01)
        n_trades = len(trade_df) if not trade_df.empty else 0

        # CAGR
        cagr = ((end_value / start_value) ** (1 / n_years) - 1) * 100

        # Volatility (annualized from monthly)
        vol = rets.std() * np.sqrt(12) * 100

        # Sharpe (using 3% risk-free)
        sharpe = (cagr / 100 - 0.03) / (vol / 100) if vol > 0 else 0

        # Max Drawdown
        cummax = ec.cummax()
        mdd = ((ec - cummax) / cummax).min() * 100

        # Win Rate
        wr = (rets > 0).sum() / len(rets) * 100 if len(rets) > 0 else 0

        # Sortino
        ds = rets[rets < 0]
        dv = ds.std() * np.sqrt(12) if len(ds) > 0 else 0
        sortino = (cagr / 100 - 0.03) / dv if dv > 0 else 0

        # Calmar
        calmar = (cagr / 100) / abs(mdd / 100) if mdd != 0 else 0

        # Benchmark
        bcagr = None
        excess_cagr = None
        if "Benchmark" in equity_df.columns:
            bm = equity_df.set_index("Date")["Benchmark"].dropna()
            if len(bm) >= 2:
                bcagr = ((bm.iloc[-1] / bm.iloc[0]) ** (1 / n_years) - 1) * 100
                excess_cagr = cagr - bcagr

        # ── Get buys/sells from latest month ──────────────────
        buys_str  = latest_month.get("buys", "")
        sells_str = latest_month.get("sells", "")
        new_buys  = [t.strip() for t in buys_str.split(",") if t.strip()] if buys_str else []
        new_sells = [t.strip() for t in sells_str.split(",") if t.strip()] if sells_str else []

        # ── Build HTML email ──────────────────────────────────
        today = datetime.now().strftime('%Y-%m-%d')

        html = f"""<html><head><style>
    body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
    .container {{ max-width: 800px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
    h1 {{ color: #2c3e50; border-bottom: 3px solid #1565C0; padding-bottom: 10px; }}
    h2 {{ color: #34495e; margin-top: 25px; border-left: 4px solid #1565C0; padding-left: 10px; }}
    .metrics {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin: 20px 0; }}
    .metric-card {{ background: linear-gradient(135deg, #1565C0 0%, #0D47A1 100%); color: white; padding: 20px; border-radius: 8px; text-align: center; }}
    .metric-value {{ font-size: 28px; font-weight: bold; margin: 10px 0; }}
    .metric-label {{ font-size: 12px; opacity: 0.9; text-transform: uppercase; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
    th {{ background-color: #1565C0; color: white; padding: 12px; text-align: left; }}
    td {{ border: 1px solid #ddd; padding: 10px; }}
    tr:nth-child(even) {{ background-color: #f9f9f9; }}
    .positive {{ color: #27ae60; font-weight: bold; }}
    .negative {{ color: #e74c3c; font-weight: bold; }}
    .change-box {{ background-color: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 20px 0; }}
    .strategy-box {{ background-color: #e8f4fd; padding: 15px; border-left: 4px solid #1565C0; margin: 20px 0; }}
    .stats-table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
    .stats-table td {{ padding: 8px 12px; border-bottom: 1px solid #eee; }}
    .stats-table td:first-child {{ color: #666; width: 55%; }}
    .stats-table td:last-child {{ font-weight: bold; text-align: right; }}
    .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #7f8c8d; font-size: 12px; text-align: center; }}
    </style></head><body><div class="container">
    <h1>📊 PB/ROE + SMA50 Portfolio Update</h1>
    <p><strong>Date:</strong> {today} | <strong>Period:</strong> {date_str}</p>

    <div class="strategy-box">
    <h3>Strategy</h3>
    <p>Top 5 OSEBX stocks by PB (50%) + ROE (50%), filtered by 50-day SMA uptrend. Max 1 per industry. Monthly rebalance.</p>
    </div>"""

        # Changes section
        if new_buys or new_sells:
            html += '<div class="change-box"><h3>📊 Changes This Month</h3>'
            if new_buys:
                html += f"<p><strong>➕ BUY:</strong> {', '.join(new_buys)}</p>"
            if new_sells:
                html += f"<p><strong>➖ SELL:</strong> {', '.join(new_sells)}</p>"
            html += "</div>"

        # Top metrics cards — CAGR based (matching backtest log)
        benchmark_card = ""
        if bcagr is not None:
            benchmark_card = f"""<div class="metric-card">
    <div class="metric-label">Benchmark CAGR</div>
    <div class="metric-value">{bcagr:.1f}%</div>
    <div class="metric-label">Excess: {excess_cagr:+.1f}%</div>
    </div>"""
        else:
            benchmark_card = f"""<div class="metric-card">
    <div class="metric-label">Total Trades</div>
    <div class="metric-value">{n_trades}</div>
    </div>"""

        html += f"""<div class="metrics">
    <div class="metric-card">
    <div class="metric-label">CAGR</div>
    <div class="metric-value {'positive' if cagr > 0 else 'negative'}">{cagr:.1f}%</div>
    </div>
    <div class="metric-card">
    <div class="metric-label">Sharpe Ratio</div>
    <div class="metric-value">{sharpe:.2f}</div>
    </div>
    {benchmark_card}
    </div>"""

        # Full results table — matching backtest log exactly
        html += """<h2>📈 Results</h2>
    <table class="stats-table">"""

        stats_rows = [
            ("Start Value",     f"${start_value:,.0f}"),
            ("End Value",       f"${end_value:,.0f}"),
            ("Total Return",    f"{total_return:.1f}%"),
            ("CAGR",            f"{cagr:.1f}%"),
            ("Sharpe",          f"{sharpe:.2f}"),
            ("Sortino",         f"{sortino:.2f}"),
            ("Max Drawdown",    f"{mdd:.1f}%"),
            ("Calmar",          f"{calmar:.2f}"),
            ("Win Rate",        f"{wr:.0f}%"),
            ("Volatility",      f"{vol:.1f}%"),
            ("Total Trades",    f"{n_trades}"),
        ]
        if bcagr is not None:
            stats_rows.append(("Benchmark CAGR", f"{bcagr:.1f}%"))
            stats_rows.append(("Excess Return",  f"{excess_cagr:+.1f}%"))

        for label, value in stats_rows:
            html += f"<tr><td>{label}</td><td>{value}</td></tr>"

        html += "</table>"

        # Holdings table
        html += """<h2>📋 Current Holdings</h2>
    <table><tr><th>#</th><th>Ticker</th></tr>"""

        if current_tickers:
            for i, ticker in enumerate(current_tickers, 1):
                html += f"<tr><td>{i}</td><td><strong>{ticker}</strong></td></tr>"
        else:
            html += '<tr><td colspan="2" style="text-align: center;">CASH — no positions</td></tr>'

        html += "</table>"
        html += f"<p><strong>Cash:</strong> ${cash:,.0f}</p>"

        # Footer
        html += f"""<div class="footer">
    <p>Automated alert from PB/ROE + SMA50 backtest</p>
    <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div></div></body></html>"""

        # ── Send email ────────────────────────────────────────
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = (
                f"📊 PB/ROE SMA50: {len(current_tickers)} stocks | "
                f"CAGR {cagr:.1f}%"
            )
            if bcagr is not None:
                msg['Subject'] += f" | Excess {excess_cagr:+.1f}%"
            msg['Subject'] += f" — {today}"
            msg['From'] = EMAIL_USER
            msg['To'] = ', '.join(EMAIL_RECIPIENTS)
            msg.attach(MIMEText(html, 'html'))

            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)
            server.quit()

            # Save current holdings so we don't re-send
            last_sent_file.write_text(",".join(current_tickers))

            print(f"\n✅ Email sent to {len(EMAIL_RECIPIENTS)} recipients!")
            print(f"   Subject: {msg['Subject']}")

        except Exception as e:
            print(f"\n❌ Email failed: {e}")
            import traceback
            traceback.print_exc()
    # Call after backtest:
    #send_pb_roe_backtest_email()
#PBROE_All3()


##Innsidere



##Mgmt sentiment #Cagr 24%
def SentimentManagement():
    # ══════════════════════════════════════════════════════════════════════
    # SKRAPER OG MOTOR — TO VALG, IKKE ETT
    # ══════════════════════════════════════════════════════════════════════
    #
    # Det finnes to komplette utgaver av NLP-strategien i denne funksjonen.
    # Begge het NlpSentimentTrader4, og den nederste overskrev den øverste i
    # navnerommet — at det likevel var v4 som kjørte, skyldtes bare at kallet
    # sto MELLOM de to definisjonene.
    #
    # Men de to utgavene er egentlig FIRE ting, ikke to: en skraper som
    # skriver artikler til DataNLP, og en backtest-motor som leser dem. De
    # henger ikke sammen — motoren bryr seg ikke om hvem som hentet
    # artiklene. Å binde dem parvis ville tvunget deg til å velge mellom
    #
    #     dyp historikk  +  en utestet motor
    #     grunn historikk +  en motor som har kjørt i månedsvis
    #
    # og ingen av de to er valget du vil ta. Derfor er de to separate brytere.
    #
    #   SKRAPER   "v4"    10 artikler per selskap, bare side 1
    #             "v4.1"  100 per selskap, blar gjennom opptil 15 sider
    #   MOTOR     "v4"    Sentiment_v4_SMA<n>_<dato>.xlsx    ← testet
    #             "v4.1"  Sentiment_v4_1_SMA<n>_<dato>.xlsx  ← utestet
    #
    # Standard er derfor den dype skraperen med den testede motoren.
    # master.py leter etter Sentiment_v4*_SMA*.xlsx og finner begge, så den
    # trenger ingen endring uansett hva du velger.
    #
    # Kan styres uten å endre koden:
    #     set AKSJE_NLP_HENT=1           (eller: python master.py --hent-nlp)
    #     set AKSJE_NLP_SKRAPER=v4.1
    #     set AKSJE_NLP_MOTOR=v4
    NLP_SKRAPER = os.environ.get("AKSJE_NLP_SKRAPER", "v4.1").strip()
    NLP_MOTOR = os.environ.get("AKSJE_NLP_MOTOR", "v4").strip()

    # Skrapingen er det dyre steget — nettleser, paginering og språkmodell,
    # timer for hele børsen. Derfor står den AV som standard, og strategien
    # kjører på artiklene som allerede ligger i DataNLP. Slå den på når du vil
    # utvide historikken.
    HENT_NYE_ARTIKLER = _miljo_paa("AKSJE_NLP_HENT")

    # De under funker, ikke den over
    ### Managment sentiment
    #Henter data for nlp av kvartallstall etc
    def NLP_Euronext_Quarter4_v4():
            
        #!/usr/bin/env python3
        """
        ================================================================================
        EURONEXT OSLO BØRS — COMPANY-PAGE SCRAPER + FINBERT NLP  (v3 — FASTER)
        ================================================================================
        Forbedringer vs. v2:
        ✅ Mye raskere: redusert slow_mo, step_delay, request_delay
        ✅ Robust modal-lukking: verifiserer at modal faktisk er lukket
        ✅ Kortere timeout på modal-klikk (15s i stedet for 30s)
        ✅ Scroll-into-view før modal-klikk for å unngå overlay-blokkering
        ✅ Dismiss alle modaler via JS før neste klikk
        ✅ Parallell PDF-ekstraksjon der mulig

        KRAV:
        pip install playwright pandas openpyxl transformers torch nltk pdfplumber requests
        playwright install chromium
        ================================================================================
        """

        import asyncio
        import io
        import logging
        import os
        import re
        import sys
        import time
        from dataclasses import dataclass, field
        from datetime import datetime
        from pathlib import Path
        from typing import List, Optional

        import pandas as pd

        # ─────────────────────────────────────────────────────────────────────────────
        # CONFIG
        # ─────────────────────────────────────────────────────────────────────────────

        @dataclass
        class Config:
            base_dir: Path          = Path(r"C:\Users\ander\Desktop\Python_K4\ExcelData")
            #tickers_file: str       = r"Data_BT\AllTickers_OSEBX_.xlsx"
            tickers_file: str       = r"Data_BT\AllTickers_OSEBX_TW_current.xlsx"
            nlp_output_dir: str     = "DataNLP"
            working_data_dir: str   = r"DataNLP\WorkingData"
            screenshots_dir: str    = r"DataNLP\Screenshots"

            # ── SPEED TUNING (v3) ──
            step_delay_ms: int      = 500          # was 1500
            start_url: str          = "https://live.euronext.com/nb/product/equities/NO0010161896-XOSL"
            euronext_base: str      = "https://live.euronext.com"

            max_articles_per_company: int = 10
            headless: bool          = True #False
            slow_mo: int            = 40           # was 120 — biggest single speedup
            request_delay: float    = 0.8          # was 2.0
            page_timeout: int       = 25_000       # was 30_000
            modal_click_timeout: int = 12_000      # NEW: shorter timeout for modal clicks
            modal_wait_ms: int      = 1_800        # NEW: wait for modal content to load
            modal_close_verify_ms: int = 600       # NEW: time to verify modal closed

            finbert_model: str      = "yiyanghkust/finbert-tone"
            max_sentences: int      = 100
            force_rerun: bool       = True

            # ── Søke-retry: prøv ulike varianter av selskapsnavnet ──
            search_retry_variants: bool = True

            @property
            def tickers_path(self) -> Path:
                return self.base_dir / self.tickers_file

            @property
            def nlp_dir(self) -> Path:
                p = self.base_dir / self.nlp_output_dir
                p.mkdir(parents=True, exist_ok=True)
                return p

            @property
            def work_dir(self) -> Path:
                p = self.base_dir / self.working_data_dir
                p.mkdir(parents=True, exist_ok=True)
                return p

            @property
            def screenshot_dir(self) -> Path:
                p = self.base_dir / self.screenshots_dir
                p.mkdir(parents=True, exist_ok=True)
                return p


        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s │ %(levelname)-7s │ %(message)s",
            datefmt="%H:%M:%S",
        )
        log = logging.getLogger(__name__)

        # ─────────────────────────────────────────────────────────────────────────────
        # STEG-LOGGER
        # ─────────────────────────────────────────────────────────────────────────────

        class StepLogger:
            def __init__(self, company: str):
                self.company = company
                self.n = 0

            def step(self, desc: str):
                self.n += 1
                print(f"\n  ┌─ STEG {self.n}: {desc}  [{self.company}]")

            def ok(self, detail: str = ""):
                msg = f"  └─ ✅ STEG {self.n} FERDIG"
                if detail:
                    msg += f": {detail}"
                print(msg)

            def fail(self, detail: str = ""):
                msg = f"  └─ ❌ STEG {self.n} FEILET"
                if detail:
                    msg += f": {detail}"
                print(msg)

            def info(self, detail: str):
                print(f"  │  ℹ️  {detail}")

            def warn(self, detail: str):
                print(f"  │  ⚠️  {detail}")


        # ─────────────────────────────────────────────────────────────────────────────
        # HJELPEFUNKSJONER
        # ─────────────────────────────────────────────────────────────────────────────

        def _safe_name(text: str, max_len: int = 30) -> str:
            return re.sub(r'[^\w]', '_', text)[:max_len]


        def _search_variants(company_name: str) -> List[str]:
            """
            Generer søkevarianter for et selskapsnavn.
            F.eks. 'Aker BP ASA' → ['Aker BP ASA', 'Aker BP', 'Aker']
            """
            variants = [company_name]
            # Fjern vanlige suffiks
            cleaned = re.sub(r'\s+(ASA|AS|A/S|Holding|Group|Gruppen)\s*$', '', company_name, flags=re.IGNORECASE).strip()
            if cleaned != company_name and cleaned:
                variants.append(cleaned)
            # Første to ord (for sammensatte navn)
            words = company_name.split()
            if len(words) >= 2:
                two_words = " ".join(words[:2])
                if two_words not in variants:
                    variants.append(two_words)
            # Første ord alene
            if len(words) >= 1 and words[0] not in variants:
                variants.append(words[0])
            return variants


        async def safe_screenshot(page, path: Path, label: str = ""):
            try:
                await page.screenshot(path=str(path), full_page=False)
                if label:
                    log.info(f"📸 Screenshot: {label} → {path.name}")
            except Exception as e:
                log.warning(f"Screenshot feilet ({label}): {e}")


        async def click_xpath(page, xpath: str, description: str,
                            timeout: int = 10_000, scroll: bool = True) -> bool:
            try:
                loc = page.locator(f"xpath={xpath}")
                count = await loc.count()
                if count == 0:
                    log.debug(f"  XPath 0 treff: {xpath[:80]}")
                    return False

                el = loc.first
                try:
                    await el.wait_for(state="visible", timeout=timeout)
                except Exception:
                    if scroll:
                        try:
                            await el.scroll_into_view_if_needed(timeout=5_000)
                            await page.wait_for_timeout(300)
                        except Exception:
                            pass

                await el.click(timeout=timeout)
                log.info(f"  ✓ Klikket: {description}")
                return True

            except Exception as e:
                log.debug(f"  click_xpath feilet ({description}): {e}")
                return False


        async def click_any(page, selectors: list, description: str,
                            timeout: int = 8_000) -> bool:
            for sel in selectors:
                try:
                    prefix = "xpath=" if sel.startswith("/") else ""
                    loc = page.locator(f"{prefix}{sel}")
                    if await loc.count() == 0:
                        continue
                    el = loc.first
                    try:
                        await el.wait_for(state="visible", timeout=timeout)
                    except Exception:
                        try:
                            await el.scroll_into_view_if_needed(timeout=3_000)
                            await page.wait_for_timeout(200)
                        except Exception:
                            pass
                    await el.click(timeout=timeout)
                    log.info(f"  ✓ Klikket (fallback): {description}  [{sel[:60]}]")
                    return True
                except Exception:
                    continue
            log.warning(f"  ✗ Alle selektorer feilet: {description}")
            return False


        def _clean_text(raw: str) -> str:
            if not raw:
                return ""
            skip = [
                "skip to main content", "toggle navigation", "euronext websites",
                "my profile", "my subscriptions", "watchlists", "quote alerts",
                "create account", "sign in", "close menu", "© 20",
                "privacy statement", "terms of use", "cookie policy",
                "to subscribe to press releases", "footer small print",
                "reject all", "accept all", "cookie settings",
            ]
            lines = []
            for line in raw.split("\n"):
                low = line.strip().lower()
                if any(p in low for p in skip):
                    continue
                if line.strip():
                    lines.append(line.strip())
            text = "\n".join(lines)
            text = re.sub(r"\n{3,}", "\n\n", text)
            return text.strip()


        # ─────────────────────────────────────────────────────────────────────────────
        # PDF-EKSTRAKSJON
        # ─────────────────────────────────────────────────────────────────────────────

        def extract_text_from_pdf_url(pdf_url: str) -> str:
            try:
                import requests
                import pdfplumber
                headers = {
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    )
                }
                resp = requests.get(pdf_url, headers=headers, timeout=30)
                resp.raise_for_status()
                with pdfplumber.open(io.BytesIO(resp.content)) as pdf:
                    texts = [pg.extract_text() for pg in pdf.pages if pg.extract_text()]
                full = "\n\n".join(texts)
                log.info(f"  📄 PDF fra URL: {len(full)} tegn")
                return _clean_text(full)
            except ImportError:
                log.warning("  pdfplumber ikke installert — hopper over PDF")
                return ""
            except Exception as e:
                log.error(f"  PDF URL-ekstraksjon feilet ({pdf_url}): {e}")
                return ""


        def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
            try:
                import pdfplumber
                with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                    texts = [pg.extract_text() for pg in pdf.pages if pg.extract_text()]
                return _clean_text("\n\n".join(texts))
            except Exception as e:
                log.error(f"  PDF bytes-ekstraksjon feilet: {e}")
                return ""


        # ─────────────────────────────────────────────────────────────────────────────
        # DATA-KLASSE
        # ─────────────────────────────────────────────────────────────────────────────

        @dataclass
        class Article:
            company: str
            title: str
            url: str
            date: str
            text: str    = ""
            pdf_url: str = ""


        # ─────────────────────────────────────────────────────────────────────────────
        # LAST SELSKAPER FRA EXCEL
        # ─────────────────────────────────────────────────────────────────────────────

        def load_companies(config: Config) -> List[str]:
            path = config.tickers_path
            if not path.exists():
                log.error(f"Fil ikke funnet: {path}")
                raise FileNotFoundError(path)
            df = pd.read_excel(path)
            #df = df.loc[:, ~df.columns.str.contains("^Unnamed")]
            df = df.loc[:, ~df.columns.astype(str).str.contains("^Unnamed", na=False)]

            for col in ["Company", "company", "Name", "name"]:
                if col in df.columns:
                    return df[col].dropna().astype(str).tolist()
            return df.iloc[:, 0].dropna().astype(str).tolist()


        # ─────────────────────────────────────────────────────────────────────────────
        # SØK + DROPDOWN  (forbedret med retry-varianter)
        # ─────────────────────────────────────────────────────────────────────────────

        async def search_and_select_company(page, company_name: str, config: Config, sl: StepLogger) -> bool:
            variants = _search_variants(company_name) if config.search_retry_variants else [company_name]

            for attempt, search_term in enumerate(variants):
                sl.info(f"Søkeforsøk {attempt + 1}/{len(variants)}: '{search_term}'")

                search_loc = None
                try:
                    loc = page.locator(f"xpath={XP['SEARCH_INPUT']}")
                    if await loc.count() > 0:
                        search_loc = loc
                    else:
                        for sel in ["input[name='search_symbol']", "nav input[type='text']",
                                    "header form input[type='text']"]:
                            loc = page.locator(sel)
                            if await loc.count() > 0:
                                search_loc = loc
                                break
                except Exception:
                    pass

                if not search_loc:
                    sl.fail("Søkefelt ikke funnet")
                    return False

                try:
                    await search_loc.first.click(timeout=8_000)
                    await page.wait_for_timeout(200)
                    await search_loc.first.fill("")
                    await page.wait_for_timeout(200)
                    await search_loc.first.type(search_term, delay=60)  # was 80
                    sl.info(f"Skrev '{search_term}' — venter på dropdown...")
                    await page.wait_for_timeout(2_500)  # was 3000
                except Exception as e:
                    sl.warn(f"Kunne ikke skrive i søkefelt: {e}")
                    continue

                clicked = await click_xpath(page, XP["DROPDOWN_FIRST"], "Dropdown første treff", timeout=8_000)
                if not clicked:
                    clicked = await click_any(
                        page,
                        ["ul.ui-autocomplete li:first-child a",
                        ".ui-autocomplete li:first-child a",
                        "ul[role='listbox'] li:first-child a",
                        "ul.ui-autocomplete li:first-child",
                        ".ui-autocomplete li:first-child"],
                        "Dropdown fallback"
                    )

                if clicked:
                    try:
                        await page.wait_for_load_state("networkidle", timeout=15_000)
                    except Exception:
                        pass
                    await page.wait_for_timeout(1_500)

                    current_url = page.url
                    if "/product/equities/" in current_url:
                        sl.ok(f"Selskapside lastet: {current_url[:80]}")
                        return True
                    else:
                        sl.warn(f"Uventet URL etter søk: {current_url[:80]} — prøver neste variant")
                        try:
                            await page.goto(config.start_url, wait_until="networkidle", timeout=config.page_timeout)
                            await page.wait_for_timeout(1_500)
                        except Exception:
                            pass
                        continue
                else:
                    sl.info(f"Ingen dropdown-treff for '{search_term}'")
                    try:
                        await page.keyboard.press("Escape")
                        await page.wait_for_timeout(300)
                    except Exception:
                        pass
                    continue

            return False


        # ─────────────────────────────────────────────────────────────────────────────
        # FORCE-DISMISS ALL MODALS (v3 — ny funksjon)
        # ─────────────────────────────────────────────────────────────────────────────

        async def _force_dismiss_all_modals(page, config: Config):
            """
            Aggressively close ALL open modals via JS + keyboard.
            This prevents modal stacking that causes timeout on articles 8-10.
            """
            # 1) JS: hide all modals, remove backdrops, restore body scroll
            await page.evaluate("""
            () => {
                // Hide all modal elements
                document.querySelectorAll('.modal.show, .modal.in, .modal[style*="display: block"]')
                    .forEach(m => {
                        m.classList.remove('show', 'in');
                        m.style.display = 'none';
                        m.setAttribute('aria-hidden', 'true');
                        m.removeAttribute('aria-modal');
                    });
                // Remove all modal backdrops
                document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
                // Restore body scroll
                document.body.classList.remove('modal-open');
                document.body.style.overflow = '';
                document.body.style.paddingRight = '';
            }
            """)
            # 2) Press Escape as backup
            try:
                await page.keyboard.press("Escape")
            except Exception:
                pass
            await page.wait_for_timeout(config.modal_close_verify_ms)

            # 3) Verify no modal is blocking
            still_open = await page.evaluate("""
            () => {
                const m = document.querySelector('.modal.show, .modal.in, .modal[style*="display: block"]');
                return !!m;
            }
            """)
            if still_open:
                log.warning("  ⚠️ Modal still open after force-dismiss — retrying")
                await page.evaluate("""
                () => {
                    document.querySelectorAll('.modal').forEach(m => {
                        m.style.display = 'none';
                        m.classList.remove('show', 'in');
                    });
                    document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
                    document.body.classList.remove('modal-open');
                    document.body.style.overflow = '';
                }
                """)
                await page.wait_for_timeout(300)


        # ─────────────────────────────────────────────────────────────────────────────
        # HENT TEKST FRA MODAL  (v3 — faster, with force-dismiss)
        # ─────────────────────────────────────────────────────────────────────────────

        async def fetch_modal_text(page, nid: str, config: Config) -> str:
            """
            Klikker lenken med data-node-nid=nid, venter på at modalen åpner seg,
            og henter teksten fra modal-innholdet.
            v3: Force-dismisses previous modals, uses shorter timeout, scrolls into view.
            """
            try:
                # ── PRE-STEP: ensure no leftover modals are blocking ──
                await _force_dismiss_all_modals(page, config)

                # ── Scroll the link into view first ──
                link_sel = f"a.standardRightCompanyPressRelease[data-node-nid='{nid}']"
                loc = page.locator(link_sel)
                if await loc.count() == 0:
                    log.warning(f"  Modal-lenke ikke funnet for nid={nid}")
                    return ""

                try:
                    await loc.first.scroll_into_view_if_needed(timeout=5_000)
                    await page.wait_for_timeout(300)
                except Exception:
                    pass

                # ── Click with shorter timeout ──
                await loc.first.click(timeout=config.modal_click_timeout)
                log.info(f"  ✓ Klikket modal-lenke nid={nid}")
                await page.wait_for_timeout(config.modal_wait_ms)

                # ── Strategi 1: Finn den spesifikke modalen via nid ──
                nid_modal_text = await page.evaluate("""
                (nid) => {
                    const modal = document.querySelector(
                        '#CompanyPressRelease-' + nid + ', ' +
                        '[id*="CompanyPressRelease"][id*="' + nid + '"]'
                    );
                    if (modal) {
                        const body = modal.querySelector('.modal-body');
                        if (body && body.innerText.trim().length > 50) {
                            return body.innerText.trim();
                        }
                    }
                    return '';
                }
                """, nid)

                if nid_modal_text and len(nid_modal_text) > 100:
                    log.info(f"  📄 Modal via nid: {len(nid_modal_text)} tegn")
                    await _force_dismiss_all_modals(page, config)
                    return _clean_text(nid_modal_text)

                # ── Strategi 2: Finn den synlige/aktive modalen dynamisk ──
                dynamic_text = await page.evaluate("""
                () => {
                    const modals = document.querySelectorAll(
                        '.modal.show, .modal.in, .modal[style*="display: block"], ' +
                        '.modal[aria-modal="true"], [role="dialog"]:not([style*="display: none"])'
                    );
                    let bestText = '';
                    for (const modal of modals) {
                        const body = modal.querySelector('.modal-body');
                        if (body) {
                            const t = body.innerText.trim();
                            if (t.length > bestText.length) bestText = t;
                        }
                        if (bestText.length < 100) {
                            const content = modal.querySelector('.modal-content');
                            if (content) {
                                const t = content.innerText.trim();
                                if (t.length > bestText.length) bestText = t;
                            }
                        }
                    }
                    return bestText;
                }
                """)

                if dynamic_text and len(dynamic_text) > 100:
                    log.info(f"  📄 Modal dynamisk: {len(dynamic_text)} tegn")
                    await _force_dismiss_all_modals(page, config)
                    return _clean_text(dynamic_text)

                # ── Strategi 3: Hardkodede XPath-mønstrene (original fallback) ──
                modal_xpaths = [
                    "/html/body/div[5]/div/div/div[2]/div[2]/div[4]/div/p[1]",
                    "/html/body/div[6]/div/div/div[2]/div[2]/div[4]/div/p[1]",
                    "/html/body/div[7]/div/div/div[2]/div[2]/div[4]/div/p[1]",
                    "/html/body/div[8]/div/div/div[2]/div[2]/div[4]/div/p[1]",
                    "/html/body/div[9]/div/div/div[2]/div[2]/div[4]/div/p[1]",
                ]

                best_text = ""
                best_xp   = ""
                for xp in modal_xpaths:
                    try:
                        el = page.locator(f"xpath={xp}")
                        if await el.count() > 0:
                            t = (await el.first.inner_text()).strip()
                            if len(t) > len(best_text):
                                best_text = t
                                best_xp   = xp
                    except Exception:
                        continue

                if best_text and best_xp:
                    container_xp = best_xp.replace("/p[1]", "")
                    try:
                        container = page.locator(f"xpath={container_xp}")
                        if await container.count() > 0:
                            full_text = (await container.first.inner_text()).strip()
                            if len(full_text) > len(best_text):
                                best_text = full_text
                    except Exception:
                        pass
                    log.info(f"  📄 Modal XPath: {len(best_text)} tegn")
                    await _force_dismiss_all_modals(page, config)
                    return _clean_text(best_text)

                # ── Strategi 4: CSS fallback-selektorer ──
                modal_css_selectors = [
                    ".modal.show .modal-body",
                    ".modal.in .modal-body",
                    f"#CompanyPressRelease-{nid} .modal-body",
                    "[id^='CompanyPressRelease-'].show .modal-body",
                    "[id^='CompanyPressRelease-'].in .modal-body",
                    ".modal-dialog .modal-body",
                    ".modal.show .modal-content",
                    ".modal.in .modal-content",
                ]
                for sel in modal_css_selectors:
                    try:
                        el = page.locator(sel)
                        if await el.count() > 0:
                            await el.first.wait_for(state="visible", timeout=4_000)
                            t = (await el.first.inner_text()).strip()
                            if len(t) > 100:
                                log.info(f"  📄 Modal CSS ({sel}): {len(t)} tegn")
                                await _force_dismiss_all_modals(page, config)
                                return _clean_text(t)
                    except Exception:
                        continue

                log.warning(f"  Modal-tekst ikke funnet for nid={nid}")
                await _force_dismiss_all_modals(page, config)
                return ""

            except Exception as e:
                log.error(f"  fetch_modal_text feilet (nid={nid}): {e}")
                # Always force-dismiss on error to prevent stacking
                try:
                    await _force_dismiss_all_modals(page, config)
                except Exception:
                    pass
                return ""


        async def _close_modal(page):
            """Legacy close — kept for compatibility but _force_dismiss_all_modals is preferred."""
            try:
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(500)
            except Exception:
                pass
            close_selectors = [
                ".modal.show .close",
                ".modal.in .close",
                ".modal-header button.close",
                ".modal.show button[aria-label='Close']",
                ".modal.show .btn-close",
                "button.close[data-dismiss='modal']",
            ]
            for sel in close_selectors:
                try:
                    cl = page.locator(sel)
                    if await cl.count() > 0:
                        await cl.first.click()
                        await page.wait_for_timeout(400)
                        return
                except Exception:
                    continue
            try:
                await page.mouse.click(10, 10)
                await page.wait_for_timeout(300)
            except Exception:
                pass


        # ─────────────────────────────────────────────────────────────────────────────
        # HENT ARTIKKELTEKST  (brukes for artikler med ekte href)
        # ─────────────────────────────────────────────────────────────────────────────

        async def fetch_article_text(page, article: Article, config: Config,
                                    return_url: str = "") -> str:
            try:
                await page.goto(article.url, wait_until="networkidle", timeout=config.page_timeout)
                await page.wait_for_timeout(1_500)

                content_type = await page.evaluate("() => document.contentType || ''")
                if "pdf" in content_type.lower() or article.url.lower().endswith(".pdf"):
                    pdf_bytes = await page.evaluate("""
                        async () => {
                            const resp = await fetch(window.location.href);
                            const buf  = await resp.arrayBuffer();
                            return Array.from(new Uint8Array(buf));
                        }
                    """)
                    text = extract_text_from_pdf_bytes(bytes(pdf_bytes))
                    if return_url:
                        await _navigate_back(page, return_url, config)
                    return text

                pdf_link = await page.evaluate("""
                () => {
                    for (const a of document.querySelectorAll('a[href]')) {
                        const h = a.href || '';
                        if (h.toLowerCase().endsWith('.pdf') ||
                            h.toLowerCase().includes('/pdf') ||
                            (a.innerText && a.innerText.toLowerCase().includes('pdf'))) {
                            return h;
                        }
                    }
                    return null;
                }
                """)

                html_text = await page.evaluate("""
                () => {
                    const selectors = [
                        '.field--name-field-press-release-body',
                        '.field--name-body',
                        '.node__content .field--type-text-with-summary',
                        '.node__content .field--type-text-long',
                        'article .field--name-body',
                        '.press-release-content',
                        '.article-body',
                        '[class*="press-release"]',
                        '[class*="article-content"]',
                    ];
                    for (const sel of selectors) {
                        const el = document.querySelector(sel);
                        if (el && el.innerText.trim().length > 100)
                            return el.innerText.trim();
                    }
                    const main = document.querySelector('#main-content, main, [role="main"]');
                    if (main) {
                        const clone = main.cloneNode(true);
                        clone.querySelectorAll(
                            'nav, footer, .menu, .breadcrumb, .pager, ' +
                            '.cookie-banner, #onetrust-banner-sdk'
                        ).forEach(n => n.remove());
                        const t = clone.innerText.trim();
                        if (t.length > 200) return t;
                    }
                    return document.body.innerText.substring(0, 15000);
                }
                """)
                html_text = _clean_text(html_text)

                if pdf_link and len(html_text) < 500:
                    log.info(f"  📎 PDF-lenke funnet: {pdf_link}")
                    article.pdf_url = pdf_link
                    pdf_text = extract_text_from_pdf_url(pdf_link)
                    if len(pdf_text) > len(html_text):
                        html_text = pdf_text

                if return_url:
                    await _navigate_back(page, return_url, config)

                return html_text

            except Exception as e:
                log.error(f"  Feil ved henting av artikkel {article.url}: {e}")
                if return_url:
                    try:
                        await _navigate_back(page, return_url, config)
                    except Exception:
                        pass
                return ""


        async def _navigate_back(page, url: str, config: Config):
            try:
                await page.goto(url, wait_until="networkidle", timeout=config.page_timeout)
                await page.wait_for_timeout(1_500)
            except Exception as e:
                log.warning(f"  Navigering tilbake feilet ({url[:60]}): {e}")
                try:
                    await page.go_back(wait_until="networkidle", timeout=config.page_timeout)
                    await page.wait_for_timeout(1_500)
                except Exception:
                    pass


        # ─────────────────────────────────────────────────────────────────────────────
        # HOVED SCRAPING PER SELSKAP
        # ─────────────────────────────────────────────────────────────────────────────

        XP = {
            "COOKIES":        "//*[@id='onetrust-reject-all-handler']",
            "SELSKAPSINFO":   "/html/body/div[2]/div[1]/div/div/div[1]/section/div[3]/div/div/div/div/nav/div/a[3]",
            "SE_ALLE":        "/html/body/div[2]/div[1]/div/div/div[1]/div/div[2]/div[1]/section/div[2]/div[2]/div[1]/div/ul/li[2]/a/svg",
            "FILTER_BTN":     "/html/body/div[2]/div[1]/div/div/div[1]/div[3]/div/main/section/div[2]/div[2]/div/div[1]/div/button[2]",
            "TOPIC_BTN":      "/html/body/div[2]/div[1]/div/div/div[1]/div[3]/div/main/section/div[2]/div[2]/div/div[1]/div/div[1]/div/div/div[2]/div/div/div[2]/div/form/div/div[3]/div/div[1]/div[2]/button",
            "HALVAAR":        "/html/body/div[2]/div[1]/div/div/div[1]/div[3]/div/main/section/div[2]/div[2]/div/div[1]/div/div[1]/div/div/div[2]/div/div/div[2]/div/form/div/div[3]/div/div[2]/div/div/div/div[12]/label",
            "AARSRAPPORT":    "label[for='edit-field-company-press-releases-target-id-1070']",
            "APPLY":          "/html/body/div[2]/div[1]/div/div/div[1]/div[3]/div/main/section/div[2]/div[2]/div/div[1]/div/div[1]/div/div/div[2]/div/div/div[2]/div/form/div/div[5]/input",
            "SEARCH_INPUT":   "/html/body/div[2]/div[1]/div/div/header/nav[1]/div/div[2]/div[1]/form/div[2]/input",
            "DROPDOWN_FIRST": "/html/body/ul[1]/li[1]/a/span[1]/a",
            "ART_ROW_TITLE":  "/html/body/div[2]/div[1]/div/div/div[1]/div[3]/div/main/section/div[2]/div[2]/div/div/div/div[3]/div/table/tbody/tr[{n}]/td[3]/a",
            "ART_ROW_DATE":   "/html/body/div[2]/div[1]/div/div/div[1]/div[3]/div/main/section/div[2]/div[2]/div/div/div/div[3]/div/table/tbody/tr[{n}]/td[1]/span[1]",
        }


        async def scrape_company(
            page,
            company_name: str,
            config: Config,
            is_first: bool,
        ) -> List[Article]:

            articles: List[Article] = []
            sl = StepLogger(company_name)
            safe = _safe_name(company_name)

            print(f"\n{'═'*70}")
            print(f"  SELSKAP: {company_name}")
            print(f"{'═'*70}")

            # ══════════════════════════════════════════════════════════════════════════
            # STEG 1  — Åpne siden / søk opp selskap
            # ══════════════════════════════════════════════════════════════════════════
            if is_first:
                sl.step("Åpner Euronext-siden (første gang)")
                try:
                    await page.goto(config.start_url, wait_until="networkidle", timeout=60_000)
                    await page.wait_for_timeout(2_000)
                    sl.ok(f"Side lastet: {config.start_url}")
                except Exception as e:
                    sl.fail(str(e))
                    return articles
                await page.wait_for_timeout(config.step_delay_ms)

                sl.step("Lukker cookie-banner")
                clicked = await click_xpath(page, XP["COOKIES"], "Reject All cookies", timeout=10_000)
                if not clicked:
                    clicked = await click_any(
                        page,
                        ["#onetrust-accept-btn-handler",
                        "button:has-text('Accept All')",
                        "button:has-text('Reject All')"],
                        "cookie fallback"
                    )
                if clicked:
                    await page.wait_for_timeout(1_000)
                    sl.ok("Cookie-banner lukket")
                else:
                    sl.warn("Ingen cookie-banner funnet (OK — fortsetter)")
                await page.wait_for_timeout(config.step_delay_ms)

            else:
                sl.step(f"Søker opp selskap i søkefeltet")
                found = await search_and_select_company(page, company_name, config, sl)
                if not found:
                    sl.fail(f"Kunne ikke finne '{company_name}' i Euronext-søk")
                    await safe_screenshot(page, config.screenshot_dir / f"search_fail_{safe}.png", "søk feilet")
                    try:
                        await page.goto(config.start_url, wait_until="networkidle", timeout=config.page_timeout)
                        await page.wait_for_timeout(1_500)
                    except Exception:
                        pass
                    return articles
                await page.wait_for_timeout(config.step_delay_ms)

            # ══════════════════════════════════════════════════════════════════════════
            # STEG 3  — Klikk SELSKAPSINFORMASJON-fanen
            # ══════════════════════════════════════════════════════════════════════════
            sl.step("Klikker SELSKAPSINFORMASJON-fanen")
            clicked = await click_xpath(page, XP["SELSKAPSINFO"], "Selskapsinformasjon-fane", timeout=10_000)
            if not clicked:
                clicked = await click_any(
                    page,
                    ["a[href*='company-information']",
                    "a.nav-link:has-text('SELSKAPSINFORMASJON')",
                    "a.nav-link:has-text('Company information')",
                    "a:has-text('SELSKAPSINFORMASJON')",
                    "a:has-text('Company information')"],
                    "Selskapsinformasjon fallback"
                )
            if not clicked:
                current = page.url
                if "/product/equities/" in current:
                    base = re.sub(r'(/product/equities/[^/]+-[A-Z]+).*', r'\1', current)
                    direct = base + "/company-information"
                    sl.warn(f"Navigerer direkte til: {direct}")
                    try:
                        await page.goto(direct, wait_until="networkidle", timeout=config.page_timeout)
                        await page.wait_for_timeout(1_500)
                        clicked = True
                    except Exception as e:
                        sl.fail(str(e))
                        return articles
            if not clicked:
                sl.fail("Kan ikke nå SELSKAPSINFORMASJON")
                return articles
            await page.wait_for_timeout(1_500)
            sl.ok("SELSKAPSINFORMASJON-fane nådd")
            await page.wait_for_timeout(config.step_delay_ms)

            # ══════════════════════════════════════════════════════════════════════════
            # STEG 4  — Klikk "Se alle" pressemeldings-listen
            # ══════════════════════════════════════════════════════════════════════════
            sl.step("Klikker 'Se alle' for pressemeldinger")
            clicked = False
            try:
                svg_loc = page.locator(f"xpath={XP['SE_ALLE']}")
                if await svg_loc.count() > 0:
                    await page.evaluate(
                        "xpath => { "
                        "  const el = document.evaluate(xpath, document, null, "
                        "    XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue; "
                        "  if (el) { "
                        "    const a = el.closest('a') || el.parentElement; "
                        "    if (a) a.click(); "
                        "  } "
                        "}",
                        XP["SE_ALLE"]
                    )
                    clicked = True
                    log.info("  ✓ Klikket Se alle (via JS parent)")
            except Exception:
                pass

            if not clicked:
                clicked = await click_any(
                    page,
                    ["a:has-text('Se alle')",
                    "a:has-text('See all')",
                    "a[href*='listview/company-press-release']",
                    "a[href*='company-press-release']"],
                    "Se alle fallback"
                )
            if clicked:
                try:
                    await page.wait_for_load_state("networkidle", timeout=12_000)
                except Exception:
                    pass
                await page.wait_for_timeout(1_500)
                sl.ok("Pressemeldings-liste lastet")
            else:
                sl.warn("'Se alle' ikke funnet — prøver å bruke eksisterende side")
            await page.wait_for_timeout(config.step_delay_ms)

            # ══════════════════════════════════════════════════════════════════════════
            # STEG 5  — Åpne filter
            # ══════════════════════════════════════════════════════════════════════════
            sl.step("Åpner filter-panel")
            clicked = await click_xpath(page, XP["FILTER_BTN"], "Filter-knapp", timeout=10_000)
            if not clicked:
                clicked = await click_any(
                    page,
                    ["button:has-text('Filters')",
                    "button:has-text('Filter')",
                    "button.filter-toggle"],
                    "Filter fallback"
                )
            if clicked:
                await page.wait_for_timeout(1_500)
                sl.ok("Filter-panel åpnet")
            else:
                sl.warn("Filter-knapp ikke funnet — fortsetter uten filter")
            await page.wait_for_timeout(config.step_delay_ms)

            # ══════════════════════════════════════════════════════════════════════════
            # STEG 6  — Åpne Topic-dropdown
            # ══════════════════════════════════════════════════════════════════════════
            sl.step("Åpner Topic-dropdown")
            clicked = await click_xpath(page, XP["TOPIC_BTN"], "Topic-dropdown", timeout=8_000)
            if not clicked:
                clicked = await click_any(
                    page,
                    ["button:has-text('Topic')",
                    "button:has-text('Emne')",
                    "details summary:has-text('Topic')"],
                    "Topic fallback"
                )
            if clicked:
                await page.wait_for_timeout(1_000)
                sl.ok("Topic-dropdown åpnet")
            else:
                sl.warn("Topic-dropdown ikke funnet")
            await page.wait_for_timeout(config.step_delay_ms)

            # ══════════════════════════════════════════════════════════════════════════
            # STEG 7  — Velg "Halvårsdata" OG "Årsrapporter og revisjonsberetninger"
            # ══════════════════════════════════════════════════════════════════════════

            # ── 7a: Halvårsdata ──
            sl.step("Velger 'Halvårsdata' i Topic-filteret")
            clicked_halv = await click_xpath(page, XP["HALVAAR"], "Halvårsdata-label", timeout=8_000)
            if not clicked_halv:
                clicked_halv = await click_any(
                    page,
                    ["label:has-text('Halvårsdata')",
                    "label:has-text('Half year')",
                    "label:has-text('Half Year')",
                    "input[value*='halvår' i]"],
                    "Halvårsdata fallback"
                )
            if clicked_halv:
                await page.wait_for_timeout(700)
                sl.ok("'Halvårsdata' valgt")
            else:
                sl.warn("'Halvårsdata' ikke funnet")
            await page.wait_for_timeout(config.step_delay_ms)

            # ── 7b: Årsrapporter og revisjonsberetninger ──
            sl.step("Velger 'Årsrapporter og revisjonsberetninger' i Topic-filteret")
            clicked_aar = await click_any(
                page,
                [XP["AARSRAPPORT"],
                "label:has-text('Årsrapporter og revisjonsberetninger')",
                "label:has-text('Annual reports')",
                "label:has-text('Annual financial report')",
                "label[for*='1070']",
                "#edit-field-company-press-releases-target-id-1070"],
                "Årsrapporter-label"
            )
            if clicked_aar:
                await page.wait_for_timeout(700)
                sl.ok("'Årsrapporter og revisjonsberetninger' valgt")
            else:
                sl.warn("'Årsrapporter og revisjonsberetninger' ikke funnet")
            await page.wait_for_timeout(config.step_delay_ms)

            # ══════════════════════════════════════════════════════════════════════════
            # STEG 8  — Trykk Apply
            # ══════════════════════════════════════════════════════════════════════════
            sl.step("Trykker Apply for å aktivere filter")
            clicked = await click_xpath(page, XP["APPLY"], "Apply-knapp", timeout=8_000, scroll=True)
            if not clicked:
                clicked = await click_any(
                    page,
                    ["input[type='submit'][value*='Apply' i]",
                    "input[type='submit'][value*='Bruk' i]",
                    "button:has-text('Apply')",
                    "button:has-text('Bruk')",
                    ".views-exposed-form input[type='submit']"],
                    "Apply fallback"
                )
            if clicked:
                try:
                    await page.wait_for_load_state("networkidle", timeout=10_000)
                except Exception:
                    pass
                await page.wait_for_timeout(2_000)
                sl.ok("Filter aktivert")
            else:
                sl.warn("Apply ikke funnet")
            await page.wait_for_timeout(config.step_delay_ms)

            await safe_screenshot(
                page,
                config.screenshot_dir / f"after_filter_{safe}.png",
                f"Etter filter: {company_name}"
            )

            # ── Lagre nåværende URL (artikkelliste) for tilbakenavigering ──
            article_list_url = page.url

            # ══════════════════════════════════════════════════════════════════════════
            # STEG 9  — Hent artikkelrader fra tabellen
            # ══════════════════════════════════════════════════════════════════════════
            sl.step("Henter artikkelliste fra tabellen")

            row_data: List[dict] = []

            modal_rows = await page.evaluate("""
            () => {
                const rows = [];
                const links = document.querySelectorAll('a.standardRightCompanyPressRelease[data-node-nid]');
                for (const a of links) {
                    const nid   = a.getAttribute('data-node-nid') || '';
                    const title = a.innerText.trim();
                    if (!nid || !title) continue;
                    let date = '';
                    const tr = a.closest('tr');
                    if (tr) {
                        const dateEl = tr.querySelector('td:first-child span, td:first-child');
                        if (dateEl) date = dateEl.innerText.trim();
                    }
                    rows.push({ nid, title, date, href: '' });
                }
                return rows;
            }
            """)

            if modal_rows:
                row_data = modal_rows
                sl.info(f"Fant {len(row_data)} modal-lenker (standardRightCompanyPressRelease)")
            else:
                for n in range(1, config.max_articles_per_company + 1):
                    title_xpath = XP["ART_ROW_TITLE"].format(n=n)
                    date_xpath  = XP["ART_ROW_DATE"].format(n=n)
                    try:
                        title_loc = page.locator(f"xpath={title_xpath}")
                        if await title_loc.count() == 0:
                            break
                        title = (await title_loc.first.inner_text()).strip()
                        href  = await title_loc.first.get_attribute("href") or ""
                        nid   = await title_loc.first.get_attribute("data-node-nid") or ""
                        date  = ""
                        try:
                            date_loc = page.locator(f"xpath={date_xpath}")
                            if await date_loc.count() > 0:
                                date = (await date_loc.first.inner_text()).strip()
                        except Exception:
                            pass
                        if title and (href or nid):
                            row_data.append({"title": title, "href": href, "nid": nid, "date": date})
                    except Exception as e:
                        log.debug(f"  Rad {n} XPath feilet: {e}")
                        break

            if not row_data:
                sl.warn("Modal-lenker og XPath feilet — prøver generell JS-fallback")
                js_rows = await page.evaluate("""
                () => {
                    const rows = [];
                    const trs = document.querySelectorAll('table tbody tr');
                    for (const tr of trs) {
                        const tds = tr.querySelectorAll('td');
                        if (tds.length < 2) continue;
                        let date = '';
                        const ds = tds[0] && tds[0].querySelector('span');
                        date = ds ? ds.innerText.trim() : (tds[0] ? tds[0].innerText.trim() : '');
                        let title = '', href = '', nid = '';
                        for (const td of tds) {
                            const a = td.querySelector('a');
                            if (a && a.innerText.trim().length > 5) {
                                title = a.innerText.trim();
                                href  = a.getAttribute('href') || '';
                                nid   = a.getAttribute('data-node-nid') || '';
                                break;
                            }
                        }
                        if (title && (href || nid)) rows.push({ date, title, href, nid });
                    }
                    return rows;
                }
                """)
                row_data = js_rows

            if row_data:
                sl.ok(f"Fant {len(row_data)} artikler")
                for i, r in enumerate(row_data[:3], 1):
                    sl.info(f"  [{i}] {r['title'][:65]}  ({r.get('date', '')})")
                if len(row_data) > 3:
                    sl.info(f"  ... og {len(row_data)-3} til")
            else:
                sl.fail("Ingen artikler funnet")
                await safe_screenshot(
                    page,
                    config.screenshot_dir / f"no_articles_{safe}.png",
                    f"Ingen artikler: {company_name}"
                )
                return articles
            await page.wait_for_timeout(config.step_delay_ms)

            row_data = row_data[:config.max_articles_per_company]

            # ══════════════════════════════════════════════════════════════════════════
            # STEG 10  — Hent tekst fra hver artikkel
            # ══════════════════════════════════════════════════════════════════════════
            sl.step(f"Henter tekst fra {len(row_data)} artikler")

            for i, row in enumerate(row_data, 1):
                nid  = row.get("nid", "")
                href = row.get("href", "")
                url  = href if href else ""
                if url.startswith("/"):
                    url = config.euronext_base + url

                art = Article(
                    company=company_name,
                    title=row["title"],
                    url=url or f"modal://{nid}",
                    date=row.get("date", ""),
                )
                sl.info(f"[{i}/{len(row_data)}] {art.title[:60]}...")

                if nid and (not href or href == ""):
                    # Modal-artikkel: klikk og hent tekst fra popup
                    art.text = await fetch_modal_text(page, nid, config)
                else:
                    # Vanlig lenke: naviger til siden, deretter tilbake
                    art.text = await fetch_article_text(page, art, config,
                                                        return_url=article_list_url)

                n_chars = len(art.text)
                if n_chars > 100:
                    sl.info(f"  → ✅ {n_chars} tegn hentet")
                else:
                    sl.warn(f"  → kun {n_chars} tegn")

                articles.append(art)
                await page.wait_for_timeout(int(config.request_delay * 1_000))

            sl.ok(f"{len(articles)} artikler hentet for {company_name}")
            await page.wait_for_timeout(config.step_delay_ms)

            # Naviger tilbake til forsiden for neste selskap
            try:
                await page.goto(config.start_url, wait_until="networkidle", timeout=config.page_timeout)
                await page.wait_for_timeout(1_500)
            except Exception:
                pass

            return articles


        # ─────────────────────────────────────────────────────────────────────────────
        # FINBERT
        # ─────────────────────────────────────────────────────────────────────────────

        class SentimentAnalyzer:
            def __init__(self, config: Config):
                self.config = config
                self.pipe   = None
                self._load()

            def _load(self):
                try:
                    from transformers import (BertTokenizer,
                                            BertForSequenceClassification,
                                            pipeline)
                    import torch
                    log.info(f"Laster FinBERT: {self.config.finbert_model}")
                    tok   = BertTokenizer.from_pretrained(self.config.finbert_model)
                    model = BertForSequenceClassification.from_pretrained(self.config.finbert_model)
                    dev   = "cuda" if torch.cuda.is_available() else "cpu"
                    self.pipe = pipeline("sentiment-analysis", model=model, tokenizer=tok, device=dev)
                    log.info(f"FinBERT klar på {dev}")
                except Exception as e:
                    log.error(f"FinBERT-lasting feilet: {e}")

            def analyze(self, text: str) -> dict:
                default = {"positive": 0.33, "neutral": 0.34, "negative": 0.33}
                if not self.pipe or not text or len(text) < 50:
                    raise RuntimeError("Article text/model unavailable; no sentiment score was produced")
                try:
                    import nltk
                    try:
                        from nltk.tokenize import sent_tokenize
                    except LookupError:
                        nltk.download("punkt",     quiet=True)
                        nltk.download("punkt_tab", quiet=True)
                        from nltk.tokenize import sent_tokenize

                    sents  = sent_tokenize(text)[:self.config.max_sentences]
                    scores = {"positive": 0.0, "negative": 0.0, "neutral": 0.0}
                    n = 0
                    for i in range(0, len(sents), 16):
                        batch = sents[i:i+16]
                        try:
                            for r in self.pipe(batch, truncation=True, max_length=512):
                                lbl = r["label"].lower()
                                if lbl in scores:
                                    scores[lbl] += r["score"]
                                    n += 1
                        except Exception:
                            for s in batch:
                                try:
                                    r = self.pipe(s, truncation=True, max_length=512)[0]
                                    lbl = r["label"].lower()
                                    if lbl in scores:
                                        scores[lbl] += r["score"]
                                        n += 1
                                except Exception as exc:
                                    raise RuntimeError("FinBERT sentence scoring failed") from exc
                    if not n:
                        raise RuntimeError("FinBERT returned no recognised scores")
                    return {k: v / n for k, v in scores.items()}
                except Exception as e:
                    raise RuntimeError("Sentiment scoring failed") from e


        # ─────────────────────────────────────────────────────────────────────────────
        # LAGRE RESULTATER
        # ─────────────────────────────────────────────────────────────────────────────

        def save_results(all_results: List[dict], config: Config, today: str, final: bool = False):
            if not all_results:
                return
            df     = pd.DataFrame(all_results)
            suffix = "_FINAL" if final else f"_{int(time.time())}"

            detail_path = config.nlp_dir / f"NLP_Sentiment_Detail_{today}{suffix}.xlsx"
            try:
                df.to_excel(detail_path, index=False)
                print(f"  💾 Detaljer lagret: {detail_path}")
            except PermissionError:
                alt = config.nlp_dir / f"NLP_Sentiment_Detail_{today}_{int(time.time())}.xlsx"
                df.to_excel(alt, index=False)
                print(f"  💾 Detaljer lagret (alt): {alt}")

            if not df.empty:
                summary = df.groupby("Company").agg(
                    Positive_Score=("Positive_Score", "mean"),
                    Neutral_Score =("Neutral_Score",  "mean"),
                    Negative_Score=("Negative_Score", "mean"),
                    Final_Score   =("Final_Score",    "mean"),
                    Article_Count =("Article_Title",  "count"),
                ).reset_index()
                summary_path = config.nlp_dir / f"Reshaped_Sentiment_Data_{today}{suffix}.xlsx"
                try:
                    summary.to_excel(summary_path, index=False)
                    print(f"  💾 Sammendrag lagret: {summary_path}")
                except Exception as e:
                    log.error(f"Sammendrag-lagring feilet: {e}")
            return df


        # ─────────────────────────────────────────────────────────────────────────────
        # CHECKPOINT
        # ─────────────────────────────────────────────────────────────────────────────

        def append_checkpoint(result: dict, config: Config, today: str):
            cp = config.work_dir / f"checkpoint_{today}.csv"
            pd.DataFrame([result]).to_csv(cp, mode="a", header=not cp.exists(), index=False)


        def load_checkpoint(config: Config, today: str) -> set:
            cp = config.work_dir / f"checkpoint_{today}.csv"
            if not cp.exists():
                return set()
            try:
                return set(pd.read_csv(cp)["Company"].unique())
            except Exception:
                return set()


        def clear_checkpoint(config: Config, today: str):
            cp = config.work_dir / f"checkpoint_{today}.csv"
            if cp.exists():
                cp.unlink()
                print(f"   🗑️  Checkpoint slettet: {cp}")


        # ─────────────────────────────────────────────────────────────────────────────
        # MAIN
        # ─────────────────────────────────────────────────────────────────────────────

        async def main():
            print("=" * 80)
            print("  EURONEXT OSLO BØRS — PLAYWRIGHT SCRAPER + FINBERT NLP  (v3 — FAST)")
            print("=" * 80)

            config = Config()
            today  = datetime.now().strftime("%Y-%m-%d")

            # STEG A: Last selskaper
            print(f"\n📋 STEG A: Laster selskaper fra Excel...")
            companies = load_companies(config)
            if not companies:
                print("   ❌ Ingen selskaper funnet.")
                return
            print(f"   ✅ STEG A FERDIG: {len(companies)} selskaper lastet")
            for i, c in enumerate(companies[:5], 1):
                print(f"      [{i}] {c}")
            if len(companies) > 5:
                print(f"      ... og {len(companies)-5} til")

            # STEG B: Last FinBERT
            print(f"\n🧠 STEG B: Laster FinBERT-modell...")
            analyzer = SentimentAnalyzer(config)
            if analyzer.pipe:
                print(f"   ✅ STEG B FERDIG: FinBERT klar")
            else:
                print(f"   ❌ STEG B FEILET: FinBERT ikke tilgjengelig — fortsetter med default-scorer")

            # STEG C: Checkpoint
            print(f"\n📂 STEG C: Sjekker checkpoint...")
            if config.force_rerun:
                print(f"   ⚡ force_rerun=True → sletter gammel checkpoint for i dag")
                clear_checkpoint(config, today)
                done      = set()
                remaining = companies[:]
                all_results: List[dict] = []
            else:
                done      = load_checkpoint(config, today)
                remaining = [c for c in companies if c not in done]
                all_results: List[dict] = []
                cp_path = config.work_dir / f"checkpoint_{today}.csv"
                if cp_path.exists():
                    try:
                        all_results = pd.read_csv(cp_path).to_dict("records")
                        print(f"   Lastet {len(all_results)} rader fra checkpoint")
                    except Exception:
                        pass

            if done:
                print(f"   ⏭  Hopper over {len(done)} allerede behandlede")
            print(f"   ✅ STEG C FERDIG: {len(remaining)} selskaper gjenstår")

            if len(remaining) == 0:
                print(f"\n   ⚠️  Ingen selskaper å behandle!")
                print(f"   Tips: Sett config.force_rerun = True for å kjøre på nytt,")
                print(f"         eller slett checkpoint-filen manuelt:")
                print(f"         {config.work_dir / f'checkpoint_{today}.csv'}")
                return

            # STEG D: Start Playwright
            print(f"\n🌐 STEG D: Starter nettleserskraping...")
            print(f"   Synlig nettleser: {not config.headless}")
            print(f"   Slow-mo: {config.slow_mo} ms")
            print(f"   Stegforsinkelse: {config.step_delay_ms} ms")
            print(f"   Modal-klikk timeout: {config.modal_click_timeout} ms")
            print(f"   Søkevarianter: {config.search_retry_variants}")
            print(f"   Selskaper å scrape: {len(remaining)}")

            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=config.headless,
                    slow_mo=config.slow_mo,
                )
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    ),
                )
                page = await context.new_page()
                print(f"   ✅ STEG D FERDIG: Nettleser startet")

                total = len(remaining)
                for idx, company in enumerate(remaining):
                    is_first  = (idx == 0)
                    comp_num  = idx + 1

                    print(f"\n{'▓'*70}")
                    print(f"  SELSKAP {comp_num}/{total}: {company}")
                    print(f"{'▓'*70}")

                    try:
                        articles = await scrape_company(page, company, config, is_first)
                    except Exception as e:
                        log.error(f"Kritisk feil for {company}: {e}")
                        articles = []
                        try:
                            await page.goto(config.start_url, wait_until="networkidle",
                                        timeout=config.page_timeout)
                            await page.wait_for_timeout(1_500)
                        except Exception:
                            pass

                    if not articles:
                        print(f"  ⚠️ Ingen artikler funnet for {company}")
                        rec = {
                            "Company": company, "Article_Title": "INGEN ARTIKLER",
                            "Article_Date": "", "Article_URL": "", "PDF_URL": "",
                            "Positive_Score": 0.0, "Neutral_Score": 1.0,
                            "Negative_Score": 0.0, "Final_Score": 0.0,
                            "Text_Length": 0, "PDF_Used": False, "Scrape_Date": today,
                        }
                        all_results.append(rec)
                        append_checkpoint(rec, config, today)
                        continue

                    print(f"\n  🧠 FinBERT-analyse på {len(articles)} artikler for {company}...")
                    for ai, art in enumerate(articles, 1):
                        sent  = analyzer.analyze(art.text)
                        final = sent["positive"] - sent["negative"]
                        rec   = {
                            "Company":        company,
                            "Article_Title":  art.title,
                            "Article_Date":   art.date,
                            "Article_URL":    art.url,
                            "PDF_URL":        art.pdf_url,
                            "Positive_Score": round(sent["positive"], 4),
                            "Neutral_Score":  round(sent["neutral"],  4),
                            "Negative_Score": round(sent["negative"], 4),
                            "Final_Score":    round(final, 4),
                            "Text_Length":    len(art.text),
                            "PDF_Used":       bool(art.pdf_url),
                            "Scrape_Date":    today,
                        }
                        all_results.append(rec)
                        append_checkpoint(rec, config, today)
                        print(
                            f"    [{ai}/{len(articles)}] {art.title[:50]}... "
                            f"→ +{sent['positive']:.3f} ={sent['neutral']:.3f} -{sent['negative']:.3f} "
                            f"⟹ {final:+.4f}"
                        )

                        safe_c = _safe_name(company, 40)
                        safe_t = _safe_name(art.title, 30)
                        txt_p  = config.work_dir / f"{safe_c}_{safe_t}_{today}.txt"
                        try:
                            txt_p.write_text(art.text[:50_000], encoding="utf-8")
                        except Exception:
                            pass

                    print(f"  ✅ FinBERT ferdig for {company}")

                    if comp_num % 5 == 0:
                        print(f"\n  💾 Mellomlagrer etter {comp_num} selskaper...")
                        save_results(all_results, config, today, final=False)

                await browser.close()
                print("\n  ✅ Nettleser lukket")

            # STEG E: Lagre endelig
            print(f"\n{'='*80}")
            print("✅ STEG E: SCRAPING FERDIG — LAGRER ENDELIGE RESULTATER")
            print(f"{'='*80}")
            save_results(all_results, config, today, final=True)

            comps_with_data = len({r["Company"] for r in all_results if r["Text_Length"] > 0})
            arts_total      = sum(1 for r in all_results if r["Text_Length"] > 0)
            pdfs_used       = sum(1 for r in all_results if r.get("PDF_Used"))

            print(f"\n  Selskaper i Excel:       {len(companies)}")
            print(f"  Selskaper behandlet:     {total}")
            print(f"  Selskaper med data:      {comps_with_data}")
            print(f"  Artikler analysert:      {arts_total}")
            print(f"  Artikler via PDF:        {pdfs_used}")
            print(f"  Resultater:              {config.nlp_dir}")
            print(f"  Working data:            {config.work_dir}")
            print(f"  Screenshots:             {config.screenshot_dir}")


        if __name__ == "__main__":
            asyncio.run(main())
    # Kalles fra dispatchen nederst når HENT_NYE_ARTIKLER er på.

    ### Public sentriment
    # Good 5 stocks - monthly rebalancing. #CAGR 40.8% #Win rate 67% (management)
    def NlpSentimentTrader4_v4():
        import os
        os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

        import sys
        import re
        import time
        import logging
        import warnings
        from dataclasses import dataclass
        from datetime import datetime, timedelta
        from pathlib import Path
        from typing import Dict, List, Set, Tuple

        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        import matplotlib.ticker as mticker
        import numpy as np
        import pandas as pd
        import yfinance as yf

        warnings.filterwarnings("ignore")

        # ─────────────────────────────────────────────────────────────────────────────
        # CONFIG
        # ─────────────────────────────────────────────────────────────────────────────

        @dataclass
        class Config:
            # ── Paths ──
            base_dir: Path = Path(r"C:\Users\ander\Desktop\Python_K4\ExcelData")
            nlp_output_dir: str = "DataNLP"
            #tickers_file: str = r"Data_BT\AllTickers_OSEBX_.xlsx"
            tickers_file: str = r"Data_BT\AllTickers_OSEBX_TW_current.xlsx"
            output_dir: str = "StrategyResults_v4_Sentiment"

            # ── Portfolio ──
            startkapital: float = 1_000_000
            n_portfolio: int = 5                    # Top N stocks to hold
            transaction_cost: float = 0.0000         # 0.1% per trade

            # ── Sentiment scoring ──
            decay_factor: float = 0.98              # Per day
            max_signal_age_days: int = 365          # Ignore articles older than this
            short_window_days: int = 45 
            min_score_threshold: float = 0.05       # Minimum sentiment to be eligible

            # ── Trend filter ──
            sma_days: int = 15                      # Only buy if price > SMA(50)

            # ── Language filter ──
            filter_norwegian: bool = True           # Remove Norwegian articles

            # ── Benchmark ──
            benchmark_ticker: str = "OSEBX.OL"
            oslo_suffix: str = ".OL"

            # ── Time period ──
            start_date: str = "2020-01-01"
            end_date: str = ""

            @property
            def nlp_dir(self) -> Path:
                return self.base_dir / self.nlp_output_dir

            @property
            def tickers_path(self) -> Path:
                return self.base_dir / self.tickers_file

            @property
            def results_dir(self) -> Path:
                p = self.base_dir / self.output_dir
                p.mkdir(parents=True, exist_ok=True)
                return p

        # ─────────────────────────────────────────────────────────────────────────────
        # LOGGING
        # ─────────────────────────────────────────────────────────────────────────────

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s  %(levelname)-8s  %(message)s",
            datefmt="%H:%M:%S",
        )
        log = logging.getLogger("SentimentV4")
        TODAY_STR = datetime.now().strftime("%Y-%m-%d")

        # ─────────────────────────────────────────────────────────────────────────────
        # HELPERS
        # ─────────────────────────────────────────────────────────────────────────────

        NORSK_ORD = {
            'og', 'har', 'til', 'fra', 'ved', 'er', 'på', 'det', 'den',
            'rapport', 'resultat', 'kvartal', 'vekst', 'drevet',
            'selskap', 'aksje', 'utbytte', 'halvår', 'årsrapport',
            'solide', 'sterke', 'høy', 'godt', 'gode', 'alle',
            'kundeaktivitet', 'utlånsvekst', 'videre', 'norsk',
            'resultater', 'publisert', 'kvartalet', 'første',
        }

        def is_norwegian(title: str) -> bool:
            if pd.isna(title):
                return False
            words = str(title).lower().split()
            matches = NORSK_ORD.intersection(words)
            return len(matches) >= 2

        def price_at(prices, ticker, dt):
            if ticker not in prices.columns:
                return None
            p = prices[ticker].dropna()
            p = p[p.index <= dt]
            return float(p.iloc[-1]) if not p.empty else None

        def check_sma(daily_prices, ticker, as_of_date, sma_days):
            if ticker not in daily_prices.columns:
                return False
            p = daily_prices[ticker].dropna()
            p = p[p.index <= as_of_date]
            if len(p) < sma_days:
                return False
            return float(p.iloc[-1]) > float(p.iloc[-sma_days:].mean())

        # ─────────────────────────────────────────────────────────────────────────────
        # DATA LOADING
        # ─────────────────────────────────────────────────────────────────────────────

        def load_sentiment_articles(config: Config) -> pd.DataFrame:
            """
            ALLE artikkelfilene i DataNLP, slått sammen og avduplisert.

            Før leste denne bare files[0] — den nyeste filen. Hver skraping
            skriver en ny fil, så alt som var hentet tidligere ble kastet ved
            neste kjøring. Det er den dyreste dataen i hele prosjektet: timer
            med skraping og språkmodell, hentet én gang og så oversett. Med ti
            artikler per selskap per fil rakk historikken noen måneder, og
            backtesten ble kort av en grunn som ikke sto noe sted.

            Nøkkelen for duplikater er selskap + dato + tittel. Samme artikkel
            i to filer er én artikkel; er den scoret på nytt i en senere
            kjøring, vinner den nyeste filen.
            """
            nlp_dir = config.nlp_dir
            filer = sorted(p for p in nlp_dir.glob("NLP_Sentiment_Detail_*.xlsx")
                           if not p.name.startswith("~$"))
            if not filer:
                raise FileNotFoundError(f"No sentiment files in {nlp_dir}")

            deler = []
            for f in filer:
                try:
                    d = pd.read_excel(f)
                except Exception as e:
                    log.warning("  Hoppet over %s: %s", f.name, e)
                    continue
                if d.empty or "Article_Date" not in d.columns:
                    log.warning("  Hoppet over %s: ingen Article_Date-kolonne", f.name)
                    continue
                d["_fil"] = f.name
                deler.append(d)
                log.info("  %-52s %5d rader", f.name, len(d))
            if not deler:
                raise FileNotFoundError(
                    f"Fant {len(filer)} fil(er) i {nlp_dir}, men ingen av dem "
                    f"kunne leses som artikler.")

            df = pd.concat(deler, ignore_index=True)
            if len(filer) > 1:
                log.info("  %d filer slått sammen → %d rader før avduplisering",
                         len(deler), len(df))

            # Fix dates: "11 Mar 2026\n14:00 CET" → "11 Mar 2026"
            df["Article_Date"] = (
                df["Article_Date"].astype(str)
                .str.replace(r'\n.*$', '', regex=True)
                .str.strip()
            )
            df["Article_Date"] = pd.to_datetime(df["Article_Date"], format="%d %b %Y", errors="coerce")

            df = df[df["Text_Length"] > 0].copy()
            df = df.dropna(subset=["Article_Date"])

            # Avdupliser på selskap + dato + tittel. Den nyeste filen vinner,
            # så en artikkel som er scoret om igjen får sin ferskeste score.
            nokler = [k for k in ("Company", "Article_Date", "Article_Title")
                      if k in df.columns]
            if nokler and len(filer) > 1:
                for_ = len(df)
                df = (df.sort_values("_fil")
                        .drop_duplicates(subset=nokler, keep="last")
                        .reset_index(drop=True))
                if for_ != len(df):
                    log.info("  Avduplisert: %d → %d rader (%d gjengangere)",
                             for_, len(df), for_ - len(df))
            df = df.drop(columns=[c for c in ("_fil",) if c in df.columns])

            log.info("Loaded %d artikler fra %d fil(er), %d selskaper",
                     len(df), len(deler), df["Company"].nunique())

            # Filter Norwegian articles
            if config.filter_norwegian:
                before = len(df)
                df["_is_norsk"] = df["Article_Title"].apply(is_norwegian)
                df = df[~df["_is_norsk"]].drop(columns=["_is_norsk"])
                log.info("Language filter: %d → %d (removed %d Norwegian)",
                        before, len(df), before - len(df))

            log.info("Date range: %s → %s", df["Article_Date"].min().date(),
                    df["Article_Date"].max().date())
            return df

        def build_ticker_map(config: Config, articles_df: pd.DataFrame) -> Dict[str, str]:
            mapping = {}
            for company in articles_df["Company"].unique():
                code = str(company).strip()
                if code and code != "nan":
                    mapping[code] = code + config.oslo_suffix
            log.info("Ticker map: %d companies → yfinance", len(mapping))
            return mapping

        def download_prices(tickers: List[str], benchmark: str,
                            start: str, end: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
            yf_tickers = list(set(tickers + [benchmark]))
            log.info("Downloading prices for %d tickers...", len(yf_tickers))

            data = yf.download(yf_tickers, start=start, end=end or None,
                            auto_adjust=True, progress=True)

            if data.empty:
                return pd.DataFrame(), pd.DataFrame()

            if isinstance(data.columns, pd.MultiIndex):
                daily = data["Close"].copy()
            else:
                daily = data[["Close"]].copy()
                daily.columns = yf_tickers[:1]

            daily.index = pd.to_datetime(daily.index)
            daily.sort_index(inplace=True)

            bench = daily[[benchmark]].copy() if benchmark in daily.columns else pd.DataFrame()
            stocks = daily.drop(columns=[benchmark], errors="ignore")

            # Drop stocks with < 60 data points
            valid = stocks.columns[stocks.count() >= 60]
            stocks = stocks[valid]

            monthly = daily.resample("ME").last()
            monthly.sort_index(inplace=True)

            log.info("Daily: %d days | Monthly: %d months | Stocks: %d",
                    len(daily), len(monthly), len(stocks.columns))
            return daily, monthly

        # ─────────────────────────────────────────────────────────────────────────────
        # SENTIMENT SCORER
        # ─────────────────────────────────────────────────────────────────────────────

        def score_sentiment_at(articles_df: pd.DataFrame, ticker_map: Dict[str, str],
                            rebal_date: pd.Timestamp, config: Config,
                            available_tickers: Set[str]) -> pd.DataFrame:
            """
            Score sentiment as the DELTA between recent sentiment and trailing baseline.
            
            - Short window (last `short_window_days`): the 'current' sentiment reading.
            - Long window (last `max_signal_age_days`):  the trailing baseline.
            - Signal = short_avg - long_avg.
            
            A company with consistently positive press has high level but ~0 delta
            (already priced in). A company whose news has IMPROVED relative to its
            own baseline has a positive delta — that's the tradable surprise.
            """
            # ── Windows ──
            short_window_days = getattr(config, "short_window_days", 45)
            long_cutoff  = rebal_date - timedelta(days=config.max_signal_age_days)
            short_cutoff = rebal_date - timedelta(days=short_window_days)

            # Long window = full baseline period (used for both baseline and short)
            long_window = articles_df[
                (articles_df["Article_Date"] < rebal_date) &
                (articles_df["Article_Date"] >= long_cutoff)
            ]
            if long_window.empty:
                return pd.DataFrame()

            signals = []
            for company in long_window["Company"].unique():
                ticker = ticker_map.get(company)
                if not ticker or ticker not in available_tickers:
                    continue

                arts = long_window[long_window["Company"] == company]

                # ── Build long-window (baseline) decayed score ──
                long_scores  = []
                # ── Build short-window (recent) decayed score ──
                short_scores = []
                latest_date  = None
                n_short_raw  = 0   # raw count in short window, for filtering

                for _, art in arts.iterrows():
                    art_date = art["Article_Date"]
                    days_old = (rebal_date - art_date).days
                    if days_old < 0:
                        continue
                    score   = float(art["Final_Score"])
                    decayed = score * (config.decay_factor ** days_old)

                    # Skip articles whose decayed contribution is essentially zero
                    if abs(decayed) < 0.001:
                        continue

                    long_scores.append(decayed)
                    if latest_date is None or art_date > latest_date:
                        latest_date = art_date

                    # Short window: same decay, but only recent articles
                    if art_date >= short_cutoff:
                        short_scores.append(decayed)
                        n_short_raw += 1

                # ── Need data in both windows to compute a meaningful delta ──
                if not long_scores or not short_scores:
                    continue

                long_avg  = float(np.mean(long_scores))
                short_avg = float(np.mean(short_scores))
                delta     = short_avg - long_avg

                # ── Require at least one fresh article, else the "short" reading
                #    is just decayed echoes of old news ──
                if n_short_raw < 1:
                    continue

                # ── Threshold on the DELTA, not the level ──
                if delta >= config.min_score_threshold:
                    signals.append({
                        "Company":         company,
                        "Ticker":          ticker,
                        "Sentiment_Score": round(delta, 4),       # delta is the new score
                        "Short_Avg":       round(short_avg, 4),   # diagnostic
                        "Long_Avg":        round(long_avg, 4),    # diagnostic
                        "N_Articles":      len(long_scores),
                        "N_Recent":        n_short_raw,
                        "Latest_Date":     latest_date,
                    })

            if not signals:
                return pd.DataFrame()

            df = pd.DataFrame(signals)
            df.sort_values("Sentiment_Score", ascending=False, inplace=True)
            df.reset_index(drop=True, inplace=True)
            return df

        # ─────────────────────────────────────────────────────────────────────────────
        # STOCK SELECTION (SMA filter, no industry cap)
        # ─────────────────────────────────────────────────────────────────────────────

        def _logg_score(rebal_date, kandidater, valgte, grunn: str) -> None:
            """
            Hele det scorede tverrsnittet for én dato — også når vi ikke kjøpte.

            Loggen lå før INNE i «vi kjøpte noe»-grenen, etter at SMA-filteret
            hadde tatt sitt. En måned der ingen passerte filteret ga null rader,
            og en kjøring der det aldri skjedde ga et tomt Score_Log-ark. For
            master.py ser det da nøyaktig ut som en modell som aldri har hatt en
            mening om noe selskap — og «kjør modellen på nytt» hjelper ikke, for
            den gjør det samme igjen.

            Et selskap som ble vurdert og forkastet skal se annerledes ut enn et
            selskap som aldri ble vurdert. Derfor står filterutfallet som en
            KOLONNE (over_sma / valgt), ikke som en manglende rad. En persentil
            regnet bare mot vinnerne sier at alle er middels.
            """
            try:
                if kandidater is None or kandidater.empty:
                    return
                dato = pd.Timestamp(rebal_date).strftime("%Y-%m-%d")
                for _rang, (_, _r) in enumerate(
                        kandidater.head(SCORE_LOG_TOPP).iterrows(), start=1):
                    tkr = str(_r["Ticker"])
                    score_log.append({
                        "date": dato,
                        "ticker": tkr,
                        "score": float(_r["Sentiment_Score"]),
                        "rank": _rang,
                        "over_sma": "JA" if bool(_r.get("Above_SMA", True)) else "NEI",
                        "valgt": "JA" if tkr in valgte else "NEI",
                        "grunn": grunn,
                    })
            except Exception as _e:
                if not getattr(select_portfolio, "_score_log_advart", False):
                    select_portfolio._score_log_advart = True
                    log.warning("Score-loggen feiler (%s) — arket Score_Log blir "
                                "tomt, og master.py mister NLP som kilde.", _e)

        def select_portfolio(sentiment_df: pd.DataFrame, daily_prices: pd.DataFrame,
                            rebal_date: pd.Timestamp,
                            config: Config) -> Tuple[List[str], pd.DataFrame]:
            if sentiment_df.empty:
                # Ingenting å logge: modellen hadde ingen scoret kandidat i det
                # hele tatt denne datoen. Det er en annen tilstand enn «alle ble
                # forkastet», og loggen skal vise forskjellen.
                return [], pd.DataFrame()

            sentiment_df = sentiment_df.copy()
            sentiment_df["Above_SMA"] = sentiment_df["Ticker"].apply(
                lambda t: check_sma(daily_prices, t, rebal_date, config.sma_days)
            )
            filtered = sentiment_df[sentiment_df["Above_SMA"]].copy()

            if filtered.empty:
                _logg_score(rebal_date, sentiment_df, set(), "ingen over SMA")
                return [], pd.DataFrame()

            # Take top N — no industry cap
            selected = filtered.head(config.n_portfolio)["Ticker"].tolist()
            sel_df = filtered[filtered["Ticker"].isin(selected)].copy()

            _logg_score(rebal_date, sentiment_df, set(selected), "handlet")
            return selected, sel_df

        # ─────────────────────────────────────────────────────────────────────────────
        # MAIN
        # ─────────────────────────────────────────────────────────────────────────────

        config = Config()

        log.info("=" * 70)
        log.info("  SENTIMENT STRATEGY v4 — PB/ROE STYLE")
        log.info("  Top %d | SMA%d | Decay %.0f%%/day | English-only",
                config.n_portfolio, config.sma_days,
                (1 - config.decay_factor) * 100)
        log.info("=" * 70)

        # ── Step 1: Load sentiment data ──
        log.info("\n📊 STEP 1: Loading sentiment data...")
        articles = load_sentiment_articles(config)
        if articles.empty:
            log.error("No articles loaded!")
            return

        # ── Step 2: Build mappings ──
        log.info("\n🏷️  STEP 2: Building mappings...")
        ticker_map = build_ticker_map(config, articles)

        # ── Step 3: Download prices ──
        log.info("\n📈 STEP 3: Downloading prices...")
        all_tickers = list(set(ticker_map.values()))
        end_date = config.end_date or datetime.now().strftime("%Y-%m-%d")
        daily, monthly = download_prices(
            all_tickers, config.benchmark_ticker, config.start_date, end_date
        )

        if daily.empty or monthly.empty:
            log.error("No price data!")
            return

        # Benchmark series
        bn = pd.Series(dtype=float)
        if config.benchmark_ticker in monthly.columns:
            b = monthly[config.benchmark_ticker].dropna()
            if not b.empty:
                bn = (b / b.iloc[0]) * config.startkapital

        # ── Step 4: Build rebalance dates ──
        # Så langt tilbake som dataene rekker. Artiklene er nesten alltid det
        # som binder — kursene går år tilbake — så backtesten er ikke kortere
        # enn strategien fortjener, den er så lang som NLP-materialet tillater.
        # Derfor står begge spennene i loggen: da ser du med én gang hvem av
        # dem som bestemmer, i stedet for å gjette på en periode du ikke valgte.
        earliest_article = articles["Article_Date"].min()
        latest_article = articles["Article_Date"].max()
        bt_start = max(earliest_article, monthly.index[0])

        # Månedsserien fra resample() ender på månedens SISTE dag, også når
        # måneden ikke er over. 8. september ga en rebalanseringsdato
        # 30. september — tre uker fram i tid, med gårsdagens kurs. En backtest
        # som handler i framtiden måler ikke noe, så vi klipper til i dag.
        i_dag = pd.Timestamp(datetime.now().date())
        bt_end = monthly.index[-1]
        if bt_end > i_dag:
            log.info("  Siste månedsslutt (%s) er ikke inntruffet — klipper til %s",
                     bt_end.date(), i_dag.date())
            bt_end = i_dag

        rdates = []
        dt = bt_start.replace(day=1)
        while dt <= bt_end:
            idx = monthly.index[
                (monthly.index.year == dt.year) & (monthly.index.month == dt.month)
            ]
            if len(idx) > 0 and idx[0] <= bt_end:
                rdates.append(idx[0])
            dt += pd.offsets.MonthBegin(1)

        log.info("\n🔄 STEP 4: Running backtest...")
        log.info("  Artikler         : %s → %s  (%d stk)",
                 pd.Timestamp(earliest_article).date(),
                 pd.Timestamp(latest_article).date(), len(articles))
        log.info("  Kurser           : %s → %s",
                 monthly.index[0].date(), monthly.index[-1].date())
        if not rdates:
            log.error("  Ingen rebalanseringsdatoer i %s → %s — backtesten "
                      "stoppet. Artiklene og kursene overlapper ikke.",
                      bt_start.date(), bt_end.date())
            return
        binder = ("artiklene" if pd.Timestamp(earliest_article) >= monthly.index[0]
                  else "kursene")
        log.info("  Backtesten starter %s fordi %s ikke rekker lenger tilbake",
                 rdates[0].date(), binder)
        log.info("  Rebalance dates: %d", len(rdates))
        log.info("  Period: %s → %s", rdates[0].date(), rdates[-1].date())

        available_tickers = set(daily.columns)

        # ── Backtest loop ──
        cash = config.startkapital
        holdings: Dict[str, float] = {}   # ticker → shares
        equity_curve = []
        trade_log = []
        monthly_log = []
        score_log = []          # (dato, ticker, score) — grunnlag for master.py
        last_sentiment = pd.DataFrame()   # keep for snapshot at end

        for rebal_dt in rdates:
            # Portfolio value BEFORE trades
            pv_before = cash + sum(
                holdings.get(t, 0) * (price_at(monthly, t, rebal_dt) or 0)
                for t in holdings
            )

            # Score sentiment at this date
            sentiment = score_sentiment_at(
                articles, ticker_map, rebal_dt, config, available_tickers
            )
            if not sentiment.empty:
                last_sentiment = sentiment.copy()

            # Select target portfolio
            target_tickers, sel_df = select_portfolio(
                sentiment, daily, rebal_dt, config
            )

            if not target_tickers:
                equity_curve.append({"date": rebal_dt, "value": pv_before})
                monthly_log.append({
                    "date": rebal_dt.strftime("%Y-%m"),
                    "portfolio_value": round(pv_before, 0),
                    "cash": round(cash, 0),
                    "n_holdings": len(holdings),
                    "holdings": ", ".join(sorted(holdings.keys())) if holdings else "CASH — no signal",
                    "buys": "", "sells": "",
                })
                log.info("%s  $%.0f  CASH (no signal)", rebal_dt.strftime("%Y-%m"), pv_before)
                continue

            target_set = set(target_tickers)
            current_set = set(holdings.keys())
            sells_set = current_set - target_set
            buys_set = target_set - current_set
            holds_set = current_set & target_set

            # ── Sell everything NOT in new target ──
            for tkr in sells_set:
                p = price_at(monthly, tkr, rebal_dt)
                if p and holdings.get(tkr, 0) > 0:
                    proceeds = holdings[tkr] * p
                    txn = proceeds * config.transaction_cost
                    cash += proceeds - txn
                    trade_log.append({
                        "date": rebal_dt.strftime("%Y-%m-%d"),
                        "ticker": tkr, "action": "SELL",
                        "shares": round(holdings[tkr], 4),
                        "price": round(p, 2),
                        "value": round(proceeds, 0),
                    })
                    del holdings[tkr]

            # ── Equal-weight target value ──
            # Recalculate portfolio value AFTER sells (cash updated)
            pv_after_sells = cash + sum(
                holdings.get(t, 0) * (price_at(monthly, t, rebal_dt) or 0)
                for t in holdings
            )
            tv = pv_after_sells / len(target_tickers)

            # ── Rebalanser i to omganger: ned først, så opp ──
            #
            # Én omgang, i scorerekkefølge, betalte for de første navnene med
            # kontanter som ennå lå bundet i de siste. Da traff «kjøp det du
            # har råd til»-grenen, og siste navn fikk en tilfeldig liten vekt:
            # 8. september sto fire posisjoner på 20 % og CODE.OL på 5,0 %,
            # med 15 % i kontanter i en strategi som skal være fullt investert.
            # Vekten var et resultat av alfabetet, ikke av scoren.
            #
            # Salg frigjør kontanter, kjøp bruker dem. Gjør vi alle salgene
            # først, er pengene der når kjøpene kommer — og likevekt blir
            # likevekt.
            handelsplan = []
            for tkr in target_tickers:
                p = price_at(monthly, tkr, rebal_dt)
                if not p or p <= 0:
                    continue
                cs = holdings.get(tkr, 0)
                diff = (tv / p) - cs
                if abs(diff * p) < 1:
                    continue
                handelsplan.append((tkr, p, cs, diff))

            for tkr, p, cs, diff in sorted(handelsplan, key=lambda x: x[3]):
                if diff > 0:
                    cost = diff * p
                    txn = cost * config.transaction_cost
                    total_cost = cost + txn
                    # Don't buy more than we have cash for
                    if total_cost > cash:
                        # Buy what we can afford
                        affordable_shares = (cash / (1 + config.transaction_cost)) / p
                        if affordable_shares < 1:
                            continue
                        diff = affordable_shares
                        cost = diff * p
                        txn = cost * config.transaction_cost
                        total_cost = cost + txn
                    cash -= total_cost
                    holdings[tkr] = cs + diff
                    action = "BUY" if tkr in buys_set else "REBAL_BUY"
                    trade_log.append({
                        "date": rebal_dt.strftime("%Y-%m-%d"),
                        "ticker": tkr, "action": action,
                        "shares": round(diff, 4),
                        "price": round(p, 2),
                        "value": round(cost, 0),
                    })
                else:
                    ss = abs(diff)
                    proceeds = ss * p
                    txn = proceeds * config.transaction_cost
                    cash += proceeds - txn
                    holdings[tkr] = max(cs - ss, 0)
                    trade_log.append({
                        "date": rebal_dt.strftime("%Y-%m-%d"),
                        "ticker": tkr, "action": "REBAL_SELL",
                        "shares": round(ss, 4),
                        "price": round(p, 2),
                        "value": round(proceeds, 0),
                    })

            # ── Record ──
            port_after = cash + sum(
                holdings.get(t, 0) * (price_at(monthly, t, rebal_dt) or 0)
                for t in holdings
            )
            equity_curve.append({"date": rebal_dt, "value": port_after})

            monthly_log.append({
                "date": rebal_dt.strftime("%Y-%m"),
                "portfolio_value": round(port_after, 0),
                "cash": round(cash, 0),
                "n_holdings": len(holdings),
                "holdings": ", ".join(sorted(holdings.keys())),
                "buys": ", ".join(sorted(buys_set)),
                "sells": ", ".join(sorted(sells_set)),
            })

            pct_change = ""
            if len(equity_curve) >= 2:
                prev_val = equity_curve[-2]["value"]
                if prev_val > 0:
                    ret = (port_after / prev_val - 1) * 100
                    pct_change = " (%+.1f%%)" % ret

            log.info("")
            log.info("--- %s  $%.0f%s ---", rebal_dt.strftime("%Y-%m"), port_after, pct_change)
            if buys_set:
                log.info("  BUY:  %s", ", ".join(sorted(buys_set)))
            if sells_set:
                log.info("  SELL: %s", ", ".join(sorted(sells_set)))
            if holds_set:
                log.info("  HOLD: %s", ", ".join(sorted(holds_set)))

            for tkr in sorted(holdings.keys()):
                p = price_at(monthly, tkr, rebal_dt)
                if p:
                    val = holdings[tkr] * p
                    score_str = "?"
                    if not sel_df.empty and tkr in sel_df["Ticker"].values:
                        row = sel_df[sel_df["Ticker"] == tkr].iloc[0]
                        score_str = "%.3f" % row["Sentiment_Score"]
                    log.info("    %-10s ($%.0f  Score:%s)", tkr, val, score_str)

            log.info("  Cash: $%.0f  |  %d stocks", cash, len(holdings))

        # ─────────────────────────────────────────────────────────────────────────────
        # METRICS
        # ─────────────────────────────────────────────────────────────────────────────

        if not equity_curve:
            log.warning("No equity curve!")
            return

        ec = pd.DataFrame(equity_curve).set_index("date")["value"]
        rets = ec.pct_change().dropna()

        if len(rets) < 2:
            log.warning("Not enough data for metrics")
            return

        # ── Nøkkeltall, med det de faktisk er verdt ─────────────────────────
        #
        # Tallene fra 8. september: CAGR 128,9 %, MaxDD 0,0 %, Sortino 0,00,
        # Calmar 0,00 — på åtte måneder. Ingen av dem var gale utregninger;
        # de var riktige formler på for få punkter, og de så like troverdige ut
        # som de treårige tallene fra PB-ROE. Det er den farlige typen feil.
        #
        #   * CAGR er en 8-måneders avkastning opphøyd i 1/0,66. En god høst
        #     blir til «129 % i året». Under MIN_AAR_FOR_CAGR sier vi fra, og
        #     total avkastning er tallet som gjelder.
        #   * Sharpe bygde på den samme CAGR-en og arvet feilen. Nå regnes den
        #     av månedsavkastningene direkte, som er standarden.
        #   * MaxDD 0,0 % betyr ikke «tapte aldri». Kurven har ett punkt per
        #     månedsslutt, og strategien sto i kontanter det meste av tiden.
        #     Antall punkter står nå i loggen ved siden av tallet.
        #   * Sortino og Calmar blir 0 når det ikke finnes nedside å dele på.
        #     Null er en verdi; her er sannheten «ikke målbar», og da skriver
        #     vi «—» i stedet for å pynte på det med et tall.
        MIN_AAR_FOR_CAGR = 2.0
        RF = 0.03

        total_ret = (ec.iloc[-1] / ec.iloc[0]) - 1
        n_years = max((ec.index[-1] - ec.index[0]).days / 365.25, 0.01)
        n_mnd = len(ec)
        cagr = (ec.iloc[-1] / ec.iloc[0]) ** (1 / n_years) - 1
        cagr_holder = n_years >= MIN_AAR_FOR_CAGR
        vol = rets.std() * np.sqrt(12)
        # Av månedsavkastningene, ikke av CAGR: en kort periode skal gi en
        # usikker Sharpe, ikke en oppblåst.
        sharpe = (rets.mean() * 12 - RF) / vol if vol > 0 else None
        mdd = ((ec - ec.cummax()) / ec.cummax()).min()
        wr = (rets > 0).sum() / len(rets)
        ds = rets[rets < 0]
        dv = ds.std() * np.sqrt(12) if len(ds) >= 2 else 0
        sortino = (rets.mean() * 12 - RF) / dv if dv > 0 else None
        calmar = cagr / abs(mdd) if (mdd != 0 and cagr_holder) else None

        def _t(x, d=2, sfx=""):
            """«—» når tallet ikke er målbart. Et pyntet 0,00 lyver."""
            return f"{x:.{d}f}{sfx}" if x is not None and np.isfinite(x) else "—"

        bcagr = None
        if not bn.empty:
            bc = bn.reindex(ec.index, method="ffill").dropna()
            if len(bc) >= 2:
                bcagr = (bc.iloc[-1] / bc.iloc[0]) ** (1 / n_years) - 1

        log.info("")
        log.info("=" * 55)
        log.info("  RESULTS — SENTIMENT v4 + SMA%d", config.sma_days)
        log.info("=" * 55)
        log.info("  Period           : %s → %s  (%.1f år, %d månedspunkter)",
                 ec.index[0].date(), ec.index[-1].date(), n_years, n_mnd)
        log.info("  Start Value      : $%.0f", ec.iloc[0])
        log.info("  End Value        : $%.0f", ec.iloc[-1])
        log.info("  Total Return     : %.1f%%", total_ret * 100)
        if cagr_holder:
            log.info("  CAGR             : %.1f%%", cagr * 100)
        else:
            log.info("  CAGR             : %.1f%%  ⚠️  IKKE MENINGSFULL — %.1f år "
                     "annualisert. Bruk total avkastning.", cagr * 100, n_years)
        log.info("  Sharpe           : %s", _t(sharpe))
        log.info("  Sortino          : %s%s", _t(sortino),
                 "" if sortino is not None else "  (færre enn 2 negative måneder)")
        log.info("  Max Drawdown     : %.1f%%  (målt på %d månedsslutt, ikke daglig)",
                 mdd * 100, n_mnd)
        log.info("  Calmar           : %s", _t(calmar))
        log.info("  Win Rate         : %.0f%%  (%d av %d måneder)",
                 wr * 100, int((rets > 0).sum()), len(rets))
        log.info("  Volatility       : %.1f%%", vol * 100)
        log.info("  Total Trades     : %d", len(trade_log))
        if bcagr is not None:
            log.info("  Benchmark CAGR   : %.1f%%", bcagr * 100)
            log.info("  Excess Return    : %+.1f%%%s", (cagr - bcagr) * 100,
                     "" if cagr_holder else "  ⚠️  begge annualisert fra kort periode")
        if not cagr_holder:
            log.warning("  ⚠️  %.1f år er for kort til å rangere denne strategien "
                        "mot de andre. Den trenger flere artikler, ikke flere "
                        "parametre.", n_years)
        log.info("=" * 55)

        # ─────────────────────────────────────────────────────────────────────────────
        # CURRENT HOLDINGS SNAPSHOT
        # ─────────────────────────────────────────────────────────────────────────────

        log.info("")
        log.info("=" * 55)
        log.info("  CURRENT HOLDINGS SNAPSHOT")
        log.info("=" * 55)

        if not holdings:
            log.info("  No positions — strategy is in CASH")
        else:
            latest_date = ec.index[-1]
            total_stock_value = 0

            for tkr in sorted(holdings.keys()):
                shares = holdings[tkr]
                price = price_at(daily, tkr, latest_date)
                if price and shares > 0:
                    value = shares * price
                    total_stock_value += value
                    pct_of_port = value / ec.iloc[-1] * 100

                    score_str = "N/A"
                    if not last_sentiment.empty and tkr in last_sentiment["Ticker"].values:
                        row = last_sentiment[last_sentiment["Ticker"] == tkr].iloc[0]
                        score_str = "%.3f" % row["Sentiment_Score"]

                    log.info("  %-12s  shares: %8.2f  price: %7.2f  value: $%9.0f  (%5.1f%%)  score: %s",
                            tkr, shares, price, value, pct_of_port, score_str)

            log.info("  %s", "-" * 51)
            log.info("  %-12s  %s  value: $%9.0f  (%5.1f%%)",
                    "Stocks", " " * 27, total_stock_value, total_stock_value / ec.iloc[-1] * 100)
            log.info("  %-12s  %s  value: $%9.0f  (%5.1f%%)",
                    "Cash", " " * 27, cash, cash / ec.iloc[-1] * 100)
            log.info("  %-12s  %s  value: $%9.0f",
                    "Total", " " * 27, ec.iloc[-1])

        log.info("=" * 55)

        # ─────────────────────────────────────────────────────────────────────────────
        # CHARTS (4-panel)
        # ─────────────────────────────────────────────────────────────────────────────

        fig, axes = plt.subplots(4, 1, figsize=(16, 20),
                                gridspec_kw={"height_ratios": [3, 1.2, 1.2, 1]})
        fig.suptitle(
            "Sentiment v4 + SMA%d — Top %d | English-only"
            % (config.sma_days, config.n_portfolio),
            fontsize=15, fontweight="bold", y=0.995
        )
        fig.patch.set_facecolor("#f8f9fa")

        # Panel 1: Equity curve vs benchmark
        ax1 = axes[0]
        ax1.plot(ec.index, ec.values, color="#1565C0", linewidth=2.2,
                label="Sentiment v4", zorder=3)
        ax1.fill_between(ec.index, config.startkapital, ec.values,
                        color="#1565C0", alpha=0.06, zorder=1)

        if not bn.empty:
            bp = bn.reindex(ec.index, method="ffill").dropna()
            if not bp.empty:
                bs = (bp / bp.iloc[0]) * config.startkapital
                ax1.plot(bs.index, bs.values, color="#FF9800", linewidth=1.8,
                        linestyle="--", label="OSEBX", alpha=0.85, zorder=2)

        # Drawdown shading
        dd = (ec - ec.cummax()) / ec.cummax()
        dd_fill = dd.copy()
        dd_fill[dd_fill >= 0] = 0
        ax1_dd = ax1.twinx()
        ax1_dd.fill_between(dd.index, 0, dd_fill.values, color="#E53935", alpha=0.12, zorder=0)
        ax1_dd.set_ylim(-0.6, 0)
        ax1_dd.set_ylabel("Drawdown", fontsize=10, color="#999")
        ax1_dd.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: "%.0f%%" % (x * 100)))

        # Annotate final value
        ax1.annotate("$%s" % f"{ec.iloc[-1]:,.0f}",
                    xy=(ec.index[-1], ec.iloc[-1]),
                    xytext=(10, 8), textcoords="offset points",
                    fontsize=11, fontweight="bold", color="#1565C0",
                    arrowprops=dict(arrowstyle="-", color="#1565C0", lw=0.8))

        if not bn.empty and not bp.empty:
            ax1.annotate("$%s" % f"{bs.iloc[-1]:,.0f}",
                        xy=(bs.index[-1], bs.iloc[-1]),
                        xytext=(10, -12), textcoords="offset points",
                        fontsize=10, color="#FF9800",
                        arrowprops=dict(arrowstyle="-", color="#FF9800", lw=0.8))

        # Samme forbehold på bildet som i loggen. Et diagram blir limt inn i en
        # mail og lest alene, uten loggen ved siden av.
        metrics_text = (
            "%s: %.1f%%  |  Sharpe: %s  |  Sortino: %s\n"
            "Max DD: %.1f%% (månedlig)  |  Win Rate: %.0f%%  |  Trades: %d"
            % ("CAGR" if cagr_holder else "Total",
               (cagr if cagr_holder else total_ret) * 100,
               _t(sharpe), _t(sortino), mdd * 100, wr * 100, len(trade_log))
        )
        if not cagr_holder:
            metrics_text += "\n⚠ %.1f år — for kort til å annualisere" % n_years
        if bcagr is not None:
            metrics_text += "\nBenchmark CAGR: %.1f%%  |  Excess: %+.1f%%" % (
                bcagr * 100, (cagr - bcagr) * 100)
        ax1.text(0.02, 0.97, metrics_text, transform=ax1.transAxes,
                fontsize=9.5, verticalalignment="top",
                bbox=dict(boxstyle="round,pad=0.5", facecolor="white",
                        edgecolor="#ddd", alpha=0.9))

        ax1.set_title("Portfolio value over time", fontweight="bold", fontsize=12, pad=10)
        ax1.legend(loc="upper left", fontsize=10, framealpha=0.9)
        ax1.grid(True, alpha=0.25)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax1.yaxis.set_major_formatter(mticker.FuncFormatter(
            lambda x, _: "$%s" % f"{x:,.0f}"))
        ax1.axhline(config.startkapital, color="#888", linewidth=0.5, linestyle=":")
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)

        # Panel 2: Monthly returns
        ax2 = axes[1]
        m_rets = ec.pct_change().dropna() * 100
        cols = ["#43A047" if r > 0 else "#E53935" for r in m_rets.values]
        ax2.bar(m_rets.index, m_rets.values, color=cols, width=20, alpha=0.8)
        ax2.axhline(0, color="black", linewidth=0.8)
        ax2.set_title("Monthly returns (%)", fontweight="bold", fontsize=11)
        ax2.grid(True, alpha=0.25, axis="y")
        ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: "%.0f%%" % x))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)

        # Panel 3: Rolling 6-month return
        ax3 = axes[2]
        if len(ec) > 6:
            roll_strat = ec.pct_change(6).dropna() * 100
            ax3.plot(roll_strat.index, roll_strat.values, color="#1565C0",
                    linewidth=1.5, label="Strategy (6m)")
            if not bn.empty:
                bn_ec = bn.reindex(ec.index, method="ffill").dropna()
                if len(bn_ec) > 6:
                    roll_bench = bn_ec.pct_change(6).dropna() * 100
                    ax3.plot(roll_bench.index, roll_bench.values, color="#FF9800",
                            linewidth=1.2, linestyle="--", label="OSEBX (6m)")
        ax3.axhline(0, color="black", linewidth=0.8)
        ax3.set_title("Rolling 6-month return", fontweight="bold", fontsize=11)
        ax3.legend(fontsize=9)
        ax3.grid(True, alpha=0.25, axis="y")
        ax3.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45)

        # Panel 4: Holdings count
        ax4 = axes[3]
        if monthly_log:
            ml = pd.DataFrame(monthly_log)
            ml["date_ts"] = pd.to_datetime(ml["date"])
            ax4.bar(ml["date_ts"], ml["n_holdings"], color="#1565C0", alpha=0.7,
                    width=20, label="Holdings")
        ax4.set_title("Holdings count over time", fontweight="bold", fontsize=11)
        ax4.legend(fontsize=9)
        ax4.grid(True, alpha=0.25, axis="y")
        ax4.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        plt.setp(ax4.xaxis.get_majorticklabels(), rotation=45)

        plt.tight_layout()
        chart_path = config.results_dir / f"Sentiment_v4_SMA{config.sma_days}_{TODAY_STR}.png"
        plt.savefig(str(chart_path), dpi=150, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        plt.close()
        log.info("Chart: %s", chart_path)

        # ─────────────────────────────────────────────────────────────────────────────
        # SAVE EXCEL
        # ─────────────────────────────────────────────────────────────────────────────

        out_path = config.results_dir / f"Sentiment_v4_SMA{config.sma_days}_{TODAY_STR}.xlsx"
        with pd.ExcelWriter(str(out_path), engine="openpyxl") as writer:
            if monthly_log:
                pd.DataFrame(monthly_log).to_excel(writer, sheet_name="Monthly_Holdings",
                                                    index=False)
            (pd.DataFrame(score_log) if score_log else pd.DataFrame(
                columns=["date", "ticker", "score", "rank", "over_sma",
                         "valgt", "grunn"])
             ).to_excel(writer, sheet_name="Score_Log", index=False)
            if not score_log:
                log.warning("Score_Log er TOM — master.py teller da NLP som en "
                            "kilde uten mening om noe selskap. Modellen kjørte "
                            "%d rebalanseringer uten å score en eneste kandidat: "
                            "se om DataNLP faktisk har artikler i perioden.",
                            len(rdates))
            else:
                _dager = len({r["date"] for r in score_log})
                log.info("Score_Log: %d rader over %d av %d rebalanseringsdatoer "
                         "(%d handlet, %d bare vurdert)",
                         len(score_log), _dager, len(rdates),
                         sum(1 for r in score_log if r["valgt"] == "JA"),
                         sum(1 for r in score_log if r["valgt"] == "NEI"))

            # Nøkkeltallene skal følge filen. Uten dette arket må enhver leser
            # regne dem om igjen fra kurven — og da får to lesere to svar, slik
            # loggen og strategisammendraget gjorde 8. september.
            pd.DataFrame([{
                "utgave": "v4",
                "fra": str(ec.index[0].date()),
                "til": str(ec.index[-1].date()),
                "aar": round(n_years, 2),
                "maanedspunkter": n_mnd,
                "artikler_fra": str(pd.Timestamp(earliest_article).date()),
                "artikler_til": str(pd.Timestamp(latest_article).date()),
                "total_avkastning": round(float(total_ret), 4),
                "cagr": round(float(cagr), 4),
                "cagr_meningsfull": "JA" if cagr_holder else "NEI",
                "sharpe": None if sharpe is None else round(float(sharpe), 3),
                "sortino": None if sortino is None else round(float(sortino), 3),
                "max_drawdown": round(float(mdd), 4),
                "drawdown_grunnlag": "månedsslutt",
                "calmar": None if calmar is None else round(float(calmar), 3),
                "volatilitet": round(float(vol), 4),
                "win_rate": round(float(wr), 4),
                "handler": len(trade_log),
                "rebalanseringer": len(rdates),
            }]).to_excel(writer, sheet_name="Metrics", index=False)

            ec_df = ec.reset_index()
            ec_df.columns = ["Date", "Strategy"]
            if not bn.empty:
                ec_df["Benchmark"] = bn.reindex(ec.index, method="ffill").values
            ec_df.to_excel(writer, sheet_name="Equity_Curve", index=False)

            if trade_log:
                pd.DataFrame(trade_log).to_excel(writer, sheet_name="Trade_Log", index=False)

        log.info("Results: %s", out_path)
        log.info("=== Sentiment Strategy v4 complete ===")
    # Kallet lå her, mellom de to definisjonene. Se dispatchen nederst.

    #New untestesscraper #Henter mer data
    def NLP_Euronext_Quarter4_v41():

        #!/usr/bin/env python3
        """
        ================================================================================
        EURONEXT OSLO BØRS — COMPANY-PAGE SCRAPER + FINBERT NLP  (v4 — DEEP HISTORY)
        ================================================================================
        Endringer vs. v3:
        ✅ Paginering: walker gjennom ALLE sider av pressemeldings-tabellen
        ✅ Konfigurerbart topic-filter: 'minimal' / 'quarterly' / 'all_financial' / 'everything'
        ✅ max_articles_per_company hevet til 100 (var 10)
        ✅ Dedupe på tvers av sider (nid + tittel)
        ✅ max_pages som safety cap

        KRAV:
            pip install playwright pandas openpyxl transformers torch nltk pdfplumber requests
            playwright install chromium
        ================================================================================
        """

        import asyncio
        import io
        import logging
        import os
        import re
        import sys
        import time
        from dataclasses import dataclass, field
        from datetime import datetime
        from pathlib import Path
        from typing import List, Optional, Set

        import pandas as pd

        # ─────────────────────────────────────────────────────────────────────────────
        # CONFIG
        # ─────────────────────────────────────────────────────────────────────────────

        @dataclass
        class Config:
            base_dir: Path          = Path(r"C:\Users\ander\Desktop\Python_K4\ExcelData")
            tickers_file: str       = r"Data_BT\AllTickers_OSEBX_TW_current.xlsx"
            nlp_output_dir: str     = "DataNLP"
            working_data_dir: str   = r"DataNLP\WorkingData"
            screenshots_dir: str    = r"DataNLP\Screenshots"

            # ── SPEED TUNING ──
            step_delay_ms: int      = 500
            start_url: str          = "https://live.euronext.com/nb/product/equities/NO0010161896-XOSL"
            euronext_base: str      = "https://live.euronext.com"

            # ── DEEP HISTORY ──
            max_articles_per_company: int = 10000  # explicit safety limit; reaching it fails
            max_pages: int          = 1000        # explicit safety limit; reaching it fails

            # ── TOPIC FILTER MODE ──
            # "minimal"       = original: Halvårsdata + Årsrapporter (~4/yr)
            # "quarterly"     = adds Kvartalsdata (~8/yr) — RECOMMENDED starting point
            # "all_financial" = adds Foreløpig regnskap + Kapitalmarkedsdager
            # "everything"    = NO topic filter — every press release (30+/yr, noisier)
            topic_filter_mode: str  = "quarterly"

            headless: bool          = True
            slow_mo: int            = 40
            request_delay: float    = 0.8
            page_timeout: int       = 25_000
            modal_click_timeout: int = 12_000
            modal_wait_ms: int      = 1_800
            modal_close_verify_ms: int = 600

            finbert_model: str      = "yiyanghkust/finbert-tone"
            max_sentences: int      = 100
            force_rerun: bool       = True

            search_retry_variants: bool = True

            @property
            def tickers_path(self) -> Path:
                return self.base_dir / self.tickers_file

            @property
            def nlp_dir(self) -> Path:
                p = self.base_dir / self.nlp_output_dir
                p.mkdir(parents=True, exist_ok=True)
                return p

            @property
            def work_dir(self) -> Path:
                p = self.base_dir / self.working_data_dir
                p.mkdir(parents=True, exist_ok=True)
                return p

            @property
            def screenshot_dir(self) -> Path:
                p = self.base_dir / self.screenshots_dir
                p.mkdir(parents=True, exist_ok=True)
                return p


        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s │ %(levelname)-7s │ %(message)s",
            datefmt="%H:%M:%S",
        )
        log = logging.getLogger(__name__)

        # ─────────────────────────────────────────────────────────────────────────────
        # STEG-LOGGER
        # ─────────────────────────────────────────────────────────────────────────────

        class StepLogger:
            def __init__(self, company: str):
                self.company = company
                self.n = 0

            def step(self, desc: str):
                self.n += 1
                print(f"\n  ┌─ STEG {self.n}: {desc}  [{self.company}]")

            def ok(self, detail: str = ""):
                msg = f"  └─ ✅ STEG {self.n} FERDIG"
                if detail:
                    msg += f": {detail}"
                print(msg)

            def fail(self, detail: str = ""):
                msg = f"  └─ ❌ STEG {self.n} FEILET"
                if detail:
                    msg += f": {detail}"
                print(msg)

            def info(self, detail: str):
                print(f"  │  ℹ️  {detail}")

            def warn(self, detail: str):
                print(f"  │  ⚠️  {detail}")


        # ─────────────────────────────────────────────────────────────────────────────
        # HJELPEFUNKSJONER
        # ─────────────────────────────────────────────────────────────────────────────

        def _safe_name(text: str, max_len: int = 30) -> str:
            return re.sub(r'[^\w]', '_', text)[:max_len]


        def _search_variants(company_name: str) -> List[str]:
            variants = [company_name]
            cleaned = re.sub(r'\s+(ASA|AS|A/S|Holding|Group|Gruppen)\s*$', '', company_name, flags=re.IGNORECASE).strip()
            if cleaned != company_name and cleaned:
                variants.append(cleaned)
            words = company_name.split()
            if len(words) >= 2:
                two_words = " ".join(words[:2])
                if two_words not in variants:
                    variants.append(two_words)
            if len(words) >= 1 and words[0] not in variants:
                variants.append(words[0])
            return variants


        async def safe_screenshot(page, path: Path, label: str = ""):
            try:
                await page.screenshot(path=str(path), full_page=False)
                if label:
                    log.info(f"📸 Screenshot: {label} → {path.name}")
            except Exception as e:
                log.warning(f"Screenshot feilet ({label}): {e}")


        async def click_xpath(page, xpath: str, description: str,
                            timeout: int = 10_000, scroll: bool = True) -> bool:
            try:
                loc = page.locator(f"xpath={xpath}")
                count = await loc.count()
                if count == 0:
                    log.debug(f"  XPath 0 treff: {xpath[:80]}")
                    return False

                el = loc.first
                try:
                    await el.wait_for(state="visible", timeout=timeout)
                except Exception:
                    if scroll:
                        try:
                            await el.scroll_into_view_if_needed(timeout=5_000)
                            await page.wait_for_timeout(300)
                        except Exception:
                            pass

                await el.click(timeout=timeout)
                log.info(f"  ✓ Klikket: {description}")
                return True

            except Exception as e:
                log.debug(f"  click_xpath feilet ({description}): {e}")
                return False


        async def click_any(page, selectors: list, description: str,
                            timeout: int = 8_000) -> bool:
            for sel in selectors:
                try:
                    prefix = "xpath=" if sel.startswith("/") else ""
                    loc = page.locator(f"{prefix}{sel}")
                    if await loc.count() == 0:
                        continue
                    el = loc.first
                    try:
                        await el.wait_for(state="visible", timeout=timeout)
                    except Exception:
                        try:
                            await el.scroll_into_view_if_needed(timeout=3_000)
                            await page.wait_for_timeout(200)
                        except Exception:
                            pass
                    await el.click(timeout=timeout)
                    log.info(f"  ✓ Klikket (fallback): {description}  [{sel[:60]}]")
                    return True
                except Exception:
                    continue
            log.warning(f"  ✗ Alle selektorer feilet: {description}")
            return False


        def _clean_text(raw: str) -> str:
            if not raw:
                return ""
            skip = [
                "skip to main content", "toggle navigation", "euronext websites",
                "my profile", "my subscriptions", "watchlists", "quote alerts",
                "create account", "sign in", "close menu", "© 20",
                "privacy statement", "terms of use", "cookie policy",
                "to subscribe to press releases", "footer small print",
                "reject all", "accept all", "cookie settings",
            ]
            lines = []
            for line in raw.split("\n"):
                low = line.strip().lower()
                if any(p in low for p in skip):
                    continue
                if line.strip():
                    lines.append(line.strip())
            text = "\n".join(lines)
            text = re.sub(r"\n{3,}", "\n\n", text)
            return text.strip()


        # ─────────────────────────────────────────────────────────────────────────────
        # PDF-EKSTRAKSJON
        # ─────────────────────────────────────────────────────────────────────────────

        def extract_text_from_pdf_url(pdf_url: str) -> str:
            try:
                import requests
                import pdfplumber
                headers = {
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    )
                }
                resp = requests.get(pdf_url, headers=headers, timeout=30)
                resp.raise_for_status()
                with pdfplumber.open(io.BytesIO(resp.content)) as pdf:
                    texts = [pg.extract_text() for pg in pdf.pages if pg.extract_text()]
                full = "\n\n".join(texts)
                log.info(f"  📄 PDF fra URL: {len(full)} tegn")
                return _clean_text(full)
            except ImportError:
                log.warning("  pdfplumber ikke installert — hopper over PDF")
                return ""
            except Exception as e:
                log.error(f"  PDF URL-ekstraksjon feilet ({pdf_url}): {e}")
                return ""


        def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
            try:
                import pdfplumber
                with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                    texts = [pg.extract_text() for pg in pdf.pages if pg.extract_text()]
                return _clean_text("\n\n".join(texts))
            except Exception as e:
                log.error(f"  PDF bytes-ekstraksjon feilet: {e}")
                return ""


        # ─────────────────────────────────────────────────────────────────────────────
        # DATA-KLASSE
        # ─────────────────────────────────────────────────────────────────────────────

        @dataclass
        class Article:
            company: str
            title: str
            url: str
            date: str
            text: str    = ""
            pdf_url: str = ""


        # ─────────────────────────────────────────────────────────────────────────────
        # LAST SELSKAPER FRA EXCEL
        # ─────────────────────────────────────────────────────────────────────────────

        def load_companies(config: Config) -> List[str]:
            path = config.tickers_path
            if not path.exists():
                log.error(f"Fil ikke funnet: {path}")
                raise FileNotFoundError(path)
            df = pd.read_excel(path)
            df = df.loc[:, ~df.columns.astype(str).str.contains("^Unnamed", na=False)]

            for col in ["Company", "company", "Name", "name"]:
                if col in df.columns:
                    return df[col].dropna().astype(str).tolist()
            return df.iloc[:, 0].dropna().astype(str).tolist()


        # ─────────────────────────────────────────────────────────────────────────────
        # SØK + DROPDOWN
        # ─────────────────────────────────────────────────────────────────────────────

        async def search_and_select_company(page, company_name: str, config: Config, sl: StepLogger) -> bool:
            variants = _search_variants(company_name) if config.search_retry_variants else [company_name]

            for attempt, search_term in enumerate(variants):
                sl.info(f"Søkeforsøk {attempt + 1}/{len(variants)}: '{search_term}'")

                search_loc = None
                try:
                    loc = page.locator(f"xpath={XP['SEARCH_INPUT']}")
                    if await loc.count() > 0:
                        search_loc = loc
                    else:
                        for sel in ["input[name='search_symbol']", "nav input[type='text']",
                                    "header form input[type='text']"]:
                            loc = page.locator(sel)
                            if await loc.count() > 0:
                                search_loc = loc
                                break
                except Exception:
                    pass

                if not search_loc:
                    sl.fail("Søkefelt ikke funnet")
                    return False

                try:
                    await search_loc.first.click(timeout=8_000)
                    await page.wait_for_timeout(200)
                    await search_loc.first.fill("")
                    await page.wait_for_timeout(200)
                    await search_loc.first.type(search_term, delay=60)
                    sl.info(f"Skrev '{search_term}' — venter på dropdown...")
                    await page.wait_for_timeout(2_500)
                except Exception as e:
                    sl.warn(f"Kunne ikke skrive i søkefelt: {e}")
                    continue

                clicked = await click_xpath(page, XP["DROPDOWN_FIRST"], "Dropdown første treff", timeout=8_000)
                if not clicked:
                    clicked = await click_any(
                        page,
                        ["ul.ui-autocomplete li:first-child a",
                        ".ui-autocomplete li:first-child a",
                        "ul[role='listbox'] li:first-child a",
                        "ul.ui-autocomplete li:first-child",
                        ".ui-autocomplete li:first-child"],
                        "Dropdown fallback"
                    )

                if clicked:
                    try:
                        await page.wait_for_load_state("networkidle", timeout=15_000)
                    except Exception:
                        pass
                    await page.wait_for_timeout(1_500)

                    current_url = page.url
                    if "/product/equities/" in current_url:
                        sl.ok(f"Selskapside lastet: {current_url[:80]}")
                        return True
                    else:
                        sl.warn(f"Uventet URL etter søk: {current_url[:80]} — prøver neste variant")
                        try:
                            await page.goto(config.start_url, wait_until="networkidle", timeout=config.page_timeout)
                            await page.wait_for_timeout(1_500)
                        except Exception:
                            pass
                        continue
                else:
                    sl.info(f"Ingen dropdown-treff for '{search_term}'")
                    try:
                        await page.keyboard.press("Escape")
                        await page.wait_for_timeout(300)
                    except Exception:
                        pass
                    continue

            return False


        # ─────────────────────────────────────────────────────────────────────────────
        # FORCE-DISMISS ALL MODALS
        # ─────────────────────────────────────────────────────────────────────────────

        async def _force_dismiss_all_modals(page, config: Config):
            await page.evaluate("""
            () => {
                document.querySelectorAll('.modal.show, .modal.in, .modal[style*="display: block"]')
                    .forEach(m => {
                        m.classList.remove('show', 'in');
                        m.style.display = 'none';
                        m.setAttribute('aria-hidden', 'true');
                        m.removeAttribute('aria-modal');
                    });
                document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
                document.body.classList.remove('modal-open');
                document.body.style.overflow = '';
                document.body.style.paddingRight = '';
            }
            """)
            try:
                await page.keyboard.press("Escape")
            except Exception:
                pass
            await page.wait_for_timeout(config.modal_close_verify_ms)

            still_open = await page.evaluate("""
            () => {
                const m = document.querySelector('.modal.show, .modal.in, .modal[style*="display: block"]');
                return !!m;
            }
            """)
            if still_open:
                log.warning("  ⚠️ Modal still open after force-dismiss — retrying")
                await page.evaluate("""
                () => {
                    document.querySelectorAll('.modal').forEach(m => {
                        m.style.display = 'none';
                        m.classList.remove('show', 'in');
                    });
                    document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
                    document.body.classList.remove('modal-open');
                    document.body.style.overflow = '';
                }
                """)
                await page.wait_for_timeout(300)


        # ─────────────────────────────────────────────────────────────────────────────
        # HENT TEKST FRA MODAL
        # ─────────────────────────────────────────────────────────────────────────────

        async def fetch_modal_text(page, nid: str, config: Config) -> str:
            try:
                await _force_dismiss_all_modals(page, config)

                link_sel = f"a.standardRightCompanyPressRelease[data-node-nid='{nid}']"
                loc = page.locator(link_sel)
                if await loc.count() == 0:
                    log.warning(f"  Modal-lenke ikke funnet for nid={nid}")
                    return ""

                try:
                    await loc.first.scroll_into_view_if_needed(timeout=5_000)
                    await page.wait_for_timeout(300)
                except Exception:
                    pass

                await loc.first.click(timeout=config.modal_click_timeout)
                log.info(f"  ✓ Klikket modal-lenke nid={nid}")
                await page.wait_for_timeout(config.modal_wait_ms)

                nid_modal_text = await page.evaluate("""
                (nid) => {
                    const modal = document.querySelector(
                        '#CompanyPressRelease-' + nid + ', ' +
                        '[id*="CompanyPressRelease"][id*="' + nid + '"]'
                    );
                    if (modal) {
                        const body = modal.querySelector('.modal-body');
                        if (body && body.innerText.trim().length > 50) {
                            return body.innerText.trim();
                        }
                    }
                    return '';
                }
                """, nid)

                if nid_modal_text and len(nid_modal_text) > 100:
                    log.info(f"  📄 Modal via nid: {len(nid_modal_text)} tegn")
                    await _force_dismiss_all_modals(page, config)
                    return _clean_text(nid_modal_text)

                dynamic_text = await page.evaluate("""
                () => {
                    const modals = document.querySelectorAll(
                        '.modal.show, .modal.in, .modal[style*="display: block"], ' +
                        '.modal[aria-modal="true"], [role="dialog"]:not([style*="display: none"])'
                    );
                    let bestText = '';
                    for (const modal of modals) {
                        const body = modal.querySelector('.modal-body');
                        if (body) {
                            const t = body.innerText.trim();
                            if (t.length > bestText.length) bestText = t;
                        }
                        if (bestText.length < 100) {
                            const content = modal.querySelector('.modal-content');
                            if (content) {
                                const t = content.innerText.trim();
                                if (t.length > bestText.length) bestText = t;
                            }
                        }
                    }
                    return bestText;
                }
                """)

                if dynamic_text and len(dynamic_text) > 100:
                    log.info(f"  📄 Modal dynamisk: {len(dynamic_text)} tegn")
                    await _force_dismiss_all_modals(page, config)
                    return _clean_text(dynamic_text)

                modal_xpaths = [
                    "/html/body/div[5]/div/div/div[2]/div[2]/div[4]/div/p[1]",
                    "/html/body/div[6]/div/div/div[2]/div[2]/div[4]/div/p[1]",
                    "/html/body/div[7]/div/div/div[2]/div[2]/div[4]/div/p[1]",
                    "/html/body/div[8]/div/div/div[2]/div[2]/div[4]/div/p[1]",
                    "/html/body/div[9]/div/div/div[2]/div[2]/div[4]/div/p[1]",
                ]

                best_text = ""
                best_xp   = ""
                for xp in modal_xpaths:
                    try:
                        el = page.locator(f"xpath={xp}")
                        if await el.count() > 0:
                            t = (await el.first.inner_text()).strip()
                            if len(t) > len(best_text):
                                best_text = t
                                best_xp   = xp
                    except Exception:
                        continue

                if best_text and best_xp:
                    container_xp = best_xp.replace("/p[1]", "")
                    try:
                        container = page.locator(f"xpath={container_xp}")
                        if await container.count() > 0:
                            full_text = (await container.first.inner_text()).strip()
                            if len(full_text) > len(best_text):
                                best_text = full_text
                    except Exception:
                        pass
                    log.info(f"  📄 Modal XPath: {len(best_text)} tegn")
                    await _force_dismiss_all_modals(page, config)
                    return _clean_text(best_text)

                modal_css_selectors = [
                    ".modal.show .modal-body",
                    ".modal.in .modal-body",
                    f"#CompanyPressRelease-{nid} .modal-body",
                    "[id^='CompanyPressRelease-'].show .modal-body",
                    "[id^='CompanyPressRelease-'].in .modal-body",
                    ".modal-dialog .modal-body",
                    ".modal.show .modal-content",
                    ".modal.in .modal-content",
                ]
                for sel in modal_css_selectors:
                    try:
                        el = page.locator(sel)
                        if await el.count() > 0:
                            await el.first.wait_for(state="visible", timeout=4_000)
                            t = (await el.first.inner_text()).strip()
                            if len(t) > 100:
                                log.info(f"  📄 Modal CSS ({sel}): {len(t)} tegn")
                                await _force_dismiss_all_modals(page, config)
                                return _clean_text(t)
                    except Exception:
                        continue

                log.warning(f"  Modal-tekst ikke funnet for nid={nid}")
                await _force_dismiss_all_modals(page, config)
                return ""

            except Exception as e:
                log.error(f"  fetch_modal_text feilet (nid={nid}): {e}")
                try:
                    await _force_dismiss_all_modals(page, config)
                except Exception:
                    pass
                return ""


        async def _close_modal(page):
            try:
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(500)
            except Exception:
                pass
            close_selectors = [
                ".modal.show .close",
                ".modal.in .close",
                ".modal-header button.close",
                ".modal.show button[aria-label='Close']",
                ".modal.show .btn-close",
                "button.close[data-dismiss='modal']",
            ]
            for sel in close_selectors:
                try:
                    cl = page.locator(sel)
                    if await cl.count() > 0:
                        await cl.first.click()
                        await page.wait_for_timeout(400)
                        return
                except Exception:
                    continue
            try:
                await page.mouse.click(10, 10)
                await page.wait_for_timeout(300)
            except Exception:
                pass


        # ─────────────────────────────────────────────────────────────────────────────
        # HENT ARTIKKELTEKST
        # ─────────────────────────────────────────────────────────────────────────────

        async def fetch_article_text(page, article: Article, config: Config,
                                    return_url: str = "") -> str:
            try:
                await page.goto(article.url, wait_until="networkidle", timeout=config.page_timeout)
                await page.wait_for_timeout(1_500)

                content_type = await page.evaluate("() => document.contentType || ''")
                if "pdf" in content_type.lower() or article.url.lower().endswith(".pdf"):
                    pdf_bytes = await page.evaluate("""
                        async () => {
                            const resp = await fetch(window.location.href);
                            const buf  = await resp.arrayBuffer();
                            return Array.from(new Uint8Array(buf));
                        }
                    """)
                    text = extract_text_from_pdf_bytes(bytes(pdf_bytes))
                    if return_url:
                        await _navigate_back(page, return_url, config)
                    return text

                pdf_link = await page.evaluate("""
                () => {
                    for (const a of document.querySelectorAll('a[href]')) {
                        const h = a.href || '';
                        if (h.toLowerCase().endsWith('.pdf') ||
                            h.toLowerCase().includes('/pdf') ||
                            (a.innerText && a.innerText.toLowerCase().includes('pdf'))) {
                            return h;
                        }
                    }
                    return null;
                }
                """)

                html_text = await page.evaluate("""
                () => {
                    const selectors = [
                        '.field--name-field-press-release-body',
                        '.field--name-body',
                        '.node__content .field--type-text-with-summary',
                        '.node__content .field--type-text-long',
                        'article .field--name-body',
                        '.press-release-content',
                        '.article-body',
                        '[class*="press-release"]',
                        '[class*="article-content"]',
                    ];
                    for (const sel of selectors) {
                        const el = document.querySelector(sel);
                        if (el && el.innerText.trim().length > 100)
                            return el.innerText.trim();
                    }
                    const main = document.querySelector('#main-content, main, [role="main"]');
                    if (main) {
                        const clone = main.cloneNode(true);
                        clone.querySelectorAll(
                            'nav, footer, .menu, .breadcrumb, .pager, ' +
                            '.cookie-banner, #onetrust-banner-sdk'
                        ).forEach(n => n.remove());
                        const t = clone.innerText.trim();
                        if (t.length > 200) return t;
                    }
                    return document.body.innerText.substring(0, 15000);
                }
                """)
                html_text = _clean_text(html_text)

                if pdf_link and len(html_text) < 500:
                    log.info(f"  📎 PDF-lenke funnet: {pdf_link}")
                    article.pdf_url = pdf_link
                    pdf_text = extract_text_from_pdf_url(pdf_link)
                    if len(pdf_text) > len(html_text):
                        html_text = pdf_text

                if return_url:
                    await _navigate_back(page, return_url, config)

                return html_text

            except Exception as e:
                log.error(f"  Feil ved henting av artikkel {article.url}: {e}")
                if return_url:
                    try:
                        await _navigate_back(page, return_url, config)
                    except Exception:
                        pass
                return ""


        async def _navigate_back(page, url: str, config: Config):
            try:
                await page.goto(url, wait_until="networkidle", timeout=config.page_timeout)
                await page.wait_for_timeout(1_500)
            except Exception as e:
                log.warning(f"  Navigering tilbake feilet ({url[:60]}): {e}")
                try:
                    await page.go_back(wait_until="networkidle", timeout=config.page_timeout)
                    await page.wait_for_timeout(1_500)
                except Exception:
                    pass


        # ─────────────────────────────────────────────────────────────────────────────
        # PAGINERING — walker gjennom alle sider
        # ─────────────────────────────────────────────────────────────────────────────

        async def _click_next_page(page, sl: StepLogger) -> bool:
            """Klikker pagination 'next'-knappen. Returnerer True hvis klikket."""
            next_selectors = [
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
            for sel in next_selectors:
                try:
                    loc = page.locator(sel)
                    if await loc.count() == 0:
                        continue
                    el = loc.first

                    # Sjekk at den ikke er disabled
                    try:
                        is_disabled = await el.evaluate("""
                            el => el.classList.contains('disabled') ||
                                el.getAttribute('aria-disabled') === 'true' ||
                                (el.closest('.disabled, [aria-disabled=\"true\"]') !== null)
                        """)
                    except Exception:
                        is_disabled = False

                    if is_disabled:
                        continue

                    try:
                        await el.scroll_into_view_if_needed(timeout=3_000)
                        await page.wait_for_timeout(200)
                    except Exception:
                        pass

                    await el.click(timeout=8_000)
                    sl.info(f"  ✓ Klikket Neste side  [{sel[:50]}]")
                    return True
                except Exception:
                    continue
            return False


        async def collect_all_article_rows(page, config: Config, sl: StepLogger) -> List[dict]:
            """
            Walker gjennom hver side av pressemeldings-tabellen og samler artikkelrader.
            Stopper når:
            - 'next' knappen ikke finnes / er disabled
            - vi har samlet max_articles_per_company rader
            - vi har besøkt max_pages sider
            - en side ikke gir nye rader (dedup)
            """
            all_rows: List[dict] = []
            seen_nids: Set[str] = set()
            seen_titles: Set[str] = set()

            for page_num in range(1, config.max_pages + 1):
                sl.info(f"Henter side {page_num}...")

                try:
                    await page.wait_for_selector("table tbody tr", timeout=10_000)
                except Exception:
                    body = (await page.locator("body").inner_text()).lower()
                    if page_num == 1 and any(t in body for t in ("no results found", "ingen resultater", "ingen treff")):
                        return []
                    raise RuntimeError(f"Management result table unavailable on page {page_num}")

                await page.wait_for_timeout(800)

                # Ekstraher rader fra denne siden — samme JS som før, pluss generell fallback
                rows = await page.evaluate("""
                () => {
                    const out = [];
                    const links = document.querySelectorAll('a.standardRightCompanyPressRelease[data-node-nid]');
                    for (const a of links) {
                        const nid   = a.getAttribute('data-node-nid') || '';
                        const title = a.innerText.trim();
                        if (!nid || !title) continue;
                        let date = '';
                        const tr = a.closest('tr');
                        if (tr) {
                            const dateEl = tr.querySelector('td:first-child span, td:first-child');
                            if (dateEl) date = dateEl.innerText.trim();
                        }
                        out.push({ nid, title, date, href: '' });
                    }
                    if (out.length === 0) {
                        const trs = document.querySelectorAll('table tbody tr');
                        for (const tr of trs) {
                            const tds = tr.querySelectorAll('td');
                            if (tds.length < 2) continue;
                            let date = '';
                            const ds = tds[0] && tds[0].querySelector('span');
                            date = ds ? ds.innerText.trim() : (tds[0] ? tds[0].innerText.trim() : '');
                            let title = '', href = '', nid = '';
                            for (const td of tds) {
                                const a = td.querySelector('a');
                                if (a && a.innerText.trim().length > 5) {
                                    title = a.innerText.trim();
                                    href  = a.getAttribute('href') || '';
                                    nid   = a.getAttribute('data-node-nid') || '';
                                    break;
                                }
                            }
                            if (title && (href || nid)) out.push({ date, title, href, nid });
                        }
                    }
                    return out;
                }
                """)

                # Dedupe på tvers av sider
                new_count = 0
                for r in rows:
                    key_nid = r.get("nid", "")
                    key_title = r.get("title", "")
                    if key_nid and key_nid in seen_nids:
                        continue
                    if not key_nid and key_title in seen_titles:
                        continue
                    if key_nid:
                        seen_nids.add(key_nid)
                    if key_title:
                        seen_titles.add(key_title)
                    all_rows.append(r)
                    new_count += 1

                sl.info(f"  Side {page_num}: {len(rows)} rader, {new_count} nye → totalt {len(all_rows)}")

                if len(all_rows) >= config.max_articles_per_company:
                    raise RuntimeError("Article safety limit reached; collection is incomplete")

                if new_count == 0:
                    raise RuntimeError("Repeated or unreadable management result page")

                # Forsøk å klikke neste side
                next_clicked = await _click_next_page(page, sl)
                if not next_clicked:
                    sl.info("  Ingen flere sider")
                    break

                try:
                    await page.wait_for_load_state("networkidle", timeout=10_000)
                except Exception:
                    pass
                await page.wait_for_timeout(1_500)

            if page_num >= config.max_pages and next_clicked:
                raise RuntimeError("Page safety limit reached; collection is incomplete")
            return all_rows


        # ─────────────────────────────────────────────────────────────────────────────
        # HOVED SCRAPING PER SELSKAP
        # ─────────────────────────────────────────────────────────────────────────────

        XP = {
            "COOKIES":        "//*[@id='onetrust-reject-all-handler']",
            "SELSKAPSINFO":   "/html/body/div[2]/div[1]/div/div/div[1]/section/div[3]/div/div/div/div/nav/div/a[3]",
            "SE_ALLE":        "/html/body/div[2]/div[1]/div/div/div[1]/div/div[2]/div[1]/section/div[2]/div[2]/div[1]/div/ul/li[2]/a/svg",
            "FILTER_BTN":     "/html/body/div[2]/div[1]/div/div/div[1]/div[3]/div/main/section/div[2]/div[2]/div/div[1]/div/button[2]",
            "TOPIC_BTN":      "/html/body/div[2]/div[1]/div/div/div[1]/div[3]/div/main/section/div[2]/div[2]/div/div[1]/div/div[1]/div/div/div[2]/div/div/div[2]/div/form/div/div[3]/div/div[1]/div[2]/button",
            "HALVAAR":        "/html/body/div[2]/div[1]/div/div/div[1]/div[3]/div/main/section/div[2]/div[2]/div/div[1]/div/div[1]/div/div/div[2]/div/div/div[2]/div/form/div/div[3]/div/div[2]/div/div/div/div[12]/label",
            "AARSRAPPORT":    "label[for='edit-field-company-press-releases-target-id-1070']",
            "APPLY":          "/html/body/div[2]/div[1]/div/div/div[1]/div[3]/div/main/section/div[2]/div[2]/div/div[1]/div/div[1]/div/div/div[2]/div/div/div[2]/div/form/div/div[5]/input",
            "SEARCH_INPUT":   "/html/body/div[2]/div[1]/div/div/header/nav[1]/div/div[2]/div[1]/form/div[2]/input",
            "DROPDOWN_FIRST": "/html/body/ul[1]/li[1]/a/span[1]/a",
            "ART_ROW_TITLE":  "/html/body/div[2]/div[1]/div/div/div[1]/div[3]/div/main/section/div[2]/div[2]/div/div/div/div[3]/div/table/tbody/tr[{n}]/td[3]/a",
            "ART_ROW_DATE":   "/html/body/div[2]/div[1]/div/div/div[1]/div[3]/div/main/section/div[2]/div[2]/div/div/div/div[3]/div/table/tbody/tr[{n}]/td[1]/span[1]",
        }


        async def scrape_company(
            page,
            company_name: str,
            config: Config,
            is_first: bool,
        ) -> List[Article]:

            articles: List[Article] = []
            sl = StepLogger(company_name)
            safe = _safe_name(company_name)

            print(f"\n{'═'*70}")
            print(f"  SELSKAP: {company_name}")
            print(f"{'═'*70}")

            # ══════════════════════════════════════════════════════════════════════════
            # STEG 1  — Åpne siden / søk opp selskap
            # ══════════════════════════════════════════════════════════════════════════
            if is_first:
                sl.step("Åpner Euronext-siden (første gang)")
                try:
                    await page.goto(config.start_url, wait_until="networkidle", timeout=60_000)
                    await page.wait_for_timeout(2_000)
                    sl.ok(f"Side lastet: {config.start_url}")
                except Exception as e:
                    sl.fail(str(e))
                    return articles
                await page.wait_for_timeout(config.step_delay_ms)

                sl.step("Lukker cookie-banner")
                clicked = await click_xpath(page, XP["COOKIES"], "Reject All cookies", timeout=10_000)
                if not clicked:
                    clicked = await click_any(
                        page,
                        ["#onetrust-accept-btn-handler",
                        "button:has-text('Accept All')",
                        "button:has-text('Reject All')"],
                        "cookie fallback"
                    )
                if clicked:
                    await page.wait_for_timeout(1_000)
                    sl.ok("Cookie-banner lukket")
                else:
                    sl.warn("Ingen cookie-banner funnet (OK — fortsetter)")
                await page.wait_for_timeout(config.step_delay_ms)

            else:
                sl.step(f"Søker opp selskap i søkefeltet")
                found = await search_and_select_company(page, company_name, config, sl)
                if not found:
                    sl.fail(f"Kunne ikke finne '{company_name}' i Euronext-søk")
                    await safe_screenshot(page, config.screenshot_dir / f"search_fail_{safe}.png", "søk feilet")
                    try:
                        await page.goto(config.start_url, wait_until="networkidle", timeout=config.page_timeout)
                        await page.wait_for_timeout(1_500)
                    except Exception:
                        pass
                    return articles
                await page.wait_for_timeout(config.step_delay_ms)

            # ══════════════════════════════════════════════════════════════════════════
            # STEG 3  — Klikk SELSKAPSINFORMASJON-fanen
            # ══════════════════════════════════════════════════════════════════════════
            sl.step("Klikker SELSKAPSINFORMASJON-fanen")
            clicked = await click_xpath(page, XP["SELSKAPSINFO"], "Selskapsinformasjon-fane", timeout=10_000)
            if not clicked:
                clicked = await click_any(
                    page,
                    ["a[href*='company-information']",
                    "a.nav-link:has-text('SELSKAPSINFORMASJON')",
                    "a.nav-link:has-text('Company information')",
                    "a:has-text('SELSKAPSINFORMASJON')",
                    "a:has-text('Company information')"],
                    "Selskapsinformasjon fallback"
                )
            if not clicked:
                current = page.url
                if "/product/equities/" in current:
                    base = re.sub(r'(/product/equities/[^/]+-[A-Z]+).*', r'\1', current)
                    direct = base + "/company-information"
                    sl.warn(f"Navigerer direkte til: {direct}")
                    try:
                        await page.goto(direct, wait_until="networkidle", timeout=config.page_timeout)
                        await page.wait_for_timeout(1_500)
                        clicked = True
                    except Exception as e:
                        sl.fail(str(e))
                        return articles
            if not clicked:
                sl.fail("Kan ikke nå SELSKAPSINFORMASJON")
                return articles
            await page.wait_for_timeout(1_500)
            sl.ok("SELSKAPSINFORMASJON-fane nådd")
            await page.wait_for_timeout(config.step_delay_ms)

            # ══════════════════════════════════════════════════════════════════════════
            # STEG 4  — Klikk "Se alle" pressemeldings-listen
            # ══════════════════════════════════════════════════════════════════════════
            sl.step("Klikker 'Se alle' for pressemeldinger")
            clicked = False
            try:
                svg_loc = page.locator(f"xpath={XP['SE_ALLE']}")
                if await svg_loc.count() > 0:
                    await page.evaluate(
                        "xpath => { "
                        "  const el = document.evaluate(xpath, document, null, "
                        "    XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue; "
                        "  if (el) { "
                        "    const a = el.closest('a') || el.parentElement; "
                        "    if (a) a.click(); "
                        "  } "
                        "}",
                        XP["SE_ALLE"]
                    )
                    clicked = True
                    log.info("  ✓ Klikket Se alle (via JS parent)")
            except Exception:
                pass

            if not clicked:
                clicked = await click_any(
                    page,
                    ["a:has-text('Se alle')",
                    "a:has-text('See all')",
                    "a[href*='listview/company-press-release']",
                    "a[href*='company-press-release']"],
                    "Se alle fallback"
                )
            if clicked:
                try:
                    await page.wait_for_load_state("networkidle", timeout=12_000)
                except Exception:
                    pass
                await page.wait_for_timeout(1_500)
                sl.ok("Pressemeldings-liste lastet")
            else:
                sl.warn("'Se alle' ikke funnet — prøver å bruke eksisterende side")
            await page.wait_for_timeout(config.step_delay_ms)

            # ══════════════════════════════════════════════════════════════════════════
            # STEG 5+6+7  — Åpne filter, topic-dropdown, velg topics (modus-avhengig)
            # ══════════════════════════════════════════════════════════════════════════
            mode = getattr(config, "topic_filter_mode", "minimal")

            if mode != "everything":
                # ── STEG 5: Åpne filter-panel ──
                sl.step("Åpner filter-panel")
                clicked = await click_xpath(page, XP["FILTER_BTN"], "Filter-knapp", timeout=10_000)
                if not clicked:
                    clicked = await click_any(
                        page,
                        ["button:has-text('Filters')",
                        "button:has-text('Filter')",
                        "button.filter-toggle"],
                        "Filter fallback"
                    )
                if clicked:
                    await page.wait_for_timeout(1_500)
                    sl.ok("Filter-panel åpnet")
                else:
                    sl.warn("Filter-knapp ikke funnet — fortsetter uten filter")
                await page.wait_for_timeout(config.step_delay_ms)

                # ── STEG 6: Åpne Topic-dropdown ──
                sl.step("Åpner Topic-dropdown")
                clicked = await click_xpath(page, XP["TOPIC_BTN"], "Topic-dropdown", timeout=8_000)
                if not clicked:
                    clicked = await click_any(
                        page,
                        ["button:has-text('Topic')",
                        "button:has-text('Emne')",
                        "details summary:has-text('Topic')"],
                        "Topic fallback"
                    )
                if clicked:
                    await page.wait_for_timeout(1_000)
                    sl.ok("Topic-dropdown åpnet")
                else:
                    sl.warn("Topic-dropdown ikke funnet")
                await page.wait_for_timeout(config.step_delay_ms)

                # ── STEG 7: Velg topics basert på modus ──
                topic_clicks = []

                # Halvårsdata (alltid)
                topic_clicks.append((
                    XP["HALVAAR"],
                    ["label:has-text('Halvårsdata')",
                    "label:has-text('Half year')",
                    "label:has-text('Half Year')",
                    "input[value*='halvår' i]"],
                    "Halvårsdata"
                ))

                # Årsrapporter (alltid)
                topic_clicks.append((
                    XP["AARSRAPPORT"],
                    ["label:has-text('Årsrapporter og revisjonsberetninger')",
                    "label:has-text('Annual reports')",
                    "label:has-text('Annual financial report')",
                    "label[for*='1070']",
                    "#edit-field-company-press-releases-target-id-1070"],
                    "Årsrapporter og revisjonsberetninger"
                ))

                if mode in ("quarterly", "all_financial"):
                    topic_clicks.append((
                        None,
                        ["label:has-text('Kvartalsdata')",
                        "label:has-text('Quarterly')",
                        "label:has-text('Quarterly report')"],
                        "Kvartalsdata"
                    ))

                if mode == "all_financial":
                    topic_clicks.append((
                        None,
                        ["label:has-text('Foreløpig regnskap')",
                        "label:has-text('Preliminary financial')"],
                        "Foreløpig regnskap"
                    ))
                    topic_clicks.append((
                        None,
                        ["label:has-text('Kapitalmarkedsdager')",
                        "label:has-text('Capital markets day')"],
                        "Kapitalmarkedsdag"
                    ))

                for primary_xp, fallback_sels, label in topic_clicks:
                    sl.step(f"Velger '{label}' i Topic-filteret")
                    clicked = False
                    if primary_xp:
                        clicked = await click_xpath(page, primary_xp, f"{label}-label", timeout=6_000)
                    if not clicked:
                        clicked = await click_any(page, fallback_sels, f"{label} fallback")
                    if clicked:
                        await page.wait_for_timeout(500)
                        sl.ok(f"'{label}' valgt")
                    else:
                        sl.warn(f"'{label}' ikke funnet")
                    await page.wait_for_timeout(config.step_delay_ms)

                # ── STEG 8: Trykk Apply ──
                sl.step("Trykker Apply for å aktivere filter")
                clicked = await click_xpath(page, XP["APPLY"], "Apply-knapp", timeout=8_000, scroll=True)
                if not clicked:
                    clicked = await click_any(
                        page,
                        ["input[type='submit'][value*='Apply' i]",
                        "input[type='submit'][value*='Bruk' i]",
                        "button:has-text('Apply')",
                        "button:has-text('Bruk')",
                        ".views-exposed-form input[type='submit']"],
                        "Apply fallback"
                    )
                if clicked:
                    try:
                        await page.wait_for_load_state("networkidle", timeout=10_000)
                    except Exception:
                        pass
                    await page.wait_for_timeout(2_000)
                    sl.ok("Filter aktivert")
                else:
                    sl.warn("Apply ikke funnet")
                await page.wait_for_timeout(config.step_delay_ms)
            else:
                sl.info(f"Topic-filter mode='everything' — hopper over filter-steg")

            await safe_screenshot(
                page,
                config.screenshot_dir / f"after_filter_{safe}.png",
                f"Etter filter: {company_name}"
            )

            # ── Lagre URL til artikkelliste (side 1) for tilbake-navigering ──
            article_list_url = page.url

            # ══════════════════════════════════════════════════════════════════════════
            # STEG 9  — Hent artikkelrader fra ALLE sider (paginering)
            # ══════════════════════════════════════════════════════════════════════════
            sl.step(f"Henter artikkelliste fra tabellen (paginering, maks {config.max_pages} sider)")

            row_data = await collect_all_article_rows(page, config, sl)

            if row_data:
                sl.ok(f"Fant {len(row_data)} artikler totalt")
                for i, r in enumerate(row_data[:3], 1):
                    sl.info(f"  [{i}] {r['title'][:65]}  ({r.get('date', '')})")
                if len(row_data) > 3:
                    sl.info(f"  ... og {len(row_data)-3} til")
            else:
                sl.fail("Ingen artikler funnet")
                await safe_screenshot(
                    page,
                    config.screenshot_dir / f"no_articles_{safe}.png",
                    f"Ingen artikler: {company_name}"
                )
                return articles
            await page.wait_for_timeout(config.step_delay_ms)

            # ══════════════════════════════════════════════════════════════════════════
            # STEG 10  — Hent tekst fra hver artikkel
            # ══════════════════════════════════════════════════════════════════════════
            # Etter paginering kan vi være på side N. Naviger tilbake til side 1
            # før vi henter modal-tekst, så lenker fremdeles finnes i DOM.
            try:
                await page.goto(article_list_url, wait_until="networkidle", timeout=config.page_timeout)
                await page.wait_for_timeout(1_500)
            except Exception:
                pass

            sl.step(f"Henter tekst fra {len(row_data)} artikler")

            for i, row in enumerate(row_data, 1):
                nid  = row.get("nid", "")
                href = row.get("href", "")
                url  = href if href else ""
                if url.startswith("/"):
                    url = config.euronext_base + url

                art = Article(
                    company=company_name,
                    title=row["title"],
                    url=url or f"modal://{nid}",
                    date=row.get("date", ""),
                )
                sl.info(f"[{i}/{len(row_data)}] {art.title[:60]}...")

                if nid and (not href or href == ""):
                    # Modal-artikkel: klikk og hent tekst fra popup
                    # Hvis modalen ikke ligger i nåværende side-DOM (vi var på side 3),
                    # må vi navigere til siden hvor den ligger. Forsøk først direkte —
                    # hvis det feiler, søk på andre sider.
                    art.text = await fetch_modal_text(page, nid, config)
                    if not art.text or len(art.text) < 100:
                        # Modal-lenke ikke funnet i DOM — prøv å paginere for å finne den
                        found_on_page = await _find_nid_via_pagination(
                            page, nid, config, sl, article_list_url
                        )
                        if found_on_page:
                            art.text = await fetch_modal_text(page, nid, config)
                        # Etter denne dansen er vi ikke nødvendigvis på side 1 igjen.
                        # Naviger tilbake for konsistens før neste artikkel.
                        try:
                            await page.goto(article_list_url, wait_until="networkidle",
                                        timeout=config.page_timeout)
                            await page.wait_for_timeout(1_000)
                        except Exception:
                            pass
                else:
                    # Vanlig lenke: naviger til siden, deretter tilbake
                    art.text = await fetch_article_text(page, art, config,
                                                        return_url=article_list_url)

                n_chars = len(art.text)
                if n_chars > 100:
                    sl.info(f"  → ✅ {n_chars} tegn hentet")
                else:
                    sl.warn(f"  → kun {n_chars} tegn")

                articles.append(art)
                await page.wait_for_timeout(int(config.request_delay * 1_000))

            sl.ok(f"{len(articles)} artikler hentet for {company_name}")
            await page.wait_for_timeout(config.step_delay_ms)

            # Naviger tilbake til forsiden for neste selskap
            try:
                await page.goto(config.start_url, wait_until="networkidle", timeout=config.page_timeout)
                await page.wait_for_timeout(1_500)
            except Exception:
                pass

            return articles


        async def _find_nid_via_pagination(page, nid: str, config: Config,
                                            sl: StepLogger, list_url: str) -> bool:
            """
            Hvis modal-lenken for `nid` ikke ligger i nåværende DOM, walker vi gjennom
            sidene til vi finner den. Returnerer True hvis funnet og DOM nå inneholder den.
            """
            # Start fra side 1
            try:
                await page.goto(list_url, wait_until="networkidle", timeout=config.page_timeout)
                await page.wait_for_timeout(1_000)
            except Exception:
                return False

            for page_num in range(1, config.max_pages + 1):
                exists = await page.evaluate(
                    """(nid) => !!document.querySelector(
                        'a.standardRightCompanyPressRelease[data-node-nid="' + nid + '"]'
                    )""",
                    nid
                )
                if exists:
                    sl.info(f"  Fant nid={nid} på side {page_num}")
                    return True

                clicked = await _click_next_page(page, sl)
                if not clicked:
                    return False
                try:
                    await page.wait_for_load_state("networkidle", timeout=10_000)
                except Exception:
                    pass
                await page.wait_for_timeout(1_200)

            return False


        # ─────────────────────────────────────────────────────────────────────────────
        # FINBERT
        # ─────────────────────────────────────────────────────────────────────────────

        class SentimentAnalyzer:
            def __init__(self, config: Config):
                self.config = config
                self.pipe   = None
                self._load()

            def _load(self):
                try:
                    from transformers import (BertTokenizer,
                                            BertForSequenceClassification,
                                            pipeline)
                    import torch
                    log.info(f"Laster FinBERT: {self.config.finbert_model}")
                    tok   = BertTokenizer.from_pretrained(self.config.finbert_model)
                    model = BertForSequenceClassification.from_pretrained(self.config.finbert_model)
                    dev   = "cuda" if torch.cuda.is_available() else "cpu"
                    self.pipe = pipeline("sentiment-analysis", model=model, tokenizer=tok, device=dev)
                    log.info(f"FinBERT klar på {dev}")
                except Exception as e:
                    log.error(f"FinBERT-lasting feilet: {e}")

            def analyze(self, text: str) -> dict:
                default = {"positive": 0.33, "neutral": 0.34, "negative": 0.33}
                if not self.pipe or not text or len(text) < 50:
                    raise RuntimeError("Article text/model unavailable; no sentiment score was produced")
                try:
                    import nltk
                    try:
                        from nltk.tokenize import sent_tokenize
                    except LookupError:
                        nltk.download("punkt",     quiet=True)
                        nltk.download("punkt_tab", quiet=True)
                        from nltk.tokenize import sent_tokenize

                    sents  = sent_tokenize(text)[:self.config.max_sentences]
                    scores = {"positive": 0.0, "negative": 0.0, "neutral": 0.0}
                    n = 0
                    for i in range(0, len(sents), 16):
                        batch = sents[i:i+16]
                        try:
                            for r in self.pipe(batch, truncation=True, max_length=512):
                                lbl = r["label"].lower()
                                if lbl in scores:
                                    scores[lbl] += r["score"]
                                    n += 1
                        except Exception:
                            for s in batch:
                                try:
                                    r = self.pipe(s, truncation=True, max_length=512)[0]
                                    lbl = r["label"].lower()
                                    if lbl in scores:
                                        scores[lbl] += r["score"]
                                        n += 1
                                except Exception as exc:
                                    raise RuntimeError("FinBERT sentence scoring failed") from exc
                    if not n:
                        raise RuntimeError("FinBERT returned no recognised scores")
                    return {k: v / n for k, v in scores.items()}
                except Exception as e:
                    raise RuntimeError("Sentiment scoring failed") from e


        # ─────────────────────────────────────────────────────────────────────────────
        # LAGRE RESULTATER
        # ─────────────────────────────────────────────────────────────────────────────

        def save_results(all_results: List[dict], config: Config, today: str, final: bool = False):
            if not all_results:
                return
            df = pd.DataFrame(all_results)
            keys = [k for k in ("Company", "Article_Date", "Article_Title") if k in df.columns]
            if keys:
                df = df.drop_duplicates(subset=keys, keep="last")
            suffix = "_FINAL" if final else f"_{int(time.time())}"

            detail_path = config.nlp_dir / f"NLP_Sentiment_Detail_{today}{suffix}.xlsx"
            try:
                df.to_excel(detail_path, index=False)
                print(f"  💾 Detaljer lagret: {detail_path}")
            except PermissionError:
                alt = config.nlp_dir / f"NLP_Sentiment_Detail_{today}_{int(time.time())}.xlsx"
                df.to_excel(alt, index=False)
                print(f"  💾 Detaljer lagret (alt): {alt}")

            if not df.empty:
                summary = df.groupby("Company").agg(
                    Positive_Score=("Positive_Score", "mean"),
                    Neutral_Score =("Neutral_Score",  "mean"),
                    Negative_Score=("Negative_Score", "mean"),
                    Final_Score   =("Final_Score",    "mean"),
                    Article_Count =("Article_Title",  "count"),
                ).reset_index()
                summary_path = config.nlp_dir / f"Reshaped_Sentiment_Data_{today}{suffix}.xlsx"
                try:
                    summary.to_excel(summary_path, index=False)
                    print(f"  💾 Sammendrag lagret: {summary_path}")
                except Exception as e:
                    log.error(f"Sammendrag-lagring feilet: {e}")
            return df


        # ─────────────────────────────────────────────────────────────────────────────
        # CHECKPOINT
        # ─────────────────────────────────────────────────────────────────────────────

        def append_checkpoint(result: dict, config: Config, today: str):
            cp = config.work_dir / f"checkpoint_{today}.csv"
            pd.DataFrame([result]).to_csv(cp, mode="a", header=not cp.exists(), index=False)


        def load_checkpoint(config: Config, today: str) -> set:
            # Only a fully processed company is resumable; one saved article is not completion.
            marker = config.work_dir / f"completed_{today}.json"
            if marker.exists():
                try:
                    return set(json.loads(marker.read_text(encoding="utf-8")))
                except (OSError, ValueError):
                    pass
            return set()

        def mark_company_complete(company, config, today):
            complete = load_checkpoint(config, today)
            complete.add(company)
            marker = config.work_dir / f"completed_{today}.json"
            temporary = marker.with_suffix(".tmp")
            temporary.write_text(json.dumps(sorted(complete)), encoding="utf-8")
            temporary.replace(marker)

        def clear_checkpoint(config: Config, today: str):
            cp = config.work_dir / f"checkpoint_{today}.csv"
            marker = config.work_dir / f"completed_{today}.json"
            if marker.exists():
                marker.unlink()
            if cp.exists():
                cp.unlink()
                print(f"   🗑️  Checkpoint slettet: {cp}")


        # ─────────────────────────────────────────────────────────────────────────────
        # MAIN
        # ─────────────────────────────────────────────────────────────────────────────

        async def main():
            print("=" * 80)
            print("  EURONEXT OSLO BØRS — PLAYWRIGHT SCRAPER + FINBERT NLP  (v4 — DEEP)")
            print("=" * 80)

            config = Config()
            today  = datetime.now().strftime("%Y-%m-%d")

            # STEG A: Last selskaper
            print(f"\n📋 STEG A: Laster selskaper fra Excel...")
            companies = load_companies(config)
            record_source("articles", status="FAILED", detail="Article collection started; not yet validated",
                          network_attempted=False, expected_count=len(companies))
            if not companies:
                raise RuntimeError("No companies available for the management scraper")
            print(f"   ✅ STEG A FERDIG: {len(companies)} selskaper lastet")
            for i, c in enumerate(companies[:5], 1):
                print(f"      [{i}] {c}")
            if len(companies) > 5:
                print(f"      ... og {len(companies)-5} til")

            # STEG B: Last FinBERT
            print(f"\n🧠 STEG B: Laster FinBERT-modell...")
            analyzer = SentimentAnalyzer(config)
            if analyzer.pipe:
                print(f"   ✅ STEG B FERDIG: FinBERT klar")
            else:
                raise RuntimeError("FinBERT model unavailable; default sentiment scores are not valid data")

            # STEG C: Checkpoint
            print(f"\n📂 STEG C: Sjekker checkpoint...")
            if config.force_rerun:
                print(f"   ⚡ force_rerun=True → sletter gammel checkpoint for i dag")
                clear_checkpoint(config, today)
                done      = set()
                remaining = companies[:]
                all_results: List[dict] = []
            else:
                done      = load_checkpoint(config, today)
                remaining = [c for c in companies if c not in done]
                all_results: List[dict] = []
                cp_path = config.work_dir / f"checkpoint_{today}.csv"
                if cp_path.exists():
                    try:
                        all_results = pd.read_csv(cp_path).to_dict("records")
                        print(f"   Lastet {len(all_results)} rader fra checkpoint")
                    except Exception:
                        pass

            if done:
                print(f"   ⏭  Hopper over {len(done)} allerede behandlede")
            print(f"   ✅ STEG C FERDIG: {len(remaining)} selskaper gjenstår")

            if len(remaining) == 0:
                record_source("articles", status="CACHED", detail="Same-day checkpoint reused; no source fetched",
                              network_attempted=False, expected_count=len(companies),
                              cached_count=len(done), usable_count=len(all_results))
                print(f"\n   ⚠️  Ingen selskaper å behandle!")
                print(f"   Tips: Sett config.force_rerun = True for å kjøre på nytt,")
                print(f"         eller slett checkpoint-filen manuelt:")
                print(f"         {config.work_dir / f'checkpoint_{today}.csv'}")
                return

            record_source("articles", status="FAILED", detail="Fetching announcement pages",
                          network_attempted=True, expected_count=len(companies), cached_count=len(done))
            # STEG D: Start Playwright
            print(f"\n🌐 STEG D: Starter nettleserskraping...")
            print(f"   Synlig nettleser:        {not config.headless}")
            print(f"   Slow-mo:                 {config.slow_mo} ms")
            print(f"   Stegforsinkelse:         {config.step_delay_ms} ms")
            print(f"   Modal-klikk timeout:     {config.modal_click_timeout} ms")
            print(f"   Søkevarianter:           {config.search_retry_variants}")
            print(f"   Topic-filter mode:       {config.topic_filter_mode}")
            print(f"   Max artikler/selskap:    {config.max_articles_per_company}")
            print(f"   Max paginering-sider:    {config.max_pages}")
            print(f"   Selskaper å scrape:      {len(remaining)}")

            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=config.headless,
                    slow_mo=config.slow_mo,
                )
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    ),
                )
                page = await context.new_page()
                print(f"   ✅ STEG D FERDIG: Nettleser startet")

                total = len(remaining)
                failed_companies = []
                for idx, company in enumerate(remaining):
                    is_first  = (idx == 0)
                    comp_num  = idx + 1

                    print(f"\n{'▓'*70}")
                    print(f"  SELSKAP {comp_num}/{total}: {company}")
                    print(f"{'▓'*70}")

                    try:
                        articles = await scrape_company(page, company, config, is_first)
                    except Exception as e:
                        log.error(f"Kritisk feil for {company}: {e}")
                        articles = []
                        try:
                            await page.goto(config.start_url, wait_until="networkidle",
                                        timeout=config.page_timeout)
                            await page.wait_for_timeout(1_500)
                        except Exception:
                            pass

                    if not articles:
                        # A loaded page with no parsed articles may be a failed navigation.
                        body = (await page.locator("body").inner_text()).lower()
                        verified_empty = any(t in body for t in ("no results found", "ingen resultater", "ingen treff"))
                        if not verified_empty:
                            for retry in range(2):
                                await page.wait_for_timeout(3000 * (retry + 1))
                                try:
                                    articles = await scrape_company(page, company, config, False)
                                except Exception:
                                    articles = []
                                if articles:
                                    break
                            if not articles:
                                failed_companies.append(company)
                                log.error("Management download incomplete for %s; checkpoint not advanced", company)
                                continue
                    if not articles:
                        print(f"  ⚠️ Ingen artikler funnet for {company}")
                        rec = {
                            "Company": company, "Article_Title": "INGEN ARTIKLER",
                            "Article_Date": "", "Article_URL": "", "PDF_URL": "",
                            "Positive_Score": 0.0, "Neutral_Score": 1.0,
                            "Negative_Score": 0.0, "Final_Score": 0.0,
                            "Text_Length": 0, "PDF_Used": False, "Scrape_Date": today,
                        }
                        all_results.append(rec)
                        append_checkpoint(rec, config, today)
                        continue

                    print(f"\n  🧠 FinBERT-analyse på {len(articles)} artikler for {company}...")
                    for ai, art in enumerate(articles, 1):
                        sent  = analyzer.analyze(art.text)
                        final = sent["positive"] - sent["negative"]
                        rec   = {
                            "Company":        company,
                            "Article_Title":  art.title,
                            "Article_Date":   art.date,
                            "Article_URL":    art.url,
                            "PDF_URL":        art.pdf_url,
                            "Positive_Score": round(sent["positive"], 4),
                            "Neutral_Score":  round(sent["neutral"],  4),
                            "Negative_Score": round(sent["negative"], 4),
                            "Final_Score":    round(final, 4),
                            "Text_Length":    len(art.text),
                            "PDF_Used":       bool(art.pdf_url),
                            "Scrape_Date":    today,
                        }
                        all_results.append(rec)
                        append_checkpoint(rec, config, today)
                        print(
                            f"    [{ai}/{len(articles)}] {art.title[:50]}... "
                            f"→ +{sent['positive']:.3f} ={sent['neutral']:.3f} -{sent['negative']:.3f} "
                            f"⟹ {final:+.4f}"
                        )

                        safe_c = _safe_name(company, 40)
                        safe_t = _safe_name(art.title, 30)
                        txt_p  = config.work_dir / f"{safe_c}_{safe_t}_{today}.txt"
                        try:
                            txt_p.write_text(art.text[:50_000], encoding="utf-8")
                        except Exception:
                            pass

                    mark_company_complete(company, config, today)
                    print(f"  ✅ FinBERT ferdig for {company}")

                    if comp_num % 5 == 0:
                        print(f"\n  💾 Mellomlagrer etter {comp_num} selskaper...")
                        save_results(all_results, config, today, final=False)

                await browser.close()
                print("\n  ✅ Nettleser lukket")

            # STEG E: Lagre endelig
            print(f"\n{'='*80}")
            print("✅ STEG E: SCRAPING FERDIG — LAGRER ENDELIGE RESULTATER")
            print(f"{'='*80}")
            save_results(all_results, config, today, final=not failed_companies)
            record_source("articles", status=("PARTIAL" if failed_companies or done else "DOWNLOADED"),
                          detail="Management announcement pages and FinBERT results processed",
                          network_attempted=True, expected_count=len(companies),
                          usable_count=len(companies) - len(failed_companies),
                          downloaded_count=len(remaining) - len(failed_companies), cached_count=len(done),
                          issues=sorted(failed_companies))
            if failed_companies:
                raise RuntimeError("Management download incomplete: " + ", ".join(failed_companies))

            comps_with_data = len({r["Company"] for r in all_results if r["Text_Length"] > 0})
            arts_total      = sum(1 for r in all_results if r["Text_Length"] > 0)
            pdfs_used       = sum(1 for r in all_results if r.get("PDF_Used"))

            print(f"\n  Selskaper i Excel:       {len(companies)}")
            print(f"  Selskaper behandlet:     {total}")
            print(f"  Selskaper med data:      {comps_with_data}")
            print(f"  Artikler analysert:      {arts_total}")
            print(f"  Artikler via PDF:        {pdfs_used}")
            print(f"  Resultater:              {config.nlp_dir}")
            print(f"  Working data:            {config.work_dir}")
            print(f"  Screenshots:             {config.screenshot_dir}")


        if __name__ == "__main__":
            asyncio.run(main())
    # Kalles fra dispatchen nederst når HENT_NYE_ARTIKLER er på.

    #New untestet
    def NlpSentimentTrader4_v41():
        import os
        os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

        import sys
        import re
        import time
        import logging
        import warnings
        from dataclasses import dataclass
        from datetime import datetime, timedelta
        from pathlib import Path
        from typing import Dict, List, Set, Tuple, Optional

        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        import matplotlib.ticker as mticker
        import numpy as np
        import pandas as pd
        import yfinance as yf

        warnings.filterwarnings("ignore")

        # ─────────────────────────────────────────────────────────────────────────────
        # CONFIG
        # ─────────────────────────────────────────────────────────────────────────────

        @dataclass
        class Config:
            # ── Paths ──
            base_dir: Path = Path(r"C:\Users\ander\Desktop\Python_K4\ExcelData")
            nlp_output_dir: str = "DataNLP"
            working_data_dir: str = r"DataNLP\WorkingData"   # FIX 3: where article bodies live
            tickers_file: str = r"Data_BT\AllTickers_OSEBX_TW_current.xlsx"
            output_dir: str = "StrategyResults_v4_Sentiment"

            # ── Portfolio ──
            startkapital: float = 1_000_000
            n_portfolio: int = 5
            transaction_cost: float = 0.0000

            # ── Sentiment scoring ──
            decay_factor: float = 0.98
            max_signal_age_days: int = 365
            short_window_days: int = 45
            min_score_threshold: float = 0.05

            # ── FIX 1: Signal lag (trading days) ──
            # News on day T can only drive trades on day T+signal_lag_days.
            # 1 = next trading day. Set to 0 to disable.
            signal_lag_days: int = 1

            # ── FIX 2: Minimum hold + asymmetric exit ──
            # Hold a position for at least this many rebalance cycles (months),
            # unless its current sentiment delta turns negative.
            min_hold_months: int = 3
            # If a held name's CURRENT delta is below this, sell regardless of min_hold.
            # Set to -0.05 to be tolerant of small dips, 0.0 for strict.
            exit_delta_threshold: float = 0.0

            # ── Trend filter ──
            sma_days: int = 50   # NB: restored to 50 — 15 is just noise

            # ── FIX 3: Body-level language filter ──
            filter_norwegian: bool = True
            body_language_filter: bool = True   # if True, use langdetect on body text

            # ── Benchmark ──
            benchmark_ticker: str = "OSEBX.OL"
            oslo_suffix: str = ".OL"

            # ── Time period ──
            start_date: str = "2020-01-01"
            end_date: str = ""

            @property
            def nlp_dir(self) -> Path:
                return self.base_dir / self.nlp_output_dir

            @property
            def work_dir(self) -> Path:
                return self.base_dir / self.working_data_dir

            @property
            def tickers_path(self) -> Path:
                return self.base_dir / self.tickers_file

            @property
            def results_dir(self) -> Path:
                p = self.base_dir / self.output_dir
                p.mkdir(parents=True, exist_ok=True)
                return p

        # ─────────────────────────────────────────────────────────────────────────────
        # LOGGING
        # ─────────────────────────────────────────────────────────────────────────────

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s  %(levelname)-8s  %(message)s",
            datefmt="%H:%M:%S",
        )
        log = logging.getLogger("SentimentV4")
        TODAY_STR = datetime.now().strftime("%Y-%m-%d")

        # ─────────────────────────────────────────────────────────────────────────────
        # HELPERS
        # ─────────────────────────────────────────────────────────────────────────────

        NORSK_ORD = {
            'og', 'har', 'til', 'fra', 'ved', 'er', 'på', 'det', 'den',
            'rapport', 'resultat', 'kvartal', 'vekst', 'drevet',
            'selskap', 'aksje', 'utbytte', 'halvår', 'årsrapport',
            'solide', 'sterke', 'høy', 'godt', 'gode', 'alle',
            'kundeaktivitet', 'utlånsvekst', 'videre', 'norsk',
            'resultater', 'publisert', 'kvartalet', 'første',
        }

        def is_norwegian_title(title: str) -> bool:
            if pd.isna(title):
                return False
            words = str(title).lower().split()
            return len(NORSK_ORD.intersection(words)) >= 2

        # ── FIX 3: body-level language detection ──
        def _safe_name(text: str, max_len: int = 30) -> str:
            return re.sub(r'[^\w]', '_', text)[:max_len]

        def detect_body_language(company: str, title: str, work_dir: Path,
                                scrape_date: str) -> Optional[str]:
            """
            Look up the article body .txt file written by the scraper and
            run langdetect on it. Returns 2-letter code or None.

            Scraper writes to: {work_dir}/{safe_company}_{safe_title}_{date}.txt
            """
            try:
                from langdetect import detect, DetectorFactory
                DetectorFactory.seed = 0   # deterministic
            except ImportError:
                return None

            safe_c = _safe_name(str(company), 40)
            safe_t = _safe_name(str(title), 30)

            # The scrape date in the filename is the date the scraper ran,
            # NOT the article date — so we glob for any matching txt.
            candidates = list(work_dir.glob(f"{safe_c}_{safe_t}_*.txt"))
            if not candidates:
                return None

            # Pick the most recent file if multiple
            path = max(candidates, key=lambda p: p.stat().st_mtime)
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")[:4000]
                if len(text) < 100:
                    return None
                return detect(text)
            except Exception:
                return None

        def price_at(prices, ticker, dt):
            if ticker not in prices.columns:
                return None
            p = prices[ticker].dropna()
            p = p[p.index <= dt]
            return float(p.iloc[-1]) if not p.empty else None

        def check_sma(daily_prices, ticker, as_of_date, sma_days):
            if ticker not in daily_prices.columns:
                return False
            p = daily_prices[ticker].dropna()
            p = p[p.index <= as_of_date]
            if len(p) < sma_days:
                return False
            return float(p.iloc[-1]) > float(p.iloc[-sma_days:].mean())

        # ─────────────────────────────────────────────────────────────────────────────
        # DATA LOADING
        # ─────────────────────────────────────────────────────────────────────────────

        def load_sentiment_articles(config: Config) -> pd.DataFrame:
            """
            ALLE artikkelfilene i DataNLP, slått sammen og avduplisert.

            Før leste denne bare files[0] — den nyeste filen. Hver skraping
            skriver en ny fil, så alt som var hentet tidligere ble kastet ved
            neste kjøring. Det er den dyreste dataen i hele prosjektet: timer
            med skraping og språkmodell, hentet én gang og så oversett. Med ti
            artikler per selskap per fil rakk historikken noen måneder, og
            backtesten ble kort av en grunn som ikke sto noe sted.

            Nøkkelen for duplikater er selskap + dato + tittel. Samme artikkel
            i to filer er én artikkel; er den scoret på nytt i en senere
            kjøring, vinner den nyeste filen.
            """
            nlp_dir = config.nlp_dir
            filer = sorted(p for p in nlp_dir.glob("NLP_Sentiment_Detail_*.xlsx")
                           if not p.name.startswith("~$"))
            if not filer:
                raise FileNotFoundError(f"No sentiment files in {nlp_dir}")

            deler = []
            for f in filer:
                try:
                    d = pd.read_excel(f)
                except Exception as e:
                    log.warning("  Hoppet over %s: %s", f.name, e)
                    continue
                if d.empty or "Article_Date" not in d.columns:
                    log.warning("  Hoppet over %s: ingen Article_Date-kolonne", f.name)
                    continue
                d["_fil"] = f.name
                deler.append(d)
                log.info("  %-52s %5d rader", f.name, len(d))
            if not deler:
                raise FileNotFoundError(
                    f"Fant {len(filer)} fil(er) i {nlp_dir}, men ingen av dem "
                    f"kunne leses som artikler.")

            df = pd.concat(deler, ignore_index=True)
            if len(filer) > 1:
                log.info("  %d filer slått sammen → %d rader før avduplisering",
                         len(deler), len(df))

            df["Article_Date"] = (
                df["Article_Date"].astype(str)
                .str.replace(r'\n.*$', '', regex=True)
                .str.strip()
            )
            df["Article_Date"] = pd.to_datetime(df["Article_Date"], format="%d %b %Y", errors="coerce")

            df = df[df["Text_Length"] > 0].copy()
            df = df.dropna(subset=["Article_Date"])

            # Avdupliser på selskap + dato + tittel. Den nyeste filen vinner,
            # så en artikkel som er scoret om igjen får sin ferskeste score.
            nokler = [k for k in ("Company", "Article_Date", "Article_Title")
                      if k in df.columns]
            if nokler and len(filer) > 1:
                for_ = len(df)
                df = (df.sort_values("_fil")
                        .drop_duplicates(subset=nokler, keep="last")
                        .reset_index(drop=True))
                if for_ != len(df):
                    log.info("  Avduplisert: %d → %d rader (%d gjengangere)",
                             for_, len(df), for_ - len(df))
            df = df.drop(columns=[c for c in ("_fil",) if c in df.columns])

            log.info("Loaded %d artikler fra %d fil(er), %d selskaper",
                     len(df), len(deler), df["Company"].nunique())

            # ── FIX 3a: title-based Norwegian filter (fast, catches obvious cases) ──
            if config.filter_norwegian:
                before = len(df)
                df["_is_norsk_title"] = df["Article_Title"].apply(is_norwegian_title)
                df = df[~df["_is_norsk_title"]].drop(columns=["_is_norsk_title"])
                log.info("Title filter: %d → %d (removed %d obvious Norwegian titles)",
                        before, len(df), before - len(df))

            # ── FIX 3b: body-based language filter (slower, much more accurate) ──
            if config.body_language_filter:
                try:
                    from langdetect import detect  # noqa: F401
                    has_langdetect = True
                except ImportError:
                    log.warning("langdetect not installed — pip install langdetect to enable "
                                "body-level language filter. Skipping body filter.")
                    has_langdetect = False

                if has_langdetect and config.work_dir.exists():
                    before = len(df)
                    # Cache lookups by (company, title) to avoid re-detecting duplicates
                    lang_cache: Dict[Tuple[str, str], Optional[str]] = {}

                    def _get_lang(row):
                        key = (str(row["Company"]), str(row["Article_Title"]))
                        if key in lang_cache:
                            return lang_cache[key]
                        lang = detect_body_language(
                            row["Company"], row["Article_Title"],
                            config.work_dir, str(row.get("Scrape_Date", ""))
                        )
                        lang_cache[key] = lang
                        return lang

                    df["_body_lang"] = df.apply(_get_lang, axis=1)
                    # Keep English; also keep unknown (None) — we don't want to silently
                    # drop articles where the .txt file is missing.
                    df = df[(df["_body_lang"] == "en") | (df["_body_lang"].isna())].copy()
                    df = df.drop(columns=["_body_lang"])
                    log.info("Body language filter: %d → %d (removed %d non-English bodies)",
                            before, len(df), before - len(df))
                elif has_langdetect and not config.work_dir.exists():
                    log.warning("Working data dir %s does not exist — body filter skipped",
                                config.work_dir)

            log.info("Date range: %s → %s", df["Article_Date"].min().date(),
                    df["Article_Date"].max().date())
            return df

        def build_ticker_map(config: Config, articles_df: pd.DataFrame) -> Dict[str, str]:
            mapping = {}
            for company in articles_df["Company"].unique():
                code = str(company).strip()
                if code and code != "nan":
                    mapping[code] = code + config.oslo_suffix
            log.info("Ticker map: %d companies → yfinance", len(mapping))
            return mapping

        def download_prices(tickers: List[str], benchmark: str,
                            start: str, end: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
            yf_tickers = list(set(tickers + [benchmark]))
            log.info("Downloading prices for %d tickers...", len(yf_tickers))

            data = yf.download(yf_tickers, start=start, end=end or None,
                            auto_adjust=True, progress=True)

            if data.empty:
                return pd.DataFrame(), pd.DataFrame()

            if isinstance(data.columns, pd.MultiIndex):
                daily = data["Close"].copy()
            else:
                daily = data[["Close"]].copy()
                daily.columns = yf_tickers[:1]

            daily.index = pd.to_datetime(daily.index)
            daily.sort_index(inplace=True)

            stocks = daily.drop(columns=[benchmark], errors="ignore")
            valid = stocks.columns[stocks.count() >= 60]
            stocks = stocks[valid]

            monthly = daily.resample("ME").last()
            monthly.sort_index(inplace=True)

            log.info("Daily: %d days | Monthly: %d months | Stocks: %d",
                    len(daily), len(monthly), len(stocks.columns))
            return daily, monthly

        # ─────────────────────────────────────────────────────────────────────────────
        # SENTIMENT SCORER  (with FIX 1: signal lag)
        # ─────────────────────────────────────────────────────────────────────────────

        def score_sentiment_at(articles_df: pd.DataFrame, ticker_map: Dict[str, str],
                            rebal_date: pd.Timestamp, config: Config,
                            available_tickers: Set[str]) -> pd.DataFrame:
            """
            Score sentiment as the DELTA between recent and trailing baseline.

            FIX 1: We only consider articles whose date is ≤ (rebal_date - signal_lag).
            This prevents "trading on news that broke the same day as rebalance".
            """
            # ── FIX 1: enforce signal lag ──
            # Use business days so weekends don't shift the cutoff weirdly.
            if config.signal_lag_days > 0:
                effective_date = rebal_date - pd.tseries.offsets.BDay(config.signal_lag_days)
            else:
                effective_date = rebal_date

            short_window_days = getattr(config, "short_window_days", 45)
            long_cutoff  = effective_date - timedelta(days=config.max_signal_age_days)
            short_cutoff = effective_date - timedelta(days=short_window_days)

            # Only articles published on or before the effective (lagged) date
            long_window = articles_df[
                (articles_df["Article_Date"] <= effective_date) &
                (articles_df["Article_Date"] >= long_cutoff)
            ]
            if long_window.empty:
                return pd.DataFrame()

            signals = []
            for company in long_window["Company"].unique():
                ticker = ticker_map.get(company)
                if not ticker or ticker not in available_tickers:
                    continue

                arts = long_window[long_window["Company"] == company]

                long_scores  = []
                short_scores = []
                latest_date  = None
                n_short_raw  = 0

                for _, art in arts.iterrows():
                    art_date = art["Article_Date"]
                    # ── FIX 1: days_old measured from effective_date, not rebal_date ──
                    days_old = (effective_date - art_date).days
                    if days_old < 0:
                        continue
                    score   = float(art["Final_Score"])
                    decayed = score * (config.decay_factor ** days_old)

                    if abs(decayed) < 0.001:
                        continue

                    long_scores.append(decayed)
                    if latest_date is None or art_date > latest_date:
                        latest_date = art_date

                    if art_date >= short_cutoff:
                        short_scores.append(decayed)
                        n_short_raw += 1

                if not long_scores or not short_scores:
                    continue

                long_avg  = float(np.mean(long_scores))
                short_avg = float(np.mean(short_scores))
                delta     = short_avg - long_avg

                if n_short_raw < 1:
                    continue

                # Keep ALL companies with a measurable delta (positive or negative).
                # The min_score_threshold filter for BUYING happens in select_portfolio.
                # We need the negatives too so the exit logic can see them.
                signals.append({
                    "Company":         company,
                    "Ticker":          ticker,
                    "Sentiment_Score": round(delta, 4),
                    "Short_Avg":       round(short_avg, 4),
                    "Long_Avg":        round(long_avg, 4),
                    "N_Articles":      len(long_scores),
                    "N_Recent":        n_short_raw,
                    "Latest_Date":     latest_date,
                })

            if not signals:
                return pd.DataFrame()

            df = pd.DataFrame(signals)
            df.sort_values("Sentiment_Score", ascending=False, inplace=True)
            df.reset_index(drop=True, inplace=True)
            return df

        # ─────────────────────────────────────────────────────────────────────────────
        # STOCK SELECTION
        # ─────────────────────────────────────────────────────────────────────────────

        def select_eligible_buys(sentiment_df: pd.DataFrame, daily_prices: pd.DataFrame,
                                rebal_date: pd.Timestamp,
                                config: Config) -> pd.DataFrame:
            """
            Stocks eligible to BUY this month: positive delta above threshold AND above SMA.
            Returns sorted DataFrame (highest score first).
            """
            if sentiment_df.empty:
                return pd.DataFrame()

            df = sentiment_df.copy()
            # Threshold for new buys
            df = df[df["Sentiment_Score"] >= config.min_score_threshold]
            if df.empty:
                return pd.DataFrame()

            df["Above_SMA"] = df["Ticker"].apply(
                lambda t: check_sma(daily_prices, t, rebal_date, config.sma_days)
            )
            df = df[df["Above_SMA"]].copy()
            return df

        # ─────────────────────────────────────────────────────────────────────────────
        # MAIN
        # ─────────────────────────────────────────────────────────────────────────────

        config = Config()

        log.info("=" * 70)
        log.info("  SENTIMENT STRATEGY v4.1 — w/ signal lag, min-hold, body lang")
        log.info("  Top %d | SMA%d | Decay %.0f%%/day | Lag %d bdays | MinHold %d mo",
                config.n_portfolio, config.sma_days,
                (1 - config.decay_factor) * 100,
                config.signal_lag_days, config.min_hold_months)
        log.info("=" * 70)

        # Step 1
        log.info("\n📊 STEP 1: Loading sentiment data...")
        articles = load_sentiment_articles(config)
        if articles.empty:
            log.error("No articles loaded!")
            return

        # Step 2
        log.info("\n🏷️  STEP 2: Building mappings...")
        ticker_map = build_ticker_map(config, articles)

        # Step 3
        log.info("\n📈 STEP 3: Downloading prices...")
        all_tickers = list(set(ticker_map.values()))
        end_date = config.end_date or datetime.now().strftime("%Y-%m-%d")
        daily, monthly = download_prices(
            all_tickers, config.benchmark_ticker, config.start_date, end_date
        )

        if daily.empty or monthly.empty:
            log.error("No price data!")
            return

        bn = pd.Series(dtype=float)
        if config.benchmark_ticker in monthly.columns:
            b = monthly[config.benchmark_ticker].dropna()
            if not b.empty:
                bn = (b / b.iloc[0]) * config.startkapital

        # Step 4: rebalance dates
        earliest_article = articles["Article_Date"].min()
        bt_start = max(earliest_article, monthly.index[0])
        bt_end = monthly.index[-1]

        rdates = []
        dt = bt_start.replace(day=1)
        while dt <= bt_end:
            idx = monthly.index[
                (monthly.index.year == dt.year) & (monthly.index.month == dt.month)
            ]
            if len(idx) > 0:
                rdates.append(idx[0])
            dt += pd.offsets.MonthBegin(1)

        log.info("\n🔄 STEP 4: Running backtest...")
        log.info("  Rebalance dates: %d", len(rdates))
        log.info("  Period: %s → %s", rdates[0].date(), rdates[-1].date())

        available_tickers = set(daily.columns)

        # ── Backtest state ──
        cash = config.startkapital
        holdings: Dict[str, float] = {}
        # ── FIX 2: track when each position was opened (index into rdates) ──
        opened_at: Dict[str, int] = {}
        equity_curve = []
        trade_log = []
        monthly_log = []
        score_log = []          # (dato, ticker, score) — grunnlag for master.py
        score_log_advart = False
        last_sentiment = pd.DataFrame()

        for rebal_idx, rebal_dt in enumerate(rdates):
            pv_before = cash + sum(
                holdings.get(t, 0) * (price_at(monthly, t, rebal_dt) or 0)
                for t in holdings
            )

            # Score sentiment at this date (with signal lag applied)
            sentiment = score_sentiment_at(
                articles, ticker_map, rebal_dt, config, available_tickers
            )
            if not sentiment.empty:
                last_sentiment = sentiment.copy()

            # ── FIX 2: Decide what to KEEP and what to SELL based on min-hold + delta sign ──
            score_lookup = (
                dict(zip(sentiment["Ticker"], sentiment["Sentiment_Score"]))
                if not sentiment.empty else {}
            )

            keep_set: Set[str] = set()
            forced_sells: Set[str] = set()
            for tkr in list(holdings.keys()):
                held_months = rebal_idx - opened_at.get(tkr, rebal_idx)
                current_delta = score_lookup.get(tkr, None)

                if current_delta is None:
                    # No measurable signal at all — sell only if past min hold
                    if held_months >= config.min_hold_months:
                        forced_sells.add(tkr)
                    else:
                        keep_set.add(tkr)
                elif current_delta < config.exit_delta_threshold:
                    # Sentiment has clearly deteriorated → exit even before min_hold
                    forced_sells.add(tkr)
                else:
                    # Sentiment still OK (positive or near-zero) → hold
                    keep_set.add(tkr)

            # ── Find new eligible buys (positive delta + above SMA) ──
            eligible = select_eligible_buys(sentiment, daily, rebal_dt, config)

            # ── Build target portfolio: keep_set + best new names, up to n_portfolio ──
            target_tickers: List[str] = list(keep_set)
            slots_left = config.n_portfolio - len(target_tickers)
            if slots_left > 0 and not eligible.empty:
                for tkr in eligible["Ticker"].tolist():
                    if tkr not in target_tickers and tkr in available_tickers:
                        target_tickers.append(tkr)
                        if len(target_tickers) >= config.n_portfolio:
                            break

            # ── SCORELOGGEN ──
            # Denne utgaven (v4.1) skriver et filnavn som passer det samme
            # søkemønsteret som v4 sitt. Uten arket her ville master.py, som
            # velger den ferskeste filen, lest en fil uten scorehistorikk og
            # meldt at NLP mangler Score_Log — uansett hvor mange ganger
            # modellen ble kjørt på nytt. Datoen skrives som TEKST med vilje.
            try:
                if not sentiment.empty:
                    for _rang, (_, _r) in enumerate(
                            sentiment.head(SCORE_LOG_TOPP).iterrows(), start=1):
                        score_log.append({
                            "date": pd.Timestamp(rebal_dt).strftime("%Y-%m-%d"),
                            "ticker": str(_r["Ticker"]),
                            "score": float(_r["Sentiment_Score"]),
                            "rank": _rang,
                            "valgt": "JA" if _r["Ticker"] in target_tickers else "NEI",
                        })
            except Exception as _e:
                if not score_log_advart:
                    score_log_advart = True
                    log.warning("Score-loggen feiler (%s) — arket Score_Log blir "
                                "tomt, og master.py mister NLP som kilde.", _e)

            # Companies dropping out of target (forced sells already excluded from keep_set)
            sells_set = (set(holdings.keys()) - set(target_tickers)) | forced_sells
            buys_set = set(target_tickers) - set(holdings.keys())
            holds_set = set(target_tickers) & set(holdings.keys())

            if not target_tickers and not holdings:
                # All cash, no signal
                equity_curve.append({"date": rebal_dt, "value": pv_before})
                monthly_log.append({
                    "date": rebal_dt.strftime("%Y-%m"),
                    "portfolio_value": round(pv_before, 0),
                    "cash": round(cash, 0),
                    "n_holdings": 0,
                    "holdings": "CASH — no signal",
                    "buys": "", "sells": "",
                })
                log.info("%s  $%.0f  CASH (no signal)", rebal_dt.strftime("%Y-%m"), pv_before)
                continue

            # ── Execute SELLS ──
            for tkr in sells_set:
                p = price_at(monthly, tkr, rebal_dt)
                if p and holdings.get(tkr, 0) > 0:
                    proceeds = holdings[tkr] * p
                    txn = proceeds * config.transaction_cost
                    cash += proceeds - txn
                    trade_log.append({
                        "date": rebal_dt.strftime("%Y-%m-%d"),
                        "ticker": tkr, "action": "SELL",
                        "shares": round(holdings[tkr], 4),
                        "price": round(p, 2),
                        "value": round(proceeds, 0),
                    })
                    del holdings[tkr]
                    opened_at.pop(tkr, None)

            # If after sells we have no target tickers (shouldn't happen often, but possible)
            if not target_tickers:
                port_after = cash
                equity_curve.append({"date": rebal_dt, "value": port_after})
                monthly_log.append({
                    "date": rebal_dt.strftime("%Y-%m"),
                    "portfolio_value": round(port_after, 0),
                    "cash": round(cash, 0),
                    "n_holdings": 0,
                    "holdings": "CASH — all exited",
                    "buys": "", "sells": ", ".join(sorted(sells_set)),
                })
                log.info("%s  $%.0f  CASH (all exited)", rebal_dt.strftime("%Y-%m"), port_after)
                continue

            # ── Equal-weight target allocation ──
            pv_after_sells = cash + sum(
                holdings.get(t, 0) * (price_at(monthly, t, rebal_dt) or 0)
                for t in holdings
            )
            tv = pv_after_sells / len(target_tickers)

            # ── BUYS / REBALANCES ──
            for tkr in target_tickers:
                p = price_at(monthly, tkr, rebal_dt)
                if not p or p <= 0:
                    continue
                cs = holdings.get(tkr, 0)
                ts = tv / p
                diff = ts - cs
                if abs(diff * p) < 1:
                    continue

                if diff > 0:
                    cost = diff * p
                    txn = cost * config.transaction_cost
                    total_cost = cost + txn
                    if total_cost > cash:
                        affordable_shares = (cash / (1 + config.transaction_cost)) / p
                        if affordable_shares < 1:
                            continue
                        diff = affordable_shares
                        cost = diff * p
                        txn = cost * config.transaction_cost
                        total_cost = cost + txn
                    cash -= total_cost
                    holdings[tkr] = cs + diff
                    action = "BUY" if tkr in buys_set else "REBAL_BUY"
                    # ── FIX 2: stamp the open date if this is a NEW position ──
                    if tkr in buys_set:
                        opened_at[tkr] = rebal_idx
                    trade_log.append({
                        "date": rebal_dt.strftime("%Y-%m-%d"),
                        "ticker": tkr, "action": action,
                        "shares": round(diff, 4),
                        "price": round(p, 2),
                        "value": round(cost, 0),
                    })
                else:
                    ss = abs(diff)
                    proceeds = ss * p
                    txn = proceeds * config.transaction_cost
                    cash += proceeds - txn
                    holdings[tkr] = max(cs - ss, 0)
                    trade_log.append({
                        "date": rebal_dt.strftime("%Y-%m-%d"),
                        "ticker": tkr, "action": "REBAL_SELL",
                        "shares": round(ss, 4),
                        "price": round(p, 2),
                        "value": round(proceeds, 0),
                    })

            # ── Record ──
            port_after = cash + sum(
                holdings.get(t, 0) * (price_at(monthly, t, rebal_dt) or 0)
                for t in holdings
            )
            equity_curve.append({"date": rebal_dt, "value": port_after})

            monthly_log.append({
                "date": rebal_dt.strftime("%Y-%m"),
                "portfolio_value": round(port_after, 0),
                "cash": round(cash, 0),
                "n_holdings": len(holdings),
                "holdings": ", ".join(sorted(holdings.keys())),
                "buys": ", ".join(sorted(buys_set)),
                "sells": ", ".join(sorted(sells_set)),
            })

            pct_change = ""
            if len(equity_curve) >= 2:
                prev_val = equity_curve[-2]["value"]
                if prev_val > 0:
                    ret = (port_after / prev_val - 1) * 100
                    pct_change = " (%+.1f%%)" % ret

            log.info("")
            log.info("--- %s  $%.0f%s ---", rebal_dt.strftime("%Y-%m"), port_after, pct_change)
            if buys_set:
                log.info("  BUY:  %s", ", ".join(sorted(buys_set)))
            if sells_set:
                log.info("  SELL: %s", ", ".join(sorted(sells_set)))
            if holds_set:
                log.info("  HOLD: %s", ", ".join(sorted(holds_set)))

            for tkr in sorted(holdings.keys()):
                p = price_at(monthly, tkr, rebal_dt)
                if p:
                    val = holdings[tkr] * p
                    held_for = rebal_idx - opened_at.get(tkr, rebal_idx)
                    score_str = "%.3f" % score_lookup.get(tkr, float('nan')) \
                        if tkr in score_lookup else "?"
                    log.info("    %-10s ($%.0f  Score:%s  Held:%dmo)",
                            tkr, val, score_str, held_for)

            log.info("  Cash: $%.0f  |  %d stocks", cash, len(holdings))

        # ─────────────────────────────────────────────────────────────────────────────
        # METRICS  (unchanged from original)
        # ─────────────────────────────────────────────────────────────────────────────

        if not equity_curve:
            log.warning("No equity curve!")
            return

        ec = pd.DataFrame(equity_curve).set_index("date")["value"]
        rets = ec.pct_change().dropna()
        if len(rets) < 2:
            log.warning("Not enough data for metrics")
            return

        total_ret = (ec.iloc[-1] / ec.iloc[0]) - 1
        n_years = max((ec.index[-1] - ec.index[0]).days / 365.25, 0.01)
        cagr = (ec.iloc[-1] / ec.iloc[0]) ** (1 / n_years) - 1
        vol = rets.std() * np.sqrt(12)
        sharpe = (cagr - 0.03) / vol if vol > 0 else 0
        mdd = ((ec - ec.cummax()) / ec.cummax()).min()
        wr = (rets > 0).sum() / len(rets)
        ds = rets[rets < 0]
        dv = ds.std() * np.sqrt(12) if len(ds) > 0 else 0
        sortino = (cagr - 0.03) / dv if dv > 0 else 0
        calmar = cagr / abs(mdd) if mdd != 0 else 0

        bcagr = None
        if not bn.empty:
            bc = bn.reindex(ec.index, method="ffill").dropna()
            if len(bc) >= 2:
                bcagr = (bc.iloc[-1] / bc.iloc[0]) ** (1 / n_years) - 1

        log.info("")
        log.info("=" * 55)
        log.info("  RESULTS — SENTIMENT v4.1 (lag+hold+lang)")
        log.info("=" * 55)
        log.info("  Start Value      : $%.0f", ec.iloc[0])
        log.info("  End Value        : $%.0f", ec.iloc[-1])
        log.info("  Total Return     : %.1f%%", total_ret * 100)
        log.info("  CAGR             : %.1f%%", cagr * 100)
        log.info("  Sharpe           : %.2f", sharpe)
        log.info("  Sortino          : %.2f", sortino)
        log.info("  Max Drawdown     : %.1f%%", mdd * 100)
        log.info("  Calmar           : %.2f", calmar)
        log.info("  Win Rate         : %.0f%%", wr * 100)
        log.info("  Volatility       : %.1f%%", vol * 100)
        log.info("  Total Trades     : %d", len(trade_log))
        if bcagr is not None:
            log.info("  Benchmark CAGR   : %.1f%%", bcagr * 100)
            log.info("  Excess Return    : %+.1f%%", (cagr - bcagr) * 100)
        log.info("=" * 55)

        # ── CURRENT HOLDINGS SNAPSHOT, CHARTS, SAVE EXCEL ──
        # (All unchanged from your original — paste in here as-is. I'm omitting
        # for brevity but no edits are needed below this line.)

        # ... [keep your existing snapshot/chart/save code] ...

        out_path = config.results_dir / f"Sentiment_v4_1_SMA{config.sma_days}_{TODAY_STR}.xlsx"
        with pd.ExcelWriter(str(out_path), engine="openpyxl") as writer:
            if monthly_log:
                pd.DataFrame(monthly_log).to_excel(writer, sheet_name="Monthly_Holdings",
                                                index=False)
            ec_df = ec.reset_index()
            ec_df.columns = ["Date", "Strategy"]
            if not bn.empty:
                ec_df["Benchmark"] = bn.reindex(ec.index, method="ffill").values
            ec_df.to_excel(writer, sheet_name="Equity_Curve", index=False)
            if trade_log:
                pd.DataFrame(trade_log).to_excel(writer, sheet_name="Trade_Log", index=False)
            (pd.DataFrame(score_log) if score_log else pd.DataFrame(
                columns=["date", "ticker", "score", "rank", "valgt"])
             ).to_excel(writer, sheet_name="Score_Log", index=False)
            if not score_log:
                log.warning("Score_Log er TOM — master.py teller da NLP som en "
                            "kilde uten mening om noe selskap.")

        log.info("Results: %s", out_path)
        log.info("=== Sentiment Strategy v4.1 complete ===")
    #NlpSentimentTrader4()

    #Just trading part of managment above 
    def NlpSentimentTrader4_Results(monster: str = "Sentiment_v4_SMA*.xlsx"):
        """
        Reads the latest output file matching `monster` and prints all backtest
        metrics including trade-level P&L stats.

        Run this AFTER en av traderne har kjørt minst én gang.

        Mønsteret er en parameter fordi de to utgavene skriver hvert sitt
        filnavn: v4 skriver Sentiment_v4_SMA*, v4.1 skriver Sentiment_v4_1_SMA*.
        Sto mønsteret fast, ville et bytte til v4.1 lest v4-tallene fra i går
        og rapportert dem som dagens.
        """

        import pandas as pd
        import numpy as np
        from pathlib import Path
        from datetime import datetime
        import logging

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s  %(levelname)-8s  %(message)s",
            datefmt="%H:%M:%S",
        )
        log = logging.getLogger("SentimentV4_Results")

        RESULTS_DIR = Path(r"C:\Users\ander\Desktop\Python_K4\ExcelData\StrategyResults_v4_Sentiment")
        BENCHMARK_TICKER = "OSEBX.OL"

        # ── Find latest file ──
        files = sorted(RESULTS_DIR.glob(monster),
                    key=lambda p: p.stat().st_mtime, reverse=True)
        if not files:
            log.error("No %s found in %s", monster, RESULTS_DIR)
            return
        
        filepath = files[0]
        log.info("Loading: %s", filepath.name)

        # ── Load sheets ──
        try:
            equity_df = pd.read_excel(filepath, sheet_name="Equity_Curve")
            monthly_df = pd.read_excel(filepath, sheet_name="Monthly_Holdings")
        except Exception as e:
            log.error("Could not read file: %s", e)
            return

        try:
            trades_df = pd.read_excel(filepath, sheet_name="Trade_Log")
        except Exception:
            trades_df = pd.DataFrame()

        if equity_df.empty:
            log.error("Equity curve is empty")
            return

        # ── Equity curve metrics ──
        equity_df["Date"] = pd.to_datetime(equity_df["Date"])
        ec = equity_df.set_index("Date")["Strategy"]
        rets = ec.pct_change().dropna()

        if len(rets) < 2:
            log.error("Not enough data points")
            return

        start_val = ec.iloc[0]
        end_val = ec.iloc[-1]
        total_ret = (end_val / start_val) - 1
        n_years = max((ec.index[-1] - ec.index[0]).days / 365.25, 0.01)
        cagr = (end_val / start_val) ** (1 / n_years) - 1
        vol = rets.std() * np.sqrt(12)
        sharpe = (cagr - 0.03) / vol if vol > 0 else 0
        mdd = ((ec - ec.cummax()) / ec.cummax()).min()
        wr = (rets > 0).sum() / len(rets)
        ds = rets[rets < 0]
        dv = ds.std() * np.sqrt(12) if len(ds) > 0 else 0
        sortino = (cagr - 0.03) / dv if dv > 0 else 0
        calmar = cagr / abs(mdd) if mdd != 0 else 0

        # ── Benchmark ──
        bcagr = None
        if "Benchmark" in equity_df.columns:
            bn = equity_df.set_index("Date")["Benchmark"].dropna()
            if len(bn) >= 2:
                bcagr = (bn.iloc[-1] / bn.iloc[0]) ** (1 / n_years) - 1

        # ── Trade-level P&L ──
        trade_returns = []
        if not trades_df.empty:
            trades_df["date"] = pd.to_datetime(trades_df["date"])
            sells = trades_df[trades_df["action"] == "SELL"].copy()
            buys = trades_df[trades_df["action"].isin(["BUY", "REBAL_BUY"])].copy()

            for _, sell in sells.iterrows():
                ticker = sell["ticker"]
                sell_price = sell["price"]
                sell_date = sell["date"]

                prior_buys = buys[
                    (buys["ticker"] == ticker) &
                    (buys["date"] < sell_date)
                ].sort_values("date", ascending=False)

                if not prior_buys.empty:
                    buy_price = prior_buys.iloc[0]["price"]
                    if buy_price > 0:
                        trade_returns.append((sell_price / buy_price - 1) * 100)

        # ── Current holdings ──
        if not monthly_df.empty:
            last_month = monthly_df.iloc[-1]
            holdings_str = str(last_month.get("holdings", ""))
            n_holdings = last_month.get("n_holdings", 0)
            cash = last_month.get("cash", 0)
        else:
            holdings_str = ""
            n_holdings = 0
            cash = 0

        # ── Print results ──
        log.info("")
        log.info("=" * 60)
        log.info("  RESULTS — NLP SENTIMENT v4")
        log.info("=" * 60)
        log.info("  File             : %s", filepath.name)
        log.info("  Period           : %s -> %s (%.1f years)",
                ec.index[0].date(), ec.index[-1].date(), n_years)
        log.info("")
        log.info("  RETURNS:")
        log.info("  Start Value      : $%.0f", start_val)
        log.info("  End Value        : $%.0f", end_val)
        log.info("  Total Return     : %.1f%%", total_ret * 100)
        log.info("  CAGR             : %.1f%%", cagr * 100)
        log.info("")
        log.info("  RISK:")
        log.info("  Sharpe           : %.2f", sharpe)
        log.info("  Sortino          : %.2f", sortino)
        log.info("  Max Drawdown     : %.1f%%", mdd * 100)
        log.info("  Calmar           : %.2f", calmar)
        log.info("  Win Rate (monthly): %.0f%%", wr * 100)
        log.info("  Volatility       : %.1f%%", vol * 100)
        log.info("")
        log.info("  TRADING:")
        log.info("  Total Trades     : %d", len(trades_df) if not trades_df.empty else 0)
        if trade_returns:
            profitable = sum(1 for r in trade_returns if r > 0)
            log.info("  Closed trades    : %d", len(trade_returns))
            log.info("  Profitable trades: %d", profitable)
            log.info("  Trade Win Rate   : %.1f%%", profitable / len(trade_returns) * 100)
            log.info("  Avg trade return : %+.2f%%", np.mean(trade_returns))
            log.info("  Median trade ret : %+.2f%%", np.median(trade_returns))
            log.info("  Best trade       : %+.2f%%", np.max(trade_returns))
            log.info("  Worst trade      : %+.2f%%", np.min(trade_returns))
        else:
            log.info("  Closed trades    : 0 (no completed round-trips)")

        if bcagr is not None:
            log.info("")
            log.info("  BENCHMARK:")
            log.info("  Benchmark CAGR   : %.1f%%", bcagr * 100)
            log.info("  Excess Return    : %+.1f%%", (cagr - bcagr) * 100)

        log.info("")
        log.info("  CURRENT HOLDINGS:")
        if holdings_str and holdings_str not in ("CASH — no signal", "nan", ""):
            tickers = [t.strip() for t in holdings_str.split(",") if t.strip()]
            for i, tkr in enumerate(tickers, 1):
                log.info("    %d. %s", i, tkr)
            log.info("  Cash: $%.0f  |  %d stocks", cash, n_holdings)
        else:
            log.info("    CASH ONLY: $%.0f", cash)

        log.info("=" * 60)

    # ══════════════════════════════════════════════════════════════════════
    # DISPATCH — to valg, ett sted
    # ══════════════════════════════════════════════════════════════════════
    #
    # Alle kallene står her, etter at begge utgavene er definert. Da er
    # rekkefølgen i filen ikke lenger med på å bestemme hva som kjører.
    SKRAPERE = {
        "v4":   (NLP_Euronext_Quarter4_v4,
                 "10 artikler per selskap, bare side 1"),
        "v4.1": (NLP_Euronext_Quarter4_v41,
                 "100 per selskap, blar gjennom opptil 15 sider"),
    }
    MOTORER = {
        "v4":   (NlpSentimentTrader4_v4,  "Sentiment_v4_SMA*.xlsx"),
        "v4.1": (NlpSentimentTrader4_v41, "Sentiment_v4_1_SMA*.xlsx"),
    }
    for navn, verdi, valg in (("AKSJE_NLP_SKRAPER", NLP_SKRAPER, SKRAPERE),
                              ("AKSJE_NLP_MOTOR", NLP_MOTOR, MOTORER)):
        if verdi not in valg:
            raise ValueError(
                f"{navn} = {verdi!r} finnes ikke. Velg én av: "
                f"{', '.join(sorted(valg))}. Standardene står øverst i "
                f"SentimentManagement().")

    motor, resultatmonster = MOTORER[NLP_MOTOR]
    print(f"\n  NLP-motor  : {NLP_MOTOR}  →  {resultatmonster}")

    if HENT_NYE_ARTIKLER:
        skraper, hva = SKRAPERE[NLP_SKRAPER]
        print(f"  NLP-skraper: {NLP_SKRAPER}  —  {hva}")
        print("  Dette tar timer. Artiklene legges i DataNLP og brukes av "
              "alle senere kjøringer.")
        try:
            skraper()
        except Exception as e:
            # Skrapingen går mot en nettside som endrer seg, og v4.1-utgaven
            # har aldri kjørt her. Den skal ikke ta backtesten med seg: de
            # artiklene som allerede ligger i DataNLP er fortsatt gyldige, og
            # en mislykket utvidelse er ikke det samme som ingen data.
            print(f"\n  ⚠️  Skrapingen ({NLP_SKRAPER}) feilet: "
                  f"{type(e).__name__}: {e}")
            print("  Backtesten kjører videre på artiklene som allerede ligger "
                  "i DataNLP.")
            traceback.print_exc()
            raise
    else:
        print("  NLP-skraper: av — kjører på artiklene som ligger i DataNLP.")
        print("  Slå på med:  python master.py --hent-nlp   "
              "(eller set AKSJE_NLP_HENT=1)")

    if not _miljo_paa("AKSJE_NLP_ONLY_DOWNLOAD"):
        motor()
        NlpSentimentTrader4_Results(resultatmonster)
#SentimentManagement() 



##Public sentiment #CAGR 14%  
def SentimentMomentumV31():
    # ============================================================================
    # INVESTOR SENTIMENT MOMENTUM — OSLO BØRS (v3.1)
    # ============================================================================
    #
    # HVA SOM VAR GALT I v3 (1 handel på 251 dager):
    #
    #   BUG 1 — last_set-desync. _handle_exits solgte posisjoner uten å nullstille
    #           last_set. Etter første trailing-exit var target == last_set for
    #           alltid → changed=False → ingen flere handler. Strategien frøs.
    #           FIX: rebalanseringsbeslutningen tas nå mot FAKTISKE posisjoner.
    #
    #   BUG 2 — 100% i ett navn. _inverse_vol_weights normaliserte til sum 1.0
    #           uansett antall kandidater. Én kandidat → hele porteføljen i én
    #           aksje. Ett tap ble hele resultatet.
    #           FIX: vektene skaleres mot max_positions. Ufylte plasser = cash.
    #
    #   BUG 3 — filtrene var kalibrert for tett data. Med 580 artikler / 98
    #           selskaper (~6 per selskap TOTALT) diskvalifiserte
    #           min_articles=2 i et 90d-vindu nesten alle, hver dag.
    #           FIX: tetthetsbevisste terskler + rangeringsbasert utvalg i
    #           stedet for absolutt z-terskel.
    #
    #   DESIGN — SMA50 + krav om 20d-avkastning over median gjorde PRISEN til
    #           hovedfilter og nyhetene til pynt. Nå er nyhetene primærsignal
    #           og prisen kun et mykt veto (kan slås helt av).
    #
    # NY DIAGNOSTIKK:
    #   FunnelStats teller hvor mange selskaper som overlever HVERT filtersteg,
    #   aggregert over hele backtesten. Uten dette er kalibrering ren gjetning.
    #   Kjør med DIAGNOSE_ONLY=True først — den handler ikke, den viser bare
    #   hvor mange signaldager du faktisk har og hvor de forsvinner.
    # ============================================================================

    import pandas as pd
    import numpy as np
    from pathlib import Path
    from datetime import datetime, timedelta
    from typing import Dict, List
    from collections import Counter
    import warnings
    warnings.filterwarnings('ignore')

    # ── Kjør denne først. Handler ikke, viser bare signaltilgjengelighet. ──
    DIAGNOSE_ONLY = False

    # ─────────────────────────────────────────────────────────────────────────
    # PARAMETERE
    # ─────────────────────────────────────────────────────────────────────────
    class Config:
        def __init__(self):
            self.base_dir      = Path(r"C:/Users/ander/Desktop/Python_K4/ExcelData")
            self.nlp_dir       = self.base_dir / "DataNLP"
            self.bt_dir        = self.base_dir / "Data_BT1"
            self.financial_dir = self.bt_dir / "FinancialData"
            self.results_dir   = self.nlp_dir / "BacktestResults"
            self.results_dir.mkdir(parents=True, exist_ok=True)

            self.start_capital  = 1_000_000
            self.backtest_days  = 365
            self.max_positions  = 5

            # ── SIGNAL: kalibrert for TYNN data (~6 artikler/selskap totalt) ──
            self.decay_halflife   = 30    # v3 brukte 14d — for aggressivt når
                                          # en artikkel fra 30d siden er den
                                          # ENESTE artikkelen selskapet har.
            self.signal_lookback  = 150   # v3: 90. Utvidet for å fange nok data.
            self.accel_window     = 21
            self.attention_window = 45
            self.min_articles     = 1     # v3: 2. Med denne tettheten er 2
                                          # ensbetydende med å ekskludere alt.

            self.w_drift     = 0.45
            self.w_accel     = 0.20
            self.w_attention = 0.20
            self.w_consensus = 0.15

            # ── UTVALG: rangering, ikke absolutt terskel ──
            # En absolutt z-terskel er ustabil når universet er lite: z er
            # definert mot dagens utvalg, så terskelen betyr ulike ting fra
            # dag til dag. Vi tar i stedet topp N som passerer et mildt gulv.
            self.min_composite_z = -0.25   # v3: +0.50 (bandt altfor hardt)
            self.extreme_pctl    = 0.99    # v3: 0.98
            self.extreme_min_n   = 25      # ekstremkutt kun når universet er
                                           # stort nok til at halen betyr noe

            # ── PRIS: mykt veto, ikke hovedfilter ──
            self.use_price_filter = True
            self.price_sma        = 200    # v3: 50. Kun "ikke i fritt fall".
            self.require_rel_str  = False  # v3: True. Dette var momentum-
                                           # kontamineringen — nå av.

            self.use_regime      = True
            self.regime_sma      = 200
            self.regime_exposure = 0.50

            # ── EXITS: løsere, single-name Oslo Børs svinger ──
            self.max_holding_days = 45
            self.stop_loss_pct    = -0.18   # v3: -0.15
            self.trail_from_peak  = -0.18   # v3: -0.12 (trailet ut på 11 dager)
            self.trail_min_gain   = 0.05    # trailing aktiveres FØRST når
                                            # posisjonen har vært 5% i pluss.
                                            # Uten dette er trailing bare en
                                            # strammere stop loss.

            # ── SIZING ──
            self.vol_window = 20
            self.max_weight = 0.30          # tak per posisjon av TOTAL kapital
            self.min_weight = 0.10

            # ── KOSTNAD: satt til 0 etter ønske. Merk at gebyrene i v3-kjøringen
            #    var 2 811 NOK av et tap på 125 276 — de var ikke problemet. ──
            self.transaction_cost = 0.0
            self.risk_free        = 0.04

            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            self.portfolio_file = self.results_dir / f"S5_SentMom31_Portfolio_{ts}.xlsx"
            self.trades_file    = self.results_dir / f"S5_SentMom31_Trades_{ts}.xlsx"
            self.signals_file   = self.results_dir / f"S5_SentMom31_Signals_{ts}.xlsx"
            self.funnel_file    = self.results_dir / f"S5_SentMom31_Funnel_{ts}.xlsx"

    # ─────────────────────────────────────────────────────────────────────────
    # FUNNEL — hvor forsvinner kandidatene?
    # ─────────────────────────────────────────────────────────────────────────
    class FunnelStats:
        """
        Teller overlevende per filtersteg, aggregert over alle handelsdager.
        Dette er det viktigste diagnoseverktøyet: uten det vet du ikke om et
        magert resultat skyldes dårlig signal eller et filter som stenger alt.
        """
        def __init__(self):
            self.stage_totals = Counter()
            self.stage_days_nonzero = Counter()
            self.days = 0
            self.daily: List[dict] = []

        def log(self, date, counts: dict):
            self.days += 1
            for k, v in counts.items():
                self.stage_totals[k] += v
                if v > 0:
                    self.stage_days_nonzero[k] += 1
            row = {'Date': date}
            row.update(counts)
            self.daily.append(row)

        def report(self, order: List[str]):
            print("\n" + "=" * 74)
            print("  SIGNALFUNNEL — hvor forsvinner kandidatene?")
            print("=" * 74)
            print(f"  {'Steg':<28} {'Snitt/dag':>10} {'Dager >0':>10} {'% dager':>10}")
            print("  " + "─" * 70)
            for k in order:
                avg = self.stage_totals[k] / max(self.days, 1)
                nz = self.stage_days_nonzero[k]
                pct = nz / max(self.days, 1) * 100
                print(f"  {k:<28} {avg:>10.2f} {nz:>10} {pct:>9.1f}%")
            print("=" * 74)
            worst = None
            prev_k = None
            for k in order:
                if prev_k is not None:
                    a, b = self.stage_totals[prev_k], self.stage_totals[k]
                    if a > 0:
                        drop = 1 - b / a
                        if worst is None or drop > worst[1]:
                            worst = (f"{prev_k} → {k}", drop)
                prev_k = k
            if worst:
                print(f"  Største fall: {worst[0]} ({worst[1]*100:.0f}% kuttet)")
                print("=" * 74)

    # ─────────────────────────────────────────────────────────────────────────
    # DATA
    # ─────────────────────────────────────────────────────────────────────────
    class DataLoader:
        def __init__(self, config):
            self.config = config

        def load_all(self):
            step4_files = sorted(
                self.config.nlp_dir.glob("Step4_Sentiment_Changes_*.xlsx"),
                key=lambda p: p.stat().st_mtime, reverse=True)
            if not step4_files:
                raise FileNotFoundError("Fant ingen Step4-fil!")
            sent_df = pd.read_excel(step4_files[0])
            sent_df['Article_Date'] = pd.to_datetime(sent_df['Article_Date'],
                                                     errors='coerce')
            sent_df = sent_df.dropna(subset=['Article_Date'])
            n_raw = len(sent_df)

            if 'Article_Title' in sent_df.columns:
                key = (sent_df['Company'].astype(str).str.upper().str.strip()
                       + "|" + sent_df['Article_Date'].dt.date.astype(str)
                       + "|" + sent_df['Article_Title'].astype(str)
                              .str.upper().str.replace(r'[^A-ZÆØÅ0-9 ]', '', regex=True)
                              .str.split().str[:8].str.join(' '))
                sent_df = sent_df.loc[~key.duplicated()].copy()

            span = (sent_df['Article_Date'].max() - sent_df['Article_Date'].min()).days
            per_co = len(sent_df) / max(sent_df['Company'].nunique(), 1)
            print(f"✅ Sentiment: {step4_files[0].name}")
            print(f"   {n_raw} → {len(sent_df)} etter dedup | "
                  f"{sent_df['Company'].nunique()} selskaper | "
                  f"{per_co:.1f} artikler/selskap over {span} dager")
            if per_co < 10:
                print(f"   ⚠️  TYNN DATA: {per_co:.1f} artikler per selskap. "
                      f"Filtrene er løsnet deretter — men dette er "
                      f"hovedbegrensningen i strategien.")

            price_files = sorted(
                self.config.financial_dir.glob("Stock_Prices_*.xlsx"),
                key=lambda p: p.stat().st_mtime, reverse=True)
            if not price_files:
                raise FileNotFoundError("Fant ingen prisdata!")
            price_df = pd.read_excel(price_files[0])
            price_df['Date'] = pd.to_datetime(price_df['Date'], errors='coerce')
            price_df = price_df.dropna(subset=['Date', 'Close'])
            from runtime_config import validate_price_frame
            validate_price_frame(price_df.pivot_table(index='Date', columns='Ticker', values='Close'),
                                 context="Sentiment momentum prices")
            print(f"✅ Priser:    {price_files[0].name} "
                  f"({price_df['Company'].nunique()} selskaper, "
                  f"{price_df['Date'].min().date()} → {price_df['Date'].max().date()})")

            # Advarsel hvis sentimentdata slutter før prisdata
            gap = (price_df['Date'].max() - sent_df['Article_Date'].max()).days
            if gap > 7:
                print(f"   ⚠️  Sentimentdata slutter {gap} dager før prisdata "
                      f"— siste {gap} dager av backtesten har ingen ferske signaler.")

            ticker_map = self._map_tickers(sent_df, price_df)
            return sent_df, price_df, ticker_map

        def _map_tickers(self, sent_df, price_df):
            pc = price_df[['Company', 'Ticker']].drop_duplicates()
            tm = {}
            for company in sent_df['Company'].unique():
                m = pc[pc['Company'] == company]
                if not m.empty:
                    tm[company] = m.iloc[0]['Ticker']
                else:
                    cn = str(company).strip().upper().replace('  ', ' ')
                    for _, row in pc.iterrows():
                        rn = str(row['Company']).strip().upper().replace('  ', ' ')
                        if cn in rn or rn in cn:
                            tm[company] = row['Ticker']
                            break
            print(f"✅ Tickermap: {len(tm)} / {sent_df['Company'].nunique()} matchet")
            return tm

    # ─────────────────────────────────────────────────────────────────────────
    # PRISBOK
    # ─────────────────────────────────────────────────────────────────────────
    class PriceBook:
        def __init__(self, price_df, config):
            self.config = config
            self._book: Dict[object, Dict[str, float]] = {}
            self._history: Dict[str, pd.Series] = {}

            for ticker, grp in price_df.groupby('Ticker'):
                s = grp.sort_values('Date').set_index('Date')['Close'].dropna()
                s = s[~s.index.duplicated(keep='last')]
                if len(s) > 0:
                    self._history[ticker] = s

            for _, row in price_df.iterrows():
                d, t, c = row['Date'], row['Ticker'], row['Close']
                if t and not pd.isna(c) and c > 0:
                    self._book.setdefault(d, {})[t] = float(c)

            frames = [s.pct_change() for s in self._history.values() if len(s) > 60]
            if frames:
                combined = pd.concat(frames, axis=1).mean(axis=1).fillna(0.0)
                self._index = (1.0 + combined).cumprod()
            else:
                self._index = pd.Series(dtype=float)

        def prices_on(self, date):
            return self._book.get(date, {})

        def _hist_before(self, ticker, as_of_date):
            if ticker not in self._history:
                return None
            s = self._history[ticker]
            s = s[s.index < as_of_date]
            return s if len(s) > 0 else None

        def above_sma(self, ticker, as_of_date, sma_days):
            s = self._hist_before(ticker, as_of_date)
            if s is None:
                return False
            # Tolerant: hvis vi har mindre historikk enn ønsket, bruk det vi har
            # (min 20 dager). v3 returnerte False og kuttet nye/tynne serier helt.
            n = min(sma_days, len(s))
            if n < 20:
                return True
            return float(s.iloc[-1]) > float(s.iloc[-n:].mean())

        def realized_vol(self, ticker, as_of_date):
            s = self._hist_before(ticker, as_of_date)
            w = self.config.vol_window
            if s is None or len(s) < w + 1:
                return None
            v = float(s.pct_change().dropna().iloc[-w:].std())
            return v if v > 1e-6 else None

        def trailing_return(self, ticker, as_of_date, days=20):
            s = self._hist_before(ticker, as_of_date)
            if s is None or len(s) < days + 1:
                return None
            return float(s.iloc[-1] / s.iloc[-days - 1] - 1.0)

        def regime_ok(self, as_of_date):
            if self._index.empty:
                return True
            s = self._index[self._index.index < as_of_date]
            n = self.config.regime_sma
            if len(s) < n:
                return True
            return float(s.iloc[-1]) > float(s.iloc[-n:].mean())

    # ─────────────────────────────────────────────────────────────────────────
    # SIGNALMOTOR
    # ─────────────────────────────────────────────────────────────────────────
    class SignalEngine:
        def __init__(self, config, book, ticker_map, funnel):
            self.config = config
            self.book = book
            self.tm = ticker_map
            self.funnel = funnel

        @staticmethod
        def _zscore(series):
            s = pd.to_numeric(series, errors='coerce')
            mu, sd = s.mean(), s.std()
            if sd is None or sd == 0 or pd.isna(sd):
                return pd.Series(0.0, index=s.index)
            return ((s - mu) / sd).fillna(0.0)

        def _decay(self, days_old):
            return 0.5 ** (days_old / self.config.decay_halflife)

        def build(self, sent_df, eval_date):
            c = self.config
            counts = {'artikler_i_vindu': 0, 'selskaper_i_vindu': 0,
                      'etter_min_artikler': 0, 'etter_ekstremkutt': 0,
                      'etter_z_gulv': 0, 'etter_prisfilter': 0, 'valgt': 0}

            lo = eval_date - timedelta(days=c.signal_lookback)
            win = sent_df[(sent_df['Article_Date'] < eval_date) &
                          (sent_df['Article_Date'] >= lo)].copy()
            counts['artikler_i_vindu'] = len(win)
            if win.empty:
                self.funnel.log(eval_date, counts)
                return pd.DataFrame()

            counts['selskaper_i_vindu'] = win['Company'].nunique()
            win['DaysOld'] = (eval_date - win['Article_Date']).dt.days
            win['W'] = win['DaysOld'].apply(self._decay)

            rows = []
            for company, g in win.groupby('Company'):
                if len(g) < c.min_articles:
                    continue
                g = g.sort_values('Article_Date')

                chg = pd.to_numeric(g['Sentiment_Change'], errors='coerce').fillna(0.0)
                w = g['W'].values
                drift = float(np.sum(chg.values * w) / max(np.sum(w), 1e-9))

                recent = g[g['DaysOld'] <= c.accel_window]
                older = g[(g['DaysOld'] > c.accel_window) &
                          (g['DaysOld'] <= c.accel_window * 3)]
                if len(recent) >= 1 and len(older) >= 1:
                    r_m = float(pd.to_numeric(recent['Sentiment_Change'],
                                              errors='coerce').fillna(0).mean())
                    o_m = float(pd.to_numeric(older['Sentiment_Change'],
                                              errors='coerce').fillna(0).mean())
                    accel = r_m - o_m
                else:
                    accel = 0.0

                n_recent = int((g['DaysOld'] <= c.attention_window).sum())
                span = max((g['Article_Date'].max() - g['Article_Date'].min()).days, 1)
                base_rate = len(g) / span * c.attention_window
                attention = np.log1p(n_recent) - np.log1p(max(base_rate, 0.1))

                fs = pd.to_numeric(g['Final_Score'], errors='coerce').dropna()
                consensus = (1.0 / (1.0 + float(fs.std()))
                             if len(fs) >= 2 and fs.std() > 0 else 0.5)

                rows.append({'Company': company, 'Drift': drift, 'Accel': accel,
                             'Attention': attention, 'Consensus': consensus,
                             'NArticles': len(g), 'NRecent': n_recent})

            counts['etter_min_artikler'] = len(rows)
            if not rows:
                self.funnel.log(eval_date, counts)
                return pd.DataFrame()

            df = pd.DataFrame(rows)
            df['zDrift']     = self._zscore(df['Drift'])
            df['zAccel']     = self._zscore(df['Accel'])
            df['zAttention'] = self._zscore(df['Attention'])
            df['zConsensus'] = self._zscore(df['Consensus'])
            df['Composite'] = (c.w_drift * df['zDrift'] + c.w_accel * df['zAccel'] +
                               c.w_attention * df['zAttention'] +
                               c.w_consensus * df['zConsensus'])

            # Ekstremkutt kun når universet er stort nok til å ha en hale
            if len(df) >= c.extreme_min_n:
                df = df[df['Composite'] <= df['Composite'].quantile(c.extreme_pctl)]
            counts['etter_ekstremkutt'] = len(df)

            df = df[df['Composite'] >= c.min_composite_z]
            counts['etter_z_gulv'] = len(df)
            if df.empty:
                self.funnel.log(eval_date, counts)
                return pd.DataFrame()

            # ── Pris som MYKT veto ──
            if c.use_price_filter:
                keep, rels = [], {}
                for _, r in df.iterrows():
                    t = self.tm.get(r['Company'])
                    if not t:
                        continue
                    if not self.book.above_sma(t, eval_date, c.price_sma):
                        continue
                    rels[r['Company']] = self.book.trailing_return(t, eval_date, 20) or 0.0
                    keep.append(r['Company'])
                df = df[df['Company'].isin(keep)].copy()
                if not df.empty:
                    df['Rel20d'] = df['Company'].map(rels)
                    if c.require_rel_str and len(df) >= 6:
                        df = df[df['Rel20d'] >= df['Rel20d'].median()]
            else:
                df = df.copy()
                df['Rel20d'] = 0.0

            counts['etter_prisfilter'] = len(df)
            if df.empty:
                self.funnel.log(eval_date, counts)
                return pd.DataFrame()

            df = df.sort_values('Composite', ascending=False).reset_index(drop=True)
            df['Rank'] = range(1, len(df) + 1)
            counts['valgt'] = min(len(df), c.max_positions)
            self.funnel.log(eval_date, counts)
            return df

    # ─────────────────────────────────────────────────────────────────────────
    # PORTEFØLJE
    # ─────────────────────────────────────────────────────────────────────────
    class Portfolio:
        def __init__(self, capital, transaction_cost):
            self.cash = capital
            self._start = capital
            self.tc = 0.0  # User-requested zero commission, spread and slippage.
            self.positions: Dict[str, dict] = {}
            self.trades: List[dict] = []
            self.history: List[dict] = []

        def value(self, prices):
            return self.cash + sum(p['shares'] * prices.get(t, p['last_price'])
                                   for t, p in self.positions.items())

        def mark(self, prices):
            for t, p in self.positions.items():
                px = prices.get(t)
                if px:
                    p['last_price'] = px
                    p['peak_price'] = max(p.get('peak_price', px), px)

        def buy(self, ticker, company, price, shares, date, rank, score, weight):
            if shares <= 0:
                return False
            cost = shares * price
            fee = cost * self.tc
            if self.cash < cost + fee:
                return False
            self.cash -= (cost + fee)
            self.positions[ticker] = dict(shares=shares, buy_price=price, buy_fee=fee,
                                          buy_date=date, company=company,
                                          last_price=price, peak_price=price)
            self.trades.append(dict(Date=date, Ticker=ticker, Company=company,
                                    Action='BUY', Shares=shares, Price=price,
                                    Value=cost, Fee=round(fee, 2), PnL=None,
                                    Reason=f"Rank {rank} | z={score:.2f} | "
                                           f"vekt {weight*100:.0f}%"))
            print(f"  BUY  {shares:>6,} {ticker:<9} @ {price:>8.2f} = {cost:>11,.0f}"
                  f"  (rank {rank}, z={score:+.2f}, {weight*100:.0f}%)")
            return True

        def sell(self, ticker, price, date, reason):
            if ticker not in self.positions:
                return False
            pos = self.positions.pop(ticker)
            proceeds = pos['shares'] * price
            fee = proceeds * self.tc
            net = proceeds - fee
            pnl = net - (pos['shares'] * pos['buy_price'] + pos['buy_fee'])
            pnl_pct = pnl / (pos['shares'] * pos['buy_price']) * 100
            days = (date - pos['buy_date']).days
            self.cash += net
            self.trades.append(dict(Date=date, Ticker=ticker, Company=pos['company'],
                                    Action='SELL', Shares=pos['shares'], Price=price,
                                    Value=proceeds, Fee=round(fee, 2),
                                    PnL=round(pnl, 2), Days_Held=days, Reason=reason))
            print(f"  SELL {pos['shares']:>6,} {ticker:<9} @ {price:>8.2f} = {net:>11,.0f}"
                  f"  (P&L {pnl:+,.0f} / {pnl_pct:+.1f}%, {days}d, {reason})")
            return True

        def record(self, date, prices, regime):
            v = self.value(prices)
            self.history.append(dict(Date=date, Portfolio_Value=v, Cash=self.cash,
                                     Position_Value=v - self.cash,
                                     Num_Positions=len(self.positions),
                                     Regime='RISK_ON' if regime else 'RISK_OFF',
                                     Return_pct=(v / self._start - 1) * 100))

        def win_rate(self):
            s = [t for t in self.trades if t['Action'] == 'SELL' and t['PnL'] is not None]
            return sum(1 for t in s if t['PnL'] > 0) / len(s) * 100 if s else 0.0

        def avg_holding_days(self):
            s = [t for t in self.trades
                 if t['Action'] == 'SELL' and t.get('Days_Held') is not None]
            return sum(t['Days_Held'] for t in s) / len(s) if s else 0.0

        def total_fees(self):
            return sum(t.get('Fee', 0) or 0 for t in self.trades)

    # ─────────────────────────────────────────────────────────────────────────
    # BACKTESTER
    # ─────────────────────────────────────────────────────────────────────────
    class Backtester:
        def __init__(self, config):
            self.config = config
            self.sent_df, self.price_df, self.ticker_map = DataLoader(config).load_all()
            self.book = PriceBook(self.price_df, config)
            self.funnel = FunnelStats()
            self.engine = SignalEngine(config, self.book, self.ticker_map, self.funnel)
            self.port = Portfolio(config.start_capital, config.transaction_cost)
            self.signal_log: List[dict] = []
            # KANDIDATLOGGEN — én rad per dag per kandidat, uavhengig av om
            # den ble kjøpt. signal_log over er en HANDELSLOGG og duger ikke
            # som scorehistorikk: en modell som bare rapporterer navnene den
            # kjøpte, rapporterer bare sine egne vinnere, og en persentil
            # regnet mot den viser topp karakter hver eneste dag.
            self.score_log: List[dict] = []
            self._score_log_advart = False

        def _weights(self, tickers, date):
            """
            FIX BUG 2: vektene skaleres mot max_positions, ikke mot antall
            kandidater. Med 1 kandidat og max 5 får den ~1/5 av kapitalen —
            resten står i cash. v3 ga den 100%.
            """
            c = self.config
            inv = {}
            for t in tickers:
                v = self.book.realized_vol(t, date)
                inv[t] = (1.0 / v) if v else None
            valid = [v for v in inv.values() if v]
            fallback = float(np.median(valid)) if valid else 1.0
            raw = {t: (inv[t] if inv[t] else fallback) for t in tickers}
            s = sum(raw.values())
            rel = {t: raw[t] / s for t in raw}
            # skalér ned til andelen plasser som faktisk er fylt
            fill = len(tickers) / c.max_positions
            w = {t: min(max(x * fill, c.min_weight * fill), c.max_weight)
                 for t, x in rel.items()}
            tot = sum(w.values())
            if tot > 1.0:
                w = {t: x / tot for t, x in w.items()}
            return w

        def _handle_exits(self, prices, date):
            c = self.config
            for t in list(self.port.positions.keys()):
                pos = self.port.positions[t]
                px = prices.get(t)
                if not px:
                    continue
                held = (date - pos['buy_date']).days
                previous = pos['last_price']
                ret = previous / pos['buy_price'] - 1.0
                peak_gain = pos.get('peak_price', px) / pos['buy_price'] - 1.0
                from_peak = previous / pos.get('peak_price', previous) - 1.0

                if ret <= c.stop_loss_pct:
                    self.port.sell(t, px, date, f"Stop {ret*100:.1f}%")
                elif peak_gain >= c.trail_min_gain and from_peak <= c.trail_from_peak:
                    # FIX: trailing aktiveres først når posisjonen HAR vært i
                    # pluss. v3 trailet ut en posisjon som aldri hadde tjent noe.
                    self.port.sell(t, px, date, f"Trailing {from_peak*100:.1f}%")
                elif held >= c.max_holding_days:
                    self.port.sell(t, px, date, f"Tidsexit {held}d")

        def run(self):
            c = self.config
            print("\n" + "=" * 74)
            print("  INVESTOR SENTIMENT MOMENTUM — v3.1")
            print(f"  Composite: {c.w_drift:.2f}·drift + {c.w_accel:.2f}·accel + "
                  f"{c.w_attention:.2f}·attention + {c.w_consensus:.2f}·consensus")
            print(f"  Halveringstid {c.decay_halflife}d | lookback {c.signal_lookback}d | "
                  f"min artikler {c.min_articles} | z-gulv {c.min_composite_z}")
            pf = (f"SMA{c.price_sma}" + (" + rel.styrke" if c.require_rel_str else "")
                  if c.use_price_filter else "AV")
            print(f"  Prisveto: {pf}  |  Regime: "
                  f"{'SMA' + str(c.regime_sma) if c.use_regime else 'AV'}")
            print(f"  Exits: {c.max_holding_days}d / stop {c.stop_loss_pct*100:.0f}% / "
                  f"trail {c.trail_from_peak*100:.0f}% (etter +{c.trail_min_gain*100:.0f}%)")
            print(f"  Kostnad: {c.transaction_cost*100:.2f}%/side")
            if DIAGNOSE_ONLY:
                print("  *** DIAGNOSEMODUS — ingen handler utføres ***")
            print("=" * 74 + "\n")

            end_date = self.price_df['Date'].max()
            start_date = end_date - timedelta(days=c.backtest_days)
            trading_days = sorted([d for d in self.price_df['Date'].unique()
                                   if start_date <= d <= end_date])
            print(f"Periode: {pd.Timestamp(start_date).date()} → "
                  f"{pd.Timestamp(end_date).date()} ({len(trading_days)} dager)\n")

            rebal_count = 0

            stale_counts = {}
            for date in trading_days:
                prices = self.book.prices_on(date)
                for ticker in self.port.positions:
                    stale_counts[ticker] = 0 if ticker in prices else stale_counts.get(ticker, 0) + 1
                    if stale_counts[ticker] > 5:
                        raise RuntimeError("Sentiment momentum held price missing for more than five sessions: " + ticker)
                if not prices:
                    continue

                # Execute yesterday's price-based exit decisions at today's actual close.
                if not DIAGNOSE_ONLY:
                    self._handle_exits(prices, date)
                self.port.mark(prices)

                regime = self.book.regime_ok(date) if c.use_regime else True
                sig = self.engine.build(self.sent_df, date)

                if DIAGNOSE_ONLY:
                    continue

                if sig.empty:
                    self.port.record(date, prices, regime)
                    continue

                cands = []
                for _, r in sig.iterrows():
                    if len(cands) >= c.max_positions:
                        break
                    t = self.ticker_map.get(r['Company'])
                    if t and t in prices:
                        cands.append((t, r))

                # Kandidatloggen skrives her, før beslutningen: den skal si
                # hva modellen MENTE denne dagen, ikke hva den endte med å
                # eie. Datoen skrives som tekst — skriver pandas en ekte
                # datocelle, blir den til Excels serienummer 45900 på disk,
                # og en leser som venter ÅÅÅÅ-MM-DD forkaster hele loggen.
                try:
                    _valgt = {t for t, _ in cands}
                    _dag = pd.Timestamp(date).strftime('%Y-%m-%d')
                    for _rang, (_, _r) in enumerate(
                            sig.head(SCORE_LOG_TOPP).iterrows(), start=1):
                        _t = self.ticker_map.get(_r['Company'])
                        if not _t:
                            continue
                        self.score_log.append({
                            'Date': _dag,
                            'Ticker': _t,
                            'Composite': round(float(_r['Composite']), 4),
                            'Rank': _rang,
                            'Kandidat': 'JA' if _t in _valgt else 'NEI',
                            'Har_Kurs': 'JA' if _t in prices else 'NEI'})
                except Exception as _e:
                    if not self._score_log_advart:
                        self._score_log_advart = True
                        print(f"  ⚠️  Kandidatloggen feiler ({_e}) — arket "
                              f"Score_Log blir tomt, og master.py mister "
                              f"SentMom som kilde.")

                if not cands:
                    self.port.record(date, prices, regime)
                    continue

                target = set(t for t, _ in cands)
                held = set(self.port.positions.keys())

                # FIX BUG 1: beslutningen tas mot FAKTISKE posisjoner, ikke mot
                # et husket target. Da kan ikke exits desynke logikken, og ledige
                # plasser fylles fortløpende ("jevnt og trutt").
                needs_action = (target != held) and (
                    len(held - target) > 0 or len(held) < c.max_positions)

                if needs_action:
                    rebal_count += 1
                    print(f"\n{'─'*74}")
                    print(f"  {pd.Timestamp(date).date()}  HANDEL #{rebal_count}  "
                          f"({len(cands)}/{c.max_positions} kandidater, "
                          f"{len(held)} holdt)  [{'RISK_ON' if regime else 'RISK_OFF'}]")
                    print(f"{'─'*74}")

                    for t in list(self.port.positions.keys()):
                        if t not in target and prices.get(t):
                            self.port.sell(t, prices[t], date, "Ute av topplisten")

                    weights = self._weights([t for t, _ in cands], date)
                    gross = 1.0 if regime else c.regime_exposure
                    total_val = self.port.value(prices)

                    for t, r in cands:
                        if t in self.port.positions:
                            continue
                        w = weights[t] * gross
                        px = prices[t]
                        shares = int((total_val * w) / (px * (1 + c.transaction_cost)))
                        if self.port.buy(t, r['Company'], px, shares, date,
                                         int(r['Rank']), float(r['Composite']), w):
                            self.signal_log.append({
                                'Date': date, 'Company': r['Company'], 'Ticker': t,
                                'Composite': round(float(r['Composite']), 4),
                                'zDrift': round(float(r['zDrift']), 3),
                                'zAccel': round(float(r['zAccel']), 3),
                                'zAttention': round(float(r['zAttention']), 3),
                                'zConsensus': round(float(r['zConsensus']), 3),
                                'NArticles': int(r['NArticles']),
                                'Rel20d_pct': round(float(r.get('Rel20d', 0)) * 100, 2),
                                'Weight_pct': round(w * 100, 1),
                                'Regime': 'RISK_ON' if regime else 'RISK_OFF'})

                    print(f"  Verdi: {self.port.value(prices):,.0f} NOK | "
                          f"Posisjoner: {len(self.port.positions)}/{c.max_positions} | "
                          f"Win rate: {self.port.win_rate():.1f}%")

                self.port.record(date, prices, regime)

            self.funnel.report(['selskaper_i_vindu', 'etter_min_artikler',
                                'etter_ekstremkutt', 'etter_z_gulv',
                                'etter_prisfilter', 'valgt'])
            if self.funnel.daily:
                pd.DataFrame(self.funnel.daily).to_excel(
                    self.config.funnel_file, index=False)
                print(f"  Funnel-logg: {self.config.funnel_file.name}\n")

            if not DIAGNOSE_ONLY:
                self._save(rebal_count)

        def _save(self, rebal_count):
            c = self.config
            hist = pd.DataFrame(self.port.history)
            if hist.empty:
                print("\n⚠️  Ingen porteføljehistorikk — ingen handelsdager med priser.\n")
                return
            trades = pd.DataFrame(self.port.trades) if self.port.trades else pd.DataFrame()
            sigs = pd.DataFrame(self.signal_log) if self.signal_log else pd.DataFrame()

            hist.to_excel(c.portfolio_file, index=False)
            if not trades.empty:
                trades.to_excel(c.trades_file, index=False)

            # Signalfilen får to ark. «Signals» er handelsloggen som før;
            # «Score_Log» er kandidatloggen master.py rangerer på. Arket
            # skrives selv når det er tomt: et MANGLENDE ark betyr «gammel
            # fil», et TOMT ark betyr «kjørt, men ingenting å logge» — og de
            # to feilene skal ikke se like ut.
            scores = pd.DataFrame(self.score_log) if self.score_log else pd.DataFrame(
                columns=['Date', 'Ticker', 'Composite', 'Rank', 'Kandidat', 'Har_Kurs'])
            with pd.ExcelWriter(str(c.signals_file), engine='openpyxl') as _w:
                (sigs if not sigs.empty
                 else pd.DataFrame(columns=['Date', 'Ticker', 'Composite'])
                 ).to_excel(_w, sheet_name='Signals', index=False)
                scores.to_excel(_w, sheet_name='Score_Log', index=False)
            if scores.empty:
                print("  ⚠️  Score_Log er TOM — master.py teller da SentMom som "
                      "en kilde uten mening om noe selskap.")
            else:
                print(f"  Kandidatlogg: {len(scores)} rader "
                      f"({scores['Ticker'].nunique()} selskaper) → "
                      f"{c.signals_file.name} [Score_Log]")

            start, end = c.start_capital, hist['Portfolio_Value'].iloc[-1]
            ret = (end / start - 1) * 100
            n_days = max((hist['Date'].iloc[-1] - hist['Date'].iloc[0]).days, 1)
            cagr = ((end / start) ** (365.25 / n_days) - 1) * 100
            rets = hist['Portfolio_Value'].pct_change().dropna()
            sharpe = ((rets.mean() * 252 - c.risk_free) / (rets.std() * np.sqrt(252))
                      if rets.std() > 0 else 0.0)
            down = rets[rets < 0]
            sortino = ((rets.mean() * 252 - c.risk_free) / (down.std() * np.sqrt(252))
                       if len(down) > 0 and down.std() > 0 else 0.0)
            cummax = hist['Portfolio_Value'].cummax()
            mdd = ((hist['Portfolio_Value'] - cummax) / cummax).min() * 100
            invested = (hist['Position_Value'] / hist['Portfolio_Value']).mean() * 100

            exit_mix = ""
            if not trades.empty and 'Reason' in trades.columns:
                sells = trades[trades['Action'] == 'SELL']
                if not sells.empty:
                    k = sells['Reason'].str.split().str[0].value_counts()
                    exit_mix = " | ".join(f"{a}:{b}" for a, b in k.items())

            print("\n" + "=" * 74)
            print("  RESULTATER — SENTIMENT MOMENTUM v3.1")
            print("=" * 74)
            print(f"  Startkapital ............ {start:>15,.0f} NOK")
            print(f"  Sluttverdi .............. {end:>15,.0f} NOK")
            print(f"  Total avkastning ........ {ret:>15.2f} %")
            print(f"  CAGR .................... {cagr:>15.2f} %")
            print(f"  Sharpe (rf={c.risk_free:.0%}) ......... {sharpe:>15.3f}")
            print(f"  Sortino ................. {sortino:>15.3f}")
            print(f"  Max drawdown ............ {mdd:>15.2f} %")
            print(f"  Win rate ................ {self.port.win_rate():>15.1f} %")
            print(f"  Snitt holdedager ........ {self.port.avg_holding_days():>15.1f}")
            print(f"  Snitt investert ......... {invested:>15.1f} %")
            print(f"  Gebyrer ................. {self.port.total_fees():>15,.0f} NOK")
            print(f"  Handelsdager ............ {rebal_count:>15}")
            print(f"  Antall handler .......... {len(trades):>15}")
            if exit_mix:
                print(f"  Exit-fordeling .......... {exit_mix}")
            n_sells = len(trades[trades['Action'] == 'SELL']) if not trades.empty else 0
            if n_sells < 20:
                print(f"\n  ⚠️  Kun {n_sells} avsluttede handler. Alle tall over er "
                      f"statistisk meningsløse\n      på dette utvalget — bruk dem "
                      f"til å feilsøke logikken, ikke til å vurdere edge.")
            print("=" * 74 + "\n")

    Backtester(Config()).run()
#SentimentMomentumV31()


##Ledelses-sentiment: fjorten måter å lese det samme datagrunnlaget
def SentimentApproachLab():
    """
    Tester FJORTEN måter å lese ledelsens sentiment på, målt i KRONER.

    Et laboratorium, ikke en strategi: den handler ingenting, sender ingen mail
    og rører ikke master.py. Den svarer på ett spørsmål — finnes det en lesemåte
    av dette datagrunnlaget som faktisk gir avkastning?

    ─────────────────────────────────────────────────────────────────────────
    HVA FØRSTE KJØRING VISTE, OG HVA SOM ER ENDRET

    Ti lesemåter ga alle mellom −0,9 % og −2,6 % «meravkastning» mot OSEBX.
    Det var ikke ti uavhengige nederlag: OSEBX er kapitalvektet og dominert av
    Equinor, DNB og Mowi, mens artikkeluniverset er 274 LIKEVEKTEDE navn,
    overveiende små. Fem likevektede småselskaper mot en storselskapsindeks
    måler størrelse, ikke sentiment.

    Nå måles absolutt avkastning på en sammenhengende equity-kurve i stedet:
    kjøp topp N, hold til neste rebalansering, gjenta, la det renteberegne.
    Det er tallet du sitter igjen med.

    Én kolonne står igjen som kontroll — TILFELDIG, altså snittet av ALLE
    kandidater samme måned. Den er ikke en referanseindeks, men svaret på
    «tjente vi på rangeringen, eller ville pil og blink gitt det samme?».
    Ligger en lesemåte likt med TILFELDIG, er koden verdiløs uansett hvor
    hyggelig avkastningen ser ut.

    To feil i forrige utgave er rettet. «rel. markedet» trakk fra et tall som
    var likt for alle selskaper samme dato, noe som ikke endrer en rangering —
    raden var identisk med «nivå» på hvert siffer, og lesemåten har aldri
    eksistert. Og porten krevde 40 observasjoner der 3,3 år gir maks 39
    måneder, så den kunne aldri åpne.

    ─────────────────────────────────────────────────────────────────────────
    HVA DATAENE PEKTE PÅ

    Kvintilspredningen — topp mot bunn innenfor samme univers, det ene målet
    som ikke påvirkes av hvilken indeks man sammenligner med — viste en tydelig
    gradient:

        vedvarende (to forbedringer på rad)   +3,29 %
        vendepunkt (brudd over egen median)   +3,10 %
        akselerasjon                          +0,49 %
        z mot egen historikk                  +0,18 %
        ren endring                           −0,08 %
        NIVÅ                                  −1,73 %
        endring + SMA-filter                  −1,86 %

    Jo mer lesemåten krever en VEDVARENDE endring, jo bedre rangerer den. Rent
    nivå rangerer verst — den kroniske optimisten er verdiløs, akkurat som
    hypotesen sa. Og prisfilteret gjorde det verre, ikke bedre.

    Derfor er utvalget her vridd kraftig mot endring: elleve av fjorten leser
    endringen på hver sin måte, tre er kontroller vi vet svaret på.

    ─────────────────────────────────────────────────────────────────────────
    KJØRING

        SentimentApproachLab()

    Leser artiklene som ligger i DataNLP — skraper ingenting. Noen minutter.
    """

    import logging
    import warnings
    from dataclasses import dataclass
    from datetime import datetime, timedelta
    from pathlib import Path
    from typing import Callable, Dict, List, Optional, Tuple

    import numpy as np
    import pandas as pd
    import yfinance as yf

    warnings.filterwarnings("ignore")
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s  %(levelname)-8s  %(message)s",
                        datefmt="%H:%M:%S")
    log = logging.getLogger("SentLab")

    # ═════════════════════════════════════════════════════════════════════════
    # OPPSETT
    # ═════════════════════════════════════════════════════════════════════════

    @dataclass
    class Config:
        base_dir: Path = Path(os.environ.get(
            "AKSJE_BASE_DIR", r"C:\Users\ander\Desktop\Python_K4\ExcelData"))
        nlp_output_dir: str = "DataNLP"
        output_dir: str = "StrategyResults_v4_Sentiment"
        oslo_suffix: str = ".OL"

        startkapital: float = 1_000_000.0
        topp_n: int = 5
        # Holdeperioden ER rebalanseringsintervallet. Da overlapper ikke
        # avkastningene, og kurven kan renteberegnes uten å telle samme
        # måned to ganger.
        hold_dager: int = 21
        # Ekstra horisonter, kun som hendelsesstatistikk. De overlapper og kan
        # derfor IKKE renteberegnes — de står der for å svare på om signalet er
        # tregt, ikke for å vise en kurve.
        ekstra_horisonter: Tuple[int, ...] = (63, 126)

        inn_utvalg_slutt: str = "2025-06-30"
        min_rapporter: int = 3
        maks_alder_dager: int = 400
        # Færre enn dette, og en t-verdi er en tilfeldighet med desimaler.
        min_maaneder: int = 20

        @property
        def nlp_dir(self) -> Path:
            return self.base_dir / self.nlp_output_dir

        @property
        def ut_dir(self) -> Path:
            p = self.base_dir / self.output_dir
            p.mkdir(parents=True, exist_ok=True)
            return p

    config = Config()

    # ═════════════════════════════════════════════════════════════════════════
    # DATA
    # ═════════════════════════════════════════════════════════════════════════

    def les_artikler() -> pd.DataFrame:
        """Alle artikkelfilene, slått sammen og avduplisert."""
        filer = sorted(p for p in config.nlp_dir.glob("NLP_Sentiment_Detail_*.xlsx")
                       if not p.name.startswith("~$"))
        if not filer:
            raise FileNotFoundError(f"Ingen artikkelfiler i {config.nlp_dir}")

        deler = []
        for f in filer:
            try:
                d = pd.read_excel(f)
            except Exception:
                continue
            if not d.empty and "Article_Date" in d.columns:
                d["_fil"] = f.name
                deler.append(d)
        if not deler:
            raise FileNotFoundError(f"Ingen lesbare artikkelfiler i {config.nlp_dir}")

        df = pd.concat(deler, ignore_index=True)
        df["Article_Date"] = (df["Article_Date"].astype(str)
                              .str.replace(r"\n.*$", "", regex=True).str.strip())
        df["Article_Date"] = pd.to_datetime(df["Article_Date"],
                                            format="%d %b %Y", errors="coerce")
        df = df.dropna(subset=["Article_Date"])
        if "Text_Length" in df.columns:
            df = df[df["Text_Length"] > 0]
        if "Final_Score" not in df.columns:
            raise KeyError("Artikkelfilene mangler Final_Score.")
        df["Final_Score"] = pd.to_numeric(df["Final_Score"], errors="coerce")
        df = df.dropna(subset=["Final_Score"])

        nokler = [k for k in ("Company", "Article_Date", "Article_Title")
                  if k in df.columns]
        if nokler:
            df = df.sort_values("_fil").drop_duplicates(subset=nokler, keep="last")
        df = df.sort_values(["Company", "Article_Date"]).reset_index(drop=True)

        log.info("Artikler : %d fra %d fil(er), %d selskaper, %s → %s",
                 len(df), len(deler), df["Company"].nunique(),
                 df["Article_Date"].min().date(), df["Article_Date"].max().date())
        return df

    def hent_kurser(tickere: List[str]) -> Tuple[pd.DataFrame, pd.DataFrame]:
        log.info("Kurser   : laster ned %d tickere …", len(tickere))
        data = yf.download(tickere, start="2019-01-01", auto_adjust=True,
                           progress=False)
        if data.empty:
            raise RuntimeError("yfinance ga ingen data.")
        if isinstance(data.columns, pd.MultiIndex):
            kurs = data["Close"].copy()
            volum = (data["Volume"].copy() if "Volume" in data.columns.levels[0]
                     else pd.DataFrame(index=kurs.index))
        else:
            kurs = data[["Close"]].copy(); kurs.columns = tickere[:1]
            volum = data[["Volume"]].copy(); volum.columns = tickere[:1]
        for d in (kurs, volum):
            d.index = pd.to_datetime(d.index)
            d.sort_index(inplace=True)
        kurs = kurs[[c for c in kurs.columns if kurs[c].count() >= 120]]
        log.info("Kurser   : %d tickere med nok historikk, %s → %s",
                 len(kurs.columns), kurs.index[0].date(), kurs.index[-1].date())
        return kurs, volum

    # ═════════════════════════════════════════════════════════════════════════
    # DE FJORTEN LESEMÅTENE
    # ═════════════════════════════════════════════════════════════════════════
    #
    # Hver får selskapets rapporter FØR handledagen, nyeste først, pluss kurs og
    # volum. Hver returnerer ett tall — høyere er mer positivt — eller None for
    # «ingen mening i dag». None er et ekte svar: en lesemåte som krever et
    # vendepunkt skal tie de månedene ingen vender.

    @dataclass
    class Pakke:
        scorer: np.ndarray
        datoer: List[pd.Timestamp]
        dato: pd.Timestamp
        kurs: pd.Series
        volum: pd.Series

    def _hist(p: Pakke) -> Optional[Tuple[np.ndarray, float, float]]:
        """(historikk uten siste, median, standardavvik) — eller None."""
        if len(p.scorer) < config.min_rapporter + 1:
            return None
        h = p.scorer[1:]
        sd = float(np.std(h, ddof=1))
        if sd < 1e-6:
            return None
        return h, float(np.median(h)), sd

    def _over_sma(p: Pakke, dager: int) -> bool:
        k = p.kurs.dropna()
        return len(k) >= dager and float(k.iloc[-1]) > float(k.iloc[-dager:].mean())

    def _volumbekreftelse(p: Pakke, dager: int = 60) -> float:
        v = p.volum.dropna()
        if len(v) < dager:
            return 1.0
        med = float(v.iloc[-dager:].median())
        return float(v.iloc[-5:].mean()) / med if med > 0 else 1.0

    def _forbedringer(p: Pakke) -> List[float]:
        """Endringene mellom påfølgende rapporter, nyeste først."""
        return [float(p.scorer[i] - p.scorer[i + 1])
                for i in range(len(p.scorer) - 1)]

    # ── KONTROLLER — vi vet omtrent svaret, og de er med for å bevise det ────

    def a_nivaa(p: Pakke) -> Optional[float]:
        """Referansen: hvor positiv ledelsen er, absolutt. Rangerte verst."""
        return float(p.scorer[0]) if len(p.scorer) else None

    def a_delta_rapport(p: Pakke) -> Optional[float]:
        """Ren endring: siste rapport minus forrige. Hypotesen i enkleste form."""
        return float(p.scorer[0] - p.scorer[1]) if len(p.scorer) >= 2 else None

    def a_endring_volum(p: Pakke) -> Optional[float]:
        """
        Endringen skalert med om noen faktisk handlet på den.

        Med som kontroll: volumbekreftelse gjorde det VERRE forrige gang
        (−0,60 %). Beholdt for å se om det holder seg når målet er absolutt.
        """
        d = a_delta_rapport(p)
        return None if d is None else float(d * min(_volumbekreftelse(p), 3.0))

    # ── ENDRING MOT SELSKAPETS EGEN MÅLESTOKK ───────────────────────────────

    def a_z_selskap(p: Pakke) -> Optional[float]:
        """
        Siste rapport mot selskapets egen historikk.

        Kuren mot den kroniske optimisten: skriver en ledelse alltid at det går
        strålende, ligger snittet høyt og z rundt null.
        """
        h = _hist(p)
        if h is None:
            return None
        hist, _, sd = h
        return float((p.scorer[0] - np.mean(hist)) / sd)

    def a_delta_normalisert(p: Pakke) -> Optional[float]:
        """
        Endringen delt på selskapets TYPISKE endringsstørrelse.

        En bevegelse på 0,05 er mye for en ledelse som pleier å flytte seg
        0,01, og ingenting for en som svinger 0,20 hver gang. Rå delta
        rangerer de to likt; dette gjør ikke det.
        """
        f = _forbedringer(p)
        if len(f) < config.min_rapporter:
            return None
        typisk = float(np.mean(np.abs(f[1:])))
        return float(f[0] / typisk) if typisk > 1e-6 else None

    # ── ENDRINGENS RETNING OVER TID ─────────────────────────────────────────

    def a_akselerasjon(p: Pakke) -> Optional[float]:
        """Øker forbedringen? (s0−s1) − (s1−s2)."""
        if len(p.scorer) < 3:
            return None
        return float((p.scorer[0] - p.scorer[1]) - (p.scorer[1] - p.scorer[2]))

    def a_helning(p: Pakke) -> Optional[float]:
        """
        Regresjonshelningen gjennom de fire siste rapportene.

        Én rapport kan være en god kvartalsslutt eller en ny
        kommunikasjonssjef. Helningen bruker alle fire og lar dem stemme, så en
        enkelt bråkete rapport ikke avgjør. Skalert med selskapets eget
        standardavvik, ellers måler den bare hvem som svinger mest.
        """
        h = _hist(p)
        if h is None or len(p.scorer) < 4:
            return None
        _, _, sd = h
        y = p.scorer[:4][::-1]                    # eldste først
        helning = float(np.polyfit(np.arange(len(y)), y, 1)[0])
        return helning / sd

    def a_konsistens(p: Pakke) -> Optional[float]:
        """
        Hvor stor andel av de siste fire endringene som var forbedringer,
        ganget med samlet styrke.

        Tre av fire opp er en retning. To av fire er en mynt. Forskjellen
        mellom dem er nettopp det «vedvarende» fanget opp forrige gang.
        """
        f = _forbedringer(p)[:4]
        if len(f) < 3:
            return None
        h = _hist(p)
        if h is None:
            return None
        _, _, sd = h
        andel = float(np.mean([x > 0 for x in f]))
        return float(andel * (sum(f) / sd))

    # ── VEDVARENDE ENDRING — den som rangerte best ──────────────────────────

    def a_vedvarende2(p: Pakke) -> Optional[float]:
        """To forbedringer på rad. Beste kvintilspredning forrige runde."""
        f = _forbedringer(p)
        if len(f) < 2 or f[0] <= 0 or f[1] <= 0:
            return None
        return float(f[0] + f[1])

    def a_vedvarende3(p: Pakke) -> Optional[float]:
        """
        Tre på rad. Strengere, fyrer sjeldnere.

        Hvis gradienten fra forrige kjøring er ekte — mer bekreftelse, bedre
        rangering — skal denne slå to på rad. Gjør den ikke det, har vi funnet
        toppen av kurven, og det er like nyttig å vite.
        """
        f = _forbedringer(p)
        if len(f) < 3 or any(x <= 0 for x in f[:3]):
            return None
        return float(sum(f[:3]))

    def a_vedvarende_vektet(p: Pakke) -> Optional[float]:
        """
        To på rad, men vektet med hvor stor bevegelsen er i selskapets egen
        målestokk. Skiller en ledelse som krøp oppover fra en som tok et sprang.
        """
        v = a_vedvarende2(p)
        h = _hist(p)
        if v is None or h is None:
            return None
        return float(v / h[2])

    # ── BRUDD ───────────────────────────────────────────────────────────────

    def _vendepunkt(p: Pakke, terskel: float) -> Optional[float]:
        """
        Krysser selskapet sitt eget normalnivå nedenfra?

        To krav, begge målt i selskapets standardavvik: NÅ tydelig over, og
        FORRIGE gang ikke. Første krav skiller brudd fra støy — en ledelse på
        0,79–0,81 krysser sin egen median annenhver rapport uten å si noe nytt.
        Andre krav gjør det til et vendepunkt og ikke en tilstand: satt den
        allerede der forrige kvartal, er nyheten gammel.
        """
        h = _hist(p)
        if h is None:
            return None
        _, median, sd = h
        z_naa = (float(p.scorer[0]) - median) / sd
        z_for = (float(p.scorer[1]) - median) / sd
        if z_naa < terskel or z_for >= terskel:
            return None
        return float(z_naa)

    def a_vendepunkt(p: Pakke) -> Optional[float]:
        """Brudd over egen median. Nest beste kvintilspredning forrige runde."""
        return _vendepunkt(p, 0.5)

    def a_vendepunkt_sterk(p: Pakke) -> Optional[float]:
        """Samme, men bruddet må være stort (1,5 standardavvik). Færre, tydeligere."""
        return _vendepunkt(p, 1.5)

    def a_snu_fra_bunn(p: Pakke) -> Optional[float]:
        """
        Selskaper som lå i BUNNEN av sitt eget spenn og nå er tydelig over.

        Den dypeste formen for hypotesen: ikke bare «bedre enn vanlig», men
        «har snudd fra sitt eget bunnivå». Fyrer sjelden — og skal det.
        """
        h = _hist(p)
        if h is None or len(p.scorer) < 4:
            return None
        hist, _, sd = h
        bunn = float(np.percentile(hist, 25))
        var_i_bunn = float(p.scorer[1]) <= bunn
        naa_over = (float(p.scorer[0]) - bunn) / sd >= 1.0
        if not (var_i_bunn and naa_over):
            return None
        return float((p.scorer[0] - bunn) / sd)

    # ── KOMBINASJON AV DE TO SOM VIRKET ─────────────────────────────────────

    def a_brudd_og_vedvarende(p: Pakke) -> Optional[float]:
        """
        Begge vinnerne samtidig: et brudd som ALLEREDE har vart.

        De to rangerte best hver for seg. Måler de det samme, gir denne
        ingenting nytt. Måler de forskjellige ting, skal snittet av to
        uavhengige signaler være bedre enn hvert av dem.
        """
        b = _vendepunkt(p, 0.5)
        v = a_vedvarende_vektet(p)
        if b is None or v is None:
            return None
        return float(0.5 * (b + v))

    APPROACHER: Dict[str, Tuple[Callable, str]] = {
        "1 nivå":            (a_nivaa, "KONTROLL — absolutt nivå"),
        "2 delta-rapport":   (a_delta_rapport, "KONTROLL — ren endring"),
        "3 endring+volum":   (a_endring_volum, "KONTROLL — endring × omsetning"),
        "4 z-selskap":       (a_z_selskap, "mot egen historikk"),
        "5 delta-normalis.": (a_delta_normalisert, "endring / egen typisk endring"),
        "6 akselerasjon":    (a_akselerasjon, "øker forbedringen?"),
        "7 helning":         (a_helning, "retning gjennom fire rapporter"),
        "8 konsistens":      (a_konsistens, "andel opp × styrke"),
        "9 vedvarende-2":    (a_vedvarende2, "to forbedringer på rad"),
        "10 vedvarende-3":   (a_vedvarende3, "tre på rad"),
        "11 vedv.-vektet":   (a_vedvarende_vektet, "to på rad, i egen målestokk"),
        "12 vendepunkt":     (a_vendepunkt, "brudd over egen median"),
        "13 vendep.-sterk":  (a_vendepunkt_sterk, "brudd på 1,5 sd"),
        "14 snu-fra-bunn":   (a_snu_fra_bunn, "opp fra eget bunnivå"),
        "15 brudd+vedvar.":  (a_brudd_og_vedvarende, "brudd som allerede har vart"),
    }

    # ═════════════════════════════════════════════════════════════════════════
    # MÅLINGEN — I KRONER
    # ═════════════════════════════════════════════════════════════════════════

    def avkastning(kurs: pd.Series, dato: pd.Timestamp,
                   dager: int) -> Optional[float]:
        """Absolutt avkastning fra `dato` og `dager` handledager fram."""
        try:
            i = kurs.index.searchsorted(dato)
            j = i + dager
            if j >= len(kurs.index):
                return None
            k0, k1 = float(kurs.iloc[i]), float(kurs.iloc[j])
            if not (np.isfinite(k0) and np.isfinite(k1)) or k0 <= 0:
                return None
            return k1 / k0 - 1.0
        except Exception:
            return None

    def t_verdi(x: List[float]) -> Optional[float]:
        if len(x) < 3:
            return None
        sd = float(np.std(x, ddof=1))
        return float(np.mean(x) / (sd / np.sqrt(len(x)))) if sd > 1e-12 else None

    def maks_fall(kurve: List[float]) -> float:
        topp, verst = kurve[0], 0.0
        for v in kurve:
            topp = max(topp, v)
            verst = min(verst, v / topp - 1.0)
        return verst

    def kjor_maalingen(artikler: pd.DataFrame, kurs: pd.DataFrame,
                       volum: pd.DataFrame) -> pd.DataFrame:
        kart = {c: str(c).strip() + config.oslo_suffix
                for c in artikler["Company"].dropna().unique()
                if str(c).strip() and str(c).strip() != "nan"}
        kart = {c: t for c, t in kart.items() if t in kurs.columns}
        log.info("Kobling  : %d av %d selskaper har kurser",
                 len(kart), artikler["Company"].nunique())
        if not kart:
            raise RuntimeError("Ingen selskaper lot seg koble mot kurser.")

        per_selskap = {c: d for c, d in artikler.groupby("Company") if c in kart}
        datoer = list(pd.date_range(
            artikler["Article_Date"].min(),
            min(kurs.index[-1], pd.Timestamp(datetime.now().date())), freq="ME"))
        delingsdato = pd.Timestamp(config.inn_utvalg_slutt)

        rader: List[dict] = []
        for navn, (funksjon, _) in APPROACHER.items():
            for dato in datoer:
                dagens: List[Tuple[str, float]] = []
                for selskap, d in per_selskap.items():
                    hist = d[(d["Article_Date"] < dato) &
                             (d["Article_Date"] >= dato - timedelta(
                                 days=config.maks_alder_dager))]
                    if hist.empty:
                        continue
                    hist = hist.sort_values("Article_Date", ascending=False)
                    ticker = kart[selskap]
                    k = kurs[ticker]
                    k = k[k.index <= dato].dropna()
                    if len(k) < 60:
                        continue
                    v = volum[ticker] if ticker in volum.columns else pd.Series(dtype=float)
                    v = v[v.index <= dato].dropna() if len(v) else v
                    pakke = Pakke(scorer=hist["Final_Score"].to_numpy(dtype=float),
                                  datoer=list(hist["Article_Date"]),
                                  dato=dato, kurs=k, volum=v)
                    try:
                        s = funksjon(pakke)
                    except Exception:
                        s = None
                    if s is not None and np.isfinite(s):
                        dagens.append((ticker, float(s)))

                if len(dagens) < config.topp_n * 2:
                    continue
                dagens.sort(key=lambda x: -x[1])

                def snitt(gruppe, dager):
                    v = [avkastning(kurs[t], dato, dager) for t, _ in gruppe]
                    v = [x for x in v if x is not None]
                    return float(np.mean(v)) if v else None

                topp = snitt(dagens[:config.topp_n], config.hold_dager)
                if topp is None:
                    continue
                # TILFELDIG: snittet av ALLE kandidater samme måned. Ikke en
                # indeks — svaret på om rangeringen var verdt noe.
                tilfeldig = snitt(dagens, config.hold_dager)
                bunn = snitt(dagens[-config.topp_n:], config.hold_dager)

                rad = {"approach": navn, "dato": dato, "n_kandidater": len(dagens),
                       "topp": topp, "tilfeldig": tilfeldig, "bunn": bunn,
                       "utvalg": "INN" if dato <= delingsdato else "UT"}
                for h in config.ekstra_horisonter:
                    rad[f"topp_{h}d"] = snitt(dagens[:config.topp_n], h)
                rader.append(rad)
            log.info("  %-18s ferdig", navn)
        return pd.DataFrame(rader)

    def oppsummer(m: pd.DataFrame) -> pd.DataFrame:
        ut = []
        for navn, (_, forklaring) in APPROACHER.items():
            d = m[m["approach"] == navn].sort_values("dato")
            r = d["topp"].dropna().tolist()
            if not r:
                continue
            # Equity-kurven: holdeperioden ER rebalanseringsintervallet, så
            # avkastningene overlapper ikke og kan renteberegnes.
            kurve = [config.startkapital]
            for x in r:
                kurve.append(kurve[-1] * (1.0 + x))
            aar = len(r) / 12.0
            total = kurve[-1] / kurve[0] - 1.0

            tilf = d["tilfeldig"].dropna().tolist()
            kurve_t = [config.startkapital]
            for x in tilf:
                kurve_t.append(kurve_t[-1] * (1.0 + x))

            uto = d[d["utvalg"] == "UT"]["topp"].dropna().tolist()
            kurve_u = [config.startkapital]
            for x in uto:
                kurve_u.append(kurve_u[-1] * (1.0 + x))
            aar_u = len(uto) / 12.0

            sd = float(np.std(r, ddof=1)) if len(r) > 1 else 0.0
            ut.append({
                "Lesemåte": navn, "Idé": forklaring, "Mnd": len(r),
                "Snitt_Kand": float(d["n_kandidater"].mean()),
                "Slutt_NOK": kurve[-1],
                "Total_Pst": total * 100.0,
                "CAGR_Pst": (((kurve[-1] / kurve[0]) ** (1 / aar) - 1) * 100.0
                             if aar >= 0.5 else np.nan),
                "MaxDD_Pst": maks_fall(kurve) * 100.0,
                "Sharpe": (float(np.mean(r)) * 12 / (sd * np.sqrt(12))
                           if sd > 1e-12 else np.nan),
                "Treff_Pst": float(np.mean([x > 0 for x in r])) * 100.0,
                "Mnd_Pst": float(np.mean(r)) * 100.0,
                "t": t_verdi(r),
                "Tilfeldig_Pst": (((kurve_t[-1] / kurve_t[0]) ** (1 / (len(tilf) / 12.0)) - 1)
                                  * 100.0 if len(tilf) >= 6 else np.nan),
                "UT_CAGR_Pst": (((kurve_u[-1] / kurve_u[0]) ** (1 / aar_u) - 1) * 100.0
                                if aar_u >= 0.5 else np.nan),
                "Topp_minus_Bunn_Pst": float(
                    np.mean([a - b for a, b in zip(d["topp"], d["bunn"])
                             if pd.notna(a) and pd.notna(b)] or [np.nan])) * 100.0,
                "H63_Pst": float(d["topp_63d"].dropna().mean()) * 100.0
                if d["topp_63d"].notna().any() else np.nan,
                "H126_Pst": float(d["topp_126d"].dropna().mean()) * 100.0
                if d["topp_126d"].notna().any() else np.nan,
            })
        return pd.DataFrame(ut)

    # ═════════════════════════════════════════════════════════════════════════
    # RAPPORT
    # ═════════════════════════════════════════════════════════════════════════

    def _t(v, d=2, sfx=""):
        return "—" if v is None or (isinstance(v, float) and not np.isfinite(v)) \
            else f"{v:.{d}f}{sfx}"

    def skriv_rapport(s: pd.DataFrame) -> None:
        print("\n" + "=" * 118)
        print("  LEDELSES-SENTIMENT — FJORTEN LESEMÅTER, MÅLT I KRONER")
        print("=" * 118)
        print(f"  Kjøp topp {config.topp_n}, hold {config.hold_dager} handledager, "
              f"rebalanser, renteberegn. Start {config.startkapital:,.0f} kr."
              .replace(",", " "))
        print(f"  «Tilfeldig» = snittet av ALLE kandidater samme måned — "
              f"det pil og blink ville gitt fra samme pool.\n")
        print(f"  {'Lesemåte':<18}{'Mnd':>4}{'Kand':>6}{'Slutt NOK':>12}"
              f"{'CAGR':>9}{'MaxDD':>9}{'Sharpe':>8}{'Treff':>7}{'t':>6}"
              f"{'Tilfeldig':>10}{'UT CAGR':>9}{'T−B':>7}")
        print("  " + "-" * 114)
        for _, r in s.sort_values("CAGR_Pst", ascending=False).iterrows():
            print(f"  {r['Lesemåte']:<18}{int(r['Mnd']):>4}"
                  f"{r['Snitt_Kand']:>6.0f}{r['Slutt_NOK']:>12,.0f}"
                  f"{_t(r['CAGR_Pst'], 1, '%'):>9}{_t(r['MaxDD_Pst'], 1, '%'):>9}"
                  f"{_t(r['Sharpe']):>8}{_t(r['Treff_Pst'], 0, '%'):>7}"
                  f"{_t(r['t']):>6}{_t(r['Tilfeldig_Pst'], 1, '%'):>10}"
                  f"{_t(r['UT_CAGR_Pst'], 1, '%'):>9}"
                  f"{_t(r['Topp_minus_Bunn_Pst'], 1, '%'):>7}"
                  .replace(",", " "))

        print(f"\n  Tregere horisonter (snitt per signal, IKKE renteberegnet — "
              f"de overlapper):")
        print(f"  {'Lesemåte':<18}{'21d':>9}{'63d':>9}{'126d':>9}")
        print("  " + "-" * 45)
        for _, r in s.sort_values("CAGR_Pst", ascending=False).head(6).iterrows():
            print(f"  {r['Lesemåte']:<18}{_t(r['Mnd_Pst'], 2, '%'):>9}"
                  f"{_t(r['H63_Pst'], 2, '%'):>9}{_t(r['H126_Pst'], 2, '%'):>9}")

        gyldige = s.dropna(subset=["CAGR_Pst"])
        gyldige = gyldige[gyldige["Mnd"] >= config.min_maaneder]
        if gyldige.empty:
            print("\n  Ingen lesemåte fikk nok måneder til å dømmes.")
            print("=" * 118 + "\n")
            return

        beste = gyldige.sort_values("CAGR_Pst", ascending=False).iloc[0]
        nivaa = s[s["Lesemåte"] == "1 nivå"]
        nivaa_cagr = float(nivaa["CAGR_Pst"].iloc[0]) if len(nivaa) else np.nan

        krav = {
            "positiv CAGR": beste["CAGR_Pst"] > 0,
            "positiv også på ut-utvalget": (np.isfinite(beste["UT_CAGR_Pst"])
                                            and beste["UT_CAGR_Pst"] > 0),
            "slår tilfeldig plukk fra samme pool":
                (not np.isfinite(beste["Tilfeldig_Pst"])
                 or beste["CAGR_Pst"] > beste["Tilfeldig_Pst"]),
            "rangerer i begge ender (topp > bunn)":
                (np.isfinite(beste["Topp_minus_Bunn_Pst"])
                 and beste["Topp_minus_Bunn_Pst"] > 0),
            "t over 2,5 (14 forsøk)": beste["t"] is not None and beste["t"] > 2.5,
            "slår «1 nivå»": (not np.isfinite(nivaa_cagr)
                              or beste["CAGR_Pst"] > nivaa_cagr),
        }
        print(f"\n  BESTE: «{beste['Lesemåte']}» — CAGR {_t(beste['CAGR_Pst'], 1, ' %')}, "
              f"slutt {beste['Slutt_NOK']:,.0f} kr, maxDD "
              f"{_t(beste['MaxDD_Pst'], 1, ' %')}".replace(",", " "))
        print(f"  Tilfeldig plukk fra samme pool: "
              f"{_t(beste['Tilfeldig_Pst'], 1, ' %')} · "
              f"«1 nivå»: {_t(nivaa_cagr, 1, ' %')}\n")
        print("  PORTEN:")
        for tekst, ok in krav.items():
            print(f"    {'✓' if ok else '✗'}  {tekst}")
        if all(krav.values()):
            print("\n  ✅ PORTEN ER ÅPEN. Bygg en strategi på denne — med friksjon,")
            print("     og med en ekte backtest før du handler på den.")
        else:
            print("\n  🚫 PORTEN ER STENGT. Ingen lesemåte klarer alle kravene.")
            print("     Se hvilke haker som mangler: er det bare t-verdien, har du")
            print("     et svakt signal og for lite data. Er det «slår tilfeldig",)
            print("     plukk», tjener du på universet og ikke på rangeringen.")

        spenn = float(gyldige["CAGR_Pst"].max() - gyldige["CAGR_Pst"].median())
        print(f"\n  Spennet fra median til best er {spenn:.1f} prosentpoeng CAGR.")
        print("  Fjorten lesemåter er prøvd på de samme dataene — den beste raden")
        print("  er delvis heldig. Les den som en hypotese, ikke som et resultat.")
        print("=" * 118 + "\n")

    # ═════════════════════════════════════════════════════════════════════════
    # HOVEDLØP
    # ═════════════════════════════════════════════════════════════════════════

    log.info("=" * 74)
    log.info("  SENTIMENT APPROACH LAB — fjorten lesemåter, målt i kroner")
    log.info("=" * 74)

    artikler = les_artikler()
    tickere = sorted({str(c).strip() + config.oslo_suffix
                      for c in artikler["Company"].dropna().unique()
                      if str(c).strip() and str(c).strip() != "nan"})
    kurs, volum = hent_kurser(tickere)

    maalinger = kjor_maalingen(artikler, kurs, volum)
    if maalinger.empty:
        log.error("Ingen målinger — artiklene og kursene overlapper ikke.")
        return

    sammendrag = oppsummer(maalinger)
    skriv_rapport(sammendrag)

    sti = config.ut_dir / f"Sentiment_ApproachLab_{datetime.now():%Y-%m-%d}.xlsx"
    with pd.ExcelWriter(str(sti), engine="openpyxl") as w:
        sammendrag.to_excel(w, sheet_name="Sammendrag", index=False)
        maalinger.to_excel(w, sheet_name="Maalinger", index=False)
        (maalinger.pivot_table(index="dato", columns="approach", values="topp")
         .to_excel(w, sheet_name="Maanedsavkastning"))
    log.info("Skrevet  : %s", sti)
    log.info("=== SentimentApproachLab ferdig ===")
#SentimentApproachLab()


##Ledelses-sentiment: hendelsesdrevet — 12 innganger × 32 exit, og én produksjonsfil
def SentimentHendelseLab(skriv_master: bool = True):
    """
    Kjøper på DAGEN rapporten kommer, hvis tonen har bedret seg nok.

    Tolv inngangsstrategier på én idé. Seks terskler for hvor stor bedringen fra
    selskapets FORRIGE rapport må være, og de samme seks igjen med krav om
    kurs over SMA50 på kjøpsdagen:

        S1  ≥ 20 %      S7   ≥ 20 %  + SMA50
        S2  ≥ 50 %      S8   ≥ 50 %  + SMA50
        S3  ≥ 85 %      S9   ≥ 85 %  + SMA50
        S4  ≥ 135 %     S10  ≥ 135 % + SMA50
        S5  ≥ 200 %     S11  ≥ 200 % + SMA50
        S6  ≥ 300 %     S12  ≥ 300 % + SMA50

    Denne utgaven beholder inngangslogikken, men tester MANGE forskjellige
    salgsmetoder på hver av de tolv inngangsstrategiene. Resultatet blir derfor
    én rad per kombinasjon av inngangsstrategi og exit-strategi.

    EXIT-ALTERNATIVER SOM TESTES
    ----------------------------
      * Faste hold: 3, 5, 8, 10, 15, 21, 30, 42 og 63 handledager.
      * Alpha-plateau: velg robust holdetid KUN på INN-utvalget.
      * Neste rapport.
      * Sentimentreversering.
      * Kurs under SMA50, SMA10 eller EMA20.
      * Fast stop-loss: -5 %, -8 %, -10 %.
      * ATR20-stop: 2.0x, 2.5x, 3.0x ATR.
      * Trailing stop: 10 % og 2.5x ATR.
      * Profit target: +5 %, +10 %, +15 %.
      * Kombinert +10 % target / -7 % stop.
      * Break-even etter at handelen først har vært +5 %.
      * Relativ exit hvis aksjen ligger 3 prosentpoeng bak markedet.
      * Kapasitets-erstatning når en mye sterkere ny hendelse kommer.
      * Hybrid: alpha-horisont + sentimentreversering + erstatning.
      * Hybrid + ATR3: samme, med katastrofestopp på 3x ATR.

    VIKTIGE ENDRINGER FRA ORIGINALEN
    --------------------------------
      1) Dynamiske exits krever dag-for-dag-simulering. Porteføljen markeres
         derfor til markedet hver handledag. MaxDD blir dermed en reell daglig
         drawdown, ikke bare en funksjon av realiserte handler.

      2) Markedsavkastningen beregnes over HVER HANDELS FAKTISKE inn/ut-vindu.
         Det er nødvendig når ulike exit-regler gir ulike holdetider.

      3) Dag+1 er fortsatt en robusthetssjekk mot samme-dags look-ahead. For
         dynamiske exits brukes samme faktiske antall holdedager som handelen,
         men inngangen forskyves én handledag.

      4) Nyhetsbaserte exits utføres som standard én handledag etter artikkelen,
         fordi artikkelklokkeslettet er strippet bort og vi ikke vet om nyheten
         kom før eller etter børsslutt.

    ─────────────────────────────────────────────────────────────────────────
    DETTE ER OGSÅ KILDEN master.py LESER  (skriv_master=True)
    ─────────────────────────────────────────────────────────────────────────
    Laben er et laboratorium: 12 × 32 = 384 backtester, ingen portefølje. Master
    trenger det motsatte — ÉN kombinasjon, med én scorelogg og ett sett
    nøkkeltall. Derfor velges én til slutt og skrives som

        StrategyResults_v4_Sentiment/Sentiment_v6_Hendelse_SMA50_<dato>.xlsx

    med akkurat de arkene master.py og mail/mail_strategier.py allerede leser:
    «Score_Log», «Metrics», «Equity_Curve», «Monthly_Holdings», «Trade_Log»,
    «Posisjoner_Na».

    HVILKEN KOMBINASJON? Den samme PORTEN rapporten selv stiller opp — slår
    markedet, positiv snitthandel, positiv også på ut-utvalget, positiv alpha på
    ut-utvalget, holder seg med kjøp dagen etter, nok handler, gulvet binder på
    under 30 %. Består ingen, skrives filen likevel (master skal ikke miste en
    fjerdedel av grunnlaget sitt), men da står «porten_bestod = NEI» i Metrics og
    mailkortet får en rød IKKE ROBUST-boks. Overstyres med

        set AKSJE_SENT_VALG=S1|TP10          (inngang | exit-kode)

    ALLE MÅLTE TALL I MAILEN ER LABENS EGEN RAD, uregnet — CAGR, total,
    drawdown, treffrate, snitt handel, alpha. En egen «live»-kjøring uten
    modenhetsfilter og uten tvangssalg eier BARE posisjonslisten, fordi den
    strenge kjøringen forkaster de ferskeste signalene med vilje.

    KJØRING
    -------
        SentimentHendelseLab()                    # lab + produksjonsfil
        SentimentHendelseLab(skriv_master=False)  # bare laben

    Leser artiklene som ligger i DataNLP — skraper ingenting.
    """

    import logging
    import os
    import warnings
    from dataclasses import asdict, dataclass
    from datetime import datetime
    from math import exp, sqrt
    from pathlib import Path
    from typing import Dict, List, Optional, Tuple

    import numpy as np
    import pandas as pd
    import yfinance as yf

    warnings.filterwarnings("ignore")
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s  %(levelname)-8s  %(message)s",
                        datefmt="%H:%M:%S")
    log = logging.getLogger("HendelseLab")

    # Samme grense som resten av systemet bruker. Under to år er en annualisert
    # avkastning en forstørrelse, ikke et anslag, og mailen skal si det.
    MIN_AAR_FOR_CAGR = 2.0
    # Risikofri rente, samme som PB-ROE og den månedlige NLP-utgaven bruker.
    RISIKOFRI = 0.03

    # ═════════════════════════════════════════════════════════════════════════
    # OPPSETT
    # ═════════════════════════════════════════════════════════════════════════

    @dataclass
    class Config:
        base_dir: Path = Path(os.environ.get(
            "AKSJE_BASE_DIR", r"C:\Users\ander\Desktop\Python_K4\ExcelData"))
        nlp_output_dir: str = "DataNLP"
        output_dir: str = "StrategyResults_v5_Sentiment_Exit"
        # Produksjonsfilen må ligge der master.py og mail/mail_strategier.py
        # allerede leter. De to skal ikke trenge en ny sti for at motoren under
        # skal kunne byttes.
        master_dir: str = "StrategyResults_v4_Sentiment"
        oslo_suffix: str = ".OL"

        terskler: Tuple[float, ...] = (20.0, 50.0, 85.0, 135.0, 200.0, 300.0)
        sma_dager: int = 50

        # 0 = kjøp på artikkeldagens slutt, som i originalen.
        KJOPSFORSINKELSE: int = 1
        # Exit på ny informasjon gjøres dagen etter, fordi klokkeslett mangler.
        NYHETS_EXIT_FORSINKELSE: int = 1

        hold_dager: int = 21
        dynamisk_maks_hold: int = 63
        maks_posisjoner: int = 10
        startkapital: float = 1_000_000.0

        gulv: float = 0.05
        inn_utvalg_slutt: str = os.environ.get("AKSJE_SELECTION_CUTOFF", "2025-06-30")
        min_signaler: int = 30

        # Alpha-plateau: velg korteste horisont som er innenfor 95 % av beste
        # positive INN-alpha. Hvis ingen positiv robust alpha finnes: 21 dager.
        alpha_horisonter: Tuple[int, ...] = (3, 5, 8, 10, 15, 21, 30, 42, 63)
        alpha_plateau_andel: float = 0.95

        # Indikatorer / dynamiske exit-parametre.
        atr_dager: int = 20
        min_dager_for_trend_exit: int = 2
        min_dager_for_relative_exit: int = 3
        sentiment_reversal_raw: float = -0.10
        relative_stop: float = -0.03

        # Erstatning: en åpen posisjon må være minst så gammel, og den nye
        # hendelsens prioritet må være minst denne faktoren over svakeste åpne.
        replace_min_age: int = 5
        replace_strength_ratio: float = 1.50
        replace_decay_days: float = 10.0

        @property
        def nlp_dir(self) -> Path:
            return self.base_dir / self.nlp_output_dir

        @property
        def ut_dir(self) -> Path:
            p = self.base_dir / self.output_dir
            p.mkdir(parents=True, exist_ok=True)
            return p

        @property
        def master_ut_dir(self) -> Path:
            p = self.base_dir / self.master_dir
            p.mkdir(parents=True, exist_ok=True)
            return p

    config = Config()

    @dataclass(frozen=True)
    class Strategi:
        navn: str
        terskel: float
        krev_sma: bool

    STRATEGIER: List[Strategi] = (
        [Strategi(f"S{i} ≥{t:.0f}%", t, False)
         for i, t in enumerate(config.terskler, start=1)]
        + [Strategi(f"S{i + len(config.terskler)} ≥{t:.0f}%+SMA", t, True)
           for i, t in enumerate(config.terskler, start=1)])

    @dataclass(frozen=True)
    class ExitStrategi:
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
        breakeven_trigger: Optional[float] = None
        relative_stop: Optional[float] = None
        sentiment_reversal_raw: Optional[float] = None
        replacement: bool = False
        alpha_plateau: bool = False

    # Alle exit-metodene fra diskusjonen er implementert som separate tester.
    EXIT_STRATEGIER: List[ExitStrategi] = []

    for d in config.alpha_horisonter:
        EXIT_STRATEGIER.append(ExitStrategi(
            kode=f"F{d:02d}", navn=f"Fast {d}d", type="FIXED",
            beskrivelse=f"Selg etter nøyaktig {d} handledager.",
            maks_dager=d, fast_dager=d))

    EXIT_STRATEGIER += [
        ExitStrategi(
            kode="ALPHA", navn="Alpha-plateau", type="ALPHA",
            beskrivelse="Korteste robuste INN-horisont innen 95 % av beste positive alpha.",
            maks_dager=max(config.alpha_horisonter), alpha_plateau=True),
        ExitStrategi(
            kode="NEXT", navn="Neste rapport", type="NEXT_REPORT",
            beskrivelse="Selg ved første senere rapport; 63d hard cap.",
            maks_dager=config.dynamisk_maks_hold),
        ExitStrategi(
            kode="SREV", navn="Sent.rev", type="SENT_REV",
            beskrivelse=f"Selg når senere sentimentskift ≤ {config.sentiment_reversal_raw:+.2f}; 63d cap.",
            maks_dager=config.dynamisk_maks_hold,
            sentiment_reversal_raw=config.sentiment_reversal_raw),
        ExitStrategi(
            kode="SMA50", navn="Under SMA50", type="SMA",
            beskrivelse="Selg ved close under SMA50 etter minst 2 dager; 63d cap.",
            maks_dager=config.dynamisk_maks_hold, sma_exit=50),
        ExitStrategi(
            kode="SMA10", navn="Under SMA10", type="SMA",
            beskrivelse="Selg ved close under SMA10 etter minst 2 dager; 63d cap.",
            maks_dager=config.dynamisk_maks_hold, sma_exit=10),
        ExitStrategi(
            kode="EMA20", navn="Under EMA20", type="EMA",
            beskrivelse="Selg ved close under EMA20 etter minst 2 dager; 63d cap.",
            maks_dager=config.dynamisk_maks_hold, ema_exit=20),
        ExitStrategi(
            kode="SL05", navn="Stop -5%", type="STOP",
            beskrivelse="Close-basert stop-loss på -5 %; 63d cap.",
            maks_dager=config.dynamisk_maks_hold, stop_loss=-0.05),
        ExitStrategi(
            kode="SL08", navn="Stop -8%", type="STOP",
            beskrivelse="Close-basert stop-loss på -8 %; 63d cap.",
            maks_dager=config.dynamisk_maks_hold, stop_loss=-0.08),
        ExitStrategi(
            kode="SL10", navn="Stop -10%", type="STOP",
            beskrivelse="Close-basert stop-loss på -10 %; 63d cap.",
            maks_dager=config.dynamisk_maks_hold, stop_loss=-0.10),
        ExitStrategi(
            kode="ATR20", navn="ATR stop 2.0x", type="ATR_STOP",
            beskrivelse="Selg under entry minus 2.0x ATR20 målt ved entry; 63d cap.",
            maks_dager=config.dynamisk_maks_hold, atr_mult=2.0),
        ExitStrategi(
            kode="ATR25", navn="ATR stop 2.5x", type="ATR_STOP",
            beskrivelse="Selg under entry minus 2.5x ATR20 målt ved entry; 63d cap.",
            maks_dager=config.dynamisk_maks_hold, atr_mult=2.5),
        ExitStrategi(
            kode="ATR30", navn="ATR stop 3.0x", type="ATR_STOP",
            beskrivelse="Selg under entry minus 3.0x ATR20 målt ved entry; 63d cap.",
            maks_dager=config.dynamisk_maks_hold, atr_mult=3.0),
        ExitStrategi(
            kode="TR10", navn="Trail 10%", type="TRAIL_PCT",
            beskrivelse="Selg 10 % under høyeste close siden entry; 63d cap.",
            maks_dager=config.dynamisk_maks_hold, trail_pct=0.10),
        ExitStrategi(
            kode="TRATR", navn="Trail ATR2.5", type="TRAIL_ATR",
            beskrivelse="Selg 2.5x aktuell ATR20 under høyeste close siden entry; 63d cap.",
            maks_dager=config.dynamisk_maks_hold, trail_atr_mult=2.5),
        ExitStrategi(
            kode="TP05", navn="Target +5%", type="TARGET",
            beskrivelse="Ta gevinst ved +5 % close; 63d cap.",
            maks_dager=config.dynamisk_maks_hold, profit_target=0.05),
        ExitStrategi(
            kode="TP10", navn="Target +10%", type="TARGET",
            beskrivelse="Ta gevinst ved +10 % close; 63d cap.",
            maks_dager=config.dynamisk_maks_hold, profit_target=0.10),
        ExitStrategi(
            kode="TP15", navn="Target +15%", type="TARGET",
            beskrivelse="Ta gevinst ved +15 % close; 63d cap.",
            maks_dager=config.dynamisk_maks_hold, profit_target=0.15),
        ExitStrategi(
            kode="TPSL", navn="+10/-7", type="TARGET_STOP",
            beskrivelse="Ta gevinst ved +10 % eller stop ved -7 %; 63d cap.",
            maks_dager=config.dynamisk_maks_hold,
            profit_target=0.10, stop_loss=-0.07),
        ExitStrategi(
            kode="BE05", navn="BE etter +5", type="BREAKEVEN",
            beskrivelse="Når handelen har vært +5 %, selg senere ved close ≤ entry; 63d cap.",
            maks_dager=config.dynamisk_maks_hold, breakeven_trigger=0.05),
        ExitStrategi(
            kode="REL03", navn="Relativ -3pp", type="RELATIVE",
            beskrivelse="Selg når aksjen ligger minst 3pp bak equal-weight marked siden entry; 63d cap.",
            maks_dager=config.dynamisk_maks_hold,
            relative_stop=config.relative_stop),
        ExitStrategi(
            kode="REPL", navn="Erstatt svak", type="REPLACE",
            beskrivelse="Baseline 21d, men la mye sterkere ferskt signal erstatte svak gammel posisjon.",
            maks_dager=config.hold_dager, fast_dager=config.hold_dager,
            replacement=True),
        ExitStrategi(
            kode="HYB", navn="Hybrid", type="HYBRID",
            beskrivelse="Alpha-horisont + sentimentreversering + kapasitets-erstatning.",
            maks_dager=max(config.alpha_horisonter),
            sentiment_reversal_raw=config.sentiment_reversal_raw,
            replacement=True, alpha_plateau=True),
        ExitStrategi(
            kode="HYBATR", navn="Hybrid+ATR3", type="HYBRID_ATR",
            beskrivelse="Hybrid + katastrofestopp på 3.0x ATR20.",
            maks_dager=max(config.alpha_horisonter), atr_mult=3.0,
            sentiment_reversal_raw=config.sentiment_reversal_raw,
            replacement=True, alpha_plateau=True),
    ]

    # ═════════════════════════════════════════════════════════════════════════
    # DATA
    # ═════════════════════════════════════════════════════════════════════════

    @dataclass
    class MarkedsData:
        close: pd.DataFrame
        high: pd.DataFrame
        low: pd.DataFrame
        atr20: pd.DataFrame
        sma10: pd.DataFrame
        sma50: pd.DataFrame
        ema20: pd.DataFrame
        market_index: pd.Series

    def kontroller_priser(close: pd.DataFrame) -> pd.DataFrame:
        """Flag unverified adjusted-price discontinuities; never clip a return.

        A fourfold change between actual observations needs source verification.
        This is a data-validation boundary, not a claim that large moves cannot
        happen. Missing observations are not replaced before this check.
        """
        issues = []
        for ticker in close.columns:
            prices = pd.to_numeric(close[ticker], errors="coerce").dropna()
            for day, price in prices[~np.isfinite(prices) | (prices <= 0)].items():
                issues.append(dict(ticker=ticker, date=str(day.date()),
                                   issue="non_positive_or_non_finite", price=float(price)))
            good = prices[np.isfinite(prices) & (prices > 0)]
            ratio = good / good.shift(1)
            for day in ratio.index[(ratio >= 4.0) | (ratio <= 0.25)]:
                issues.append(dict(ticker=ticker, date=str(day.date()),
                                   issue="unverified_adjusted_price_discontinuity",
                                   previous_price=float(good.shift(1).loc[day]),
                                   price=float(good.loc[day]), ratio=float(ratio.loc[day])))
        return pd.DataFrame(issues, columns=["ticker", "date", "issue", "previous_price", "price", "ratio"])

    def hent_kurser(tickere: List[str]) -> MarkedsData:
        log.info("Kurser   : laster ned %d tickere …", len(tickere))
        record_source("management_prices", status="FAILED", detail="Price download started; not validated",
                      network_attempted=True, expected_count=len(tickere))
        data = yf.download(tickere, start="2019-01-01", auto_adjust=True,
                           repair=False, progress=False, end=datetime.now().strftime("%Y-%m-%d"))
        if data.empty:
            raise RuntimeError("yfinance ga ingen data.")

        def felt(navn: str) -> pd.DataFrame:
            if isinstance(data.columns, pd.MultiIndex):
                if navn not in data.columns.get_level_values(0):
                    return pd.DataFrame(index=data.index)
                x = data[navn].copy()
            else:
                if navn not in data.columns:
                    return pd.DataFrame(index=data.index)
                x = data[[navn]].copy()
                x.columns = tickere[:1]
            x.index = pd.to_datetime(x.index)
            return x.sort_index()

        close = felt("Close")
        high = felt("High")
        low = felt("Low")
        if close.empty:
            raise RuntimeError("yfinance ga ingen Close-data.")

        from runtime_config import validate_price_frame
        missing = [t for t in tickere if t not in close.columns or close[t].dropna().empty]
        record_source("management_prices", status="PARTIAL", detail="Validating downloaded prices",
                      network_attempted=True, expected_count=len(tickere),
                      usable_count=len(tickere) - len(missing), downloaded_count=len(tickere) - len(missing),
                      cached_count=0, issues=missing)
        validate_price_frame(close, tickere, "Management prices")
        gode = [c for c in close.columns if close[c].notna().any()]
        close = close[gode].copy()
        high = high.reindex(index=close.index, columns=gode)
        low = low.reindex(index=close.index, columns=gode)

        # Persist the actual adjusted observations, including gaps, for auditing.
        # A failed download never silently substitutes an older successful run.
        close.to_csv(config.ut_dir / "management_prices_close.csv", index_label="Date")
        high.to_csv(config.ut_dir / "management_prices_high.csv", index_label="Date")
        low.to_csv(config.ut_dir / "management_prices_low.csv", index_label="Date")
        issues = kontroller_priser(close)
        issues.to_csv(config.ut_dir / "management_price_issues.csv", index=False)
        if not issues.empty:
            examples = ", ".join(issues["ticker"].drop_duplicates().head(8))
            raise RuntimeError(
                "Management prices require source verification: "
                + examples + ". See management_price_issues.csv. No backtest or variant "
                "is published from these prices; prices were not clipped or guessed.")

        record_source("management_prices", status="DOWNLOADED", detail="All requested price series validated",
                      network_attempted=True, expected_count=len(tickere), usable_count=len(gode),
                      downloaded_count=len(gode), cached_count=0,
                      latest_observation=str(close.index.max().date()))
        # ATR20 = gjennomsnittlig True Range. Vi bruker den til volatilitetstilpassede
        # stoppnivåer, men selve exit-signalet er close-basert for å unngå antakelser
        # om intradag-fill og gaps.
        prev_close = close.shift(1)
        tr1 = (high - low).abs()
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        tr_values = np.nanmax(np.stack([tr1.to_numpy(), tr2.to_numpy(),
                                        tr3.to_numpy()]), axis=0)
        tr = pd.DataFrame(tr_values, index=close.index, columns=close.columns)
        atr20 = tr.rolling(config.atr_dager, min_periods=max(5, config.atr_dager // 2)).mean()

        sma10 = close.rolling(10).mean()
        sma50 = close.rolling(config.sma_dager).mean()
        ema20 = close.ewm(span=20, adjust=False, min_periods=20).mean()

        # Equal-weight daglig markedsindeks brukes KUN til den relative exit-triggeren.
        # Rapportkolonnen "Marked" bruker fortsatt gjennomsnittlig universavkastning
        # over hver handels eksakte inn/ut-vindu, som i originalen.
        daglig = close.pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan)
        market_index = (1.0 + daglig.mean(axis=1).fillna(0.0)).cumprod()

        log.info("Kurser   : %d tickere, %s → %s", len(close.columns),
                 close.index[0].date(), close.index[-1].date())
        return MarkedsData(close, high, low, atr20, sma10, sma50, ema20, market_index)

    # ═════════════════════════════════════════════════════════════════════════
    # HENDELSENE
    # ═════════════════════════════════════════════════════════════════════════

    def bygg_signaler(artikler: pd.DataFrame, md: MarkedsData) -> pd.DataFrame:
        """
        Én rad per rapport som har en forrige rapport å måles mot.

        I motsetning til originalen preberegnes ikke én bestemt 21-dagers
        avkastning. Exit-vinduet bestemmes senere av den exit-strategien som
        faktisk testes.
        """
        kurs = md.close
        kart = {c: str(c).strip() + config.oslo_suffix
                for c in artikler["Company"].dropna().unique()
                if str(c).strip() and str(c).strip() != "nan"}
        kart = {c: t for c, t in kart.items() if t in kurs.columns}
        log.info("Kobling  : %d av %d selskaper har kurser",
                 len(kart), artikler["Company"].nunique())
        if not kart:
            raise RuntimeError("Ingen selskaper lot seg koble mot kurser.")

        over_sma = (kurs > md.sma50)

        rader: List[dict] = []
        n_dager = len(kurs.index)
        signal_id = 0
        for selskap, d in artikler.groupby("Company"):
            if selskap not in kart:
                continue
            ticker = kart[selskap]
            d = d.sort_values("Article_Date")
            scorer = d["Final_Score"].to_numpy(dtype=float)
            datoer = list(d["Article_Date"])
            titler = (list(d["Article_Title"]) if "Article_Title" in d.columns
                      else [""] * len(d))

            for i in range(1, len(scorer)):
                ny, forrige = float(scorer[i]), float(scorer[i - 1])
                raa = abs(forrige)
                gulv_bandt = raa < config.gulv
                bedring = (ny - forrige) / max(raa, config.gulv) * 100.0
                if not np.isfinite(bedring):
                    continue

                rapport_i = int(kurs.index.searchsorted(pd.Timestamp(datoer[i]).normalize(), side="right"))
                inn = rapport_i
                if inn <= 0 or inn >= n_dager:
                    continue

                k0 = kurs[ticker].iloc[inn]
                if kurs[ticker].iloc[:inn].notna().sum() < 120:
                    continue
                if not np.isfinite(k0) or k0 <= 0:
                    continue

                signal_id += 1
                rader.append({
                    "signal_id": signal_id,
                    "dato": kurs.index[inn],
                    "artikkeldato": datoer[i],
                    "rapport_i": rapport_i,
                    "nyhets_exit_i": rapport_i,
                    "selskap": selskap,
                    "ticker": ticker,
                    "tittel": str(titler[i])[:90],
                    "forrige_score": round(forrige, 4),
                    "ny_score": round(ny, 4),
                    "endring": round(ny - forrige, 4),
                    "bedring_pst": round(bedring, 1),
                    "gulv_bandt": gulv_bandt,
                    "over_sma": bool(over_sma[ticker].iloc[max(0, inn - 1)])
                    if ticker in over_sma.columns else False,
                    "inn_i": inn,
                })

        if not rader:
            log.warning("Signaler : 0 hendelser. Ingen selskaper har to "
                        "rapporter innenfor kursperioden.")
            return pd.DataFrame(columns=[
                "signal_id", "dato", "artikkeldato", "rapport_i", "nyhets_exit_i",
                "selskap", "ticker", "tittel", "forrige_score", "ny_score",
                "endring", "bedring_pst", "gulv_bandt", "over_sma", "inn_i"])

        s = pd.DataFrame(rader).sort_values(["inn_i", "signal_id"]).reset_index(drop=True)
        log.info("Signaler : %d hendelser (én per rapport med en forrige å måles mot)",
                 len(s))
        if len(s):
            log.info("Gulvet band på %.0f %% av alle hendelser — se docstringen.",
                     s["gulv_bandt"].mean() * 100)
        return s

    # ═════════════════════════════════════════════════════════════════════════
    # MARKED / ALPHA
    # ═════════════════════════════════════════════════════════════════════════

    def les_artikler() -> pd.DataFrame:
        filer = sorted(p for p in config.nlp_dir.glob("NLP_Sentiment_Detail_*.xlsx")
                       if not p.name.startswith("~$") and ("_FINAL" in p.name or not any(
                           ch.isdigit() for ch in p.stem.rsplit("_", 1)[-1]) or len(p.stem.rsplit("_", 1)[-1]) <= 8))
        if not filer:
            raise FileNotFoundError(f"Ingen artikkelfiler i {config.nlp_dir}")
        deler = []
        for f in filer:
            try:
                d = pd.read_excel(f)
            except Exception:
                continue
            if not d.empty and "Article_Date" in d.columns:
                d["_fil"] = f.name
                deler.append(d)
        if not deler:
            raise FileNotFoundError(f"Ingen lesbare artikkelfiler i {config.nlp_dir}")
        df = pd.concat(deler, ignore_index=True)
        df["Article_Date"] = (df["Article_Date"].astype(str)
                              .str.replace(r"\n.*$", "", regex=True).str.strip())
        first_parse = pd.to_datetime(df["Article_Date"], format="%d %b %Y", errors="coerce")
        df["Article_Date"] = first_parse.fillna(pd.to_datetime(df["Article_Date"], format="mixed", errors="coerce"))
        df = df.dropna(subset=["Article_Date"])
        if "Text_Length" in df.columns:
            df = df[df["Text_Length"] > 0]
        if "Final_Score" not in df.columns:
            raise KeyError("Artikkelfilene mangler Final_Score.")
        df["Final_Score"] = pd.to_numeric(df["Final_Score"], errors="coerce")
        df = df.dropna(subset=["Final_Score"])
        nokler = [k for k in ("Company", "Article_Date", "Article_Title")
                  if k in df.columns]
        if nokler:
            df = df.sort_values("_fil").drop_duplicates(subset=nokler, keep="last")
        df = df.sort_values(["Company", "Article_Date"]).reset_index(drop=True)
        log.info("Artikler : %d fra %d fil(er), %d selskaper, %s → %s",
                 len(df), len(deler), df["Company"].nunique(),
                 df["Article_Date"].min().date(), df["Article_Date"].max().date())
        return df

    marked_cache: Dict[Tuple[int, int], float] = {}

    def markedsavkastning(md: MarkedsData, inn: int, ut: int) -> float:
        """Gjennomsnittlig universavkastning over nøyaktig samme inn/ut-vindu."""
        key = (int(inn), int(ut))
        if key in marked_cache:
            return marked_cache[key]
        if inn < 0 or ut >= len(md.close.index) or ut <= inn:
            return np.nan
        a, b = md.close.iloc[inn], md.close.iloc[ut]
        r = (b / a - 1.0).replace([np.inf, -np.inf], np.nan).dropna()
        v = float(r.mean()) if len(r) else np.nan
        marked_cache[key] = v
        return v

    def velg_alpha_horisonter(signaler: pd.DataFrame, md: MarkedsData):
        """
        For hver av de tolv inngangsstrategiene:
        - bruk KUN handler som både starter og avsluttes senest INN-cutoff,
        - mål stock - market for alle konfigurerte horisonter,
        - velg korteste horisont som er innenfor alpha_plateau_andel av beste
          POSITIVE alpha.

        Dette er en enkel robust alpha-decay-regel, ikke en dag-for-dag ML-fit.
        """
        cutoff = pd.Timestamp(config.inn_utvalg_slutt)
        cutoff_i = int(md.close.index.searchsorted(cutoff, side="right") - 1)
        tabell: List[dict] = []
        valgte_hold: Dict[str, int] = {}

        for s in STRATEGIER:
            grense = s.terskel - 1e-9
            v = signaler[(signaler["bedring_pst"] >= grense)
                         & (signaler["over_sma"] if s.krev_sma
                            else signaler["bedring_pst"].notna())]
            rader_s = []
            for h in config.alpha_horisonter:
                aksje_ret, marked_ret, alpha = [], [], []
                for _, r in v.iterrows():
                    inn = int(r["inn_i"])
                    ut = inn + h
                    if ut > cutoff_i or ut >= len(md.close.index):
                        continue
                    k = md.close[r["ticker"]]
                    p0, p1 = k.iloc[inn], k.iloc[ut]
                    if not (np.isfinite(p0) and np.isfinite(p1)) or p0 <= 0:
                        continue
                    ar = float(p1 / p0 - 1.0)
                    mr = markedsavkastning(md, inn, ut)
                    if not np.isfinite(mr):
                        continue
                    aksje_ret.append(ar)
                    marked_ret.append(mr)
                    alpha.append(ar - mr)
                n = len(alpha)
                ap = float(np.mean(alpha)) * 100.0 if n else np.nan
                row = {
                    "Strategi": s.navn,
                    "Hold_Dager": h,
                    "N_INN": n,
                    "Aksje_Pst": float(np.mean(aksje_ret)) * 100.0 if n else np.nan,
                    "Marked_Pst": float(np.mean(marked_ret)) * 100.0 if n else np.nan,
                    "Alpha_Pst": ap,
                }
                tabell.append(row)
                rader_s.append(row)

            kandidater = [r for r in rader_s
                           if r["N_INN"] >= config.min_signaler
                           and np.isfinite(r["Alpha_Pst"])]
            if kandidater:
                beste_alpha = max(r["Alpha_Pst"] for r in kandidater)
                if beste_alpha > 0:
                    gulv_alpha = beste_alpha * config.alpha_plateau_andel
                    robuste = [r for r in kandidater if r["Alpha_Pst"] >= gulv_alpha]
                    valgt = min(robuste, key=lambda x: x["Hold_Dager"])["Hold_Dager"]
                else:
                    valgt = config.hold_dager
            else:
                valgt = config.hold_dager
            valgte_hold[s.navn] = int(valgt)
            log.info("Alpha    : %-16s -> %2d dager", s.navn, valgt)

        return valgte_hold, pd.DataFrame(tabell)

    def lag_nyhetskart(signaler: pd.DataFrame) -> Dict[Tuple[str, int], List[dict]]:
        """Alle senere rapporter kan påvirke en åpen posisjon, uansett inngangsterskel."""
        kart: Dict[Tuple[str, int], List[dict]] = {}
        for _, r in signaler.iterrows():
            i = int(r["nyhets_exit_i"])
            key = (r["ticker"], i)
            kart.setdefault(key, []).append({
                "artikkeldato": pd.Timestamp(r["artikkeldato"]),
                "endring": float(r["endring"]),
                "signal_id": int(r["signal_id"]),
            })
        return kart

    nyhetskart: Dict[Tuple[str, int], List[dict]] = {}

    def har_senere_rapport(pos: dict, dag_i: int) -> bool:
        for ev in nyhetskart.get((pos["ticker"], dag_i), []):
            if ev["artikkeldato"] > pos["artikkeldato"]:
                return True
        return False

    def har_sentiment_reversering(pos: dict, dag_i: int, terskel: float) -> bool:
        for ev in nyhetskart.get((pos["ticker"], dag_i), []):
            if (ev["artikkeldato"] > pos["artikkeldato"]
                    and ev["endring"] <= terskel):
                return True
        return False

    def _t(v, d=2, sfx=""):
        try:
            if v is None or not np.isfinite(float(v)):
                return "—"
        except Exception:
            return "—"
        return f"{float(v):.{d}f}{sfx}"

    # ═════════════════════════════════════════════════════════════════════════
    # PORTEFØLJESIMULATOR MED DYNAMISKE EXITS
    # ═════════════════════════════════════════════════════════════════════════

    def effektiv_maks_hold(e: ExitStrategi, alpha_hold: int) -> int:
        if e.type in ("ALPHA", "HYBRID", "HYBRID_ATR"):
            return int(alpha_hold)
        if e.type == "FIXED":
            return int(e.fast_dager)
        return int(e.maks_dager)

    def prioritet(pos: dict, dag_i: int) -> float:
        alder = max(0, dag_i - pos["inn_i"])
        return float(pos["bedring_pst"]) * exp(-alder / config.replace_decay_days)

    def exit_arsak(pos: dict, dag_i: int, e: ExitStrategi,
                   md: MarkedsData, alpha_hold: int) -> Optional[str]:
        """Returnerer exit-årsak hvis posisjonen skal selges på dagens close."""
        alder = dag_i - pos["inn_i"]
        if alder <= 0:
            return None

        ticker = pos["ticker"]
        px = md.close[ticker].iloc[dag_i]
        if not np.isfinite(px) or px <= 0:
            return None

        ret = float(px / pos["entry_price"] - 1.0)
        pos["peak_close"] = max(pos["peak_close"], float(px))

        # Nyhetsbaserte exits først: ny informasjon kan ugyldiggjøre den gamle tesen.
        if e.type == "NEXT_REPORT" and har_senere_rapport(pos, dag_i):
            return "neste_rapport"

        if e.type in ("SENT_REV", "HYBRID", "HYBRID_ATR"):
            terskel = (e.sentiment_reversal_raw
                       if e.sentiment_reversal_raw is not None
                       else config.sentiment_reversal_raw)
            if har_sentiment_reversering(pos, dag_i, terskel):
                return "sentiment_reversering"

        # Pris-/risikobaserte exits.
        if e.type == "STOP" and e.stop_loss is not None and ret <= e.stop_loss:
            return "stop_loss"

        if e.type in ("ATR_STOP", "HYBRID_ATR") and e.atr_mult is not None:
            atr0 = pos.get("entry_atr", np.nan)
            if np.isfinite(atr0) and px <= pos["entry_price"] - e.atr_mult * atr0:
                return "atr_stop"

        if e.type == "TRAIL_PCT" and e.trail_pct is not None:
            if px <= pos["peak_close"] * (1.0 - e.trail_pct):
                return "trailing_stop"

        if e.type == "TRAIL_ATR" and e.trail_atr_mult is not None:
            atr = md.atr20[ticker].iloc[dag_i]
            if np.isfinite(atr) and px <= pos["peak_close"] - e.trail_atr_mult * atr:
                return "trailing_atr"

        if e.type == "TARGET" and e.profit_target is not None:
            if ret >= e.profit_target:
                return "profit_target"

        if e.type == "TARGET_STOP":
            if e.profit_target is not None and ret >= e.profit_target:
                return "profit_target"
            if e.stop_loss is not None and ret <= e.stop_loss:
                return "stop_loss"

        if e.type == "BREAKEVEN" and e.breakeven_trigger is not None:
            if (not pos["breakeven_armed"]) and ret >= e.breakeven_trigger:
                pos["breakeven_armed"] = True
                pos["breakeven_arm_i"] = dag_i
            if (pos["breakeven_armed"]
                    and dag_i > pos["breakeven_arm_i"]
                    and px <= pos["entry_price"]):
                return "break_even"

        if e.type == "RELATIVE" and e.relative_stop is not None:
            if alder >= config.min_dager_for_relative_exit:
                m0 = md.market_index.iloc[pos["inn_i"]]
                m1 = md.market_index.iloc[dag_i]
                mr = float(m1 / m0 - 1.0) if np.isfinite(m0) and m0 > 0 else np.nan
                if np.isfinite(mr) and (ret - mr) <= e.relative_stop:
                    return "relativ_underprestasjon"

        if e.type == "SMA" and e.sma_exit is not None:
            if alder >= config.min_dager_for_trend_exit:
                ma = md.sma50[ticker].iloc[dag_i] if e.sma_exit == 50 else md.sma10[ticker].iloc[dag_i]
                if np.isfinite(ma) and px < ma:
                    return f"under_sma{e.sma_exit}"

        if e.type == "EMA" and e.ema_exit is not None:
            if alder >= config.min_dager_for_trend_exit:
                ma = md.ema20[ticker].iloc[dag_i]
                if np.isfinite(ma) and px < ma:
                    return f"under_ema{e.ema_exit}"

        # Tidsbasert cap kommer sist, slik at en faktisk tese-/risikoexit på samme
        # dag får den informative exit-årsaken.
        maks_hold = effektiv_maks_hold(e, alpha_hold)
        if alder >= maks_hold:
            if e.type == "FIXED":
                return "fast_hold"
            if e.type == "ALPHA":
                return "alpha_horisont"
            if e.type in ("REPLACE",):
                return "fast_hold"
            if e.type in ("HYBRID", "HYBRID_ATR"):
                return "alpha_horisont"
            return "maks_hold"

        return None

    def kjor_strategi(s: Strategi, e: ExitStrategi, signaler: pd.DataFrame,
                      md: MarkedsData, alpha_hold_map: Dict[str, int],
                      live: bool = True) -> dict:
        """
        Dag-for-dag-porteføljesimulator.

        Kapitalen deles i maks_posisjoner like plasser. Exit vurderes først på
        dagens close; deretter behandles nye signaler på samme dags close. Hvis
        exit-strategien tillater erstatning, kan et mye sterkere ferskt signal
        selge svakeste gamle posisjon og ta plassen dens.

        live=True er produksjonsmodus: ingen modenhetsfilter, ingen tvangssalg.
        Samme simulering eier kurven, nøkkeltallene, handler og beholdning.
        """
        grense = s.terskel - 1e-9
        valgte = signaler[(signaler["bedring_pst"] >= grense)
                          & (signaler["over_sma"] if s.krev_sma
                             else signaler["bedring_pst"].notna())].copy()

        alpha_hold = int(alpha_hold_map.get(s.navn, config.hold_dager))
        maks_hold = effektiv_maks_hold(e, alpha_hold)
        n_dager = len(md.close.index)

        # For å unngå høyresensur krever vi at hele hard-cap-vinduet + Dag+1
        # faktisk kan observeres. Dette gir ulikt antall modne signaler for 3d
        # og 63d-regler, og det rapporteres eksplisitt som "Umodne".
        if live:
            umodne = 0
        else:
            moden_mask = valgte["inn_i"].astype(int) + maks_hold + 1 < n_dager
            umodne = int((~moden_mask).sum())
            valgte = valgte[moden_mask].copy()

        if valgte.empty:
            return {
                "Strategi": s.navn, "Terskel_Pst": s.terskel, "SMA": s.krev_sma,
                "Exit_Kode": e.kode, "Exit": e.navn, "Valgt_Hold": maks_hold,
                "Signaler": 0, "Handler": 0, "Tapt": 0, "Umodne": umodne,
                "Apne_Na": 0, "Live": live,
                "Slutt_NOK": config.startkapital, "handler": pd.DataFrame(),
                "kurve": pd.Series(dtype=float), "apne": [],
                "beholdning": pd.DataFrame(),
            }

        signaler_per_dag: Dict[int, List[pd.Series]] = {}
        for _, r in valgte.iterrows():
            signaler_per_dag.setdefault(int(r["inn_i"]), []).append(r)

        slot_cash = [config.startkapital / config.maks_posisjoner
                     for _ in range(config.maks_posisjoner)]
        apne: Dict[int, dict] = {}
        handler: List[dict] = []
        beholdning_log: List[dict] = []
        tapt = 0
        erstattet = 0
        equity_curve: List[Tuple[pd.Timestamp, float]] = []
        valuation_issues: List[dict] = []

        first_day = max(0, int(signaler["inn_i"].min()) - 1)
        last_entry = int(valgte["inn_i"].max())
        last_day = (n_dager - 1 if live
                    else min(n_dager - 1, last_entry + maks_hold + 2))

        def selg(slot: int, dag_i: int, grunn: str) -> bool:
            nonlocal erstattet
            pos = apne.get(slot)
            if pos is None:
                return False
            px = md.close[pos["ticker"]].iloc[dag_i]
            if not np.isfinite(px) or px <= 0:
                return False

            avk = float(px / pos["entry_price"] - 1.0)
            slot_cash[slot] = pos["capital"] * (1.0 + avk)
            dager = int(dag_i - pos["inn_i"])
            marked = markedsavkastning(md, pos["inn_i"], dag_i)

            # Dag+1: samme faktiske antall holdedager, men inngang én dag senere.
            inn1 = pos["inn_i"] + 1
            ut1 = inn1 + dager
            dag1 = np.nan
            if ut1 < n_dager:
                k = md.close[pos["ticker"]]
                p0, p1 = k.iloc[inn1], k.iloc[ut1]
                if np.isfinite(p0) and np.isfinite(p1) and p0 > 0:
                    dag1 = float(p1 / p0 - 1.0)

            handler.append({
                "strategi": s.navn,
                "exit_kode": e.kode,
                "exit": e.navn,
                "signal_id": pos["signal_id"],
                "dato": md.close.index[pos["inn_i"]],
                "ut_dato": md.close.index[dag_i],
                "ticker": pos["ticker"],
                "selskap": pos["selskap"],
                "tittel": pos["tittel"],
                "bedring_pst": pos["bedring_pst"],
                "endring": pos["endring"],
                "forrige_score": pos["forrige_score"],
                "ny_score": pos["ny_score"],
                "gulv_bandt": pos["gulv_bandt"],
                "over_sma": pos["over_sma"],
                "inn_i": pos["inn_i"],
                "ut_i": dag_i,
                "hold_dager": dager,
                "exit_arsak": grunn,
                "entry_price": pos["entry_price"],
                "exit_price": float(px),
                "kapital": pos["capital"],
                "avk": avk,
                "avk_dag1": dag1,
                "marked": marked,
                "alpha": avk - marked if np.isfinite(marked) else np.nan,
                "utvalg": ("INN" if md.close.index[pos["inn_i"]]
                           <= pd.Timestamp(config.inn_utvalg_slutt) else "UT"),
            })
            if grunn == "replacement":
                erstattet += 1
            del apne[slot]
            return True

        def kjop(slot: int, r: pd.Series, dag_i: int) -> bool:
            ticker = r["ticker"]
            px = md.close[ticker].iloc[dag_i]
            if not np.isfinite(px) or px <= 0:
                return False
            atr0 = md.atr20[ticker].iloc[dag_i]
            apne[slot] = {
                "slot": slot,
                "capital": float(slot_cash[slot]),
                "signal_id": int(r["signal_id"]),
                "inn_i": dag_i,
                "artikkeldato": pd.Timestamp(r["artikkeldato"]),
                "ticker": ticker,
                "selskap": r["selskap"],
                "tittel": r["tittel"],
                "bedring_pst": float(r["bedring_pst"]),
                "endring": float(r["endring"]),
                "forrige_score": float(r["forrige_score"]),
                "ny_score": float(r["ny_score"]),
                "gulv_bandt": bool(r["gulv_bandt"]),
                "over_sma": bool(r["over_sma"]),
                "entry_price": float(px),
                "last_mark_price": float(px),
                "last_mark_i": dag_i,
                "entry_atr": float(atr0) if np.isfinite(atr0) else np.nan,
                "peak_close": float(px),
                "breakeven_armed": False,
                "breakeven_arm_i": -1,
            }
            return True

        for dag_i in range(first_day, last_day + 1):
            # 1) Exits på dagens close.
            for slot in list(apne.keys()):
                pos = apne[slot]
                age = dag_i - pos["inn_i"]
                # Scheduled expiry is known in advance; price exits use yesterday's close.
                grunn = pos.get("pending_exit")
                if not grunn and e.type == "NEXT_REPORT" and har_senere_rapport(pos, dag_i):
                    grunn = "neste_rapport"
                if (not grunn and e.type in ("SENT_REV", "HYBRID", "HYBRID_ATR")
                        and har_sentiment_reversering(pos, dag_i,
                            e.sentiment_reversal_raw if e.sentiment_reversal_raw is not None
                            else config.sentiment_reversal_raw)):
                    grunn = "sentiment_reversering"
                if not grunn:
                    grunn = ("utlopt" if age >= maks_hold else
                             exit_arsak(pos, dag_i - 1, e, md, alpha_hold)
                             if dag_i > pos["inn_i"] else None)
                if grunn:
                    if not selg(slot, dag_i, grunn):
                        pos["pending_exit"] = grunn

            # 2) Nye signaler på dagens close.
            for r in signaler_per_dag.get(dag_i, []):
                frie = [i for i in range(config.maks_posisjoner) if i not in apne]
                if frie:
                    if not kjop(frie[0], r, dag_i):
                        tapt += 1
                    continue

                # Kapasitets-erstatning er en portefølje-exit, ikke en egenskap
                # ved én isolert trade. Testes bare i REPL/HYBRID-variantene.
                if e.replacement:
                    kandidater = [p for p in apne.values()
                                  if dag_i - p["inn_i"] >= config.replace_min_age]
                    if kandidater:
                        svakest = min(kandidater, key=lambda p: prioritet(p, dag_i))
                        ny_prio = float(r["bedring_pst"])
                        gammel_prio = prioritet(svakest, dag_i)
                        if ny_prio >= gammel_prio * config.replace_strength_ratio:
                            slot = svakest["slot"]
                            if selg(slot, dag_i, "replacement"):
                                if not kjop(slot, r, dag_i):
                                    tapt += 1
                                continue
                tapt += 1

            # 3) Ekte daglig mark-to-market equity.
            verdi = 0.0
            for slot in range(config.maks_posisjoner):
                if slot not in apne:
                    verdi += slot_cash[slot]
                else:
                    pos = apne[slot]
                    px = md.close[pos["ticker"]].iloc[dag_i]
                    if np.isfinite(px) and px > 0:
                        pos["last_mark_price"] = float(px)
                        pos["last_mark_i"] = dag_i
                    elif dag_i - pos["last_mark_i"] == 6:
                        valuation_issues.append({"ticker": pos["ticker"],
                            "date": str(md.close.index[dag_i].date()),
                            "issue": "held_position_without_quote_for_6_sessions"})
                    # The share count is capital / entry; mark it ONCE. A missing
                    # quote retains the last observed mark (no invented trade).
                    # Extended missing marks invalidate publication below.
                    verdi += pos["capital"] / pos["entry_price"] * pos["last_mark_price"]
            equity_curve.append((md.close.index[dag_i], verdi))

            # Beholdningen logges bare når den endrer seg. Mailen leser den siste.
            na = sorted(p["ticker"] for p in apne.values())
            if not beholdning_log or beholdning_log[-1]["tickere"] != na:
                beholdning_log.append({"dato": md.close.index[dag_i],
                                       "tickere": na})

        # Hard sikkerhet: dersom en posisjon ikke ble solgt pga. manglende kurs
        # på forventet dag, selg på siste dag med gyldig close i simuleringen.
        # I produksjonsmodus gjøres ikke dette — en åpen posisjon er åpen.
        if not live:
            for slot in list(apne.keys()):
                pos = apne[slot]
                for dag_i in range(last_day, pos["inn_i"], -1):
                    px = md.close[pos["ticker"]].iloc[dag_i]
                    if np.isfinite(px) and px > 0:
                        selg(slot, dag_i, "slutt_tvang")
                        break

        h = pd.DataFrame(handler)
        kurve = (pd.Series({d: v for d, v in equity_curve}).sort_index()
                 if equity_curve else pd.Series(dtype=float))
        apne_na = [dict(p) for p in apne.values()]
        bh = pd.DataFrame([{"dato": r["dato"],
                            "holdings": ", ".join(r["tickere"]) or "CASH"}
                           for r in beholdning_log])
        slutt = (float(kurve.iloc[-1]) if (live and len(kurve))
                 else float(sum(slot_cash)))
        if h.empty:
            return {
                "Strategi": s.navn, "Terskel_Pst": s.terskel, "SMA": s.krev_sma,
                "Exit_Kode": e.kode, "Exit": e.navn, "Valgt_Hold": maks_hold,
                "Signaler": len(valgte), "Handler": 0, "Tapt": tapt,
                "Umodne": umodne, "Erstattet": erstattet,
                "Apne_Na": len(apne_na), "Live": live,
                "Slutt_NOK": slutt, "handler": h,
                "kurve": kurve, "apne": apne_na, "beholdning": bh,
                "data_valid": not valuation_issues, "valuation_issues": valuation_issues,
            }

        first_trade = h["dato"].min()
        last_trade = h["ut_dato"].max()
        if live and len(kurve) >= 2:
            first_trade, last_trade = kurve.index[0], kurve.index[-1]
        aar = max((last_trade - first_trade).days / 365.25, 0.01)

        verdier = [v for _, v in equity_curve] or [config.startkapital, slutt]
        topp, mdd = verdier[0], 0.0
        for v in verdier:
            topp = max(topp, v)
            mdd = min(mdd, v / topp - 1.0)

        uto = h[h["utvalg"] == "UT"]
        innh = h[h["utvalg"] == "INN"]
        alpha_valid = h["alpha"].dropna()
        total_slot_days = max(float(h["hold_dager"].sum()), 1.0)
        alpha_slotdag = float(alpha_valid.sum() / total_slot_days) * 100.0 if len(alpha_valid) else np.nan

        def uten_storste_vinnere(df: pd.DataFrame, kolonne: str,
                                 andel: float = 0.01) -> float:
            """
            Samme kolonne, uten de største vinnerne.

            Dette er ikke en ny metode — det er gjennomsnittet av «avk»/«alpha»
            etter at øverste andel av handlene på trade-retur er fjernet. Et
            profit target på +10 % kan ikke gi 24 % snitthandel med mindre noen
            få aksjer gapper voldsomt opp fra en lav inngangskurs. Uten denne
            kolonnen ser et slikt tall ut som en strategi.
            """
            x = df[["avk", "alpha"]].dropna()
            if x.empty:
                return np.nan
            n = min(max(int(np.ceil(len(x) * andel)), 1), max(len(x) - 1, 0))
            if n > 0:
                x = x.drop(index=x.nlargest(n, "avk").index)
            return float(x[kolonne].mean()) * 100.0 if len(x) else np.nan

        return {
            "Strategi": s.navn,
            "Terskel_Pst": s.terskel,
            "SMA": s.krev_sma,
            "Exit_Kode": e.kode,
            "Exit": e.navn,
            "Valgt_Hold": maks_hold,
            "Signaler": len(valgte),
            "Handler": len(h),
            "Tapt": tapt,
            "Umodne": umodne,
            "Erstattet": erstattet,
            "Apne_Na": len(apne_na),
            "Live": live,
            "Slutt_NOK": slutt,
            "Total_Pst": (slutt / config.startkapital - 1.0) * 100.0,
            "CAGR_Pst": (((slutt / config.startkapital) ** (1 / aar) - 1) * 100.0
                         if aar >= 0.5 else np.nan),
            "MaxDD_Pst": mdd * 100.0,
            "Snitt_Handel_Pst": float(h["avk"].mean()) * 100.0,
            "Median_Handel_Pst": float(h["avk"].median()) * 100.0,
            "Treff_Pst": float((h["avk"] > 0).mean()) * 100.0,
            "Marked_Pst": float(h["marked"].mean()) * 100.0
            if h["marked"].notna().any() else np.nan,
            "Mot_marked_Pst": float(h["alpha"].mean()) * 100.0
            if h["alpha"].notna().any() else np.nan,
            "Alpha_per_slotdag_Pst": alpha_slotdag,
            "Snitt_Hold_Dager": float(h["hold_dager"].mean()),
            "Median_Hold_Dager": float(h["hold_dager"].median()),
            "Dag1_Pst": float(h["avk_dag1"].mean()) * 100.0
            if h["avk_dag1"].notna().any() else np.nan,
            "INN_Snitt_Pst": float(innh["avk"].mean()) * 100.0 if len(innh) else np.nan,
            "INN_Mot_marked_Pst": float(innh["alpha"].mean()) * 100.0
            if len(innh) and innh["alpha"].notna().any() else np.nan,
            "UT_Snitt_Pst": float(uto["avk"].mean()) * 100.0 if len(uto) else np.nan,
            "UT_Mot_marked_Pst": float(uto["alpha"].mean()) * 100.0
            if len(uto) and uto["alpha"].notna().any() else np.nan,
            "Gulv_Pst": float(h["gulv_bandt"].mean()) * 100.0,
            # Lagt til: uten disse kan et tak på +10 % vise 24 % snitthandel
            # uten at noe i tabellen røper hvorfor.
            "Snitt_Uten_Topp1pct_Pst": uten_storste_vinnere(h, "avk"),
            "Alpha_Uten_Topp1pct_Pst": uten_storste_vinnere(h, "alpha"),
            "Beste_Handel_Pst": float(h["avk"].max()) * 100.0,
            "Verste_Handel_Pst": float(h["avk"].min()) * 100.0,
            "handler": h,
            "kurve": kurve,
            "apne": apne_na,
            "beholdning": bh,
            "data_valid": not valuation_issues,
            "valuation_issues": valuation_issues,
        }

    # ═════════════════════════════════════════════════════════════════════════
    # RAPPORT
    # ═════════════════════════════════════════════════════════════════════════

    def beste_per_exit(sammendrag: pd.DataFrame) -> pd.DataFrame:
        rader = []
        for kode, g in sammendrag.groupby("Exit_Kode", sort=False):
            gyldig = g[(g["Handler"] >= config.min_signaler)
                       & g["Mot_marked_Pst"].notna()]
            if gyldig.empty:
                row = g.sort_values("Handler", ascending=False).iloc[0].copy()
            else:
                # Primær rangering: faktisk portefølje-CAGR, deretter alpha/trade.
                row = gyldig.sort_values(
                    ["CAGR_Pst", "Mot_marked_Pst"], ascending=False).iloc[0].copy()
            rader.append(row)
        return pd.DataFrame(rader).reset_index(drop=True)

    def porten(r) -> Dict[str, bool]:
        """
        Kravene rapporten stiller. Samlet ett sted, fordi produksjonsvalget skal
        bruke NØYAKTIG samme port som rapporten skriver ut — ikke en annen.
        """
        return {
            "slår markedet på samme faktiske vindu": bool(r["Mot_marked_Pst"] > 0),
            "positiv snitthandel": bool(r["Snitt_Handel_Pst"] > 0),
            "positiv også på ut-utvalget": bool(np.isfinite(r["UT_Snitt_Pst"])
                                                and r["UT_Snitt_Pst"] > 0),
            "positiv alpha også på ut-utvalget":
                bool(np.isfinite(r["UT_Mot_marked_Pst"])
                     and r["UT_Mot_marked_Pst"] > 0),
            "holder seg med kjøp dagen etter":
                bool(not np.isfinite(r["Dag1_Pst"])
                     or r["Dag1_Pst"] > r["Snitt_Handel_Pst"] * 0.5),
            f"minst {config.min_signaler} handler":
                bool(r["Handler"] >= config.min_signaler),
            "gulvet binder på under 30 % av handlene": bool(r["Gulv_Pst"] < 30.0),
            # Lagt til: et profit target på +10 % kan ikke gi 24 % snitthandel
            # med mindre noen få gap bærer alt. Da er raden en måling av de
            # gapene, ikke av strategien.
            "holder uten den øverste prosenten vinnere":
                bool(np.isfinite(r.get("Snitt_Uten_Topp1pct_Pst", np.nan))
                     and r["Snitt_Uten_Topp1pct_Pst"] > 0),
        }

    def skriv_rapport(s: pd.DataFrame, signaler: pd.DataFrame,
                      exit_beste: pd.DataFrame,
                      prod: Optional[dict] = None,
                      prod_grunn: str = "") -> None:
        print("\n" + "=" * 150)
        print("  LEDELSES-SENTIMENT — ALLE EXIT-ALTERNATIVER")
        print("=" * 150)
        print(f"  Én rapport = én hendelse = ett kjøp. Inngangsforsinkelse "
              f"{config.KJOPSFORSINKELSE} dag, maks {config.maks_posisjoner} posisjoner, "
              f"start {config.startkapital:,.0f} kr.".replace(",", " "))
        print(f"  {len(STRATEGIER)} inngangsstrategier × {len(EXIT_STRATEGIER)} exit-varianter "
              f"= {len(STRATEGIER) * len(EXIT_STRATEGIER)} backtester.")
        print(f"  {len(signaler)} sentimenthendelser totalt i datagrunnlaget.\n")

        print("  EXIT-REGLER:")
        for e in EXIT_STRATEGIER:
            print(f"    {e.kode:<6} {e.navn:<18} {e.beskrivelse}")

        kol_h = (f"  {'Strategi':<17}{'Sign':>6}{'Handl':>7}{'Tapt':>6}{'Umod':>6}"
                 f"{'Dager':>7}{'Slutt NOK':>12}{'CAGR':>8}{'MaxDD':>8}"
                 f"{'Snitt':>8}{'u/topp1%':>9}{'Beste':>9}{'Treff':>7}{'Marked':>8}"
                 f"{'Mot mrk':>9}{'α/slotd':>9}{'Dag+1':>8}{'UT α':>8}")

        # Full output: alle 12 inngangsstrategiene vises under hver exit-metode.
        for e in EXIT_STRATEGIER:
            g = s[s["Exit_Kode"] == e.kode]
            print("\n" + "-" * 150)
            print(f"  EXIT {e.kode} — {e.navn}: {e.beskrivelse}")
            print(kol_h)
            print("  " + "-" * 146)
            for _, r in g.iterrows():
                print(f"  {r['Strategi']:<17}{int(r.get('Signaler', 0)):>6}"
                      f"{int(r.get('Handler', 0)):>7}{int(r.get('Tapt', 0)):>6}"
                      f"{int(r.get('Umodne', 0)):>6}"
                      f"{_t(r.get('Snitt_Hold_Dager'), 1):>7}"
                      f"{float(r.get('Slutt_NOK', config.startkapital)):>12,.0f}"
                      f"{_t(r.get('CAGR_Pst'), 1, '%'):>8}"
                      f"{_t(r.get('MaxDD_Pst'), 1, '%'):>8}"
                      f"{_t(r.get('Snitt_Handel_Pst'), 2, '%'):>8}"
                      f"{_t(r.get('Snitt_Uten_Topp1pct_Pst'), 2, '%'):>9}"
                      f"{_t(r.get('Beste_Handel_Pst'), 0, '%'):>9}"
                      f"{_t(r.get('Treff_Pst'), 0, '%'):>7}"
                      f"{_t(r.get('Marked_Pst'), 2, '%'):>8}"
                      f"{_t(r.get('Mot_marked_Pst'), 2, '%'):>9}"
                      f"{_t(r.get('Alpha_per_slotdag_Pst'), 3, '%'):>9}"
                      f"{_t(r.get('Dag1_Pst'), 2, '%'):>8}"
                      f"{_t(r.get('UT_Mot_marked_Pst'), 2, '%'):>8}".replace(",", " "))

        print("\n" + "=" * 150)
        print("  BESTE INNGANGSSTRATEGI INNEN HVER EXIT-METODE")
        print("=" * 150)
        print(f"  {'Exit':<7}{'Navn':<19}{'Strategi':<18}{'Hold':>6}{'Handl':>7}"
              f"{'Tapt':>6}{'CAGR':>8}{'MaxDD':>8}{'Snitt':>8}{'u/topp1%':>9}"
              f"{'Mot mrk':>9}{'UT α':>8}")
        print("  " + "-" * 124)
        for _, r in exit_beste.iterrows():
            print(f"  {r['Exit_Kode']:<7}{r['Exit']:<19}{r['Strategi']:<18}"
                  f"{int(r.get('Valgt_Hold', 0)):>6}{int(r.get('Handler', 0)):>7}"
                  f"{int(r.get('Tapt', 0)):>6}{_t(r.get('CAGR_Pst'), 1, '%'):>8}"
                  f"{_t(r.get('MaxDD_Pst'), 1, '%'):>8}"
                  f"{_t(r.get('Snitt_Handel_Pst'), 2, '%'):>8}"
                  f"{_t(r.get('Snitt_Uten_Topp1pct_Pst'), 2, '%'):>9}"
                  f"{_t(r.get('Mot_marked_Pst'), 2, '%'):>9}"
                  f"{_t(r.get('UT_Mot_marked_Pst'), 2, '%'):>8}")

        gyldige = s[(s["Handler"] >= config.min_signaler)
                    & s["Mot_marked_Pst"].notna()]
        if gyldige.empty:
            print(f"\n  🚫 PORTEN ER STENGT. Ingen kombinasjon fikk "
                  f"{config.min_signaler} handler å dømmes på.")
            print("=" * 150 + "\n")
            return

        # Best total = portefølje-CAGR først, alpha per trade som tie-breaker.
        beste = gyldige.sort_values(["CAGR_Pst", "Mot_marked_Pst"],
                                    ascending=False).iloc[0]
        krav = porten(beste)

        print(f"\n  BESTE TOTALT PÅ CAGR: {beste['Strategi']} + {beste['Exit_Kode']} "
              f"({beste['Exit']})")
        print(f"    CAGR {_t(beste['CAGR_Pst'], 2, '%')}, MaxDD {_t(beste['MaxDD_Pst'], 2, '%')}, "
              f"Mot marked {_t(beste['Mot_marked_Pst'], 2, '%')} per handel, "
              f"UT-alpha {_t(beste['UT_Mot_marked_Pst'], 2, '%')}, "
              f"snitt hold {_t(beste['Snitt_Hold_Dager'], 1)} dager.")
        print(f"    Snitthandel {_t(beste['Snitt_Handel_Pst'], 2, '%')}, uten øverste "
              f"1 % vinnere {_t(beste.get('Snitt_Uten_Topp1pct_Pst'), 2, '%')}, "
              f"beste enkelthandel {_t(beste.get('Beste_Handel_Pst'), 0, '%')}.")
        print("\n  PORTEN:")
        for tekst, ok in krav.items():
            print(f"    {'✓' if ok else '✗'}  {tekst}")

        if all(krav.values()):
            print("\n  ✅ PORTEN ER ÅPEN etter disse testene.")
        else:
            print("\n  🚫 PORTEN ER STENGT. Ikke velg exit kun fordi den er best i hele samplet.")

        # En rad der snitthandelen faller sammen uten den øverste prosenten er
        # ikke en strategi, den er en måling av noen få gap.
        skjeve = gyldige[(gyldige["Snitt_Handel_Pst"] > 3.0)
                         & (gyldige["Snitt_Uten_Topp1pct_Pst"]
                            < gyldige["Snitt_Handel_Pst"] * 0.5)]
        if len(skjeve):
            print(f"\n  ⚠  {len(skjeve)} kombinasjon(er) mister over halve snitthandelen")
            print("     når øverste 1 % av vinnerne fjernes. De øverste:")
            for _, r in skjeve.sort_values("Snitt_Handel_Pst",
                                           ascending=False).head(6).iterrows():
                print(f"       {r['Strategi']:<16} + {r['Exit_Kode']:<7}"
                      f"snitt {_t(r['Snitt_Handel_Pst'], 2, '%'):>8} → "
                      f"{_t(r['Snitt_Uten_Topp1pct_Pst'], 2, '%'):>8}"
                      f"   beste enkelthandel {_t(r['Beste_Handel_Pst'], 0, '%')}")
            print("     Et profit target på +10 % kan ikke gi 24 % snitthandel med mindre")
            print("     noen få aksjer gapper opp fra en lav inngangskurs. Sjekk «Handler»-")
            print("     arket og sorter på avk.")

        if prod is not None:
            print("\n" + "=" * 150)
            print("  PRODUKSJON — DEN KOMBINASJONEN master.py OG MAILEN LESER")
            print("=" * 150)
            print(f"  Valgt   : {prod['Strategi']} + {prod['Exit_Kode']} ({prod['Exit']})")
            print(f"  Grunnlag: {prod_grunn}")
            print(f"  {'Handler':>9}{'Dager':>8}{'Total':>10}{'CAGR':>9}{'MaxDD':>9}"
                  f"{'Snitt':>9}{'u/topp1%':>10}{'Åpne nå':>10}")
            print("  " + "-" * 74)
            print(f"  {int(prod.get('Handler', 0)):>9}"
                  f"{_t(prod.get('Snitt_Hold_Dager'), 1):>8}"
                  f"{_t(prod.get('Total_Pst'), 1, '%'):>10}"
                  f"{_t(prod.get('CAGR_Pst'), 1, '%'):>9}"
                  f"{_t(prod.get('MaxDD_Pst'), 1, '%'):>9}"
                  f"{_t(prod.get('Snitt_Handel_Pst'), 2, '%'):>9}"
                  f"{_t(prod.get('Snitt_Uten_Topp1pct_Pst'), 2, '%'):>10}"
                  f"{int(prod.get('Apne_Na_Live', 0)):>10}")
            print("  Tallene over er de SAMME som i tabellen lenger opp for denne")
            print("  kombinasjonen — mailen og Metrics-arket viser dem uregnet.")

        print("\n  VIKTIG: Nå testes mange flere valg enn før. Den beste raden er derfor enda")
        print("  mer utsatt for multiple-testing/overfitting. Alpha-plateauet trenes bare på")
        print("  INN-utvalget, men alle øvrige exit-parametre bør også valideres kronologisk")
        print("  før de brukes live.")
        print("=" * 150 + "\n")

    # ═════════════════════════════════════════════════════════════════════════
    # PRODUKSJON — ÉN KOMBINASJON, FILEN MASTER LESER
    # ═════════════════════════════════════════════════════════════════════════

    def velg_produksjon(sammendrag: pd.DataFrame):
        from runtime_config import choose_variant
        rows = sammendrag.replace({np.nan: None}).to_dict("records")
        if not rows:
            raise RuntimeError("Management lab has no comparable results")
        # Replace diagnostics before any validation can fail; never refer to a
        # comparison CSV left over from an earlier successful run.
        pd.DataFrame(rows).to_csv(config.ut_dir / "variant_comparison.csv", index=False)
        valid_rows = [r for r in rows if r.get("Train_Data_Valid", True)]
        if not valid_rows:
            raise RuntimeError("No management variant has valid training valuations")
        eligible = [r for r in valid_rows if r.get("Train_Trades", 0) >= config.min_signaler
                    and r.get("Train_CAGR_Pst") is not None
                    and r.get("Train_Trimmed_Return") is not None]
        # Bug-fix-only baseline: previous trimmed-return ranking, now training-only.
        baseline = (sorted(eligible, key=lambda r: (-r["Train_Trimmed_Return"], r["Variant"]))[0]["Variant"]
                    if eligible else "S1|F21")
        selected, reason = choose_variant(valid_rows, baseline, config.min_signaler)
        manual = os.environ.get("AKSJE_SENT_VALG", "").strip().upper()
        if manual:
            selected = next((r for r in rows if r["Variant"] == manual), None)
            if selected is None:
                raise ValueError("Unknown AKSJE_SENT_VALG: " + manual)
            reason = "Manual selection; not selected from the evaluation period."
        for row in rows:
            row["Selected"] = row["Variant"] == selected["Variant"]
            row["Baseline"] = row["Variant"] == baseline
        pd.DataFrame(rows).to_csv(config.ut_dir / "variant_comparison.csv", index=False)
        if not selected.get("data_valid", True):
            raise RuntimeError("Selected management variant has unverified held-position "
                               "valuations. See variant_comparison.csv; no result is published.")
        config.selected_comparison = selected
        config.baseline_variant = baseline
        name, code = selected["Variant"].split("|")
        strategy = next(x for x in STRATEGIER if x.navn.split()[0] == name)
        exit_rule = next(x for x in EXIT_STRATEGIER if x.kode == code)
        return strategy, exit_rule, reason + " Cutoff: " + config.inn_utvalg_slutt

    def _maal_kurve(kurve: pd.Series, cagr_fasit: Optional[float] = None,
                    aar_fasit: Optional[float] = None) -> dict:
        """
        Nøkkeltall fra den daglige kurven, men risikotall fra MÅNEDSPUNKTER.

        Sharpe regnet på daglige avkastninger og Sharpe regnet på månedlige er
        to forskjellige tall, og de tre andre strategiene i mailen rapporterer
        det månedlige. Å legge et daglig tall i samme kolonne ville sammenlignet
        to mål med samme navn.

        `cagr_fasit` og `aar_fasit` settes når laben alt HAR regnet ut tallet.
        Laben annualiserer over første inngang → siste exit; kurven går litt
        lenger. Å regne CAGR på nytt her ville gitt et annet tall enn tabellen
        laben selv skriver ut, og da er vi tilbake til to svar om samme fil.
        Sharpe, Sortino og Calmar regnes her fordi laben ikke regner dem i det
        hele tatt — men de bygger da på CAGR-en laben fant.
        """
        ut = {"total": np.nan, "cagr": np.nan, "mdd": np.nan, "vol": np.nan,
              "sharpe": None, "sortino": None, "calmar": None, "aar": np.nan,
              "maanedspunkter": 0, "fra": "", "til": ""}
        k = kurve.dropna()
        if len(k) < 2:
            return ut
        start, slutt = float(k.iloc[0]), float(k.iloc[-1])
        if start <= 0:
            return ut
        aar = (float(aar_fasit) if aar_fasit is not None
               else max((k.index[-1] - k.index[0]).days / 365.25, 0.01))
        cagr = (float(cagr_fasit) if cagr_fasit is not None
                else (slutt / start) ** (1.0 / aar) - 1.0)
        topp = k.cummax()
        mdd = float(((k - topp) / topp).min())

        m = k.resample("ME").last().dropna()
        r = m.pct_change().dropna()
        vol = float(r.std() * sqrt(12)) if len(r) > 1 and r.std() > 0 else 0.0
        ned = r[r < 0]
        dv = float(ned.std() * sqrt(12)) if len(ned) > 1 and ned.std() > 0 else 0.0
        ut.update({
            "total": slutt / start - 1.0, "cagr": cagr, "mdd": mdd, "vol": vol,
            "mdd_kurve": mdd,
            "sharpe": (cagr - RISIKOFRI) / vol if vol > 0 else None,
            "sortino": (cagr - RISIKOFRI) / dv if dv > 0 else None,
            "calmar": cagr / abs(mdd) if mdd else None,
            "aar": aar, "maanedspunkter": int(len(m)),
            "fra": str(k.index[0].date()), "til": str(k.index[-1].date()),
        })
        return ut

    def universkurve(md: MarkedsData, kurve: pd.Series) -> pd.Series:
        """
        Likevektet kjøp-og-hold av DET SAMME universet over DET SAMME vinduet.

        Dette er den eneste sammenligningen som ikke blander inn noe annet. En
        likevektet portefølje av små selskaper med rapporter på Euronext målt mot
        en kapitalvektet OSEBX måler størrelse og vekting, ikke signalet — og da
        vet du ikke hva tallet var. Benchmarken her deler univers og vekting med
        strategien; det eneste som skiller er HVILKE av dem den eier og NÅR.
        """
        if not len(kurve):
            return pd.Series(dtype=float)
        vindu = md.close.loc[kurve.index[0]:kurve.index[-1]]
        if vindu.empty:
            return pd.Series(dtype=float)
        forste = vindu.iloc[0]
        gyldig = [c for c in vindu.columns
                  if np.isfinite(forste.get(c, np.nan)) and forste.get(c, 0) > 0]
        if not gyldig:
            return pd.Series(dtype=float)
        rel = vindu[gyldig].divide(forste[gyldig], axis=1)
        return (rel.mean(axis=1) * config.startkapital).reindex(kurve.index,
                                                               method="ffill")

    def bygg_score_log(signaler: pd.DataFrame, s: Strategi,
                       handlet: set) -> pd.DataFrame:
        """
        Hele tverrsnittet av hendelser — også de strategien sa nei til.

        Et selskap som ble vurdert og forkastet skal se annerledes ut enn et
        selskap som aldri ble vurdert. Master regner persentiler mot kildens egen
        historikk, og en logg som bare inneholder kjøpene sier at alle kjøpene var
        middels gode. Filterutfallet står derfor som KOLONNER (over_sma, valgt),
        ikke som en manglende rad.

        `score` er RÅ endring i sentiment, ikke bedring_pst. Gulvet i
        prosentnevneren band på 89–96 % av hendelsene, og for dem er prosenten
        bare rå endring ganget med 20 — men ikke for de andre, så rekkefølgen
        vrir seg. Master bruker bare rekkefølgen. `bedring_pst` står i
        nabokolonnen, for terskelen som slipper en hendelse inn er en prosent.
        """
        if signaler.empty:
            return pd.DataFrame(columns=["date", "ticker", "score", "rank",
                                         "over_sma", "valgt", "grunn",
                                         "bedring_pst", "forrige_score",
                                         "ny_score", "endring", "gulv_bandt",
                                         "artikkeldato", "signal_id"])
        grense = s.terskel - 1e-9
        rader: List[dict] = []
        for dato, g in signaler.groupby("dato", sort=True):
            g = g.sort_values("endring", ascending=False)
            for rang, (_, r) in enumerate(g.iterrows(), start=1):
                passerte = bool(r["bedring_pst"] >= grense
                                and (bool(r["over_sma"]) or not s.krev_sma))
                sid = int(r["signal_id"])
                rader.append({
                    "date": pd.Timestamp(dato).strftime("%Y-%m-%d"),
                    "ticker": str(r["ticker"]),
                    "score": round(float(r["endring"]), 4),
                    "rank": rang,
                    "over_sma": "JA" if bool(r["over_sma"]) else "NEI",
                    "valgt": "JA" if sid in handlet else "NEI",
                    "grunn": ("handlet" if sid in handlet else
                              "passerte terskelen, men ingen plass"
                              if passerte else f"under {s.terskel:.0f} %"
                              if r["bedring_pst"] < grense else "under SMA50"),
                    "bedring_pst": round(float(r["bedring_pst"]), 1),
                    "forrige_score": float(r["forrige_score"]),
                    "ny_score": float(r["ny_score"]),
                    "endring": float(r["endring"]),
                    "gulv_bandt": "JA" if bool(r["gulv_bandt"]) else "NEI",
                    "artikkeldato": pd.Timestamp(r["artikkeldato"]).strftime("%Y-%m-%d"),
                    "signal_id": sid,
                })
        return pd.DataFrame(rader)

    def bygg_trade_log(h: pd.DataFrame, apne: List[dict]) -> pd.DataFrame:
        """
        To rader per handel — kjøp og salg — i formatet mailen alt leser.

        Åpne posisjoner får bare kjøpsraden. Det er ikke en mangel: en posisjon
        som står åpen HAR ikke et salg, og et påtvunget salg på siste rad ville
        gjort urealisert gevinst om til en handel som aldri skjedde.
        """
        rader: List[dict] = []

        def legg(dato, ticker, handling, antall, kurs, arsak,
                 pnl=None, dager=None) -> None:
            rader.append({"date": pd.Timestamp(dato).strftime("%Y-%m-%d"),
                          "ticker": str(ticker), "action": handling,
                          "shares": round(float(antall), 4),
                          "price": round(float(kurs), 4),
                          "value": round(float(antall) * float(kurs), 2),
                          "pnl": None if pnl is None else round(float(pnl), 2),
                          "dager": None if dager is None else int(dager),
                          "reason": arsak})

        if h is not None and not h.empty:
            for _, r in h.iterrows():
                kurs_inn = float(r["entry_price"])
                if kurs_inn <= 0:
                    continue
                # Den FAKTISKE kapitalen i plassen, ikke en likt delt
                # startkapital: plassen har rentet seg opp eller ned siden
                # første handel, og «100 000 kr» på hver rad i ti år er et tall
                # porteføljen aldri hadde.
                antall = float(r.get("kapital",
                                     config.startkapital
                                     / config.maks_posisjoner)) / kurs_inn
                legg(r["dato"], r["ticker"], "BUY", antall, kurs_inn,
                     f"{r['bedring_pst']:.0f} % bedring "
                     f"({r['forrige_score']:+.2f} → {r['ny_score']:+.2f})")
                # P&L i kroner på salgsraden. Uten den må mailen gjette hvilket
                # kjøp salget hører til, og strategien kan eie SAMME aksje i to
                # plasser samtidig: da matchet den 30. mars-salget mot 2.
                # mars-kjøpet i stedet for 2. januar, og viste +1,28 % der laben
                # målte +4,15 %. Paringen er kjent her; den skal ikke gjettes.
                legg(r["ut_dato"], r["ticker"], "SELL", antall,
                     float(r["exit_price"]), str(r["exit_arsak"]),
                     pnl=antall * (float(r["exit_price"]) - kurs_inn),
                     dager=int(r["hold_dager"]))
        for p in apne:
            kurs_inn = float(p["entry_price"])
            if kurs_inn <= 0:
                continue
            antall = float(p["capital"]) / kurs_inn
            legg(md.close.index[p["inn_i"]], p["ticker"], "BUY", antall, kurs_inn,
                 f"{p['bedring_pst']:.0f} % bedring — STÅR ÅPEN")
        if not rader:
            return pd.DataFrame(columns=["date", "ticker", "action", "shares",
                                         "price", "value", "reason"])
        return pd.DataFrame(rader).sort_values(["date", "ticker", "action"]
                                               ).reset_index(drop=True)

    def bygg_posisjoner_na(apne: List[dict]) -> pd.DataFrame:
        """
        Hva du eier nå, og HVORFOR du eier det.

        Uten dette arket kan mailen bare vise tickeren, for en komma-separert
        streng i Monthly_Holdings er alt den har. Men hele poenget med denne
        strategien er endringen som utløste kjøpet — «0,20 → 0,82, 310 %
        bedring» — og en posisjonsliste uten den sier ikke hvorfor aksjen er
        der. Da må du åpne labfilen for å finne det ut, og det gjør ingen.
        """
        kol = ["ticker", "selskap", "inn_dato", "dager", "bedring_pst",
               "forrige_score", "ny_score", "endring", "entry_price",
               "kurs_na", "avk_pst", "tittel", "shares", "capital", "market_value", "quote_date"]
        if not apne:
            return pd.DataFrame(columns=kol)
        siste_i = len(md.close.index) - 1
        rader = []
        for pos in sorted(apne, key=lambda x: -float(x["bedring_pst"])):
            k = md.close[pos["ticker"]]
            na = float(k.iloc[siste_i]) if np.isfinite(k.iloc[siste_i]) else np.nan
            if not np.isfinite(na):
                siste_gyldig = k.iloc[:siste_i + 1].last_valid_index()
                na = float(k.loc[siste_gyldig]) if siste_gyldig is not None else np.nan
            inn = float(pos["entry_price"])
            rader.append({
                "ticker": pos["ticker"],
                "selskap": pos["selskap"],
                "inn_dato": str(md.close.index[pos["inn_i"]].date()),
                "dager": int(siste_i - pos["inn_i"]),
                "bedring_pst": round(float(pos["bedring_pst"]), 1),
                "forrige_score": round(float(pos["forrige_score"]), 4),
                "ny_score": round(float(pos["ny_score"]), 4),
                "endring": round(float(pos["endring"]), 4),
                "entry_price": round(inn, 4),
                "kurs_na": None if not np.isfinite(na) else round(na, 4),
                "avk_pst": (None if not np.isfinite(na) or inn <= 0
                            else round((na / inn - 1.0) * 100.0, 2)),
                "tittel": str(pos.get("tittel", ""))[:90],
                "shares": float(pos["capital"]) / inn,
                "capital": float(pos["capital"]),
                "market_value": None if not np.isfinite(na) else float(pos["capital"]) / inn * na,
                "quote_date": str(k.iloc[:siste_i + 1].last_valid_index().date()),
            })
        return pd.DataFrame(rader)[kol]

    def skriv_master_fil(streng: dict, live: dict, s: Strategi, e: ExitStrategi,
                         signaler: pd.DataFrame, grunn: str,
                         antall_bestod: int) -> Optional[Path]:
        """
        Produksjonsfilen: de fem arkene master.py og mailen alt leser.

        Arknavnene og kolonnenavnene er IKKE valgfrie. «Score_Log» med date /
        ticker / score er det master.py rangerer på, og «Metrics» med cagr som
        brøk er det mailen viser. Å finne på nye navn her betyr å endre to lesere
        i tillegg, og da er det to steder til som kan bli uenige om samme fil.

        TO KJØRINGER, OG DET ER HELT BESTEMT HVEM SOM EIER HVA
        -----------------------------------------------------
        `streng` er den vanlige kjøringen — nøyaktig den raden laben skriver i
        Sammendrag og i den utskrevne tabellen for denne kombinasjonen. ALLE
        MÅLTE TALL kommer derfra, uregnet: CAGR, total, drawdown, treffrate,
        alpha. Ikke fordi det ene tallet er penere, men fordi mailen og
        labrapporten ellers ville oppgitt to CAGR-er for den samme strategien —
        og det har skjedd før i denne koden: 157,37 % i mailen mot 146,68 % i
        loggen, for samme fil.

        `live` er den samme kombinasjonen uten modenhetsfilter og uten
        tvangssalg. Den eier ÉN ting: hva du faktisk eier nå. Den strenge
        kjøringen forkaster de ferskeste signalene med vilje (ellers kunne en
        8-dagersregel lånt signaler 63-dagersregelen ikke rakk å måle), og en
        posisjonsliste uten dem er en liste over forrige kvartal.

        Sharpe, Sortino og Calmar regnes her, av den strenge kurven, fordi laben
        ikke regner dem. De bygger på labens egen CAGR, ikke på en ny.
        """
        if not streng.get("data_valid", True):
            raise RuntimeError("Management valuation is incomplete; refusing to publish performance")
        kurve = streng.get("kurve")
        h = streng.get("handler")
        if kurve is None or not len(kurve) or h is None or h.empty:
            log.warning("Produksjon: den strenge kjøringen har ingen handler — "
                        "filen master leser hoppes over.")
            return None

        # Labens egen periode og CAGR. Samme formel den bruker selv: første
        # inngang → siste exit, ikke kurvens ytterpunkter.
        aar_lab = max((kurve.index[-1] - kurve.index[0]).days / 365.25, 0.01)
        cagr_lab = streng.get("CAGR_Pst")
        cagr_lab = (None if cagr_lab is None or not np.isfinite(cagr_lab)
                    else float(cagr_lab) / 100.0)
        n = _maal_kurve(kurve, cagr_fasit=cagr_lab, aar_fasit=aar_lab)

        bench = universkurve(md, kurve)
        b_cagr = np.nan
        if len(bench) >= 2 and float(bench.iloc[0]) > 0 and aar_lab > 0:
            b_cagr = (float(bench.iloc[-1]) / float(bench.iloc[0])
                      ) ** (1.0 / aar_lab) - 1.0

        apne = live.get("apne", []) if live else []
        handlet = set(int(x) for x in h["signal_id"])
        h_live = live.get("handler") if live else None
        if h_live is not None and not h_live.empty:
            handlet |= set(int(x) for x in h_live["signal_id"])
        handlet |= {int(pos["signal_id"]) for pos in apne}
        score_log = bygg_score_log(signaler, s, handlet)
        # Handelsloggen er den strenge — de målte handlene — pluss det som står
        # åpent nå, som bare kjøpsrader. En åpen posisjon HAR ikke et salg.
        trade_log = bygg_trade_log(h, apne)

        beholdning = live.get("beholdning") if live else None
        siste_dag = ((live.get("kurve").index[-1]
                      if live and len(live.get("kurve", [])) else kurve.index[-1]))
        if beholdning is None or beholdning.empty:
            beholdning = pd.DataFrame([{"dato": str(siste_dag.date()),
                                        "holdings": "CASH"}])
        else:
            beholdning = beholdning.copy()
            beholdning["dato"] = [pd.Timestamp(d).strftime("%Y-%m-%d")
                                  for d in beholdning["dato"]]
        na = ", ".join(sorted(pos["ticker"] for pos in apne)) or "CASH"
        if beholdning.iloc[-1]["holdings"] != na:
            beholdning = pd.concat([beholdning, pd.DataFrame(
                [{"dato": str(siste_dag.date()), "holdings": na}])],
                ignore_index=True)

        # Tre tilstander, ikke to. Et manuelt valg har ikke STRØKET på porten —
        # det ble aldri vurdert mot den, og «NEI» ville sagt noe annet enn det
        # som skjedde.
        manuelt = "manual" in grunn.lower() or "manuelt" in grunn.lower()
        if manuelt:
            port_status = "IKKE VURDERT — valgt manuelt"
        elif grunn.startswith("INGEN") or antall_bestod == 0:
            port_status = "NEI"
        else:
            port_status = "JA"
        bestod = port_status == "JA"
        krav = porten(streng)
        stryk = [k for k, ok in krav.items() if not ok]

        def fra_lab(nokkel: str, skala: float = 1.0, d: int = 4):
            """Tallet slik laben regnet det ut. Ingen ny utregning her."""
            v = streng.get(nokkel)
            try:
                if v is None or not np.isfinite(float(v)):
                    return None
            except (TypeError, ValueError):
                return None
            return round(float(v) * skala, d)

        live_kurve = live.get("kurve") if live else None
        live_slutt = (float(live_kurve.iloc[-1]) if live_kurve is not None
                      and len(live_kurve) else None)
        metrics = {
            "accounting_version": 2,
            "data_valid": True,
            "as_of": str(kurve.index[-1].date()),
            "selection_method": "training_cagr",
            "selection_cutoff": config.inn_utvalg_slutt,
            "baseline_variant": getattr(config, "baseline_variant", ""),
            "train_cagr_pst": getattr(config, "selected_comparison", {}).get("Train_CAGR_Pst"),
            "test_cagr_pst": getattr(config, "selected_comparison", {}).get("Test_CAGR_Pst"),
            "utgave": "v6-hendelse",
            "motor": "SentimentHendelseLab — hendelsesdrevet, kjøp dagen etter rapporten",
            "valgt_strategi": s.navn,
            "valgt_exit": e.kode,
            "valgt_exit_navn": e.navn,
            "exit_beskrivelse": e.beskrivelse,
            "max_hold_sessions": streng.get("Valgt_Hold", effektiv_maks_hold(e, config.hold_dager)),
            "max_positions": config.maks_posisjoner,
            "sentiment_denominator_floor": config.gulv,
            "entry_delay_sessions": 1,
            "price_exit_delay_sessions": 1,
            "exit_parameters_json": __import__("json").dumps(asdict(e), ensure_ascii=False),
            "replacement_min_age_sessions": config.replace_min_age,
            "replacement_strength_ratio": config.replace_strength_ratio,
            "replacement_decay_sessions": config.replace_decay_days,
            "minimum_trend_exit_age_sessions": config.min_dager_for_trend_exit,
            "minimum_relative_exit_age_sessions": config.min_dager_for_relative_exit,
            "transaction_cost": 0.0,
            "valgt_terskel_pst": s.terskel,
            "krev_sma50": "JA" if s.krev_sma else "NEI",
            "valg_grunn": grunn,
            "robusthetsport_bestod": port_status,
            "porten_stryk": "; ".join(stryk) if stryk else "",
            "kombinasjoner_testet": len(STRATEGIER) * len(EXIT_STRATEGIER),
            "kombinasjoner_bestod": int(antall_bestod),
            # ── ALLE MÅLTE TALL: labens egen rad, uregnet ────────────────────
            "maalt_paa": "én daglig simulering for kurve, nøkkeltall, handler og åpne posisjoner",
            "fra": str(pd.Timestamp(kurve.index[0]).date()),
            "til": str(pd.Timestamp(kurve.index[-1]).date()),
            "aar": round(float(aar_lab), 2),
            "maanedspunkter": n["maanedspunkter"],
            "hendelser_totalt": int(len(signaler)),
            "hendelser_over_terskel": int(streng.get("Signaler", 0)),
            "handler": int(streng.get("Handler", 0)),
            "umodne_forkastet": int(streng.get("Umodne", 0)),
            "tapt_ingen_plass": int(streng.get("Tapt", 0)),
            # Seks desimaler på brøkene. Fire ville vist 6,69 % der laben
            # skriver 6,6947 % i Sammendrag, og da er de to arkene uenige så
            # snart noen ser på mer enn to desimaler.
            "total_avkastning": fra_lab("Total_Pst", 0.01, 6),
            "cagr": fra_lab("CAGR_Pst", 0.01, 6),
            "cagr_meningsfull": "JA" if float(aar_lab) >= MIN_AAR_FOR_CAGR else "NEI",
            "max_drawdown": fra_lab("MaxDD_Pst", 0.01, 6),
            "drawdown_grunnlag": "daglig mark-to-market",
            "treffrate": fra_lab("Treff_Pst", 0.01, 6),
            "snitt_handel_pst": fra_lab("Snitt_Handel_Pst", 1.0, 3),
            "median_handel_pst": fra_lab("Median_Handel_Pst", 1.0, 3),
            "snitt_hold_dager": fra_lab("Snitt_Hold_Dager", 1.0, 1),
            # Beste og verste handel: laben rapporterer dem ikke i raden sin,
            # men det er max og min av SAMME kolonne den snitter («avk»), ikke en
            # ny metode. Uten dem ville kortets «Ytterpunkter» stått på et annet
            # grunnlag enn «Snitt handel» rett over.
            "alpha_pst": fra_lab("Mot_marked_Pst", 1.0, 3),
            "alpha_uten_topp1pct_pst": fra_lab("Alpha_Uten_Topp1pct_Pst", 1.0, 3),
            "verste_handel_pst": fra_lab("Verste_Handel_Pst", 1.0, 2),
            "post_alpha_pst": fra_lab("UT_Mot_marked_Pst", 1.0, 3),
            "ut_snitt_pst": fra_lab("UT_Snitt_Pst", 1.0, 3),
            "ekstra_dag_pst": fra_lab("Dag1_Pst", 1.0, 3),
            # Uten disse to ser en rad båret av noen få gap ut som en strategi.
            "snitt_uten_topp1pct_pst": fra_lab("Snitt_Uten_Topp1pct_Pst", 1.0, 3),
            "beste_handel_pst": fra_lab("Beste_Handel_Pst", 1.0, 2),
            "gulv_pst": fra_lab("Gulv_Pst", 1.0, 1),
            # ── Regnet her, fordi laben ikke regner dem ──────────────────────
            "sharpe": None if n["sharpe"] is None else round(float(n["sharpe"]), 3),
            "sortino": None if n["sortino"] is None else round(float(n["sortino"]), 3),
            "calmar": None if n["calmar"] is None else round(float(n["calmar"]), 3),
            "volatilitet": round(float(n["vol"]), 4),
            "risikotall_grunnlag": ("Sharpe/Sortino/Calmar er regnet av "
                                    "månedspunktene på labens kurve, med labens "
                                    "egen CAGR: (CAGR − 3 %) / årlig vol. Laben "
                                    "regner dem ikke selv."),
            "benchmark_cagr": None if not np.isfinite(b_cagr) else round(float(b_cagr), 4),
            "benchmark_grunnlag": ("likevektet kjøp-og-hold av samme univers, "
                                   "samme vindu"),
            # ── Live: eier BARE posisjonslisten ─────────────────────────────
            "apne_na": len(apne),
            "live_grunnlag": "samme simulering som kurve og nøkkeltall; siste observerte kurs, ingen tvangssalg",
            "live_total_avkastning": (None if live_slutt is None else
                                      round(live_slutt / config.startkapital - 1.0, 4)),
            "live_handler": int(live.get("Handler", 0)) if live else 0,
            "score_i_score_log": "rå endring i sentiment (ny − forrige)",
        }

        posisjoner_na = bygg_posisjoner_na(apne)

        sti = (config.master_ut_dir /
               f"Sentiment_v6_Hendelse_SMA{config.sma_dager}_"
               f"{datetime.now():%Y-%m-%d}.xlsx")
        ec = pd.DataFrame({"Date": kurve.index, "Strategy": kurve.values})
        if len(bench) == len(kurve):
            ec["Benchmark"] = bench.values
        try:
            with pd.ExcelWriter(str(sti), engine="openpyxl") as w:
                score_log.to_excel(w, sheet_name="Score_Log", index=False)
                pd.DataFrame([metrics]).to_excel(w, sheet_name="Metrics", index=False)
                ec.to_excel(w, sheet_name="Equity_Curve", index=False)
                beholdning.to_excel(w, sheet_name="Monthly_Holdings", index=False)
                trade_log.to_excel(w, sheet_name="Trade_Log", index=False)
                posisjoner_na.to_excel(w, sheet_name="Posisjoner_Na", index=False)
                pd.DataFrame([asdict(x) for x in EXIT_STRATEGIER]).to_excel(
                    w, sheet_name="Exit_Regler", index=False)
        except Exception as feil:
            log.error("Produksjonsfilen kunne ikke skrives (%s). master.py "
                      "faller tilbake på den månedlige utgaven hvis den finnes, "
                      "ellers teller NLP som nøytral 50.", feil)
            return None

        if score_log.empty:
            log.warning("Score_Log er TOM — master.py teller da NLP som en kilde "
                        "uten mening om noe selskap. Laben fant %d hendelser.",
                        len(signaler))
        else:
            log.info("Score_Log: %d rader over %d dager (%d handlet, %d bare "
                     "vurdert)", len(score_log),
                     score_log["date"].nunique(),
                     int((score_log["valgt"] == "JA").sum()),
                     int((score_log["valgt"] == "NEI").sum()))
        log.info("Produksjon: %s + %s → %s", s.navn, e.kode, sti.name)
        if manuelt:
            log.warning("Produksjonsvalget er IKKE vurdert mot robusthetsporten: "
                        "%s", grunn)
        elif not bestod:
            log.warning("Produksjonsvalget bestod IKKE robusthetsporten: %s", grunn)
        return sti

    # ═════════════════════════════════════════════════════════════════════════
    # HOVEDLØP
    # ═════════════════════════════════════════════════════════════════════════

    log.info("=" * 74)
    log.info("  SENTIMENT HENDELSE LAB — exit-laboratorium")
    log.info("=" * 74)

    artikler = les_artikler()
    tickere = sorted({str(c).strip() + config.oslo_suffix
                      for c in artikler["Company"].dropna().unique()
                      if str(c).strip() and str(c).strip() != "nan"})
    md = hent_kurser(tickere)
    signaler = bygg_signaler(artikler, md)
    if signaler.empty:
        log.error("Ingen hendelser — artiklene og kursene overlapper ikke.")
        return

    nyhetskart.clear()
    nyhetskart.update(lag_nyhetskart(signaler))
    alpha_hold_map, alpha_decay = velg_alpha_horisonter(signaler, md)

    resultater: List[dict] = []
    handler_lister: List[pd.DataFrame] = []
    total = len(STRATEGIER) * len(EXIT_STRATEGIER)
    nr = 0
    for e in EXIT_STRATEGIER:
        log.info("Exit     : %s — %s", e.kode, e.navn)
        for s in STRATEGIER:
            nr += 1
            r = kjor_strategi(s, e, signaler, md, alpha_hold_map)
            h = r.pop("handler")
            from runtime_config import split_metrics
            curve_for_selection = r.get("kurve", pd.Series(dtype=float))
            r.update(split_metrics(list(curve_for_selection.items()), config.inn_utvalg_slutt))
            train_h = (h[h["ut_dato"] <= pd.Timestamp(config.inn_utvalg_slutt)]
                       if h is not None and not h.empty else pd.DataFrame())
            r["Train_Trades"] = len(train_h)
            r["Train_Data_Valid"] = not any(
                issue["date"] <= config.inn_utvalg_slutt
                for issue in r.get("valuation_issues", []))
            trimmed = (train_h.sort_values("avk").iloc[:max(1, int(len(train_h) * .99))]
                       if len(train_h) else train_h)
            r["Train_Trimmed_Return"] = float(trimmed["avk"].mean()) if len(trimmed) else float("nan")
            r["Variant"] = s.navn.split()[0] + "|" + e.kode
            for nokkel in ("kurve", "apne", "beholdning"):
                r.pop(nokkel, None)
            if h is not None and not h.empty:
                handler_lister.append(h)
            resultater.append(r)
            if nr % 25 == 0 or nr == total:
                log.info("Fremdrift: %d / %d backtester", nr, total)

    sammendrag = pd.DataFrame(resultater)
    alle_handler = (pd.concat(handler_lister, ignore_index=True)
                    if handler_lister else pd.DataFrame())
    exit_beste = beste_per_exit(sammendrag)

    # ── Produksjonskombinasjonen: én av de 384, kjørt både strengt og live ───
    prod = prod_live = prod_rad = None
    prod_s = prod_e = None
    prod_grunn = ""
    antall_bestod = 0
    if not sammendrag.empty:
        gyldige = sammendrag[(sammendrag["Handler"] >= config.min_signaler)
                             & sammendrag["Mot_marked_Pst"].notna()]
        if not gyldige.empty:
            antall_bestod = int(gyldige.apply(
                lambda r: all(porten(r).values()), axis=1).sum())
    if skriv_master:
        # Produksjonssteget skal ikke kunne koste deg laben. 384 backtester er
        # det dyre; filen master leser kan skrives på nytt med én ny kjøring.
        try:
            prod_s, prod_e, prod_grunn = velg_produksjon(sammendrag)
            if prod_s is not None and prod_e is not None:
                log.info("Produksjon: %s + %s — kjører på nytt for å få kurven "
                         "og handelsloggen …", prod_s.navn, prod_e.kode)
                prod = kjor_strategi(prod_s, prod_e, signaler, md, alpha_hold_map)
                prod_live = prod
                prod_rad = {k: v for k, v in prod.items()
                            if k not in ("handler", "kurve", "apne", "beholdning")}
                prod_rad["Apne_Na_Live"] = len(prod_live.get("apne", []))
            else:
                log.warning("Produksjon: ingen kombinasjon kunne velges (%s) — "
                            "filen master leser blir ikke skrevet.", prod_grunn)
        except Exception as feil:
            log.error("Produksjonssteget feilet (%s). Laben fullføres, men "
                      "master.py får ingen ny fil — den faller tilbake på den "
                      "månedlige utgaven hvis den finnes.", feil)
            prod = prod_live = prod_rad = None

    skriv_rapport(sammendrag, signaler, exit_beste, prod_rad, prod_grunn)

    if prod is not None:
        try:
            production_path = skriv_master_fil(prod, prod_live, prod_s, prod_e, signaler,
                                               prod_grunn, antall_bestod)
            if production_path is None:
                raise RuntimeError("Management production file was not written")
        except Exception as feil:
            log.error("Produksjonsfilen kunne ikke bygges (%s). Laben "
                      "fullføres.", feil)

    # Exit-årsakstabell gjør det lett å se om en regel faktisk trigget eller om
    # nesten alle handler bare endte i hard cap.
    if not alle_handler.empty:
        exit_aarsaker = (alle_handler.groupby(
            ["exit_kode", "exit", "strategi", "exit_arsak"], dropna=False)
            .size().rename("Antall").reset_index())
    else:
        exit_aarsaker = pd.DataFrame()

    exit_regler = pd.DataFrame([asdict(e) for e in EXIT_STRATEGIER])

    # Excel-vennlige sorteringer.
    if not sammendrag.empty:
        sammendrag = sammendrag.sort_values(
            ["Exit_Kode", "SMA", "Terskel_Pst"]).reset_index(drop=True)
    if not alle_handler.empty:
        alle_handler = alle_handler.sort_values(
            ["exit_kode", "strategi", "dato", "signal_id"]).reset_index(drop=True)

    sti = config.ut_dir / f"Sentiment_HendelseLab_Exit_{datetime.now():%Y-%m-%d}.xlsx"
    with pd.ExcelWriter(str(sti), engine="openpyxl") as w:
        sammendrag.to_excel(w, sheet_name="Sammendrag", index=False)
        exit_beste.to_excel(w, sheet_name="Exit_Beste", index=False)
        exit_regler.to_excel(w, sheet_name="Exit_Regler", index=False)
        alpha_decay.to_excel(w, sheet_name="Alpha_Decay", index=False)
        if prod_rad is not None:
            # Raden mailen viser, i laben den kom fra. Ett tall, to steder.
            pd.DataFrame([{**prod_rad, "Valg_Grunn": prod_grunn}]).to_excel(
                w, sheet_name="Produksjon", index=False)
        signaler.to_excel(w, sheet_name="Signaler", index=False)
        if not alle_handler.empty:
            alle_handler.to_excel(w, sheet_name="Handler", index=False)
            # De tjue største enkelthandlene, samlet. Bærer noen få gap hele
            # snittet, står de her og er til å sjekke på ett blikk.
            (alle_handler.nlargest(20, "avk")[
                ["strategi", "exit_kode", "ticker", "dato", "ut_dato",
                 "entry_price", "exit_price", "avk", "hold_dager", "exit_arsak"]]
             .to_excel(w, sheet_name="Storste_Vinnere", index=False))
        if not exit_aarsaker.empty:
            exit_aarsaker.to_excel(w, sheet_name="Exit_Aarsaker", index=False)
        (signaler[["bedring_pst", "endring", "forrige_score", "ny_score",
                   "gulv_bandt"]].describe()
         .to_excel(w, sheet_name="Fordeling"))

    log.info("Skrevet  : %s", sti)
    log.info("=== SentimentHendelseLab ferdig ===")
    if skriv_master and (prod is None or 'production_path' not in locals() or production_path is None):
        raise RuntimeError("Management export failed; no current report may be sent")
    return production_path if skriv_master else sti
#SentimentHendelseLab()


##Ledelses-sentiment: tolv måter å komme seg UT av handelen
def SentimentExitLab():
    """
    Samme inngang, tolv ulike exit. Hva er det riktige tidspunktet å selge?

    Inngangen holdes FAST — samme terskel, samme dag, samme signal — og bare
    exiten varieres. Ellers blandes to effekter, og du vet ikke om et bedre
    tall kom fra å kjøpe smartere eller selge smartere.

        E1  tid-5              5 handledager
        E2  tid-21             21 handledager (dagens)
        E3  tid-63             63 handledager
        E4  neste-rapport      til selskapet rapporterer igjen (tak 90 d)
        E5  sentiment-ned      ut hvis neste rapport er svakere
        E6  decay-1.00         ren fortrengning, ingen forfall  ← KONTROLL
        E7  decay-0.99         halveringstid 69 dager
        E8  decay-0.97         halveringstid 23 dager
        E9  decay-0.90         halveringstid 7 dager
        E10 trailing-15        −15 % fra toppen (intradag)
        E11 tp20-tid42         +20 % gevinstsikring, ellers 42 dager
        E12 sma-brudd          ut når kursen faller under SMA50

    ─────────────────────────────────────────────────────────────────────────
    DECAY-KONKURRANSEN (E6–E9)

    Dette er ikke en exit-regel i vanlig forstand — det er ingen utgangsdato i
    det hele tatt. Hvert signal får med seg scoren sin (bedringen i prosent),
    og den forfaller litt hver dag:

        score i dag = bedring ved rapporten × decay^(dager siden)

    Porteføljen er til enhver tid de N høyeste scorene. Kommer det et ferskt
    signal som er sterkere enn den svakeste posisjonen din, tar det plassen.
    Exiten er dermed ENDOGEN: du selger ikke fordi klokka har gått, men fordi
    noen andre har en bedre grunn til å eie plassen.

    Halveringstider, og hvor lenge et 400 %-signal holder plassen mot et
    ferskt på 50 %:

        1,00   aldri            ∞ dager     ← kontrollen: hva gir fortrengning
        0,99   69 dager       207 dager        alene, uten forfall?
        0,97   23 dager        69 dager
        0,90    7 dager        20 dager

    E6 er med nettopp som kontroll. Slår 0,97 den, er det FORFALLET som gjør
    jobben. Slår den ikke, er det bare fortrengningen — og da er decay-tallet
    en parameter du ikke trenger.

    ─────────────────────────────────────────────────────────────────────────
    HVORFOR HIGH OG LOW HENTES NÅ

    Forrige utgave lastet bare ned sluttkurser. Da kan ikke trailing stop og
    take-profit måles ærlig: du ser bare om SLUTTKURSEN brøt nivået, ikke om
    aksjen var innom det i løpet av dagen. Stops utløses da sjeldnere i
    backtesten enn i virkeligheten, og resultatet blir for pent — særlig på
    illikvide småselskaper.

    E10 og E11 bruker derfor intradag High og Low. Ett forbehold står igjen:
    de antar at du får fylt PÅ nivået. Gapper aksjen forbi stoppen på åpning,
    fikk du en verre kurs. Tallene for E10 er altså fortsatt et lite hakk for
    gode, og det er en grunn til å ikke velge den på marginene.

    ─────────────────────────────────────────────────────────────────────────
    KJØRING

        SentimentExitLab()

    Leser artiklene i DataNLP — skraper ingenting.
    """

    import logging
    import warnings
    from dataclasses import dataclass
    from datetime import datetime
    from pathlib import Path
    from typing import Callable, Dict, List, Optional, Tuple

    import numpy as np
    import pandas as pd
    import yfinance as yf

    warnings.filterwarnings("ignore")
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s  %(levelname)-8s  %(message)s",
                        datefmt="%H:%M:%S")
    log = logging.getLogger("ExitLab")

    # ═════════════════════════════════════════════════════════════════════════
    # OPPSETT
    # ═════════════════════════════════════════════════════════════════════════

    @dataclass
    class Config:
        base_dir: Path = Path(os.environ.get(
            "AKSJE_BASE_DIR", r"C:\Users\ander\Desktop\Python_K4\ExcelData"))
        nlp_output_dir: str = "DataNLP"
        output_dir: str = "StrategyResults_v4_Sentiment"
        oslo_suffix: str = ".OL"

        # ── INNGANGEN — holdes fast for alle tolv ────────────────────────
        INN_TERSKEL: float = 50.0      # % bedring fra forrige rapport
        INN_KREV_SMA: bool = False
        sma_dager: int = 50
        gulv: float = 0.05

        startkapital: float = 1_000_000.0
        maks_posisjoner: int = 10
        # Ingen exit får holde en plass lenger enn dette. En posisjon som blir
        # stående i evigheten er ikke en strategi, den er en sperre.
        maks_hold_dager: int = 90

        inn_utvalg_slutt: str = "2025-06-30"
        min_handler: int = 30

        @property
        def nlp_dir(self) -> Path:
            return self.base_dir / self.nlp_output_dir

        @property
        def ut_dir(self) -> Path:
            p = self.base_dir / self.output_dir
            p.mkdir(parents=True, exist_ok=True)
            return p

    config = Config()

    # ═════════════════════════════════════════════════════════════════════════
    # DATA
    # ═════════════════════════════════════════════════════════════════════════

    def les_artikler() -> pd.DataFrame:
        filer = sorted(p for p in config.nlp_dir.glob("NLP_Sentiment_Detail_*.xlsx")
                       if not p.name.startswith("~$"))
        if not filer:
            raise FileNotFoundError(f"Ingen artikkelfiler i {config.nlp_dir}")
        deler = []
        for f in filer:
            try:
                d = pd.read_excel(f)
            except Exception:
                continue
            if not d.empty and "Article_Date" in d.columns:
                d["_fil"] = f.name
                deler.append(d)
        if not deler:
            raise FileNotFoundError(f"Ingen lesbare artikkelfiler i {config.nlp_dir}")
        df = pd.concat(deler, ignore_index=True)
        df["Article_Date"] = (df["Article_Date"].astype(str)
                              .str.replace(r"\n.*$", "", regex=True).str.strip())
        df["Article_Date"] = pd.to_datetime(df["Article_Date"],
                                            format="%d %b %Y", errors="coerce")
        df = df.dropna(subset=["Article_Date"])
        if "Text_Length" in df.columns:
            df = df[df["Text_Length"] > 0]
        if "Final_Score" not in df.columns:
            raise KeyError("Artikkelfilene mangler Final_Score.")
        df["Final_Score"] = pd.to_numeric(df["Final_Score"], errors="coerce")
        df = df.dropna(subset=["Final_Score"])
        nokler = [k for k in ("Company", "Article_Date", "Article_Title")
                  if k in df.columns]
        if nokler:
            df = df.sort_values("_fil").drop_duplicates(subset=nokler, keep="last")
        df = df.sort_values(["Company", "Article_Date"]).reset_index(drop=True)
        log.info("Artikler : %d fra %d fil(er), %d selskaper, %s → %s",
                 len(df), len(deler), df["Company"].nunique(),
                 df["Article_Date"].min().date(), df["Article_Date"].max().date())
        return df

    def hent_kurser(tickere: List[str]
                    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """(slutt, høy, lav) — intradag trengs for at stops skal kunne måles."""
        log.info("Kurser   : laster ned %d tickere (Close, High, Low) …",
                 len(tickere))
        data = yf.download(tickere, start="2019-01-01", auto_adjust=True,
                           progress=False)
        if data.empty:
            raise RuntimeError("yfinance ga ingen data.")

        def felt(navn: str) -> pd.DataFrame:
            if isinstance(data.columns, pd.MultiIndex):
                return data[navn].copy() if navn in data.columns.levels[0] \
                    else pd.DataFrame(index=data.index)
            d = data[[navn]].copy()
            d.columns = tickere[:1]
            return d

        slutt, hoy, lav = felt("Close"), felt("High"), felt("Low")
        for d in (slutt, hoy, lav):
            d.index = pd.to_datetime(d.index)
            d.sort_index(inplace=True)
        gyldige = [c for c in slutt.columns if slutt[c].count() >= 120]
        slutt = slutt[gyldige]
        hoy = hoy.reindex(columns=gyldige)
        lav = lav.reindex(columns=gyldige)
        # Mangler intradag for en ticker, faller vi tilbake på sluttkursen.
        # Da blir stoppen målt på close for akkurat den — konservativt, og
        # bedre enn å kaste selskapet ut av testen.
        hoy = hoy.fillna(slutt)
        lav = lav.fillna(slutt)
        log.info("Kurser   : %d tickere, %s → %s", len(gyldige),
                 slutt.index[0].date(), slutt.index[-1].date())
        return slutt, hoy, lav

    # ═════════════════════════════════════════════════════════════════════════
    # SIGNALENE — samme inngang for alle tolv
    # ═════════════════════════════════════════════════════════════════════════

    def bygg_signaler(artikler: pd.DataFrame, slutt: pd.DataFrame) -> pd.DataFrame:
        kart = {c: str(c).strip() + config.oslo_suffix
                for c in artikler["Company"].dropna().unique()
                if str(c).strip() and str(c).strip() != "nan"}
        kart = {c: t for c, t in kart.items() if t in slutt.columns}
        log.info("Kobling  : %d av %d selskaper har kurser",
                 len(kart), artikler["Company"].nunique())
        if not kart:
            raise RuntimeError("Ingen selskaper lot seg koble mot kurser.")

        over_sma = (slutt > slutt.rolling(config.sma_dager).mean())
        n = len(slutt.index)
        rader: List[dict] = []
        for selskap, d in artikler.groupby("Company"):
            if selskap not in kart:
                continue
            ticker = kart[selskap]
            d = d.sort_values("Article_Date")
            sc = d["Final_Score"].to_numpy(dtype=float)
            dat = list(d["Article_Date"])
            for i in range(1, len(sc)):
                ny, forrige = float(sc[i]), float(sc[i - 1])
                raa = abs(forrige)
                bedring = (ny - forrige) / max(raa, config.gulv) * 100.0
                if not np.isfinite(bedring):
                    continue
                inn = int(slutt.index.searchsorted(dat[i]))
                if inn >= n - 2:
                    continue
                # Neste rapport for SAMME selskap — grunnlaget for E4 og E5.
                if i + 1 < len(sc):
                    neste_i = int(slutt.index.searchsorted(dat[i + 1]))
                    neste_darligere = bool(float(sc[i + 1]) < ny)
                else:
                    neste_i, neste_darligere = -1, False
                rader.append({
                    "inn_i": inn, "dato": slutt.index[inn],
                    "artikkeldato": dat[i], "selskap": selskap, "ticker": ticker,
                    "forrige_score": round(forrige, 4), "ny_score": round(ny, 4),
                    "endring": round(ny - forrige, 4),
                    "bedring_pst": round(bedring, 1),
                    "gulv_bandt": raa < config.gulv,
                    "over_sma": bool(over_sma[ticker].iloc[inn])
                    if ticker in over_sma.columns else False,
                    "neste_rapport_i": neste_i,
                    "neste_darligere": neste_darligere,
                })
        if not rader:
            log.warning("Signaler : 0 hendelser.")
            return pd.DataFrame(columns=["inn_i", "dato", "ticker", "bedring_pst"])

        s = pd.DataFrame(rader).sort_values("inn_i").reset_index(drop=True)
        # Inngangsfilteret — likt for alle tolv exitene.
        f = s[(s["bedring_pst"] >= config.INN_TERSKEL - 1e-9)
              & (s["over_sma"] if config.INN_KREV_SMA
                 else s["bedring_pst"].notna())].reset_index(drop=True)
        log.info("Signaler : %d hendelser, %d passerer inngangen "
                 "(≥%.0f %%%s)", len(s), len(f), config.INN_TERSKEL,
                 " + SMA50" if config.INN_KREV_SMA else "")
        if len(f):
            log.info("Gulvet band på %.0f %% av dem.", f["gulv_bandt"].mean() * 100)
        return f

    # ═════════════════════════════════════════════════════════════════════════
    # DE TOLV EXITENE
    # ═════════════════════════════════════════════════════════════════════════

    @dataclass
    class Exit:
        navn: str
        forklaring: str
        modus: str                     # "hendelse" eller "konkurranse"
        dager: int = 0
        decay: float = 1.0
        trail: float = 0.0             # trailing stop, andel fra toppen
        tp: float = 0.0                # take-profit, andel over inngang
        neste_rapport: bool = False
        bare_hvis_darligere: bool = False
        sma_brudd: bool = False

    EXITER: List[Exit] = [
        Exit("E1 tid-5", "5 handledager", "hendelse", dager=5),
        Exit("E2 tid-21", "21 handledager (dagens)", "hendelse", dager=21),
        Exit("E3 tid-63", "63 handledager", "hendelse", dager=63),
        Exit("E4 neste-rapport", "til selskapet rapporterer igjen", "hendelse",
             neste_rapport=True),
        Exit("E5 sentiment-ned", "ut hvis neste rapport er svakere", "hendelse",
             neste_rapport=True, bare_hvis_darligere=True),
        Exit("E6 decay-1.00", "ren fortrengning — KONTROLL", "konkurranse",
             decay=1.00),
        Exit("E7 decay-0.99", "halveringstid 69 dager", "konkurranse", decay=0.99),
        Exit("E8 decay-0.97", "halveringstid 23 dager", "konkurranse", decay=0.97),
        Exit("E9 decay-0.90", "halveringstid 7 dager", "konkurranse", decay=0.90),
        Exit("E10 trailing-15", "−15 % fra toppen (intradag)", "hendelse",
             trail=0.15),
        Exit("E11 tp20-tid42", "+20 % eller 42 dager", "hendelse", dager=42, tp=0.20),
        Exit("E12 sma-brudd", "ut under SMA50", "hendelse", sma_brudd=True),
    ]

    # ═════════════════════════════════════════════════════════════════════════
    # SIMULATOREN
    # ═════════════════════════════════════════════════════════════════════════

    def simuler(e: Exit, signaler: pd.DataFrame, slutt: pd.DataFrame,
                hoy: pd.DataFrame, lav: pd.DataFrame,
                under_sma: pd.DataFrame) -> dict:
        """
        Én daglig løkke som håndterer begge modusene.

        «hendelse»    : et signal tar en ledig plass og holdes til regelen sier ut.
        «konkurranse» : porteføljen er til enhver tid de N høyeste forfalte
                        scorene. Ingen utgangsdato — du mister plassen når noen
                        andre fortjener den mer.
        """
        n_dager = len(slutt.index)
        forste = int(signaler["inn_i"].min())
        # Signaler gruppert på inngangsdag, for oppslag i løkka.
        per_dag: Dict[int, List[dict]] = {}
        for r in signaler.to_dict("records"):
            per_dag.setdefault(int(r["inn_i"]), []).append(r)

        kontanter = config.startkapital
        pos: Dict[str, dict] = {}
        handler: List[dict] = []
        kurve: List[Tuple[pd.Timestamp, float]] = []
        tapt = 0

        def verdi(i: int) -> float:
            v = kontanter
            for t, p in pos.items():
                k = slutt[t].iloc[i]
                v += p["antall"] * (float(k) if np.isfinite(k) else p["inn_kurs"])
            return v

        def selg(t: str, i: int, kurs_ut: float, grunn: str) -> None:
            nonlocal kontanter
            p = pos.pop(t)
            kontanter += p["antall"] * kurs_ut
            handler.append({
                "exit": e.navn, "ticker": t, "inn_dato": slutt.index[p["inn_i"]],
                "ut_dato": slutt.index[i], "dager": i - p["inn_i"],
                "inn_kurs": round(p["inn_kurs"], 4), "ut_kurs": round(kurs_ut, 4),
                "avk": kurs_ut / p["inn_kurs"] - 1.0,
                "bedring_pst": p["bedring_pst"], "grunn": grunn,
                "utvalg": ("INN" if slutt.index[p["inn_i"]]
                           <= pd.Timestamp(config.inn_utvalg_slutt) else "UT"),
            })

        def kjop(r: dict, i: int) -> bool:
            nonlocal kontanter
            t = r["ticker"]
            if t in pos:
                return False
            k = slutt[t].iloc[i]
            if not np.isfinite(k) or k <= 0:
                return False
            belop = min(kontanter, verdi(i) / config.maks_posisjoner)
            if belop < 1:
                return False
            kontanter -= belop
            pos[t] = {"antall": belop / float(k), "inn_kurs": float(k),
                      "inn_i": i, "topp": float(k),
                      "bedring_pst": r["bedring_pst"],
                      "neste_rapport_i": int(r.get("neste_rapport_i", -1)),
                      "neste_darligere": bool(r.get("neste_darligere", False))}
            return True

        for i in range(forste, n_dager):
            # ── 1. EXIT ──────────────────────────────────────────────────
            for t in list(pos.keys()):
                p = pos[t]
                alder = i - p["inn_i"]
                if alder < 1:
                    continue
                k = slutt[t].iloc[i]
                if not np.isfinite(k):
                    continue
                k = float(k)
                h = float(hoy[t].iloc[i]) if np.isfinite(hoy[t].iloc[i]) else k
                l = float(lav[t].iloc[i]) if np.isfinite(lav[t].iloc[i]) else k
                p["topp"] = max(p["topp"], h)

                if e.modus == "konkurranse":
                    # Ingen tidsbasert exit her — heller ikke maks holdetid.
                    # Kandidatens levetid styres i steg 2, og å selge her ville
                    # bare gitt en runde churn: solgt på dag 90, kjøpt tilbake
                    # samme dag fordi kandidaten fortsatt sto på lista, og
                    # solgt igjen dagen etter. Tre signaler ble til seks
                    # handler.
                    continue
                elif e.tp and h >= p["inn_kurs"] * (1 + e.tp):
                    selg(t, i, p["inn_kurs"] * (1 + e.tp), "gevinstsikring")
                    continue
                elif e.trail and l <= p["topp"] * (1 - e.trail):
                    selg(t, i, p["topp"] * (1 - e.trail), "trailing")
                    continue
                elif e.sma_brudd and bool(under_sma[t].iloc[i]):
                    selg(t, i, k, "under SMA50")
                    continue
                elif e.neste_rapport and p["neste_rapport_i"] > 0 \
                        and i >= p["neste_rapport_i"]:
                    if not e.bare_hvis_darligere or p["neste_darligere"]:
                        selg(t, i, k, "ny rapport")
                        continue
                    # Rapporten var ikke svakere: nullstill så vi venter på
                    # den neste i stedet for å sjekke den samme hver dag.
                    p["neste_rapport_i"] = -1
                elif e.dager and alder >= e.dager:
                    selg(t, i, k, "tid")
                    continue
                if t in pos and alder >= config.maks_hold_dager:
                    selg(t, i, k, "maks holdetid")

            # ── 2. ENTRY ─────────────────────────────────────────────────
            if e.modus == "konkurranse":
                # Alle levende kandidater, med forfalt score.
                lev: List[Tuple[float, dict]] = []
                for j in range(max(forste, i - 400), i + 1):
                    for r in per_dag.get(j, []):
                        d = (e.decay ** (i - j)) if e.decay < 1.0 else 1.0
                        s = r["bedring_pst"] * d
                        # Under 1 % av opprinnelig styrke er signalet dødt.
                        if e.decay < 1.0 and d < 0.01:
                            continue
                        # >= og ikke >: på nøyaktig dag 90 er kandidaten død.
                        # Med > levde den én dag for lenge, og posisjonen ble
                        # solgt og kjøpt tilbake på samme dag.
                        if i - j >= config.maks_hold_dager:
                            continue
                        lev.append((s, r))
                lev.sort(key=lambda x: -x[0])
                mal = {r["ticker"] for _, r in lev[:config.maks_posisjoner]}
                for t in list(pos.keys()):
                    if t not in mal:
                        k = slutt[t].iloc[i]
                        if np.isfinite(k) and i - pos[t]["inn_i"] >= 1:
                            selg(t, i, float(k), "fortrengt")
                for s, r in lev[:config.maks_posisjoner]:
                    if r["ticker"] not in pos and len(pos) < config.maks_posisjoner:
                        kjop(r, i)
            else:
                for r in per_dag.get(i, []):
                    if len(pos) >= config.maks_posisjoner:
                        tapt += 1
                        continue
                    kjop(r, i)

            if i % 5 == 0 or i == n_dager - 1:
                kurve.append((slutt.index[i], verdi(i)))

        # Gjør opp det som står igjen.
        for t in list(pos.keys()):
            k = slutt[t].iloc[-1]
            if np.isfinite(k):
                selg(t, n_dager - 1, float(k), "slutt på data")

        h = pd.DataFrame(handler)
        sluttverdi = kontanter
        verdier = [v for _, v in kurve] or [config.startkapital, sluttverdi]
        topp, mdd = verdier[0], 0.0
        for v in verdier:
            topp = max(topp, v)
            mdd = min(mdd, v / topp - 1.0)
        aar = max((slutt.index[-1] - slutt.index[forste]).days / 365.25, 0.01)
        uto = h[h["utvalg"] == "UT"]["avk"] if len(h) else pd.Series(dtype=float)

        return {
            "Exit": e.navn, "Idé": e.forklaring, "Modus": e.modus,
            "Handler": len(h), "Tapt": tapt,
            "Snitt_Dager": float(h["dager"].mean()) if len(h) else np.nan,
            "Slutt_NOK": sluttverdi,
            "Total_Pst": (sluttverdi / config.startkapital - 1.0) * 100.0,
            "CAGR_Pst": (((sluttverdi / config.startkapital) ** (1 / aar) - 1)
                         * 100.0 if aar >= 0.5 else np.nan),
            "MaxDD_Pst": mdd * 100.0,
            "Snitt_Handel_Pst": float(h["avk"].mean()) * 100.0 if len(h) else np.nan,
            "Median_Pst": float(h["avk"].median()) * 100.0 if len(h) else np.nan,
            "Treff_Pst": float((h["avk"] > 0).mean()) * 100.0 if len(h) else np.nan,
            "Beste_Pst": float(h["avk"].max()) * 100.0 if len(h) else np.nan,
            "Verste_Pst": float(h["avk"].min()) * 100.0 if len(h) else np.nan,
            "UT_Snitt_Pst": float(uto.mean()) * 100.0 if len(uto) else np.nan,
            "handler": h,
        }

    # ═════════════════════════════════════════════════════════════════════════
    # KONTROLLEN
    # ═════════════════════════════════════════════════════════════════════════

    def kjop_og_hold(signaler: pd.DataFrame, slutt: pd.DataFrame) -> float:
        """
        Hva ga et likevektet kjøp av HELE universet over samme periode?

        Ikke en indeks — svaret på om exiten i det hele tatt er verdt å tenke
        på. Slår ingen av de tolv denne, er det ikke exiten som er problemet.
        """
        i0 = int(signaler["inn_i"].min())
        a, b = slutt.iloc[i0], slutt.iloc[-1]
        r = (b / a - 1.0).replace([np.inf, -np.inf], np.nan).dropna()
        if r.empty:
            return np.nan
        aar = max((slutt.index[-1] - slutt.index[i0]).days / 365.25, 0.01)
        return ((1.0 + float(r.mean())) ** (1 / aar) - 1.0) * 100.0

    # ═════════════════════════════════════════════════════════════════════════
    # RAPPORT
    # ═════════════════════════════════════════════════════════════════════════

    def _t(v, d=2, sfx=""):
        return "—" if v is None or (isinstance(v, float) and not np.isfinite(v)) \
            else f"{v:.{d}f}{sfx}"

    def skriv_rapport(s: pd.DataFrame, kjop_hold: float, n_sig: int) -> None:
        print("\n" + "=" * 122)
        print("  LEDELSES-SENTIMENT — TOLV EXIT PÅ SAMME INNGANG")
        print("=" * 122)
        print(f"  Inngang (lik for alle): ≥{config.INN_TERSKEL:.0f} % bedring"
              f"{' + SMA50' if config.INN_KREV_SMA else ''}, kjøp på "
              f"rapportdagen. {n_sig} signaler.")
        print(f"  Maks {config.maks_posisjoner} posisjoner, tak "
              f"{config.maks_hold_dager} dagers holdetid. Start "
              f"{config.startkapital:,.0f} kr.\n".replace(",", " "))
        print(f"  {'Exit':<18}{'Handl':>7}{'Tapt':>6}{'Dager':>7}"
              f"{'Slutt NOK':>12}{'CAGR':>8}{'MaxDD':>8}{'Snitt':>8}{'Med':>8}"
              f"{'Treff':>7}{'Beste':>8}{'Verste':>8}{'UT':>8}")
        print("  " + "-" * 118)
        forrige = None
        for _, r in s.sort_values("CAGR_Pst", ascending=False).iterrows():
            if forrige is not None and r["Modus"] != forrige:
                print("  " + "·" * 118)
            forrige = r["Modus"]
            print(f"  {r['Exit']:<18}{int(r['Handler']):>7}{int(r['Tapt']):>6}"
                  f"{_t(r['Snitt_Dager'], 0):>7}{r['Slutt_NOK']:>12,.0f}"
                  f"{_t(r['CAGR_Pst'], 1, '%'):>8}{_t(r['MaxDD_Pst'], 1, '%'):>8}"
                  f"{_t(r['Snitt_Handel_Pst'], 2, '%'):>8}"
                  f"{_t(r['Median_Pst'], 2, '%'):>8}"
                  f"{_t(r['Treff_Pst'], 0, '%'):>7}"
                  f"{_t(r['Beste_Pst'], 0, '%'):>8}"
                  f"{_t(r['Verste_Pst'], 0, '%'):>8}"
                  f"{_t(r['UT_Snitt_Pst'], 2, '%'):>8}".replace(",", " "))

        print(f"\n  Kjøp-og-hold hele universet, samme periode: "
              f"{_t(kjop_hold, 1, ' %')} i året.")
        print("  Slår ingen av de tolv den, er det ikke exiten som er problemet.")

        # ── Hva sier tidsrekken? ─────────────────────────────────────────
        tid = s[s["Exit"].str.startswith(("E1 ", "E2 ", "E3 "))]
        if len(tid) == 3:
            v = {r["Exit"][:6]: r["Snitt_Handel_Pst"] for _, r in tid.iterrows()}
            print(f"\n  HOLDETID  5d: {_t(v.get('E1 tid'), 2, '%')}   "
                  f"21d: {_t(v.get('E2 tid'), 2, '%')}   "
                  f"63d: {_t(v.get('E3 tid'), 2, '%')}  (snitt per handel)")
            print("  Stigende → drift, hold lenger. Spiss på 5d → en pop du "
                  "ikke rekker.")
            print("  Flat → ingen effekt å time, og exit er feil sted å lete.")

        # ── Hva er decay verdt utover fortrengning? ──────────────────────
        kon = s[s["Modus"] == "konkurranse"].set_index("Exit")
        if "E6 decay-1.00" in kon.index:
            basis = float(kon.loc["E6 decay-1.00", "CAGR_Pst"])
            beste_d = kon.drop("E6 decay-1.00", errors="ignore")
            if len(beste_d):
                b = beste_d["CAGR_Pst"].idxmax()
                d = float(beste_d.loc[b, "CAGR_Pst"]) - basis
                print(f"\n  FORFALLET: beste decay «{b}» ligger {d:+.1f} "
                      f"prosentpoeng over ren fortrengning (E6).")
                print("  Er differansen liten, er det FORTRENGNINGEN som gjør "
                      "jobben,")
                print("  og decay-tallet er en parameter du ikke trenger.")

        # ── PORTEN ───────────────────────────────────────────────────────
        gyldige = s[(s["Handler"] >= config.min_handler)
                    & s["CAGR_Pst"].notna()]
        if gyldige.empty:
            print(f"\n  🚫 PORTEN ER STENGT. Ingen exit fikk "
                  f"{config.min_handler} handler å dømmes på.")
            print("=" * 122 + "\n")
            return
        beste = gyldige.sort_values("CAGR_Pst", ascending=False).iloc[0]
        krav = {
            "positiv CAGR": beste["CAGR_Pst"] > 0,
            "slår kjøp-og-hold av universet":
                (not np.isfinite(kjop_hold) or beste["CAGR_Pst"] > kjop_hold),
            "positiv snitthandel": beste["Snitt_Handel_Pst"] > 0,
            "positiv også på ut-utvalget": (np.isfinite(beste["UT_Snitt_Pst"])
                                            and beste["UT_Snitt_Pst"] > 0),
            f"minst {config.min_handler} handler":
                beste["Handler"] >= config.min_handler,
        }
        print(f"\n  BESTE: «{beste['Exit']}» — CAGR "
              f"{_t(beste['CAGR_Pst'], 1, ' %')}, {int(beste['Handler'])} handler, "
              f"snitt holdetid {_t(beste['Snitt_Dager'], 0)} dager")
        print("\n  PORTEN:")
        for tekst, ok in krav.items():
            print(f"    {'✓' if ok else '✗'}  {tekst}")
        if all(krav.values()):
            print("\n  ✅ PORTEN ER ÅPEN.")
        else:
            print("\n  🚫 PORTEN ER STENGT. «Slår kjøp-og-hold» er den viktigste:")
            print("     uten den har du gjort mye arbeid for å tape mot å eie alt.")
        print("\n  Tolv exit på de samme dataene — den beste raden er delvis")
        print("  heldig. E10 og E11 antar dessuten fyll PÅ stoppnivået; gapper")
        print("  aksjen forbi, fikk du verre kurs enn tabellen viser.")
        print("=" * 122 + "\n")

    # ═════════════════════════════════════════════════════════════════════════
    # HOVEDLØP
    # ═════════════════════════════════════════════════════════════════════════

    log.info("=" * 74)
    log.info("  SENTIMENT EXIT LAB — samme inngang, tolv exit")
    log.info("=" * 74)

    artikler = les_artikler()
    tickere = sorted({str(c).strip() + config.oslo_suffix
                      for c in artikler["Company"].dropna().unique()
                      if str(c).strip() and str(c).strip() != "nan"})
    slutt, hoy, lav = hent_kurser(tickere)
    signaler = bygg_signaler(artikler, slutt)
    if signaler.empty:
        log.error("Ingen signaler passerte inngangen.")
        return
    under_sma = (slutt < slutt.rolling(config.sma_dager).mean())

    resultater = []
    for e in EXITER:
        r = simuler(e, signaler, slutt, hoy, lav, under_sma)
        log.info("  %-18s %4d handler, snitt %s dager",
                 e.navn, r["Handler"],
                 f"{r['Snitt_Dager']:.0f}" if np.isfinite(r["Snitt_Dager"]) else "—")
        resultater.append(r)

    alle_handler = pd.concat([r.pop("handler") for r in resultater],
                             ignore_index=True)
    sammendrag = pd.DataFrame(resultater)
    skriv_rapport(sammendrag, kjop_og_hold(signaler, slutt), len(signaler))

    sti = config.ut_dir / f"Sentiment_ExitLab_{datetime.now():%Y-%m-%d}.xlsx"
    with pd.ExcelWriter(str(sti), engine="openpyxl") as w:
        sammendrag.to_excel(w, sheet_name="Sammendrag", index=False)
        signaler.to_excel(w, sheet_name="Signaler", index=False)
        alle_handler.to_excel(w, sheet_name="Handler", index=False)
        if len(alle_handler):
            (alle_handler.pivot_table(index="exit", columns="grunn",
                                      values="avk", aggfunc="count")
             .to_excel(w, sheet_name="Exit_grunner"))
    log.info("Skrevet  : %s", sti)
    log.info("=== SentimentExitLab ferdig ===")
#SentimentExitLab()


# Portable paths apply to nested path constants; strategy source logic is unchanged.
configure_paths(globals())

if __name__ == "__main__":
    from run_strategy import main
    raise SystemExit(main())
