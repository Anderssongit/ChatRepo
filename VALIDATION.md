# Validation — 20 September 2026

This branch implements simulated trades and email recommendations, not broker
orders. Four strategy families and 25% capital per strategy are retained.
Default calculations and training-only variant selection use zero trading costs.
The active implementation lives in the root, without runtime source patches.

## Executed checks

- All root Python files compiled successfully.
- The final full suite passed **161 tests, with no failures or skips**, using
  Python 3.12, pandas 2.3.3, yfinance 0.2.66 and installed Playwright/Chromium.
  This includes PB momentum, insider quote availability, and a local browser
  fixture that verifies article endpoint discovery and subsequent retrieval.
- Tests exercise real temporary Excel writes/reads, ticker identity, future and
  unscored article exclusion, same-day article ordering, cached-source labels,
  failures, HTML escaping, portfolio accounting, weighted entry costs,
  training/heldout separation, stale quotes, price jumps and completed months.
- Mocked master integration calculates before email, saves the current-policy
  completion manifest, and reuses only validated outputs. No real email was sent.
- The test runner blocks Python remote sockets and SMTP. Browser fixture tests
  use local pages. No real email was sent during validation.
- Separate live smoke checks downloaded a valid Euronext list containing **294
  companies**, and **13 daily observations for EQNR.OL** from Yahoo (latest
  observation returned: 2026-09-16). This proves these sample requests worked;
  it does not establish complete coverage for every strategy input.

The PB-ROE and Sentiment Momentum fingerprints intentionally changed to protect
the corrected bodies. Changes include input paths, observed fundamental
availability, completed-month dates, prior-observation price decisions,
cash/weight accounting and price validation. The strategy families remain.

## Verification limits

The full production download, TradingView and Euronext article traversal,
FinBERT model download and SMTP delivery have not been verified here. Synthetic
tests cannot establish full provider coverage or account authentication.
Run SETUP.cmd and then RUN_ALL.cmd --mail-kladd on the target machine.

No new real combined CAGR or profitable live result is claimed. Historical
figures from earlier deliveries do not validate the changed execution policy;
older strategy exports require regeneration.

## Conservative behaviour

- Reshaping a cached file never counts as a fresh download.
- Required source failures prevent a new complete portfolio report.
- Power-of-ten price patterns do not justify automatic historical rescaling.
- Insider trades require a genuine quote on their execution date. Missing
  quotes delay sales and rebalancing; marks may carry for at most five sessions,
  after which valuation fails as incomplete instead of assuming a total loss.
- PB-ROE ratios are usable from their recorded observation date. A fresh
  installation may lack enough point-in-time observations for a historical
  PB-ROE/four-strategy return. Absent publication timestamps are not invented.
- Current company lists do not prove historical membership or complete delisted
  coverage. Zero trading cost does not establish actual fill feasibility.

## Reproduce

```text
python -m pip install -r requirements-test.txt
python -m playwright install chromium
python run_tests.py
```

The optional GitHub Actions template is ci-tests.yml.example; local validation
uses the commands above. Active tests are root test_*.py files;
the dated patch-test directory is historical reference, not the current suite.
