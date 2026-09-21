"""Shared portable paths, deferred imports and chronological comparison helpers."""
from __future__ import annotations
import importlib
import math
import os
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LEGACY = r"C:\Users\ander\Desktop\Python_K4\ExcelData"


def configure_console():
    """Keep Norwegian text and symbols usable in Windows redirected logs."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def data_root(explicit=None):
    if explicit or os.environ.get("AKSJE_BASE_DIR"):
        return Path(explicit or os.environ["AKSJE_BASE_DIR"]).expanduser().resolve()
    if (ROOT / "ExcelData").is_dir():
        return ROOT / "ExcelData"
    return ROOT / "ExcelData"


class LazyImport:
    """Unused legacy integrations do not prevent the four models importing."""
    def __init__(self, module, attribute=None):
        self.module, self.attribute = module, attribute

    def _get(self):
        obj = importlib.import_module(self.module)
        return getattr(obj, self.attribute) if self.attribute else obj

    def __getattr__(self, key):
        return getattr(self._get(), key)

    def __call__(self, *args, **kwargs):
        return self._get()(*args, **kwargs)


def configure_paths(namespace, explicit=None):
    """Relocate path constants, including nested functions, without editing models.

    The two protected function source bodies stay byte-identical. Only their
    absolute ExcelData path constants change when a different data root is used.
    """
    base = data_root(explicit)
    os.environ["AKSJE_BASE_DIR"] = str(base)

    def translate(c):
        if isinstance(c, types.CodeType):
            return c.replace(co_consts=tuple(translate(x) for x in c.co_consts))
        if isinstance(c, tuple):
            return tuple(translate(x) for x in c)
        if isinstance(c, str):
            normalized = c.replace("\\", "/")
            prefix = LEGACY.replace("\\", "/")
            if normalized.lower().startswith(prefix.lower()):
                suffix = normalized[len(prefix):].lstrip("/")
                return str(base / suffix) if suffix else str(base)
        return c

    for obj in list(namespace.values()):
        if isinstance(obj, types.FunctionType) and obj.__module__ == namespace.get("__name__"):
            original = getattr(obj, "_portable_original_code", obj.__code__)
            obj._portable_original_code = original
            obj.__code__ = translate(original)
    return base


def annual_return(values, dates, min_days=180):
    if len(values) < 2:
        return None
    from datetime import date
    days = (date.fromisoformat(str(dates[-1])[:10]) - date.fromisoformat(str(dates[0])[:10])).days
    if days < min_days or values[0] <= 0 or values[-1] <= 0:
        return None
    value = (values[-1] / values[0]) ** (365.25 / days) - 1
    return 100 * value if math.isfinite(value) else None


def split_metrics(curve, cutoff):
    """Curve rows are (date, portfolio value); heldout starts at cutoff value."""
    rows = sorted((str(d)[:10], float(v)) for d, v in curve if math.isfinite(float(v)))
    train = [(d, v) for d, v in rows if d <= cutoff]
    test = (train[-1:] + [(d, v) for d, v in rows if d > cutoff])
    def calc(group):
        return annual_return([v for _, v in group], [d for d, _ in group])
    return {"Train_CAGR_Pst": calc(train), "Test_CAGR_Pst": calc(test),
            "Train_Days": len(train), "Test_Days": max(0, len(test) - 1),
            "Selection_Cutoff": cutoff}


def choose_variant(rows, baseline, min_trades=20):
    """Only training columns affect selection. Test returns are display-only."""
    eligible = [r for r in rows if r.get("Train_CAGR_Pst") is not None
                and math.isfinite(float(r["Train_CAGR_Pst"]))
                and int(r.get("Train_Trades", 0)) >= min_trades
                and int(r.get("Train_Days", 0)) >= 126]
    base = next((r for r in rows if r["Variant"] == baseline), None)
    if not eligible:
        if base is None:
            raise ValueError("No baseline result or sufficient training data.")
        return base, "Baseline retained: insufficient training history for selection."
    best = sorted(eligible, key=lambda r: (-float(r["Train_CAGR_Pst"]), r["Variant"]))[0]
    return best, "Highest training CAGR among existing variants; test period was not used for selection."


def capped_weights(raw_weights, cap):
    """Redistribute only into spare capacity; unallocatable capital stays cash."""
    if not 0 < cap <= 1:
        raise ValueError("Position cap must be in (0, 1].")
    raw = {str(k): max(0.0, float(v)) for k, v in raw_weights.items()
           if math.isfinite(float(v))}
    result = dict.fromkeys(raw, 0.0)
    remaining = min(1.0, cap * len(raw))
    active = {k for k, v in raw.items() if v > 0}
    while active and remaining > 1e-12:
        total = sum(raw[k] for k in active)
        overflowing = {k for k in active if remaining * raw[k] / total >= cap}
        if not overflowing:
            for k in active:
                result[k] = remaining * raw[k] / total
            break
        for k in overflowing:
            result[k] = cap
            remaining -= cap
        active -= overflowing
    return result


def observed_month_ends(daily, as_of=None):
    """Completed month observations with actual session dates, never future labels."""
    import pandas as pd
    cutoff = pd.Timestamp(as_of or pd.Timestamp.now()).normalize()
    values = daily.loc[daily.index < cutoff.replace(day=1)].copy()
    if values.empty:
        return values
    last_sessions = values.index.to_series().groupby(values.index.to_period("M")).max()
    return values.loc[last_sessions.to_list()].copy()


def historical_fundamentals(frame, decision_date):
    """Only use versions observed before the decision, without revision lookahead."""
    import pandas as pd
    if "AvailableDate" not in frame.columns:
        raise ValueError("Fundamental records require their actual observation date.")
    known = frame.loc[pd.to_datetime(frame["AvailableDate"]) < pd.Timestamp(decision_date)]
    known = known.loc[known.index < pd.Timestamp(decision_date)]
    known = known.sort_values("AvailableDate")
    return known.loc[~known.index.duplicated(keep="last")].sort_index()


def validate_price_frame(frame, expected=(), context="Prices"):
    """Fail on missing series or suspicious scale jumps; never silently rescale."""
    import numpy as np
    import pandas as pd
    if frame.empty:
        raise RuntimeError(context + ": provider returned no prices.")
    missing = [str(t) for t in expected
               if t not in frame.columns or frame[t].dropna().empty]
    if missing:
        raise RuntimeError(context + ": missing tickers: " + ", ".join(missing))
    problems = []
    for ticker in frame.columns:
        original = frame[ticker]
        series = pd.to_numeric(original, errors="coerce")
        bad = original.notna() & (~np.isfinite(series) | (series <= 0))
        if bad.any():
            problems.append(str(ticker) + " invalid price")
        observed = series.dropna()
        ratio = observed.div(observed.shift(1))
        if ((ratio >= 5) | (ratio <= .2)).any():
            problems.append(str(ticker) + " extreme jump needs source verification")
    if problems:
        raise RuntimeError(context + ": " + "; ".join(problems))


def protected_input_errors(base):
    """Check required inputs without fetching or changing the protected models."""
    base = Path(base)
    required = [
        (base / "Data_BT", "AllTickers_OSEBX_TW_current.xlsx"),
        (base / "DataNLP", "Step4_Sentiment_Changes_*.xlsx"),
        (base / "Data_BT1" / "FinancialData", "Stock_Prices_*.xlsx"),
    ]
    return [str(folder / pattern) for folder, pattern in required
            if not any(folder.glob(pattern))]
