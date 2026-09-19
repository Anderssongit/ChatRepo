"""Combine four existing strategy NAVs as four 25% capital allocations.

No candidate scores or underlying stock trades are reconstructed. Monthly
source curves limit the portfolio to completed month-end observations.

2026-09-18 correction
---------------------
`_monthly_observations` used to drop a month-end silently when a component's
last observation was too far before it. On 2026-09-18 that hid the fact that
Sentiment Momentum's prices stop at 2026-08-19 - eight business days before
2026-08-31 - so the joint window could not pass 2026-07-31 no matter what was
done about the management leg. Drops are now returned, reported as warnings,
and named in the error when too few common month-ends remain.
"""
from __future__ import annotations

import calendar
import csv
import json
import math
import re
import statistics
from datetime import date, datetime, timedelta
from pathlib import Path


class PortfolioDataError(ValueError):
    """Inputs cannot substantiate a capital portfolio."""


def _date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _month_end(day):
    return day.replace(day=calendar.monthrange(day.year, day.month)[1])


def _business_days_after(start, end):
    return sum((start + timedelta(days=i)).weekday() < 5
               for i in range(1, (end - start).days + 1))


def _declared_valid(value):
    return value is True or str(value).strip().lower() in ('true', '1', '1.0', 'ja', 'yes', 'ok')


def _prepare(component, as_of):
    name = component['name']
    errors = list(component.get('errors') or [])
    if component.get('valid') is False:
        errors.append(component.get('error') or 'source declared invalid')
    if errors:
        raise PortfolioDataError(f"{name}: {'; '.join(map(str, errors))}")
    rows = {}
    future = 0
    warnings = list(component.get('warnings') or [])
    for raw_date, raw_value in component.get('observations', []):
        try:
            day = _date(raw_date)
            value = float(raw_value)
        except (ValueError, TypeError, OverflowError) as exc:
            raise PortfolioDataError(f'{name}: invalid date or NAV: {raw_date!r}, {raw_value!r}') from exc
        if day > as_of:
            future += 1
            continue
        if not math.isfinite(value) or value <= 0:
            raise PortfolioDataError(f'{name}: non-positive or non-finite NAV on {day}')
        if day in rows:
            raise PortfolioDataError(f'{name}: duplicate NAV date {day}')
        rows[day] = value
    rows = dict(sorted(rows.items()))
    if len(rows) < 2:
        raise PortfolioDataError(f'{name}: fewer than two usable NAV observations')
    if future:
        warnings.append(f'{name}: excluded {future} observations after {as_of}.')
    previous = None
    for day, value in rows.items():
        if previous is not None:
            change = value / previous - 1
            if change > 1 or change < -0.8:
                warnings.append(f'{name}: NAV move {change:+.1%} on {day}; verify source accounting and prices.')
        previous = value
    return rows, warnings


def _monthly_observations(rows, as_of, max_gap_business_days=5):
    """Return (usable_month_ends, dropped).

    Never carry a missing month's value from a previous month. The month must
    be complete as of the report date; near-end holiday gaps are bounded.
    `dropped` records every month-end rejected for gap, so the caller can say
    which component capped the joint window and why.
    """
    months = {}
    for day, value in rows.items():
        end = _month_end(day)
        if end <= as_of:
            months[end] = (day, value)
    usable, dropped = {}, []
    for end, item in months.items():
        gap = _business_days_after(item[0], end)
        if gap <= max_gap_business_days:
            usable[end] = item
        else:
            dropped.append({'month_end': end, 'last_observation': item[0],
                            'gap_business_days': gap,
                            'limit_business_days': max_gap_business_days})
    return usable, sorted(dropped, key=lambda d: d['month_end'])


def _metrics(values, dates, risk_free_pct):
    returns = [b / a - 1 for a, b in zip(values, values[1:])]
    days = (dates[-1] - dates[0]).days
    total = values[-1] / values[0] - 1
    cagr = (values[-1] / values[0]) ** (365.25 / days) - 1 if days >= 180 else None
    peak = values[0]
    drawdown = 0.0
    for value in values:
        peak = max(peak, value)
        drawdown = min(drawdown, value / peak - 1)
    volatility = statistics.stdev(returns) * math.sqrt(12) if len(returns) >= 2 else 0.0
    rf_month = (1 + risk_free_pct / 100) ** (1 / 12) - 1
    sharpe = (statistics.mean(returns) - rf_month) * 12 / volatility if volatility else None
    return {'CAGR_Pst': None if cagr is None else cagr * 100,
            'MaxDD_Pst': drawdown * 100, 'Sharpe': sharpe,
            'Periode': f'{dates[0]} → {dates[-1]}',
            'Startkapital': values[0], 'Sluttverdi': values[-1],
            'Total_Pst': total * 100, 'Volatilitet_Pst': volatility * 100,
            'frequency': 'monthly', 'Observasjoner': len(values),
            'drawdown_basis': 'completed month-end NAVs; intramonth losses are not observable'}


def build_capital_portfolio(curves, *, rebalance='monthly', as_of=None,
                            start_capital=1_000_000.0, risk_free_pct=3.0):
    """Return a monthly portfolio, with 25% allocated to each of four strategies.

    Each component supplies name, observations [(date, NAV)], source, frequency,
    and optionally valid/errors/warnings/variant. The first common completed
    month end is the initial allocation; every following common month end marks
    the sleeves to market, then rebalances to 25% for the following month.
    """
    curves = list(curves)
    if len(curves) != 4 or len({c['name'] for c in curves}) != 4:
        raise PortfolioDataError('Exactly four distinct strategy NAV curves are required.')
    if rebalance != 'monthly':
        raise PortfolioDataError('Daily rebalancing cannot be substantiated by the monthly PB-ROE NAV. Use monthly.')
    if not math.isfinite(float(start_capital)) or start_capital <= 0:
        raise PortfolioDataError('Start capital must be finite and positive.')
    as_of = _date(as_of or date.today())
    prepared, monthly, warnings, coverage = {}, {}, [], {}
    for component in curves:
        name = component['name']
        prepared[name], notes = _prepare(component, as_of)
        warnings.extend(notes)
        monthly[name], dropped = _monthly_observations(prepared[name], as_of)
        last_observation = max(prepared[name])
        coverage[name] = {
            'last_observation': last_observation,
            'last_usable_month_end': max(monthly[name]) if monthly[name] else None,
            'dropped_month_ends': dropped,
            'age_days': (as_of - last_observation).days,
        }
        for drop in dropped:
            warnings.append(
                f"{name}: {drop['month_end']} excluded - last observation "
                f"{drop['last_observation']} is {drop['gap_business_days']} business days "
                f"before it (limit {drop['limit_business_days']}). Refreshing the other "
                "strategies cannot recover this month.")
    # Name the component that caps the joint window before any date math fails.
    covered = {n: c['last_usable_month_end'] for n, c in coverage.items()
               if c['last_usable_month_end'] is not None}
    uncovered = [n for n, c in coverage.items() if c['last_usable_month_end'] is None]
    if uncovered:
        raise PortfolioDataError(
            'No completed month-end can be substantiated for: ' + ', '.join(sorted(uncovered))
            + '. Every component must supply at least one month-end NAV.')
    binding = min(covered, key=covered.get)
    warnings.append(
        f"The joint window ends at {covered[binding]} because {binding} has no later "
        "usable month-end. This is the binding constraint on the shared period.")
    dates = sorted(set.intersection(*(set(points) for points in monthly.values())))
    selection_cutoffs = []
    for component in curves:
        metadata = component.get('metadata') or {}
        selection = component.get('selection') or {}
        cutoff = metadata.get('selection_cutoff') or selection.get('Selection_Cutoff')
        if cutoff:
            try:
                selection_cutoffs.append(_date(cutoff))
            except (TypeError, ValueError) as exc:
                raise PortfolioDataError(f"{component['name']}: invalid variant selection cutoff {cutoff!r}") from exc
    selection_cutoff = max(selection_cutoffs) if selection_cutoffs else None
    if selection_cutoff:
        # The cutoff close may be the initial NAV only. Every measured return
        # must occur after the latest date used to choose either active variant.
        dates = [d for d in dates if d >= selection_cutoff]
        warnings.append(f'Porteføljen starter ved første felles månedsslutt på eller etter {selection_cutoff}, '
                        'siste dato brukt til variantvalg. Avkastningen måles først etter dette startpunktet.')
    if len(dates) < 2:
        reason = f' after variant selection cutoff {selection_cutoff}' if selection_cutoff else ''
        detail = '; '.join(f"{n} reaches {covered[n]}" for n in sorted(covered, key=covered.get))
        raise PortfolioDataError(
            f'Fewer than two common completed month-end observations{reason}; '
            f'no portfolio return can be calculated. Binding component: {binding} '
            f'(last usable month-end {covered[binding]}). Coverage: {detail}.')
    for a, b in zip(dates, dates[1:]):
        expected = _month_end(a + timedelta(days=1))
        if b != expected:
            raise PortfolioDataError(f'Missing common month-end NAV between {a} and {b}; refusing to invent a monthly rebalance.')
    names = [c['name'] for c in curves]
    units = {n: start_capital / 4 / monthly[n][dates[0]][1] for n in names}
    equity, trades = [], []
    for index, day in enumerate(dates):
        before = {n: units[n] * monthly[n][day][1] for n in names}
        total = sum(before.values())
        target = total / 4
        equity.append({'Dato': str(day), 'Verdi_NOK': total,
                       'Antall_Strategier': 4,
                       'Observation_Dates': {n: str(monthly[n][day][0]) for n in names}})
        for n in names:
            transfer = target if index == 0 else target - before[n]
            if abs(transfer) > 1e-8:
                trades.append({'Dato': str(day), 'Strategi': n,
                               'Type': 'INITIAL_ALLOCATION' if index == 0 else ('ALLOCATE' if transfer > 0 else 'WITHDRAW'),
                               'Verdi_NOK': abs(transfer), 'Transfer_NOK': transfer,
                               'Kostnad_NOK': 0.0,
                               'Level': 'strategy capital allocation'})
            units[n] = target / monthly[n][day][1]
    last = dates[-1]
    holdings = [{'Strategi': n, 'Dato': str(last), 'Verdi_NOK': equity[-1]['Verdi_NOK'] / 4,
                 'Andel_Pst': 25.0, 'Target_Pst': 25.0, 'Antall': units[n],
                 'NAV': monthly[n][last][1], 'Observation_Date': str(monthly[n][last][0]),
                 'Type': 'strategy sleeve'} for n in names]
    components = []
    for source in curves:
        n = source['name']
        raw = [monthly[n][d][1] for d in dates]
        normalized = [start_capital / 4 * v / raw[0] for v in raw]
        components.append({'Strategi': n, **_metrics(normalized, dates, risk_free_pct),
                           'source': source.get('source'), 'source_frequency': source.get('frequency'),
                           'Source_Start': str(min(prepared[n])), 'Source_End': str(max(prepared[n])),
                           'variant': source.get('variant'), 'valid': True})
    warnings.extend([
        'Returns use the same completed month-end window for all four strategies. No daily PB-ROE NAV is interpolated.',
        'Drawdown and volatility are measured monthly and can miss losses within a month.',
        'Underlying strategy costs remain as exported. Capital transfers assume no additional costs.',
        f'The shared portfolio ends on {last}; this is a historical allocation snapshot, not current stock holdings.',
    ])
    if (last.year, last.month) != (as_of.year, as_of.month):
        warnings.append(f'No trailing values are extended beyond the common source coverage through {last}.')
    if (last - dates[0]).days < 365:
        warnings.append('The common history is shorter than one year; annualized metrics are extrapolations of this shorter window.')
    metrics = _metrics([r['Verdi_NOK'] for r in equity], dates, risk_free_pct)
    metrics.update({'Rebalance': 'monthly', 'Andel_Per_Strategi_Pst': 25.0,
                    'N_Strategier': 4, 'As_Of': str(as_of), 'Cost_Basis': 'exported strategy NAVs; capital transfers cost 0'})
    metrics['Selection_Cutoff'] = str(selection_cutoff) if selection_cutoff else None
    return {'equity': equity, 'holdings': holdings, 'trades': trades,
            'metrics': metrics, 'components': components, 'warnings': warnings,
            'sources': [c.get('source') for c in curves],
            'coverage': {n: {'last_observation': str(c['last_observation']),
                             'last_usable_month_end': str(c['last_usable_month_end']),
                             'age_days': c['age_days'],
                             'dropped_month_ends': [
                                 {'month_end': str(d['month_end']),
                                  'last_observation': str(d['last_observation']),
                                  'gap_business_days': d['gap_business_days']}
                                 for d in c['dropped_month_ends']]}
                         for n, c in coverage.items()},
            'binding_component': binding,
            'common_period': {'start': str(dates[0]), 'end': str(last),
                              'frequency': 'monthly', 'observations': len(dates), 'return_periods': len(dates) - 1,
                              'selection_cutoff': str(selection_cutoff) if selection_cutoff else None}}


def _latest(folder, pattern, run_timestamp=False):
    paths = [p for p in Path(folder).glob(pattern)
             if not p.name.startswith('~$') and 'BEFORE_FIX' not in p.name]
    if run_timestamp:
        # Match the individual SentMom mail reader: all sibling outputs share
        # a run timestamp. Copying/touching an old file must not select it.
        pattern = re.compile(r'S5_SentMom31_Portfolio_(\d{8}_\d{6})\.xlsx$')
        stamped = [(pattern.fullmatch(p.name).group(1), p) for p in paths if pattern.fullmatch(p.name)]
        if not stamped:
            raise PortfolioDataError(f'No timestamped SentMom portfolio in {folder}')
        return max(stamped, key=lambda pair: pair[0])[1]
    if not paths:
        raise PortfolioDataError(f'No {pattern} in {folder}')
    return max(paths, key=lambda p: (p.stat().st_mtime_ns, p.name))


def _source(path, sheet=None):
    path = Path(path)
    stat = path.stat()
    return {'path': str(path.resolve()), 'sheet': sheet, 'mtime_ns': stat.st_mtime_ns, 'size': stat.st_size}


def load_production_curves(excel_dir, insider_dir, selected_insider=None):
    """Read existing files only. Invalid/missing exports remain explicit components.

    Requires pandas/openpyxl only at this boundary, never for portfolio math.
    insider_dir is the pipeline data directory (containing 6_backtest).
    """
    import pandas as pd
    base, insider_dir = Path(excel_dir), Path(insider_dir)
    specs = [
        ('PB-ROE-Momentum', base / 'DataPB_ROE' / 'Backtest', 'BT_v3_Enhanced_*.xlsx', 'Equity_Curve', 'Strategy_v3', 'monthly'),
        ('NLP Sentiment — ledelse', base / 'StrategyResults_v4_Sentiment', 'Sentiment_v6_Hendelse_SMA*.xlsx', 'Equity_Curve', 'Strategy', 'daily'),
        ('Sentiment Momentum v3.1', base / 'DataNLP' / 'BacktestResults', 'S5_SentMom31_Portfolio_*.xlsx', 0, 'Portfolio_Value', 'daily'),
    ]
    result = []
    for name, folder, pattern, sheet, value_column, frequency in specs:
        component = {'name': name, 'frequency': frequency, 'observations': [], 'valid': True, 'errors': []}
        try:
            path = _latest(folder, pattern, run_timestamp=(value_column == 'Portfolio_Value'))
            component['source'] = _source(path, sheet)
            frame = pd.read_excel(path, sheet_name=sheet)
            component['observations'] = list(zip(frame['Date'], frame[value_column]))
            if name == 'NLP Sentiment — ledelse':
                metrics = pd.read_excel(path, sheet_name='Metrics').iloc[0].to_dict()
                component['metadata'] = metrics
                version = metrics.get('accounting_version', 0)
                if pd.isna(version) or float(version) < 2:
                    component['errors'].append('Management export predates accounting_version=2; rerun the corrected management model.')
                if not _declared_valid(metrics.get('data_valid', False)):
                    component['errors'].append('Management export is not marked data_valid; resolve the reported price-quality issues and rerun.')
                component['variant'] = str(metrics.get('valgt_strategi', '')) + ' | ' + str(metrics.get('valgt_exit', ''))
        except Exception as exc:
            component['errors'].append(f'{type(exc).__name__}: {exc}')
        component['valid'] = not component['errors']
        result.append(component)
    component = {'name': 'Innsidehandel — Oslo Børs', 'frequency': 'daily',
                 'observations': [], 'valid': True, 'errors': []}
    try:
        folder = insider_dir if insider_dir.name == '6_backtest' else insider_dir / '6_backtest'
        selection_path = folder / 'selected_variant.json'
        selection = json.loads(selection_path.read_text(encoding='utf-8'))
        variant = selected_insider or selection['Variant']
        if selected_insider and selected_insider != selection['Variant']:
            raise PortfolioDataError('Requested insider variant differs from the saved selected variant; rerun selection.')
        path = folder / 'strategi_equity.csv'
        with path.open(encoding='utf-8-sig', newline='') as handle:
            rows = [r for r in csv.DictReader(handle) if r['Strategi'] == variant]
        if not rows:
            raise PortfolioDataError(f'No equity curve for selected insider variant {variant}')
        component.update(observations=[(r['Dato'], r['Verdi_NOK']) for r in rows],
                         source=_source(path), variant=variant, selection=selection,
                         selection_source=_source(selection_path))
    except Exception as exc:
        component['errors'].append(f'{type(exc).__name__}: {exc}')
    component['valid'] = not component['errors']
    result.append(component)
    return result


def build_from_files(excel_dir, insider_dir, selected_insider=None, **kwargs):
    return build_capital_portfolio(load_production_curves(excel_dir, insider_dir, selected_insider), **kwargs)
