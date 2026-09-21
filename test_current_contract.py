"""Public contracts for acquisition, chronological inputs and report provenance."""
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import data_acquisition as acquisition
import download_status as status
import innsidehandel_pipeline as ip
from runtime_config import capped_weights, observed_month_ends, historical_fundamentals, validate_price_frame


class DownloadReporting(unittest.TestCase):
    def setUp(self):
        status.reset()

    def test_success_requires_evidence_for_every_required_source(self):
        for keys in status.SOURCES.values():
            for key in keys:
                status.record_source(key, "DERIVED" if key == "step4" else "DOWNLOADED", network_attempted=key != "step4")
        self.assertTrue(all(r['status'] == 'DOWNLOADED' for r in status.strategy_rows()))
        status.record_source('articles', 'FAILED', 'Source unavailable')
        rows = {r['strategy']: r['status'] for r in status.strategy_rows()}
        self.assertEqual(rows['NLP Sentiment — ledelse'], 'FAILED')
        self.assertEqual(rows['Sentiment Momentum v3.1'], 'FAILED')
        self.assertEqual(rows['PB-ROE-Momentum'], 'DOWNLOADED')

    def test_cached_report_does_not_claim_download(self):
        self.assertTrue(all(r['status'] == 'CACHED' for r in status.strategy_rows(cached_run=True)))

    def test_failed_email_starts_with_status_and_escapes_provider_errors(self):
        status.record_source('articles', 'FAILED', '<script>bad</script>')
        html = status.prepend_summary('<html><body><h1>Failure</h1></body></html>', status.strategy_rows())
        self.assertLess(html.index('download-status'), html.index('<h1>'))
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertEqual(status.prepend_summary(html, status.strategy_rows()), html)

    def test_stage_exception_is_recorded(self):
        with tempfile.TemporaryDirectory() as folder:
            opp = ip.Oppsett(base_dir=Path(folder))
            with patch.object(ip, '_steg1_nedlasting_impl', side_effect=RuntimeError('unavailable')):
                with self.assertRaises(RuntimeError):
                    ip.steg1_nedlasting(opp, ip.stillelogger())
        self.assertEqual(status.get_source('insider_announcements')['status'], 'FAILED')


class DataContracts(unittest.TestCase):
    def test_same_day_articles_cannot_invent_intraday_order(self):
        rows = [dict(Company='A', Article_Date=d, Article_Title=t, Final_Score=v)
                for d, t, v in [('2024-01-02','old',.1), ('2024-01-03','one',.3), ('2024-01-03','two',.5)]]
        built = acquisition.sentiment_change_rows(rows, tickers={'A':'A'})
        self.assertEqual([r['Sentiment_Change'] for r in built], [0,.2,.4])
        self.assertEqual(built, acquisition.sentiment_change_rows(rows[::-1], tickers={'A':'A'}))

    def test_future_and_unscored_articles_are_excluded(self):
        rows = [dict(Company='A', Article_Date=d, Article_Title=t, Final_Score=v, Text_Length=n)
                for d,t,v,n in [('2024-01-02','valid',.1,100), ('2025-01-01','future',.5,100),
                                ('2024-01-03','empty',.8,0), ('2024-01-04','invalid',9,100)]]
        self.assertEqual(len(acquisition.sentiment_change_rows(rows, as_of=date(2024,2,1))), 1)

    def test_workbooks_are_real_excel_and_share_exact_ticker_identity(self):
        companies = [{'Symbol':'EQNR', 'Selskap':'Equinor ASA'}]
        with tempfile.TemporaryDirectory() as folder:
            p = acquisition.write_workbook(Path(folder)/'tickers.xlsx', acquisition.ticker_workbook_rows(companies), acquisition.TICKER_COLUMNS, index=True)
            frame = pd.read_excel(p)
            self.assertEqual(frame['Company'].tolist(), ['EQNR'])
        prices = acquisition.price_workbook_rows({'EQNR.OL':{date(2024,1,2):{'close':10,'adjclose':9,'volum':100}}})
        self.assertEqual(prices[0]['Company'], 'EQNR')
        self.assertEqual(prices[0]['Ticker'], 'EQNR.OL')

    def test_all_build_stages_record_failures_without_claiming_success(self):
        with tempfile.TemporaryDirectory() as folder:
            opp = ip.Oppsett(base_dir=Path(folder)/'data')
            with patch.object(acquisition, 'ensure_stock_list', side_effect=RuntimeError('offline')):
                rows = acquisition.build_all(Path(folder)/'excel', opp, ip.stillelogger(), steps=('tickers','prices'))
        self.assertEqual([r['status'] for r in rows], ['FAILED','FAILED'])

    def test_cached_source_is_not_renamed_downloaded_when_workbook_written(self):
        with tempfile.TemporaryDirectory() as folder:
            opp = ip.Oppsett(base_dir=Path(folder)/'data')
            companies = [{'Symbol':'EQNR', 'Selskap':'Equinor ASA'}]
            evidence = acquisition._result('tickers','Universe','CACHED',detail='from disk')
            with patch.object(acquisition, 'ensure_stock_list', return_value=(companies,evidence)):
                rows = acquisition.build_all(Path(folder)/'excel', opp, ip.stillelogger(), steps=('tickers',), download=False)
            self.assertEqual(rows[0]['status'], 'CACHED')
            self.assertTrue(Path(rows[0]['Fil']).exists())


class RealisticInputs(unittest.TestCase):
    def test_weights_do_not_renormalize_above_cap_or_invent_borrowing(self):
        weights = capped_weights({'A':100,'B':1,'C':1}, .25)
        self.assertTrue(all(0 <= w <= .25 for w in weights.values()))
        self.assertLessEqual(sum(weights.values()), .75 + 1e-9)

    def test_partial_month_is_not_dated_in_the_future(self):
        frame = pd.DataFrame({'A':[10,11,12]}, index=pd.to_datetime(['2024-01-30','2024-01-31','2024-02-02']))
        result = observed_month_ends(frame, '2024-02-15')
        self.assertEqual(list(result.index), [pd.Timestamp('2024-01-31')])

    def test_later_fundamental_revision_cannot_rewrite_old_decision(self):
        frame = pd.DataFrame({'PB':[1,99], 'AvailableDate':pd.to_datetime(['2024-01-10','2024-03-10'])},
                             index=pd.to_datetime(['2023-09-30','2023-09-30']))
        self.assertEqual(historical_fundamentals(frame,'2024-02-01')['PB'].tolist(), [1])
        self.assertTrue(historical_fundamentals(frame,'2024-01-09').empty)

    def test_hundredfold_price_jump_is_not_silently_repaired(self):
        frame = pd.DataFrame({'A':[1,100]}, index=pd.to_datetime(['2024-01-02','2024-01-03']))
        with self.assertRaisesRegex(RuntimeError, 'verification'):
            validate_price_frame(frame, ['A'])
        self.assertEqual(frame['A'].tolist(), [1,100])

    def test_missing_requested_ticker_blocks_price_validation(self):
        with self.assertRaisesRegex(RuntimeError, 'missing tickers'):
            validate_price_frame(pd.DataFrame({'A':[1,2]}), ['A','B'])


if __name__ == '__main__':
    unittest.main()
