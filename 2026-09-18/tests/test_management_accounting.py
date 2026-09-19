"""Accounting regressions: extract definitions only, never download or email."""
import ast
import hashlib
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from management_test_helpers import _hent, _md_av


class ManagementAccounting(unittest.TestCase):
    def setUp(self):
        self.ns = _hent()
        self.ns["config"].maks_posisjoner = 1
        self.ns["config"].startkapital = 1000.0
        self.ns["config"].min_signaler = 1

    def run_prices(self, values, exit_code="F03"):
        ns = self.ns
        dates = pd.bdate_range("2024-01-01", periods=len(values))
        close = pd.DataFrame({"A.OL": values}, index=dates)
        md = _md_av(ns, close)
        ns["md"] = md
        signal = pd.DataFrame([dict(signal_id=1, dato=dates[1],
            artikkeldato=dates[0], rapport_i=1, nyhets_exit_i=1,
            selskap="A", ticker="A.OL", tittel="report", forrige_score=.2,
            ny_score=.8, endring=.6, bedring_pst=300., gulv_bandt=False,
            over_sma=True, inn_i=1)])
        strategy = ns["Strategi"]("S1 ≥20%", 20., False)
        rule = next(e for e in ns["EXIT_STRATEGIER"] if e.kode == exit_code)
        result = ns["kjor_strategi"](strategy, rule, signal, md, {}, live=True)
        return result, strategy, rule, signal

    def test_ten_percent_price_move_is_ten_percent_nav_move(self):
        result, *_ = self.run_prices([100, 100, 110, 110, 110])
        self.assertEqual(result["kurve"].iloc[2], 1100.)
        self.assertEqual(result["kurve"].iloc[3], 1100.)

    def test_exit_has_no_artificial_nav_snapback(self):
        result, *_ = self.run_prices([100, 100, 110, 110, 110, 110])
        self.assertEqual(result["Handler"], 1)
        self.assertEqual(result["kurve"].iloc[3], result["kurve"].iloc[4])
        self.assertAlmostEqual(result["handler"].iloc[0]["avk"], .10)
        self.assertEqual(result["Slutt_NOK"], 1100.)

    def test_missing_quote_keeps_last_actual_mark_not_entry_capital(self):
        result, *_ = self.run_prices([100, 100, 110, np.nan, np.nan, 110])
        self.assertTrue(result["data_valid"])
        self.assertEqual(result["kurve"].iloc[3], 1100.)
        self.assertEqual(result["kurve"].iloc[4], 1100.)
        self.assertEqual(result["handler"].iloc[0]["ut_i"], 5)

    def test_six_missing_sessions_prevent_publication(self):
        result, strategy, rule, signals = self.run_prices(
            [100, 100, 110] + [np.nan] * 6 + [110])
        self.assertFalse(result["data_valid"])
        self.assertEqual(len(result["valuation_issues"]), 1)
        with self.assertRaisesRegex(RuntimeError, "refusing to publish"):
            self.ns["skriv_master_fil"](result, result, strategy, rule, signals, "test", 0)

    def test_jump_guard_flags_actual_observation_gap_without_clipping(self):
        prices = pd.DataFrame({"BSP.OL": [.10144, np.nan, 10.144]},
                              index=pd.bdate_range("2024-12-30", periods=3))
        original = prices.copy(deep=True)
        issues = self.ns["kontroller_priser"](prices)
        self.assertEqual(issues.iloc[0]["ticker"], "BSP.OL")
        self.assertAlmostEqual(issues.iloc[0]["ratio"], 100.)
        pd.testing.assert_frame_equal(prices, original)

    def test_ordinary_price_movements_are_not_rejected(self):
        prices = pd.DataFrame({"A.OL": [100., 110., 85., np.nan, 95.]},
                              index=pd.bdate_range("2024-01-01", periods=5))
        self.assertTrue(self.ns["kontroller_priser"](prices).empty)

    def test_export_declares_accounting_version_and_consistent_nav(self):
        result, strategy, rule, signals = self.run_prices([100, 100, 110, 110, 110, 110])
        with tempfile.TemporaryDirectory() as directory:
            self.ns["config"].base_dir = Path(directory)
            path = self.ns["skriv_master_fil"](result, result, strategy, rule, signals,
                                               "Manual selection", 0)
            metrics = pd.read_excel(path, sheet_name="Metrics").iloc[0]
            curve = pd.read_excel(path, sheet_name="Equity_Curve")
            self.assertEqual(int(metrics["accounting_version"]), 2)
            self.assertTrue(bool(metrics["data_valid"]))
            self.assertEqual(curve.Strategy.iloc[-1], 1100.)
            self.assertEqual(metrics["max_hold_sessions"], 3)
            self.assertIn("IKKE VURDERT", metrics["robusthetsport_bestod"])

    def test_protected_functions_are_byte_identical(self):
        source = (ROOT / "Only_260820.py").read_text(encoding="utf-8-sig")
        expected = json.loads((ROOT / "protected_strategy_hashes.json").read_text())
        for node in ast.parse(source).body:
            if isinstance(node, ast.FunctionDef) and node.name in expected:
                body = "\n".join(source.splitlines()[node.lineno - 1:node.end_lineno])
                self.assertEqual(hashlib.sha256(body.encode()).hexdigest(), expected[node.name])

    def test_invalid_selection_writes_current_diagnostics_before_rejection(self):
        row = dict(Variant="S1|F21", Train_Trades=40, Train_CAGR_Pst=12.,
                   Train_Days=300, Train_Trimmed_Return=.01,
                   Train_Data_Valid=True, data_valid=False)
        with tempfile.TemporaryDirectory() as directory, patch.dict("os.environ", {"AKSJE_SENT_VALG": ""}):
            self.ns["config"].base_dir = Path(directory)
            destination = self.ns["config"].ut_dir / "variant_comparison.csv"
            destination.write_text("stale_diagnostics\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "unverified"):
                self.ns["velg_produksjon"](pd.DataFrame([row]))
            saved = pd.read_csv(destination)
            self.assertEqual(saved.iloc[0]["Variant"], "S1|F21")
            self.assertTrue(bool(saved.iloc[0]["Selected"]))
            self.assertFalse(bool(saved.iloc[0]["data_valid"]))

    def test_mail_prefers_all_saved_management_risk_metrics(self):
        # Compile nested definitions, without executing the mail entry point.
        from typing import Dict, List, Optional, Tuple
        from datetime import datetime
        from collections import defaultdict
        source = (ROOT / "mail" / "mail_strategier.py").read_text(encoding="utf-8")
        outer = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef)
                     and n.name == "MailAlleStrategier")
        functions = [n for n in outer.body if isinstance(n, ast.FunctionDef)]
        ns = dict(pd=pd, np=np, Path=Path, Dict=Dict, List=List, Optional=Optional,
                  Tuple=Tuple, datetime=datetime, defaultdict=defaultdict,
                  MIN_AAR_FOR_CAGR=2., RF_HARMONISERT=.03, ANTALL_HANDLER=10,
                  MGMT_HENDELSE="Sentiment_v6_Hendelse_SMA*.xlsx",
                  MGMT_MAANEDLIG="Sentiment_v4*_SMA*.xlsx", MGMT_DIR=Path("."))
        exec(compile(ast.Module(body=functions, type_ignores=[]), "<mail-definitions>", "exec"), ns)
        ns["nyeste"] = lambda *args: Path("fixture.xlsx")
        days = pd.bdate_range("2024-01-01", periods=280)
        curve = pd.DataFrame(dict(Date=days, Strategy=np.linspace(100., 110., len(days)),
                                  Benchmark=np.linspace(100., 200., len(days))))
        metrics = pd.DataFrame([dict(accounting_version=2, data_valid=True,
            cagr=.12, total_avkastning=.5, volatilitet=.345, sharpe=.999,
            sortino=1.3, calmar=.4, max_drawdown=-.2, snitt_hold_dager=17.,
            benchmark_cagr=.07, handler=0)])
        def read(path, sheet_name, **kwargs):
            if sheet_name == "Equity_Curve":
                return curve.copy()
            if sheet_name == "Metrics":
                return metrics.copy()
            return pd.DataFrame()
        with patch.object(pd, "read_excel", side_effect=read):
            result = ns["les_sentiment_mgmt"]()
        self.assertIsNone(result["mangler"])
        for key, value in dict(vol=34.5, sharpe=.999, sortino=1.3, calmar=.4,
                               mdd=-20., cagr=12., total=50., holdedager=17.,
                               benchmark_cagr=7., excess=5.).items():
            self.assertAlmostEqual(result["n"][key], value, msg=key)


if __name__ == "__main__":
    unittest.main()
