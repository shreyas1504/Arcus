# Scenario Lab backtest results (v2: stress test)

Plan v2 measures the claim the page makes: **if a shock like this happens, what does it do to this portfolio?** Each dev event (1999–2022) is the scenario; betas use only prices before it; the estimate uses that event's real factor moves and is compared with the stocks' real moves. Baseline: portfolio beta × the S&P path. Pass marks were fixed in PLAN.md before this run.

**Dev results are in-sample for the two tuned choices (ridge strength, stress betas). The one-time 2023+ holdout (C5) is the gate.** The forecast results from C4 are kept in `results_forecast_v1.md`.

- Events: **96** (16 skipped, mostly 1999–2002 with too few precedents); portfolios per event: 200 random + archetypes from 125 US large caps.
- Tuned on dev: alpha = 0.1, stress betas = False (by H1 MAE, then H2; all four shown below).
- Recovery-time cases with a known real recovery: 19776 across 96 events.

| Gate v2 | Pass mark | Dev result [90% CI] | |
|---|---|---|---|
| H1 · 21-day portfolio MAE, factor vs beta × S&P | ≥ 10% lower | 1.7% [1.6%, 1.8%] vs 2.0% [1.9%, 2.2%]: 19.0% [15.9%, 22.0%] lower | pass |
| H2 · holding ranking (Spearman) | ≥ 0.30 | 0.46 [0.44, 0.49] | pass |
| H3 · worst fall within 63 days, MAE | ≥ 10% lower | 1.5% [1.4%, 1.7%] vs 2.0% [1.8%, 2.2%]: 22.0% [17.0%, 26.7%] lower | pass |
| H4 · recovery time, within one bucket | ≥ 75% and exact ≥ baseline | within one 94.9% [93.4%, 96.3%]; exact 71.8% [69.4%, 74.2%] vs baseline 64.8% [61.1%, 68.5%] | pass |

H4 buckets: never fell, 1–21, 22–63, 64–126, 127–252, 253–504 trading days, not within 504. Only cases whose real recovery is known (recovered, or observed for all 504 days) are scored.

### Ridge strength and stress betas (dev)
| alpha | stress betas | H1 MAE | H2 rank |
|---|---|---|---|
| 0.1 | False | 0.0165 | 0.464 |
| 0.1 | True | 0.0176 | 0.413 |
| 1.0 | False | 0.0236 | 0.440 |
| 1.0 | True | 0.0241 | 0.399 |

### Low-confidence threshold (off-topic controls)
Threshold = max(0.5, 95th percentile of the controls' best cosine) = **0.523**. Real dev questions (event triggers) above it: 96% (median best cosine 0.643).

| Highest-scoring controls | best cosine |
|---|---|
| What is the rule of offside in football? | 0.536 |
| What if aliens land in Paris and ask for coffee? | 0.528 |
| How many moons does Jupiter have? | 0.516 |
| Why is the sky blue? | 0.516 |
| What if it rains chocolate tomorrow? | 0.512 |

### Per event (dev)
| Event | H1 MAE | baseline | H2 rank | H3 MAE | baseline | H4 within one | H4 exact | baseline exact |
|---|---|---|---|---|---|---|---|---|
| worldcom-bankruptcy-2002 | 3.2% | 4.1% | 0.12 | 3.1% | 4.5% | 97.6% | 45.1% | 35.4% |
| bali-bombing-2002 | 2.8% | 3.2% | 0.41 | — | — | 92.7% | 67.5% | 66.5% |
| sars-global-alert-2003 | 1.8% | 2.3% | 0.46 | 0.8% | 0.9% | 99.5% | 72.3% | 68.9% |
| iraq-war-begins-2003 | 1.6% | 1.7% | 0.45 | 0.8% | 0.9% | 100.0% | 85.0% | 85.0% |
| sars-contained-2003 | 1.8% | 2.1% | 0.41 | — | — | 65.5% | 31.6% | 49.5% |
| northeast-blackout-2003 | 1.4% | 1.6% | 0.45 | 1.1% | 1.1% | 84.0% | 40.8% | 25.7% |
| istanbul-bombings-2003 | 1.6% | 2.2% | 0.36 | 1.2% | 1.3% | 100.0% | 96.6% | 96.6% |
| us-steel-tariffs-repealed-2003 | 1.6% | 2.0% | 0.28 | 1.2% | 1.3% | 99.0% | 76.2% | 66.5% |
| madrid-train-bombings-2004 | 1.6% | 1.7% | 0.33 | 1.9% | 1.8% | 92.7% | 52.4% | 43.7% |
| fed-first-hike-2004 | 1.5% | 1.7% | 0.57 | 1.7% | 1.9% | 100.0% | 64.1% | 31.6% |
| google-ipo-2004 | 1.5% | 1.6% | 0.30 | 1.2% | 1.3% | 98.5% | 71.8% | 67.5% |
| bush-reelected-2004 | 1.5% | 1.6% | -0.00 | 1.2% | 1.4% | 89.3% | 88.3% | 87.4% |
| indian-ocean-tsunami-2004 | 1.2% | 1.3% | 0.46 | — | — | 83.5% | 61.2% | 62.6% |
| london-bombings-2005 | 1.7% | 2.0% | 0.23 | 1.1% | 1.3% | 81.6% | 62.6% | 61.7% |
| yuan-revaluation-2005 | 1.3% | 1.3% | 0.25 | 1.1% | 1.4% | 88.3% | 59.7% | 59.2% |
| hurricane-katrina-2005 | 1.7% | 2.0% | 0.26 | 1.0% | 1.4% | 83.5% | 74.3% | 74.3% |
| h5n1-turkey-2005 | 2.0% | 1.9% | 0.51 | 0.8% | 0.9% | 100.0% | 74.8% | 65.0% |
| israel-lebanon-war-2006 | 1.6% | 1.9% | 0.42 | 0.8% | 0.9% | 100.0% | 73.3% | 66.0% |
| uk-airline-plot-2006 | 1.5% | 1.9% | 0.41 | 0.9% | 1.1% | 99.5% | 73.3% | 37.4% |
| north-korea-nuclear-test-2006 | 1.4% | 1.5% | 0.45 | 1.0% | 1.3% | 91.7% | 56.3% | 44.7% |
| iphone-unveiled-2007 | 1.4% | 1.6% | 0.39 | 0.8% | 0.8% | 85.4% | 68.0% | 68.9% |
| bnp-paribas-funds-suspended-2007 | 1.2% | 1.3% | 0.26 | 0.8% | 0.8% | 98.1% | 63.6% | 63.6% |
| fed-discount-rate-cut-2007-08 | 1.5% | 1.6% | 0.50 | 1.4% | 1.7% | 83.0% | 77.7% | 86.9% |
| fed-emergency-cut-2008-01 | 1.9% | 2.2% | 0.52 | 1.4% | 1.8% | 93.2% | 66.5% | 63.6% |
| bear-stearns-rescue-2008 | 1.6% | 1.7% | 0.27 | 1.1% | 1.3% | 99.0% | 81.6% | 81.6% |
| russia-georgia-war-2008 | 2.2% | 2.6% | 0.65 | 3.1% | 3.3% | 100.0% | 62.1% | 19.9% |
| fannie-freddie-conservatorship-2008 | 2.6% | 2.9% | 0.58 | 3.5% | 3.5% | 99.5% | 77.2% | 84.5% |
| lehman-bankruptcy-2008 | 2.6% | 2.8% | 0.44 | 3.4% | 3.1% | 100.0% | 68.9% | 69.9% |
| aig-rescue-loan-2008 | 2.6% | 3.0% | 0.48 | 3.4% | 3.1% | 99.0% | 72.3% | 71.8% |
| house-rejects-rescue-plan-2008 | 2.4% | 3.0% | 0.55 | 3.3% | 3.0% | 99.5% | 75.2% | 74.8% |
| house-passes-rescue-plan-2008 | 2.5% | 2.6% | 0.13 | 3.1% | 3.0% | 99.0% | 59.7% | 27.2% |
| coordinated-rate-cut-2008-10 | 2.9% | 2.8% | 0.01 | 3.1% | 2.8% | 80.1% | 70.9% | 70.9% |
| fed-mbs-purchases-2008-11 | 3.1% | 3.4% | 0.31 | 3.0% | 3.4% | 77.7% | 68.4% | 68.0% |
| fed-zero-rates-2008-12 | 2.8% | 3.1% | 0.36 | 3.4% | 3.8% | 100.0% | 73.3% | 72.3% |
| fed-treasury-purchases-2009-03 | 3.5% | 4.5% | 0.77 | 1.7% | 2.2% | 100.0% | 77.7% | 76.7% |
| swine-flu-emergency-2009 | 1.6% | 1.7% | 0.42 | 1.8% | 2.3% | 100.0% | 79.6% | 79.6% |
| bank-stress-test-results-2009 | 2.0% | 2.0% | 0.22 | 1.5% | 2.0% | 99.5% | 54.9% | 38.8% |
| h1n1-pandemic-declared-2009 | 1.6% | 2.0% | 0.79 | 1.2% | 1.8% | 100.0% | 93.2% | 92.7% |
| us-tyre-tariffs-china-2009 | 1.4% | 1.5% | 0.34 | 0.9% | 1.1% | 97.6% | 63.1% | 59.7% |
| h1n1-vaccines-approved-2009 | 1.1% | 1.3% | 0.40 | 1.0% | 1.1% | 100.0% | 68.4% | 68.4% |
| iceland-ash-cloud-2010 | 1.4% | 1.5% | 0.50 | 1.9% | 2.1% | 98.1% | 50.0% | 49.0% |
| deepwater-horizon-2010 | 1.3% | 1.3% | 0.62 | 1.6% | 1.8% | 99.5% | 54.9% | 48.5% |
| greece-junk-downgrade-2010 | 1.3% | 1.3% | 0.67 | 1.8% | 2.0% | 99.5% | 52.9% | 50.5% |
| greece-first-bailout-2010 | 1.3% | 1.4% | 0.49 | 1.8% | 2.0% | 99.0% | 62.6% | 70.4% |
| flash-crash-2010 | 1.3% | 1.4% | 0.34 | 1.4% | 1.5% | 100.0% | 61.2% | 60.7% |
| uk-hung-parliament-2010 | 1.1% | 1.1% | 0.41 | 1.5% | 1.7% | 99.0% | 63.6% | 64.6% |
| eu-750bn-package-2010 | 1.3% | 1.3% | 0.39 | 1.5% | 1.7% | 100.0% | 81.1% | 81.1% |
| yuan-flexibility-2010 | 1.1% | 1.2% | 0.43 | 0.8% | 1.0% | 100.0% | 67.0% | 65.0% |
| fed-qe2-2010-11 | 1.4% | 1.6% | 0.63 | 0.8% | 0.8% | 100.0% | 81.1% | 82.0% |
| yeonpyeong-shelling-2010 | 1.3% | 1.5% | 0.55 | 0.7% | 0.9% | 100.0% | 100.0% | 100.0% |
| libya-oil-shutdowns-2011 | 1.1% | 1.3% | 0.64 | 1.0% | 1.2% | 87.9% | 78.2% | 76.7% |
| japan-earthquake-tsunami-2011 | 1.0% | 1.2% | 0.38 | 0.9% | 1.0% | 86.9% | 85.9% | 85.0% |
| bin-laden-killed-2011 | 1.2% | 1.4% | 0.62 | 1.3% | 1.4% | 64.6% | 49.5% | 39.8% |
| iea-oil-stock-release-2011 | 1.4% | 1.9% | 0.37 | 1.3% | 1.7% | 97.6% | 59.7% | 43.2% |
| us-debt-ceiling-deal-2011 | 1.5% | 1.7% | 0.75 | 1.4% | 1.6% | 97.6% | 56.3% | 29.6% |
| us-credit-downgrade-2011 | 1.6% | 1.9% | 0.69 | 1.3% | 1.5% | 100.0% | 58.3% | 55.3% |
| thailand-floods-2011 | 1.2% | 1.5% | 0.35 | 1.0% | 1.2% | 100.0% | 88.8% | 88.8% |
| eurozone-summit-deal-2011-10 | 1.1% | 1.2% | 0.49 | 1.0% | 1.0% | 100.0% | 99.5% | 99.5% |
| eu-iran-oil-embargo-2012 | 1.2% | 1.4% | 0.56 | 0.8% | 0.8% | 94.7% | 67.5% | 67.5% |
| greek-election-may-2012 | 1.1% | 1.3% | 0.76 | 1.0% | 1.2% | 96.1% | 74.3% | 73.8% |
| greek-election-june-2012 | 1.3% | 1.6% | 0.32 | 1.2% | 1.3% | 99.5% | 70.4% | 69.4% |
| draghi-whatever-it-takes-2012 | 1.2% | 1.2% | 0.57 | 0.9% | 1.1% | 96.1% | 93.7% | 93.7% |
| fed-qe3-2012-09 | 1.0% | 1.4% | 0.63 | 1.6% | 1.6% | 100.0% | 69.9% | 35.0% |
| boston-marathon-bombing-2013 | 1.7% | 1.7% | 0.41 | 1.0% | 1.1% | 99.5% | 87.4% | 86.4% |
| us-shutdown-2013 | 1.5% | 1.5% | 0.04 | 0.9% | 0.8% | 100.0% | 99.0% | 99.0% |
| fed-taper-announcement-2013 | 1.3% | 1.3% | 0.54 | 1.3% | 1.2% | 75.7% | 75.7% | 77.2% |
| crimea-intervention-2014 | 1.0% | 1.2% | 0.36 | 0.6% | 0.8% | 100.0% | 56.8% | 52.4% |
| opec-no-cut-2014 | 1.1% | 1.5% | 0.48 | 0.9% | 1.0% | 95.1% | 67.0% | 64.6% |
| greece-bailout-referendum-2015 | 1.5% | 2.4% | 0.58 | 1.4% | 1.5% | 97.6% | 73.3% | 68.9% |
| paris-attacks-2015 | 1.4% | 1.7% | 0.51 | 1.6% | 2.3% | 99.5% | 81.1% | 77.2% |
| fed-first-hike-2015 | 1.0% | 1.5% | 0.79 | 1.6% | 2.0% | 100.0% | 84.5% | 85.4% |
| brussels-bombings-2016 | 1.0% | 1.1% | 0.74 | 1.1% | 1.1% | 98.5% | 77.2% | 79.6% |
| brexit-referendum-2016 | 1.2% | 1.3% | 0.40 | 0.8% | 0.9% | 97.6% | 96.6% | 96.6% |
| manchester-arena-bombing-2017 | 1.1% | 1.5% | 0.50 | 1.2% | 1.5% | 71.4% | 54.9% | 46.6% |
| hurricane-harvey-2017 | 1.2% | 1.6% | 0.58 | 1.0% | 1.2% | 98.1% | 67.5% | 32.0% |
| cambridge-analytica-facebook-2018 | 1.2% | 1.7% | 0.51 | 0.8% | 1.1% | 92.2% | 61.2% | 47.1% |
| section-301-china-tariffs-2018 | 1.1% | 1.5% | 0.57 | 0.7% | 0.8% | 97.1% | 70.4% | 36.4% |
| italy-government-crisis-2018 | 1.1% | 1.6% | 0.67 | 1.0% | 1.2% | 96.6% | 61.2% | 50.0% |
| fed-insurance-cut-2019 | 1.8% | 2.1% | 0.70 | 1.3% | 1.8% | 100.0% | 60.2% | 60.2% |
| abqaiq-attack-2019 | 1.1% | 1.2% | 0.55 | 1.2% | 1.6% | 100.0% | 86.4% | 88.3% |
| us-china-phase-one-2019 | 1.6% | 1.6% | 0.35 | 2.7% | 4.9% | 100.0% | 69.4% | 47.1% |
| soleimani-strike-2020 | 1.5% | 1.8% | 0.67 | 3.4% | 5.8% | 100.0% | 73.8% | 24.3% |
| covid-italy-lockdown-2020 | 3.3% | 5.7% | 0.55 | 3.3% | 5.7% | 100.0% | 66.5% | 35.9% |
| fed-emergency-cut-2020-03-03 | 2.4% | 4.3% | 0.56 | 3.0% | 5.5% | 100.0% | 78.6% | 72.8% |
| who-declares-pandemic-2020 | 2.1% | 2.3% | 0.26 | 2.4% | 3.9% | 100.0% | 96.1% | 96.1% |
| fed-zero-rates-2020-03-16 | 2.0% | 2.3% | 0.36 | 2.3% | 2.8% | 100.0% | 100.0% | 100.0% |
| opec-plus-record-cut-2020 | 2.2% | 3.4% | 0.69 | 2.1% | 3.6% | 100.0% | 80.1% | 78.2% |
| pfizer-vaccine-efficacy-2020 | 3.3% | 6.3% | 0.69 | 1.7% | 2.5% | 98.1% | 93.7% | 92.7% |
| ever-given-suez-2021 | 1.3% | 2.0% | 0.38 | 1.3% | 1.2% | 98.5% | 97.1% | 96.1% |
| omicron-variant-2021 | 1.5% | 1.9% | 0.53 | 1.8% | 4.3% | 60.2% | 49.0% | 10.2% |
| russia-invades-ukraine-2022 | 2.0% | 2.5% | 0.34 | 2.2% | 4.8% | 80.6% | 55.3% | 36.4% |
| us-russian-oil-ban-2022 | 2.2% | 3.7% | 0.19 | 2.0% | 4.8% | 93.2% | 73.3% | 8.7% |
| fed-liftoff-hike-2022 | 1.4% | 1.7% | 0.48 | 2.1% | 5.4% | 88.3% | 68.4% | 68.4% |
| fed-75bp-hike-2022 | 1.4% | 3.2% | 0.65 | 0.9% | 1.7% | 99.0% | 81.6% | 79.6% |
| uk-mini-budget-2022 | 1.6% | 2.8% | 0.64 | 0.9% | 1.1% | 100.0% | 82.0% | 72.3% |
| boe-gilt-intervention-2022 | 2.2% | 3.9% | 0.67 | 0.8% | 1.0% | 100.0% | 91.7% | 90.3% |

### Caveats
- **Conditional, not a forecast:** these numbers say how well Arcus replays a scenario on a portfolio once the scenario's market path is given. They say nothing about whether or when a shock happens.
- **Survivorship bias:** the universe is today's large caps.
- **Few events:** about one hundred; the intervals are wide.

### Reproducibility
- library.npz: `142e4265564564350be078c53ae880de2df1d16a079124dcb1204a7d1105db0f`
- library.json: `8ed9d1d0a28d08e137c32e6a2fcb4bfd68ce40016a1857f35b386cb1321944d7`
- universe manifest: `0a2723a13bd4518bc767379d612973886bff57df390971f8be3e04fea572a2c4`

## Holdout (2023+): run once on 2026-11-13T20:52:46+00:00

Frozen dev settings (alpha 0.1, stress betas False); settings and holdout-event hashes verified before the run. Events scored: **32** (0 skipped: none). Recovery cases with a known real recovery: 6561 across 32 events.

| Gate v2 | Pass mark | Holdout [90% CI] | |
|---|---|---|---|
| H1 · 21-day MAE vs beta × S&P | ≥ 10% lower | 1.6% [1.5%, 1.7%] vs 2.2% [1.9%, 2.4%]: 24.4% [19.6%, 28.9%] lower | pass |
| H2 · holding ranking | ≥ 0.30 | 0.47 [0.42, 0.51] | pass |
| H3 · 63-day worst fall MAE | ≥ 10% lower | 1.5% [1.4%, 1.6%] vs 2.0% [1.8%, 2.2%]: 23.2% [19.1%, 26.9%] lower | pass |
| H4 · recovery within one bucket | ≥ 75% and exact ≥ baseline | 93.1% [90.5%, 95.3%]; exact 70.5% [66.0%, 74.8%] vs 59.4% [51.4%, 66.7%] | pass |
| H5 · H1–H3 agree with dev | must match | | pass |

**Passed.** The engine may serve answers; recovery is shown for all holdings.

| Event | H1 MAE | baseline | H2 rank | H3 MAE | baseline | H4 within one | H4 exact | baseline exact |
|---|---|---|---|---|---|---|---|---|
| svb-closure-2023 | 1.7% | 2.3% | 0.60 | 2.3% | 3.2% | 91.7% | 80.1% | 79.6% |
| svb-depositor-backstop-2023 | 1.1% | 1.9% | 0.59 | 2.0% | 2.9% | 94.2% | 74.3% | 71.8% |
| ubs-credit-suisse-rescue-2023 | 1.1% | 1.6% | 0.47 | 1.9% | 3.1% | 79.6% | 58.3% | 50.5% |
| fed-hike-amid-bank-stress-2023 | 1.0% | 1.3% | 0.39 | 1.8% | 2.8% | 98.1% | 77.2% | 76.7% |
| opec-plus-surprise-cut-2023 | 1.3% | 1.7% | 0.47 | 1.9% | 3.1% | 98.1% | 71.4% | 14.6% |
| first-republic-failure-2023 | 2.1% | 4.1% | 0.58 | 1.7% | 2.5% | 98.5% | 74.8% | 21.4% |
| who-ends-covid-emergency-2023 | 1.9% | 3.1% | 0.65 | 1.3% | 1.6% | 95.1% | 54.9% | 35.9% |
| nvidia-ai-guidance-2023 | 1.4% | 1.7% | 0.63 | 1.4% | 1.7% | 97.1% | 67.0% | 34.0% |
| us-debt-ceiling-deal-2023 | 1.3% | 1.5% | 0.46 | 1.4% | 1.6% | 96.1% | 90.3% | 90.3% |
| fitch-us-downgrade-2023 | 1.3% | 1.7% | 0.40 | 1.5% | 2.0% | 100.0% | 91.3% | 91.3% |
| hamas-attack-israel-2023 | 1.8% | 1.9% | 0.24 | 0.9% | 1.0% | 100.0% | 85.4% | 85.4% |
| taiwan-earthquake-2024 | 1.5% | 1.5% | 0.41 | 1.4% | 1.4% | 97.6% | 60.7% | 60.7% |
| iran-strikes-israel-2024-04 | 1.3% | 1.8% | 0.49 | 1.5% | 1.5% | 97.1% | 80.6% | 80.6% |
| macron-snap-election-2024 | 1.5% | 2.7% | 0.42 | 1.4% | 2.0% | 95.1% | 60.2% | 61.2% |
| crowdstrike-outage-2024 | 2.0% | 2.2% | 0.47 | 1.2% | 1.4% | 94.7% | 56.3% | 54.9% |
| boj-rate-hike-2024 | 1.6% | 1.9% | 0.22 | 0.9% | 1.2% | 98.5% | 87.9% | 87.4% |
| mpox-global-emergency-2024 | 1.3% | 1.7% | 0.31 | 1.1% | 1.5% | 93.2% | 67.0% | 29.1% |
| fed-50bp-cut-2024 | 1.3% | 1.4% | 0.32 | 2.0% | 3.3% | 82.5% | 42.7% | 38.3% |
| south-korea-martial-law-2024 | 2.1% | 3.6% | 0.08 | 2.1% | 2.4% | 60.2% | 52.9% | 34.5% |
| canada-mexico-china-tariffs-2025 | 1.7% | 2.3% | 0.47 | 2.1% | 2.1% | 99.0% | 83.0% | 82.0% |
| liberation-day-tariffs-2025 | 2.1% | 3.7% | 0.31 | 1.4% | 2.6% | 98.1% | 73.8% | 8.7% |
| reciprocal-tariff-pause-2025 | 1.8% | 2.0% | 0.79 | 0.8% | 1.3% | 99.0% | 99.0% | 99.0% |
| nvidia-h20-export-license-2025 | 2.1% | 2.6% | 0.83 | 0.7% | 0.8% | 99.5% | 98.1% | 97.1% |
| us-china-geneva-truce-2025 | 1.4% | 1.3% | 0.67 | 1.5% | 1.9% | 95.1% | 71.4% | 67.0% |
| moodys-us-downgrade-2025 | 1.6% | 1.8% | 0.46 | 1.5% | 1.9% | 98.1% | 85.4% | 85.4% |
| israel-strikes-iran-2025-06 | 1.3% | 1.6% | 0.55 | 1.6% | 2.1% | 98.5% | 81.1% | 81.1% |
| us-strikes-iran-2025-06 | 1.5% | 1.8% | 0.53 | 1.6% | 2.0% | 85.0% | 73.8% | 67.5% |
| israel-iran-ceasefire-2025 | 1.6% | 1.7% | 0.37 | 1.7% | 2.1% | 78.6% | 62.1% | 51.5% |
| fed-resumes-cuts-2025-09 | 2.1% | 2.7% | 0.48 | 1.6% | 1.5% | 82.9% | 49.3% | 45.9% |
| us-shutdown-2025 | 2.1% | 2.5% | 0.37 | 1.4% | 1.3% | 90.8% | 47.1% | 43.2% |
| fed-third-cut-2025-12 | 1.9% | 3.3% | 0.51 | 1.8% | 2.4% | 90.3% | 53.4% | 8.7% |
| fed-hike-reversal-2026-09 | 2.2% | 2.4% | 0.41 | — | — | 96.0% | 44.3% | 64.8% |
