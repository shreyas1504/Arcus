# Scenario Lab library build report

Events: 144. Library arrays: embeddings (144, 384), factor_paths (144, 505, 13), context (144, 4).

| File | SHA256 |
|---|---|
| library.npz | `142e4265564564350be078c53ae880de2df1d16a079124dcb1204a7d1105db0f` |
| factor_history.npz | `4254c65cceebc6408fcdd3334df27c4cd4b7f3b9c38f767246135c42caf4ad03` |
| library.json | `8ed9d1d0a28d08e137c32e6a2fcb4bfd68ce40016a1857f35b386cb1321944d7` |

## Date check
z = a single day's return divided by the standard deviation of the 60 daily returns ending on day -2, over SPY and the event's sector ETFs. Flags are for review; the build never changes or drops an event.

### Moved the day before (day -1 |z| >= 3.0 and >= 1.5x days 0..+2)
The news may have been public a day earlier than the event date. **Check each against its source.**

| Event | Date | Day -1 |z| | Max |z| days 0..+2 |
|---|---|---|---|
| aol-time-warner-merger-2000 | 2000-01-10 | 5.01 | 2.18 |

### Quiet (no single-day |z| above 1.5 on days 0..+2)
The market barely reacted. Usually the date is right and the shock was small or expected; these events still teach the engine that some shocks don't move markets.

| Event | Date | Category | Max |z| days 0..+2 |
|---|---|---|---|
| us-china-wto-deal-1999 | 1999-11-15 | trade_tariffs | 0.66 |
| fed-hike-2000-05 | 2000-05-16 | monetary_policy | 0.69 |
| gore-concedes-2000 | 2000-12-14 | election_political | 1.46 |
| microsoft-breakup-overturned-2001 | 2001-06-28 | tech_sector | 0.93 |
| china-wto-approval-2001 | 2001-11-12 | trade_tariffs | 1.47 |
| enron-bankruptcy-2001 | 2001-12-03 | financial_credit | 1.2 |
| argentina-debt-default-2001 | 2001-12-24 | fiscal_debt | 0.52 |
| northeast-blackout-2003 | 2003-08-15 | disaster_supply | 0.9 |
| google-ipo-2004 | 2004-08-19 | tech_sector | 0.95 |
| yuan-revaluation-2005 | 2005-07-21 | trade_tariffs | 1.12 |
| uk-airline-plot-2006 | 2006-08-10 | terrorism | 1.38 |
| north-korea-nuclear-test-2006 | 2006-10-09 | geopolitical_conflict | 0.23 |
| iphone-unveiled-2007 | 2007-01-09 | tech_sector | 1.49 |
| fed-mbs-purchases-2008-11 | 2008-11-25 | monetary_policy | 0.89 |
| fed-zero-rates-2008-12 | 2008-12-16 | monetary_policy | 1.0 |
| swine-flu-emergency-2009 | 2009-04-27 | pandemic_health | 0.84 |
| bank-stress-test-results-2009 | 2009-05-08 | financial_credit | 1.17 |
| us-tyre-tariffs-china-2009 | 2009-09-14 | trade_tariffs | 1.29 |
| h1n1-vaccines-approved-2009 | 2009-09-15 | pandemic_health | 1.29 |
| yuan-flexibility-2010 | 2010-06-21 | trade_tariffs | 1.08 |
| bin-laden-killed-2011 | 2011-05-02 | terrorism | 0.84 |
| thailand-floods-2011 | 2011-10-13 | disaster_supply | 1.1 |
| eu-iran-oil-embargo-2012 | 2012-01-23 | energy_oil | 0.59 |
| greek-election-may-2012 | 2012-05-07 | election_political | 0.99 |
| greek-election-june-2012 | 2012-06-18 | election_political | 1.3 |
| paris-attacks-2015 | 2015-11-16 | terrorism | 1.22 |
| brussels-bombings-2016 | 2016-03-22 | terrorism | 0.55 |
| manchester-arena-bombing-2017 | 2017-05-23 | terrorism | 0.96 |
| hurricane-harvey-2017 | 2017-08-28 | disaster_supply | 1.27 |
| cambridge-analytica-facebook-2018 | 2018-03-19 | tech_sector | 1.5 |
| fed-insurance-cut-2019 | 2019-07-31 | monetary_policy | 1.43 |
| us-china-phase-one-2019 | 2019-12-13 | trade_tariffs | 1.13 |
| opec-plus-record-cut-2020 | 2020-04-13 | energy_oil | 0.83 |
| pfizer-vaccine-efficacy-2020 | 2020-11-09 | pandemic_health | 0.97 |
| uk-mini-budget-2022 | 2022-09-23 | fiscal_debt | 1.26 |
| us-debt-ceiling-deal-2023 | 2023-05-30 | fiscal_debt | 1.02 |
| macron-snap-election-2024 | 2024-06-10 | election_political | 1.48 |
| south-korea-martial-law-2024 | 2024-12-03 | election_political | 1.42 |
| canada-mexico-china-tariffs-2025 | 2025-02-03 | trade_tariffs | 1.03 |
| nvidia-h20-export-license-2025 | 2025-04-16 | tech_sector | 1.25 |
| moodys-us-downgrade-2025 | 2025-05-19 | fiscal_debt | 1.04 |
| israel-strikes-iran-2025-06 | 2025-06-13 | geopolitical_conflict | 0.72 |
| us-strikes-iran-2025-06 | 2025-06-23 | geopolitical_conflict | 1.05 |
| israel-iran-ceasefire-2025 | 2025-06-24 | geopolitical_conflict | 0.59 |
| fed-resumes-cuts-2025-09 | 2025-09-17 | monetary_policy | 0.86 |
| us-shutdown-2025 | 2025-10-01 | fiscal_debt | 0.61 |
| fed-third-cut-2025-12 | 2025-12-10 | monetary_policy | 1.38 |

Not measurable (window runs past the data): none.

SOXX not yet listed (XLK stands in for semiconductors): 10 events.
