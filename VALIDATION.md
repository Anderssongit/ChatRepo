# Validation — delivery finalized 17 September 2026

Checks use copies, temporary files, saved historical data and mocked network/email operations. Original Desktop source files and data were not modified.

## Checks

The extracted delivery passed **136 tests**, with **one pre-existing skipped test** (137 discovered), on 16 September. All four command-line entry points opened successfully. An isolated integration run rejected the old management export, then successfully built the complete mail and reused its saved calculation with a clearly marked synthetic management fixture. No mail was sent.

- Protected PB-ROE and Sentiment Momentum function source hashes match the original 260913 version. Their fetching and trading calculations were not edited.
- Four NAVs receive exactly 25% capital, with self-financing month-end transfers and compounded returns. Tests cover normalization, common dates, future/partial/stale endpoints, missing months, selection cutoffs, backup-file exclusion and invalid sources.
- Management tests cover a 10% price change producing 10% NAV change, continuous value at sale, missing quotes, invalid-valuation publication refusal, extreme-jump checks, accounting metadata, fresh failure diagnostics and mail risk metrics.
- Insider tests cover training-only robustness selection, adverse cost assumptions, future-result independence, weighted entry cost, manual overrides and precise rule descriptions.
- Master/mail tests cover calculation before final email, no default use of score blending, source validation, cached results, top-three ordering, selected variants outside the top three, cost disclosure, missing data and delivery errors.

## Saved insider replay

The existing merged announcements and prices from 260913_1 were copied into an isolated folder. The complete backtest stage, all five variants, both cost replays and normal statistical diagnostics were rerun without downloads or email.

| Rank | Variant | Full-history CAGR |
|---|---|---:|
| 1 | Score weighted — selected | 32.87% |
| 2 | Forfall-60 | 32.27% |
| 3 | Daily | 29.11% |

This reproduces the top-three ordering from the user's saved email. Selection uses only data through 2025-06-30. Chosen training CAGR is about 22.81% at 0.15% cost per side; its worst training half is about -9.33% annualized at 0.80% per side. All variants lose in the severe scenario. The separate statistical report says the evidence is too thin to establish an advantage. Neither result supports a proven MOAT.

`validation/insider_variants_20260916.csv` records all variants and cost scenarios. Full-history CAGR retains the original 252-session convention; training/test and cost-stress CAGR use calendar time. Full-history ranking includes training. Later results are excluded from the new selector, but the existing strategy family was previously developed using historical observations; this is not an untouched research holdout.

Corrected weighted entry costs produced nonzero holding returns: SALM +0.77%, LOKO +2.54%, ARR -0.95%, YAR +2.26% and XPLRA +0.44% in the selected historical snapshot.

## Management integration and actual data limitation

The complete 384-combination calculation was rerun with generated articles and prices. It exported the expected workbook sheets, 315 score rows and 785 equity rows. Signal dates were strictly after publication, and metric/equity ending dates agreed. Separate tests verify accounting version 2, publication validity and value continuity.

Real cached BSP.OL prices move from about 0.101440 on 2024-12-30 to 10.144007 on 2025-01-02: exactly 100 times. The guard flags these inputs and does not invent an adjustment. A real rerun with verified/repaired prices is required before publishing its return or a combined return.

Existing outputs overlap at completed month ends from 2025-08-31 through 2026-07-31. Their old management workbook correctly fails the accounting-version gate. No new real combined CAGR is claimed, and no synthetic result is supplied as a live strategy result.

## Not verified live

No live four-strategy download or SMTP delivery was run. Euronext page behavior, Yahoo repair results, language-model downloads and Gmail authentication remain unverified. Python 3.12, required libraries, Chromium, upstream input data and working mail credentials remain prerequisites. Normal running exercises these steps and reports failures explicitly.

## Repeat after setup

The ZIP includes the focused tests and their helpers:

```text
.venv\Scripts\python.exe -m unittest discover -s tests
```

Other obsolete tests from the historical source tree are excluded. Syntax and import/entry-point checks are also performed during packaging.
