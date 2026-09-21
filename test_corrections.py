from __future__ import annotations
import ast
import hashlib
import json
import logging
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import innsidehandel_pipeline as ip
import master
import capital_mail
from runtime_config import choose_variant, split_metrics, configure_paths


class ScraperCompleteness(unittest.TestCase):
    def test_old_watermark_requires_full_history_recheck(self):
        with tempfile.TemporaryDirectory() as directory:
            vm = ip.Vannmerke(Path(directory)/'watermark.json')
            today = date(2026,9,13)
            vm.sett(ip.GRUPPE_ARTIKLER, 'A', today, artikler=0)
            opp = SimpleNamespace(full=False, overlapp_dager=10,
                                  eldste_melding=lambda: date(2023,9,13))
            self.assertEqual(ip.artikkel_vindu(vm,'A',opp,today),
                             (False,date(2023,9,13)))
            vm.sett(ip.GRUPPE_ARTIKLER,'A',today,artikler=0,
                    liste_validering=ip.ARTIKKEL_VALIDERING)
            self.assertEqual(ip.artikkel_vindu(vm,'A',opp,today),
                             (True,date(2026,9,3)))
            vm.merk_feil(ip.GRUPPE_ARTIKLER,'A','partial download')
            self.assertFalse(ip.artikkel_vindu(vm,'A',opp,today)[0])

    def client(self, states, pages, counts=None):
        c = object.__new__(ip.Euronext)
        c.opp = SimpleNamespace(maks_sider=5, pause_mellom_sider_s=0,
                               browser_timeout_ms=10, maks_forsok=1)
        c.logger = logging.getLogger('test')
        c.nl = SimpleNamespace(ga_til=Mock(return_value=True), page=SimpleNamespace(
            wait_for_function=Mock(), evaluate=Mock(side_effect=states)))
        c.bygg_url=Mock(return_value='https://example.test/list')
        c.avvis_cookies=Mock()
        c._antall_treff=Mock(return_value=counts)
        c._les_tabell=Mock(side_effect=pages)
        return c

    def test_unloaded_page_is_not_empty_success(self):
        c=self.client([{'table':False,'empty':False,'blocked':False}], [[]])
        self.assertEqual(c._hent_liste_validert(['ISIN'],date(2020,1,1)),([],False))

    def test_blocked_page_is_failure(self):
        c=self.client([{'table':False,'empty':True,'blocked':True}], [[]])
        self.assertEqual(c._hent_liste_validert(['ISIN'],date(2020,1,1)),([],False))

    def test_explicit_zero_results_is_success(self):
        c=self.client([{'table':False,'empty':True,'blocked':False}], [[]],0)
        self.assertEqual(c._hent_liste_validert(['ISIN'],date(2020,1,1)),([],True))

    def test_partial_pagination_does_not_commit(self):
        c=self.client([{'table':True},{'empty':True}], [[{'nid':'1'}],[]],2)
        self.assertEqual(c._hent_liste_validert(['ISIN'],date(2020,1,1)),([],False))

    def test_complete_count_is_accepted(self):
        rows=[{'nid':'1'},{'nid':'2'}]
        c=self.client([{'table':True}], [rows],2)
        self.assertEqual(c._hent_liste_validert(['ISIN'],date(2020,1,1)),(rows,True))


class Chronology(unittest.TestCase):
    def test_future_cluster_members_do_not_rewrite_old_scores(self):
        first={'Dato':'2024-01-01','Klokkeslett':'10:00','Ticker':'A','Klasse':'KJOP','Person':'ONE','Verdi_NOK':100}
        later={**first,'Dato':'2024-01-10','Person':'TWO','Verdi_NOK':200}
        prefix=[dict(first)]; full=[dict(first),later]
        ip.finn_klynger(prefix,30); ip.finn_klynger(full,30)
        self.assertEqual(prefix[0],full[0])
        self.assertEqual(full[0]['Klynge_Personer'],1)
        self.assertEqual(full[1]['Klynge_Personer'],2)
        self.assertEqual(full[0]['Klynge_NOK'],100)

    def test_selection_never_uses_test_return(self):
        rows=[dict(Variant='daglig',Train_CAGR_Pst=10,Train_Trades=40,Train_Days=300,Test_CAGR_Pst=999),
              dict(Variant='other',Train_CAGR_Pst=15,Train_Trades=40,Train_Days=300,Test_CAGR_Pst=-99)]
        self.assertEqual(choose_variant(rows,'daglig')[0]['Variant'],'other')
        rows[0]['Test_CAGR_Pst']=-500;rows[1]['Test_CAGR_Pst']=500
        self.assertEqual(choose_variant(rows,'daglig')[0]['Variant'],'other')

    def test_cutoff_excludes_future_training_values(self):
        curve=[('2023-01-01',100),('2024-01-01',110),('2025-01-01',500)]
        original=split_metrics(curve,'2024-01-01')
        curve[-1]=('2025-01-01',1)
        self.assertEqual(original['Train_CAGR_Pst'],split_metrics(curve,'2024-01-01')['Train_CAGR_Pst'])

    def test_composite_waits_for_next_session(self):
        rows=[dict(Kilde='NLP',Dato='2024-01-02',Ticker='A',Score=100)]
        result=master.bygg_samlet(master.Master(),rows,[date(2024,1,2),date(2024,1,3)],logging.getLogger('test'))
        self.assertEqual([r['Dato'] for r in result],['2024-01-03'])


class IntegrityAndReporting(unittest.TestCase):
    def test_missing_insider_outputs_fail_even_without_status_file(self):
        with tempfile.TemporaryDirectory() as directory:
            m = master.Master(excel_dir=directory,innside_dir=directory)
            errors, files = master.validate_sources(m)
            self.assertTrue(any('selected_variant.json' in e for e in errors))
            self.assertTrue(any('strategier.csv' in e for e in errors))

    def test_standalone_insider_mail_uses_selected_variant(self):
        with tempfile.TemporaryDirectory() as directory:
            opp = ip.Oppsett(base_dir=Path(directory))
            opp.lag_mapper()
            (opp.s6_dir/'selected_variant.json').write_text(json.dumps({
                'Variant':'forfall-60','Selection_Cutoff':'2025-06-30',
                'Train_CAGR_Pst':12,'Test_CAGR_Pst':7}),encoding='utf-8')
            ip.skriv_csv(opp.strategier_csv,[{'Strategi':'daglig','CAGR_Pst':5},
                                            {'Strategi':'forfall-60','CAGR_Pst':10}])
            ip.skriv_csv(opp.beholdning_csv,[{'Strategi':'forfall-60','Ticker':'(kontanter)'}])
            with patch.object(ip,'send_epost',return_value=True) as send:
                ip.epost_rapport(opp,[],logging.getLogger('test'))
            html, subject = send.call_args.args[1:3]
            self.assertIn('Valgt strategi: forfall-60',html)
            self.assertIn('forfall-60 CAGR +10.0 %',subject)
            self.assertIn('0 posisjoner',subject)
            self.assertNotIn('siste dag porteføljen var hel',html)

    def test_standalone_insider_delivery_error_is_visible(self):
        with tempfile.TemporaryDirectory() as directory:
            opp = ip.Oppsett(base_dir=Path(directory));opp.lag_mapper()
            ip.skriv_csv(opp.strategier_csv,[{'Strategi':'daglig','CAGR_Pst':5}])
            with patch.object(ip,'send_epost',return_value=False):
                with self.assertRaisesRegex(RuntimeError,'Email delivery failed'):
                    ip.epost_rapport(opp,[],logging.getLogger('test'))

    def test_success_then_cached_mail_uses_completed_result(self):
        with tempfile.TemporaryDirectory() as directory:
            m=master.Master(excel_dir=directory,innside_dir=directory)
            equity=[dict(Dato='2024-01-03',Verdi_NOK=100,Antall_Navn=0)]
            stats={'CAGR_Pst':5,'Periode':'2024-01-03 → 2025-01-03'}
            sections={'strategier':[{}]*3,'stil':'','html':'','kort':{},'ekstra':''}
            portfolio=dict(equity=equity,metrics=stats,trades=[],holdings=[],components=[])
            events=[]
            with patch('data_acquisition.build_all',return_value=[]), \
                 patch.object(master.downloads,'strategy_rows',return_value=[]), \
                 patch.object(master,'protected_input_errors',return_value=[]), \
                 patch.object(master,'kjor_alle',side_effect=lambda *a: events.append('models') or []), \
                 patch.object(master,'validate_sources',return_value=([],[])), \
                 patch.object(master,'backtest_samlet') as legacy_backtest, \
                 patch.object(master,'les_alle_scorer') as legacy_scores, \
                 patch.object(master,'calculate_capital_portfolio',side_effect=lambda *a,**k: events.append('capital') or portfolio) as calculate, \
                 patch.object(master,'strategisammendrag',return_value=sections), \
                 patch.object(master,'innside_data',return_value={'valid':True}), \
                 patch.object(capital_mail,'render_capital_mail',return_value='<html>Complete report</html>'), \
                 patch.object(ip,'send_epost',side_effect=lambda *a: events.append('email') or True):
                self.assertEqual(master.kjor(['--mappe',directory,'--excel-dir',directory]),0)
                self.assertEqual(events,['models','capital','email'])
                self.assertTrue((m.ut_dir/'completed_run.json').exists())
                saved=json.loads((m.ut_dir/'completed_run.json').read_text(encoding='utf-8'))
                self.assertEqual(saved['format_version'],3)
                self.assertEqual(saved['method'],'capital_25_each')
                calculate.reset_mock()
                self.assertEqual(master.kjor(['--mappe',directory,'--excel-dir',directory,'--bare-mail','--mail-kladd']),0)
                calculate.assert_not_called()
                legacy_backtest.assert_not_called()
                legacy_scores.assert_not_called()

    def test_protected_function_source_hashes(self):
        expected=json.loads((ROOT/'protected_strategy_hashes.json').read_text())
        text=(ROOT/'Only_260820.py').read_text(encoding='utf-8-sig')
        for node in ast.parse(text).body:
            if isinstance(node,ast.FunctionDef) and node.name in expected:
                body='\n'.join(text.splitlines()[node.lineno-1:node.end_lineno])
                self.assertEqual(hashlib.sha256(body.encode()).hexdigest(),expected[node.name])

    def test_path_relocation_preserves_original_source_and_other_constants(self):
        ns={'__name__':'portable_test'}
        exec('def f():\n return r"C:\\Users\\ander\\Desktop\\Python_K4\\ExcelData\\DataPB_ROE", 123',ns)
        with tempfile.TemporaryDirectory() as directory, patch.dict('os.environ',{}):
            configure_paths(ns,directory)
            self.assertEqual(ns['f'](),(str(Path(directory)/'DataPB_ROE'),123))

    def test_failed_run_creates_failure_draft_not_performance_email(self):
        with tempfile.TemporaryDirectory() as directory:
            args=['--ikke-kjor','--mail-kladd','--mappe',directory,'--excel-dir',directory]
            with patch.object(master,'validate_sources',return_value=(['NLP output missing'],[])), patch.object(ip,'send_epost') as send:
                self.assertEqual(master.kjor(args),2)
                send.assert_not_called()
            html=next((Path(directory)/'7_master').glob('master_mail_*.html')).read_text(encoding='utf-8')
            self.assertIn('Analysis incomplete',html)
            self.assertNotIn('CAGR',html)

    def test_mail_delivery_failure_returns_error(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(master,'validate_sources',return_value=(['missing data'],[])), patch.object(ip,'send_epost',return_value=False) as send:
                self.assertEqual(master.kjor(['--ikke-kjor','--mappe',directory,'--excel-dir',directory]),3)
                send.assert_called_once()


if __name__ == '__main__':
    unittest.main()
