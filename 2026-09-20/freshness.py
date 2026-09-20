# -*- coding: utf-8 -*-
"""Data-freshness and month-end coverage gates.

WHY THIS EXISTS
---------------
In the 2026-09-18 run, Sentiment Momentum v3.1 finished in 0.9 minutes and was
reported as `OK`. It had not fetched anything: it re-ran the backtest over
cached prices ending 2026-08-19, thirty days before the report. "OK" meant
"re-read stale data without raising", not "this result is current".

That staleness then had a silent second effect. `portfolio_blend` only accepts
a month-end whose last observation is within five business days of it. From
2026-08-19 to 2026-08-31 is eight business days, so August was dropped for
Sentiment Momentum and the joint portfolio could not reach past 2026-07-31 -
whatever happens to the management leg. Nothing in the report said so.

This module makes both facts explicit and checkable before a 106-minute run
rather than after it.

Pure Python: no pandas, no numpy, no network.
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

FRESH = "FRESH"
STALE = "STALE"
MISSING = "MISSING"

# A daily strategy should be within a week of the report date; a trading week
# of slippage covers holidays without hiding a month-old file.
DEFAULT_MAX_AGE_DAYS = 7

# Same constant as portfolio_blend._monthly_observations.
DEFAULT_MAX_GAP_BUSINESS_DAYS = 5


def to_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def month_end(day: date) -> date:
    return day.replace(day=calendar.monthrange(day.year, day.month)[1])


def business_days_after(start: date, end: date) -> int:
    """Business days strictly after `start` up to and including `end`."""
    if end <= start:
        return 0
    return sum((start + timedelta(days=i)).weekday() < 5
               for i in range(1, (end - start).days + 1))


@dataclass
class Freshness:
    name: str
    last_observation: Optional[date]
    as_of: date
    max_age_days: int
    status: str
    age_days: Optional[int]
    message: str

    @property
    def ok(self) -> bool:
        return self.status == FRESH


def assess(name: str, last_observation, as_of=None, *,
           max_age_days: int = DEFAULT_MAX_AGE_DAYS) -> Freshness:
    """Classify one strategy's data tail as FRESH, STALE or MISSING."""
    as_of = to_date(as_of or date.today())
    if last_observation in (None, ""):
        return Freshness(name, None, as_of, max_age_days, MISSING, None,
                         f"{name}: no usable observation date; the export cannot be dated.")
    last = to_date(last_observation)
    age = (as_of - last).days
    if age < 0:
        return Freshness(
            name, last, as_of, max_age_days, STALE, age,
            f"{name}: last observation {last} is AFTER the report date {as_of}. "
            "A future-dated row is a label, not an observed price.")
    if age > max_age_days:
        return Freshness(
            name, last, as_of, max_age_days, STALE, age,
            f"{name}: last observation {last} is {age} calendar days before the report "
            f"date {as_of} (limit {max_age_days}). The result is historical; "
            "re-running the model does not refresh its source prices.")
    return Freshness(name, last, as_of, max_age_days, FRESH, age,
                     f"{name}: current through {last} ({age} days old).")


@dataclass
class MonthEndCoverage:
    name: str
    last_observation: date
    as_of: date
    last_usable_month_end: Optional[date]
    dropped: List[Tuple[date, int]]
    max_gap_business_days: int

    @property
    def message(self) -> str:
        if not self.dropped:
            return (f"{self.name}: month-end coverage complete through "
                    f"{self.last_usable_month_end}.")
        end, gap = self.dropped[0]
        return (f"{self.name}: {end} dropped - last observation {self.last_observation} "
                f"is {gap} business days before it (limit {self.max_gap_business_days}). "
                f"Usable month-end coverage stops at {self.last_usable_month_end}.")


def month_end_coverage(name: str, last_observation, as_of=None, *,
                       max_gap_business_days: int = DEFAULT_MAX_GAP_BUSINESS_DAYS
                       ) -> MonthEndCoverage:
    """Which completed month-ends this tail can substantiate, and which it cannot.

    Mirrors portfolio_blend._monthly_observations so a caller can predict the
    joint window before running the blend.
    """
    as_of = to_date(as_of or date.today())
    last = to_date(last_observation)
    dropped: List[Tuple[date, int]] = []
    usable: Optional[date] = None

    candidate = month_end(last)
    if candidate <= as_of:
        gap = business_days_after(last, candidate)
        if gap <= max_gap_business_days:
            usable = candidate
        else:
            dropped.append((candidate, gap))

    if usable is None:
        previous = month_end(last.replace(day=1) - timedelta(days=1))
        if previous <= as_of:
            usable = previous

    # Every later completed month-end is unreachable: there is no observation.
    cursor = month_end(candidate + timedelta(days=1))
    while cursor <= as_of:
        dropped.append((cursor, business_days_after(last, cursor)))
        cursor = month_end(cursor + timedelta(days=1))

    return MonthEndCoverage(name=name, last_observation=last, as_of=as_of,
                            last_usable_month_end=usable, dropped=dropped,
                            max_gap_business_days=max_gap_business_days)


def binding_component(coverages: Sequence[MonthEndCoverage]) -> Optional[MonthEndCoverage]:
    """Which component caps the joint window. This is the name a report must print."""
    usable = [c for c in coverages if c.last_usable_month_end is not None]
    if not usable:
        return None
    return min(usable, key=lambda c: c.last_usable_month_end)


def joint_window(coverages: Sequence[MonthEndCoverage]) -> Dict[str, object]:
    """The last common month-end, and the component responsible for it."""
    binding = binding_component(coverages)
    missing = [c.name for c in coverages if c.last_usable_month_end is None]
    return {
        "last_common_month_end": None if binding is None else binding.last_usable_month_end,
        "binding_component": None if binding is None else binding.name,
        "components_without_coverage": missing,
        "explanation": (
            "No component can substantiate a completed month-end."
            if binding is None else
            f"The joint window ends at {binding.last_usable_month_end} because "
            f"{binding.name} has no later usable month-end. Refreshing any other "
            "strategy cannot extend it."),
    }


def report(freshness: Iterable[Freshness], coverages: Sequence[MonthEndCoverage]
           ) -> Dict[str, object]:
    freshness = list(freshness)
    window = joint_window(coverages)
    blocking = [f for f in freshness if not f.ok]
    return {"freshness": [f.__dict__ for f in freshness],
            "stale_or_missing": [f.name for f in blocking],
            "messages": [f.message for f in blocking],
            "coverage": [c.message for c in coverages],
            **window}
