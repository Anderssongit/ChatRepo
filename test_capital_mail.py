"""Report regressions: actual allocation math, ranking and failure disclosure."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from capital_mail import render_capital_mail
from master import Master
from portfolio_blend import build_capital_portfolio


class CapitalMail(unittest.TestCase):
    def fixture(self):
        variants = [dict(Strategi=n, CAGR_Pst=c, Sharpe=1, MaxDD_Pst=-10)
                    for n,c in [('daglig',8),('hendelse-20',0),('forfall-60',10),
                                ('scorevektet',12),('konsentrert',-5)]]
        selection = dict(Variant='scorevektet',Selection_Cutoff='2025-06-30',
                         Reason='Svakeste treningshalvdel; ingen dokumentert MOAT.',
                         Train_CAGR_Pst=20,Test_CAGR_Pst=10,
                         Train_Moderate_CAGR_Pst=15,Test_Moderate_CAGR_Pst=7,
                         Train_Stress_CAGR_Pst=-8,Train_Stress_Worst_Half_CAGR_Pst=-9)
        insider = dict(maal=dict(Strategi='scorevektet',Selection=selection),
                       varianter=variants,beholdning=[],handler=[])
        sections = dict(kort={'PB-ROE-Momentum':'<p>PB rules</p>',
                             'NLP Sentiment — ledelse':'<p>Management rules</p>',
                             'Sentiment Momentum v3.1':'<p>Momentum rules</p>'})
        return insider, sections

    def test_complete_mail_uses_capital_math_and_actual_top_three(self):
        curves = [dict(name=n,observations=[('2025-01-31',100),('2025-02-28',end)])
                  for n,end in zip(['PB','MG','SM','IN'],[120,100,100,100])]
        portfolio = build_capital_portfolio(curves,as_of='2025-03-01')
        insider, sections = self.fixture()
        html = render_capital_mail(Master(),[],portfolio,sections,insider)
        self.assertIn('5.0 %',html)  # 20% in one sleeve becomes 5% total.
        self.assertIn('månedlig',html)
        self.assertIn('0,80 %',html)
        self.assertIn('-9.0 %',html)
        self.assertIn('1. scorevektet',html)
        self.assertIn('2. forfall-60',html)
        self.assertIn('3. daglig',html)
        self.assertNotIn('<h3>4.',html)
        self.assertNotIn('konsentrert',html)
        for text in ['PB rules','Management rules','Momentum rules']:
            self.assertIn(text,html)

    def test_selected_variant_outside_top_three_still_has_rules(self):
        insider, sections = self.fixture()
        insider['maal']['Strategi']='konsentrert'
        html=render_capital_mail(Master(),[],None,sections,insider,['missing NAV'])
        self.assertIn('Valgt utenfor topp tre: konsentrert',html)
        self.assertIn('Beregningen er ufullstendig',html)
        self.assertIn('avkastning ikke tilgjengelig',html)
        self.assertNotIn('Samlet totalavkastning',html)

    def test_error_text_is_escaped_and_missing_insider_is_explicit(self):
        html=render_capital_mail(Master(),[],None,{}, {},['<unsafe>'])
        self.assertIn('&lt;unsafe&gt;',html)
        self.assertNotIn('<unsafe>',html)
        self.assertIn('Resultater mangler',html)


if __name__ == '__main__':
    unittest.main()
