import json
import math
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from portfolio_blend import (PortfolioDataError, build_capital_portfolio,
                             load_production_curves, _latest)


def curves(values=None, dates=None):
    dates = dates or ['2025-01-31', '2025-02-28', '2025-03-31']
    values = values or [[100, 100, 100]] * 4
    return [{'name': f'Strategy {i}', 'frequency': 'monthly' if i == 0 else 'daily',
             'source': {'path': f'component-{i}'}, 'observations': list(zip(dates, vals)),
             'valid': True} for i, vals in enumerate(values)]


class CapitalPortfolioTests(unittest.TestCase):
    def test_weighted_period_returns_and_self_financing_transfers(self):
        # First period +10%/-10%/0/0 => 0%. Second +10%/0/0/0 => +2.5%.
        result = build_capital_portfolio(curves([[100,110,121], [100,90,90],
                                                [100,100,100], [100,100,100]]), as_of='2025-04-10')
        self.assertAlmostEqual(result['equity'][1]['Verdi_NOK'], 1_000_000)
        self.assertAlmostEqual(result['equity'][-1]['Verdi_NOK'], 1_025_000)
        self.assertAlmostEqual(result['metrics']['Total_Pst'], 2.5)
        self.assertEqual([h['Andel_Pst'] for h in result['holdings']], [25] * 4)
        self.assertAlmostEqual(sum(h['Verdi_NOK'] for h in result['holdings']), 1_025_000)
        for day in ('2025-02-28', '2025-03-31'):
            self.assertAlmostEqual(sum(t['Transfer_NOK'] for t in result['trades'] if t['Dato'] == day), 0)

    def test_nav_units_do_not_change_results(self):
        a = curves([[100,110,121], [100,90,90], [100,100,100], [100,100,100]])
        b = [{**c, 'observations': [(d, v * (i + 1) * 1000) for d, v in c['observations']]}
             for i, c in enumerate(a)]
        av = build_capital_portfolio(a, as_of='2025-04-10')['metrics']['Total_Pst']
        bv = build_capital_portfolio(b, as_of='2025-04-10')['metrics']['Total_Pst']
        self.assertAlmostEqual(av, bv)

    def test_future_and_current_partial_month_are_not_usable(self):
        c = curves([[100,110,9999]] * 4, ['2026-07-31', '2026-08-31', '2026-09-30'])
        for item in c[1:]:
            item['observations'][-1] = ('2026-09-14', 9999)
        r = build_capital_portfolio(c, as_of='2026-09-15')
        self.assertEqual(r['common_period']['end'], '2026-08-31')
        self.assertAlmostEqual(r['metrics']['Total_Pst'], 10)
        self.assertTrue(any('after 2026-09-15' in w for w in r['warnings']))

    def test_stale_final_partial_month_is_not_forward_filled(self):
        c = curves([[100,110,120]] * 4, ['2026-06-30', '2026-07-31', '2026-08-31'])
        c[2]['observations'][-1] = ('2026-08-19', 120)
        r = build_capital_portfolio(c, as_of='2026-09-15')
        self.assertEqual(r['common_period']['end'], '2026-07-31')

    def test_weekend_month_end_uses_actual_observation_date(self):
        c = curves([[100,110,120]] * 4, ['2025-08-31', '2025-09-30', '2025-10-31'])
        for item in c[1:]:
            item['observations'][0] = ('2025-08-29', 100)
        r = build_capital_portfolio(c, as_of='2025-11-10')
        self.assertEqual(r['equity'][0]['Dato'], '2025-08-31')
        self.assertEqual(r['equity'][0]['Observation_Dates']['Strategy 1'], '2025-08-29')

    def test_missing_internal_month_is_an_error(self):
        c = curves()
        c[2]['observations'].pop(1)
        with self.assertRaisesRegex(PortfolioDataError, 'Missing common month-end'):
            build_capital_portfolio(c, as_of='2025-04-10')

    def test_invalid_component_is_not_replaced_by_cash(self):
        c = curves()
        c[1].update(valid=False, errors=['management accounting invalid'])
        with self.assertRaisesRegex(PortfolioDataError, 'management accounting invalid'):
            build_capital_portfolio(c, as_of='2025-04-10')

    def test_invalid_nav_and_duplicate_dates(self):
        for bad in (0, -1, math.nan, math.inf):
            c = curves()
            c[0]['observations'][1] = ('2025-02-28', bad)
            with self.assertRaisesRegex(PortfolioDataError, 'non-positive or non-finite'):
                build_capital_portfolio(c, as_of='2025-04-10')
        c = curves()
        c[0]['observations'].append(('2025-02-28', 100))
        with self.assertRaisesRegex(PortfolioDataError, 'duplicate NAV'):
            build_capital_portfolio(c, as_of='2025-04-10')

    def test_daily_rebalancing_refused(self):
        with self.assertRaisesRegex(PortfolioDataError, 'monthly PB-ROE'):
            build_capital_portfolio(curves(), rebalance='daily')

    def test_latest_selection_cutoff_limits_all_measured_returns(self):
        c = curves([[50,100,110]] * 4)
        c[1]['metadata'] = {'selection_cutoff': '2025-01-15'}
        c[3]['selection'] = {'Selection_Cutoff': '2025-02-15'}
        result = build_capital_portfolio(c, as_of='2025-04-10')
        self.assertEqual(result['common_period']['start'], '2025-02-28')
        self.assertEqual(result['metrics']['Selection_Cutoff'], '2025-02-15')
        self.assertAlmostEqual(result['metrics']['Total_Pst'], 10)
        for item in c:
            item['observations'][0] = ('2025-01-31', 500000)
        changed = build_capital_portfolio(c, as_of='2025-04-10')
        self.assertEqual(result['equity'], changed['equity'])

    def test_cutoff_at_close_is_basepoint_and_future_cutoff_blocks(self):
        c = curves([[100,110,121]] * 4)
        c[1]['metadata'] = {'selection_cutoff': '2025-02-28'}
        result = build_capital_portfolio(c, as_of='2025-04-10')
        self.assertEqual(result['common_period']['start'], '2025-02-28')
        self.assertAlmostEqual(result['metrics']['Total_Pst'], 10)
        c[1]['metadata']['selection_cutoff'] = '2026-01-31'
        with self.assertRaisesRegex(PortfolioDataError, 'variant selection cutoff 2026-01-31'):
            build_capital_portfolio(c, as_of='2025-04-10')

    def test_spikes_are_exposed_not_clipped(self):
        c = curves([[100, 1000, 1000]] * 4)
        result = build_capital_portfolio(c, as_of='2025-04-10')
        self.assertTrue(any('NAV move' in w for w in result['warnings']))
        self.assertAlmostEqual(result['metrics']['Total_Pst'], 900)

    def test_sentmom_selects_run_timestamp_not_copy_time(self):
        import os
        with tempfile.TemporaryDirectory() as tmp:
            older = Path(tmp) / 'S5_SentMom31_Portfolio_20260101_000000.xlsx'
            newer = Path(tmp) / 'S5_SentMom31_Portfolio_20260201_000000.xlsx'
            older.touch()
            newer.touch()
            os.utime(older, (2000000000, 2000000000))
            os.utime(newer, (1000000000, 1000000000))
            selected = _latest(tmp, 'S5_SentMom31_Portfolio_*.xlsx', run_timestamp=True)
            self.assertEqual(selected, newer)

    def test_backup_exports_are_excluded_consistently_with_mail(self):
        import os
        with tempfile.TemporaryDirectory() as tmp:
            for stem in ('BT_v3_Enhanced', 'Sentiment_v6_Hendelse_SMA50'):
                actual = Path(tmp) / f'{stem}_2026-09-14.xlsx'
                backup = Path(tmp) / f'{stem}_2026-09-15_BEFORE_FIX.xlsx'
                actual.touch()
                backup.touch()
                os.utime(actual, (1000000000, 1000000000))
                os.utime(backup, (2000000000, 2000000000))
                self.assertEqual(_latest(tmp, stem + '_*.xlsx'), actual)
            actual = Path(tmp) / 'S5_SentMom31_Portfolio_20260914_230114.xlsx'
            actual.touch()
            (Path(tmp) / 'S5_SentMom31_Portfolio_20990914_230114_BEFORE_FIX.xlsx').touch()
            (Path(tmp) / 'S5_SentMom31_Portfolio_BEFORE_FIX_20990914_230114.xlsx').touch()
            self.assertEqual(_latest(tmp, 'S5_SentMom31_Portfolio_*.xlsx', run_timestamp=True), actual)

    def test_loader_rejects_legacy_management_and_keeps_selected_insider(self):
        class Metrics:
            iloc = [SimpleNamespace(to_dict=lambda: {'valgt_strategi': 'S3', 'valgt_exit': 'TRATR'})]
        fake_pandas = SimpleNamespace(
            read_excel=lambda path, sheet_name: Metrics() if sheet_name == 'Metrics' else
                {'Date': ['2025-01-31','2025-02-28'], 'Strategy_v3': [100,101],
                 'Strategy': [100,102], 'Portfolio_Value': [100,103]},
            isna=lambda x: x is None or (isinstance(x, float) and math.isnan(x)))
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            files = ['DataPB_ROE/Backtest/BT_v3_Enhanced_2025.xlsx',
                     'StrategyResults_v4_Sentiment/Sentiment_v6_Hendelse_SMA50_2025.xlsx',
                     'DataNLP/BacktestResults/S5_SentMom31_Portfolio_20250101_000000.xlsx']
            for relative in files:
                path = base / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            backtest = base / 'data' / '6_backtest'
            backtest.mkdir(parents=True)
            (backtest / 'selected_variant.json').write_text(json.dumps({'Variant':'scorevektet'}))
            (backtest / 'strategi_equity.csv').write_text('Strategi,Dato,Verdi_NOK\ndaglig,2025-01-31,999\nscorevektet,2025-01-31,100\nscorevektet,2025-02-28,104\n')
            with patch.dict(sys.modules, {'pandas': fake_pandas}):
                loaded = load_production_curves(base, base/'data')
                self.assertFalse(loaded[1]['valid'])
                self.assertIn('accounting_version=2', ';'.join(loaded[1]['errors']))
                self.assertTrue(loaded[3]['valid'])
                self.assertEqual(loaded[3]['variant'], 'scorevektet')
                self.assertEqual(loaded[3]['observations'], [('2025-01-31','100'),('2025-02-28','104')])
                with self.assertRaises(PortfolioDataError):
                    build_capital_portfolio(loaded, as_of='2025-03-10')


if __name__ == '__main__':
    unittest.main()
