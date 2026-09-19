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
    if Path(LEGACY).is_dir():
        return Path(LEGACY)
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


def protected_input_errors(base):
    """Check required inputs without fetching or changing the protected models."""
    base = Path(base)
    required = [
        (base / "Data_BT", "AllTickers_OSEBX_TW_260428.xlsx"),
        (base / "DataNLP", "Step4_Sentiment_Changes_*.xlsx"),
        (base / "Data_BT1" / "FinancialData", "Stock_Prices_*.xlsx"),
    ]
    return [str(folder / pattern) for folder, pattern in required
            if not any(folder.glob(pattern))]
