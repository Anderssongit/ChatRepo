# -*- coding: utf-8 -*-
"""Auditable repair of provider unit/denomination artifacts in price series.

WHY THIS EXISTS
---------------
`kontroller_priser` in Only_260820.py flags every change of 4x or more between
two actual observations and `hent_kurser` then aborts the whole management run.
That guard is right to refuse to guess, but it treats two very different things
identically:

  1. A denomination artifact. BSP.OL moves 0.101440 -> 10.144007 across one
     session: a ratio of exactly 100.000. A share price does not move 100x
     overnight; the provider changed units (ore/krone) or restated the series.
     This is provable from the data alone and is repairable deterministically.

  2. A genuine or unexplained move. Ratio 4.7, or 0.21, or a non-positive
     price. Nothing in the data proves what the correct value is.

This module separates them. Case 1 is repaired by rescaling, with every change
written to an audit trail. Case 2 is never repaired and still blocks the run.

REPAIR DIRECTION
----------------
Repairs run backwards: the segment *before* the break is rescaled to match the
segment after it. The most recent prices - the ones a live position is marked
against - are never modified.

STRUCTURE
---------
The decision logic is pure Python over plain (date, price) sequences, so it is
unit-testable without pandas, numpy or network access. `repair_price_frames`
is a thin pandas adapter for the calling code in Only_260820.py.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

# Ratios accepted as unit artifacts. A denomination change is a power of ten;
# anything else is a price move until a human says otherwise.
SCALE_FACTORS: Tuple[float, ...] = (1000.0, 100.0, 10.0, 0.1, 0.01, 0.001)

# How close to an exact power of ten a ratio must be. 0.5% leaves room for a
# genuine same-session move riding along with the restatement, and is far too
# tight to swallow an ordinary 4x event.
DEFAULT_TOLERANCE = 0.005

# Same thresholds as kontroller_priser, so this module flags exactly the same
# observations the existing guard flags - never more.
UPPER_RATIO = 4.0
LOWER_RATIO = 0.25

KIND_UNIT_SCALE = "unit_scale_artifact"
KIND_UNVERIFIED = "unverified_adjusted_price_discontinuity"
KIND_NON_POSITIVE = "non_positive_or_non_finite"


@dataclass(frozen=True)
class Break:
    """One flagged observation. `factor` is set only when it is repairable."""
    ticker: str
    index: int
    date: str
    price: float
    kind: str
    previous_date: Optional[str] = None
    previous_price: Optional[float] = None
    ratio: Optional[float] = None
    factor: Optional[float] = None

    @property
    def repairable(self) -> bool:
        return self.kind == KIND_UNIT_SCALE and self.factor is not None

    def as_row(self) -> Dict[str, object]:
        return {"ticker": self.ticker, "date": self.date, "issue": self.kind,
                "previous_date": self.previous_date or "",
                "previous_price": "" if self.previous_price is None else self.previous_price,
                "price": self.price,
                "ratio": "" if self.ratio is None else self.ratio,
                "applied_factor": "" if self.factor is None else self.factor,
                "resolution": "rescaled_earlier_segment" if self.repairable else "blocked_needs_verification"}


@dataclass
class RepairResult:
    """Repaired series for one ticker plus the full audit trail."""
    ticker: str
    prices: List[Tuple[str, Optional[float]]]
    repairs: List[Break] = field(default_factory=list)
    unresolved: List[Break] = field(default_factory=list)
    multipliers: List[float] = field(default_factory=list)

    @property
    def resolved(self) -> bool:
        return not self.unresolved

    @property
    def changed(self) -> bool:
        return bool(self.repairs)


def _valid(price: object) -> bool:
    try:
        value = float(price)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False
    return math.isfinite(value) and value > 0


def nearest_scale(ratio: float, tolerance: float = DEFAULT_TOLERANCE) -> Optional[float]:
    """Return the power of ten `ratio` matches within `tolerance`, else None."""
    if not math.isfinite(ratio) or ratio <= 0:
        return None
    for factor in SCALE_FACTORS:
        if abs(ratio / factor - 1.0) <= tolerance:
            return factor
    return None


def find_breaks(ticker: str, series: Sequence[Tuple[str, object]], *,
                tolerance: float = DEFAULT_TOLERANCE,
                upper: float = UPPER_RATIO,
                lower: float = LOWER_RATIO) -> List[Break]:
    """Flag the same observations kontroller_priser flags, but classified.

    `series` is chronological (date, price). Missing observations are skipped
    rather than filled, exactly as the original guard does via dropna().
    """
    breaks: List[Break] = []
    previous: Optional[Tuple[int, str, float]] = None
    for index, (day, raw) in enumerate(series):
        if raw is None:
            continue
        try:
            price = float(raw)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            continue
        if not _valid(price):
            if not math.isnan(price):
                breaks.append(Break(ticker=ticker, index=index, date=str(day),
                                    price=price, kind=KIND_NON_POSITIVE))
            continue
        if previous is not None:
            ratio = price / previous[2]
            if ratio >= upper or ratio <= lower:
                factor = nearest_scale(ratio, tolerance)
                breaks.append(Break(
                    ticker=ticker, index=index, date=str(day), price=price,
                    kind=KIND_UNIT_SCALE if factor else KIND_UNVERIFIED,
                    previous_date=previous[1], previous_price=previous[2],
                    ratio=ratio, factor=factor))
        previous = (index, str(day), price)
    return breaks


def repair_series(ticker: str, series: Sequence[Tuple[str, object]], *,
                  tolerance: float = DEFAULT_TOLERANCE,
                  upper: float = UPPER_RATIO,
                  lower: float = LOWER_RATIO) -> RepairResult:
    """Rescale segments before each provable unit break; verify the result.

    Anything not provably a power-of-ten artifact is left untouched and
    reported as unresolved.
    """
    breaks = find_breaks(ticker, series, tolerance=tolerance, upper=upper, lower=lower)
    repairable = {b.index: b for b in breaks if b.repairable}

    multiplier = 1.0
    multipliers = [1.0] * len(series)
    for index in range(len(series) - 1, -1, -1):
        multipliers[index] = multiplier
        found = repairable.get(index)
        if found is not None and found.factor:
            multiplier *= found.factor

    repaired: List[Tuple[str, Optional[float]]] = []
    for index, (day, raw) in enumerate(series):
        if raw is None or not _valid(raw):
            repaired.append((str(day), None if raw is None else _as_float(raw)))
            continue
        repaired.append((str(day), float(raw) * multipliers[index]))

    # Verify rather than assume: re-run detection on the repaired series.
    remaining = find_breaks(ticker, repaired, tolerance=tolerance, upper=upper, lower=lower)
    return RepairResult(ticker=ticker, prices=repaired,
                        repairs=sorted(repairable.values(), key=lambda b: b.index),
                        unresolved=remaining, multipliers=multipliers)


def _as_float(raw: object) -> Optional[float]:
    try:
        value = float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def repair_universe(universe: Dict[str, Sequence[Tuple[str, object]]], *,
                    tolerance: float = DEFAULT_TOLERANCE) -> Dict[str, RepairResult]:
    return {ticker: repair_series(ticker, series, tolerance=tolerance)
            for ticker, series in universe.items()}


def audit_rows(results: Iterable[RepairResult]) -> List[Dict[str, object]]:
    """Flat rows for management_price_issues.csv - repaired and blocked alike."""
    rows: List[Dict[str, object]] = []
    for result in results:
        rows.extend(b.as_row() for b in result.repairs)
        rows.extend(b.as_row() for b in result.unresolved)
    return sorted(rows, key=lambda r: (str(r["ticker"]), str(r["date"])))


def blocked_tickers(results: Iterable[RepairResult]) -> List[str]:
    return sorted({r.ticker for r in results if not r.resolved})


def summary(results: Iterable[RepairResult]) -> Dict[str, object]:
    results = list(results)
    return {"tickers": len(results),
            "repaired_tickers": sorted(r.ticker for r in results if r.changed),
            "blocked_tickers": blocked_tickers(results),
            "repairs": sum(len(r.repairs) for r in results),
            "unresolved": sum(len(r.unresolved) for r in results),
            "tolerance": DEFAULT_TOLERANCE,
            "policy": ("Only ratios within tolerance of a power of ten are rescaled, "
                       "backwards, leaving the most recent prices untouched. "
                       "Every other flagged observation blocks publication.")}


# ---------------------------------------------------------------------------
# pandas adapter - used by Only_260820.py. NOT exercised by the unit tests in
# this folder, because pandas is not a dependency of the decision logic above.
# ---------------------------------------------------------------------------

def repair_price_frames(close, high, low, *, tolerance: float = DEFAULT_TOLERANCE,
                        logger=None):
    """Repair close/high/low consistently and return the audit trail.

    The SAME multiplier is applied to high and low as to close. Rescaling close
    alone would leave ATR20 computed across two different denominations.

    Returns (close, high, low, results, rows).
    """
    import pandas as pd  # local import: pure logic above stays pandas-free

    close = close.copy()
    high = None if high is None else high.copy()
    low = None if low is None else low.copy()

    results: Dict[str, RepairResult] = {}
    for ticker in list(close.columns):
        column = pd.to_numeric(close[ticker], errors="coerce")
        series = [(str(day.date()) if hasattr(day, "date") else str(day),
                   None if pd.isna(value) else float(value))
                  for day, value in column.items()]
        result = repair_series(str(ticker), series, tolerance=tolerance)
        results[str(ticker)] = result
        if not result.changed:
            continue
        factors = pd.Series(result.multipliers, index=close.index, dtype="float64")
        close[ticker] = column * factors
        for frame in (high, low):
            if frame is not None and ticker in frame.columns:
                frame[ticker] = pd.to_numeric(frame[ticker], errors="coerce") * factors
        if logger is not None:
            for repair in result.repairs:
                logger.warning(
                    "Price repair %s: %s ratio %.4f treated as a x%g unit artifact; "
                    "observations before %s rescaled.",
                    ticker, repair.date, repair.ratio or 0.0, repair.factor or 1.0, repair.date)
    rows = audit_rows(results.values())
    return close, high, low, results, rows
