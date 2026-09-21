"""Exercise the actual nested PB momentum helper without running downloads."""
import ast
import unittest
from pathlib import Path

import pandas as pd


class PBMomentumChronology(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = (Path(__file__).parent / 'Only_260820.py').read_text(encoding='utf-8')
        tree = ast.parse(source)
        pb = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'PBROE_All3')
        helper = next(n for n in ast.walk(pb) if isinstance(n, ast.FunctionDef) and n.name == 'compute_momentum')
        namespace = dict(MOM_LOOKBACK_MONTHS=12, MOM_SKIP_MONTHS=1)
        exec(compile(ast.Module(body=[helper], type_ignores=[]), '<pb-helper>', 'exec'), namespace)
        cls.momentum = staticmethod(namespace['compute_momentum'])

    def test_12_minus_1_endpoints_and_no_execution_close_lookahead(self):
        dates = pd.date_range('2023-01-31', periods=14, freq='ME')
        prices = pd.DataFrame({'A': [100, 110, 120, 130, 140, 150, 160, 170, 180, 190, 200, 210, 9999, 50000]}, index=dates)
        decision = dates[12]
        # At January 2024 month-end: Dec 2023 / Jan 2023, excluding January 2024.
        self.assertAlmostEqual(self.momentum(prices, 'A', decision), 1.1)
        prices.loc[decision:, 'A'] = 1
        self.assertAlmostEqual(self.momentum(prices, 'A', decision), 1.1)


if __name__ == '__main__':
    unittest.main()
