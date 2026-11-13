# Scenario Lab backtest results

## Dev split (1999–2022): tuning and calibration

**These dev numbers are in-sample for the chosen settings and for the 80% width, so they flatter the method. The honest test is the one-time 2023+ holdout (C5).**

- Events scored: **96**; cases (event × portfolio): 19776. Skipped: 16 (fewer than 15 earlier precedents, mostly 1999–2002).
- Portfolios per event: 200 random equal-weight (5–15 stocks) plus archetypes, from a universe of 125 US large caps.
- Settings grid: 360 combinations; chosen by lowest event-weighted MAE.
- Chosen settings: `{"alpha": 1.0, "category_bonus": 0.0, "nature_penalty": 0.3, "similarity_threshold": 0.5, "stress_only": false, "top_k": 5, "use_actual": false}`
- Calibrated q_hat (80% width multiplier): **7.332**

| Metric (event-weighted, 90% bootstrap CI) | Tuned | Untuned defaults | No-parse fallback |
|---|---|---|---|
| G1 · 80% range coverage (target 75–85%) | 80.0% [75.3%, 84.5%] | 80.0% [75.7%, 84.1%] | 81.8% [77.3%, 86.1%] |
| G2 · width ÷ random-window width (≤ 0.85) | 1.72 [1.45, 2.09] | 2.14 [1.96, 2.24] | 2.01 [1.81, 2.26] |
| Typical-outcome MAE | 5.6% [4.7%, 6.6%] | 6.1% [5.2%, 7.2%] | 5.7% [4.7%, 6.6%] |
| Best baseline MAE | 5.4% [4.5%, 6.4%] | | |
| G3 · MAE improvement vs best baseline (≥ 10%) | -3.2% [-10.4%, 2.6%] | -13.1% [-22.6%, -6.0%] | -4.3% [-12.5%, 2.3%] |
| G4 · rank correlation across stocks (≥ 0.30) | 0.03 [-0.02, 0.07] | 0.01 [-0.02, 0.04] | 0.02 [-0.03, 0.07] |
| Low-confidence share | 1.0% [0.0%, 3.1%] | 1.0% [0.0%, 3.1%] | 1.0% [0.0%, 3.1%] |

Baselines (MAE): 1 · average of all past events 5.5% [4.6%, 6.6%]; 2 · beta × category-average S&P move 6.0% [5.0%, 7.1%]; 3 · random 21-day window 5.4% [4.5%, 6.5%]. Baseline 4 (language model guessing) is run on the holdout only.

Gate preview on dev (not the gate; the holdout is): G1_coverage_75_85 pass, G2_width_ratio_le_0.85 FAIL, G3_mae_10pct_better FAIL, G4_rank_corr_ge_0.30 FAIL

### Five best settings on dev MAE
| MAE | settings |
|---|---|
| 0.0560 | `{"alpha": 1.0, "category_bonus": 0.0, "nature_penalty": 0.3, "similarity_threshold": 0.5, "stress_only": false, "top_k": 5, "use_actual": false}` |
| 0.0560 | `{"alpha": 1.0, "category_bonus": 0.0, "nature_penalty": 0.3, "similarity_threshold": 0.5, "stress_only": true, "top_k": 5, "use_actual": false}` |
| 0.0562 | `{"alpha": 1.0, "category_bonus": 0.0, "nature_penalty": 0.0, "similarity_threshold": 0.65, "stress_only": false, "top_k": 5, "use_actual": false}` |
| 0.0562 | `{"alpha": 1.0, "category_bonus": 0.0, "nature_penalty": 0.0, "similarity_threshold": 0.65, "stress_only": true, "top_k": 5, "use_actual": false}` |
| 0.0564 | `{"alpha": 1.0, "category_bonus": 0.0, "nature_penalty": 0.1, "similarity_threshold": 0.5, "stress_only": true, "top_k": 5, "use_actual": false}` |

### Coverage by category (dev)
| Category | Events | Coverage | MAE |
|---|---|---|---|
| disaster_supply | 8 | 94% | 3.5% |
| election_political | 6 | 85% | 4.0% |
| energy_oil | 8 | 88% | 3.6% |
| financial_credit | 11 | 45% | 12.9% |
| fiscal_debt | 9 | 90% | 4.6% |
| geopolitical_conflict | 8 | 88% | 3.2% |
| monetary_policy | 17 | 83% | 6.3% |
| pandemic_health | 10 | 74% | 8.3% |
| tech_sector | 3 | 63% | 3.3% |
| terrorism | 10 | 85% | 2.8% |
| trade_tariffs | 6 | 86% | 3.2% |

### Per event (dev, tuned settings)
| Event | Coverage | MAE | Best baseline MAE | Rank | Low conf. | Precedents used |
|---|---|---|---|---|---|---|
| worldcom-bankruptcy-2002 | 27% | 10.0% | 9.1% | -0.40 |  | enron-bankruptcy-2001, argentina-debt-default-2001, china-wto-approval-2001, us-china-wto-deal-1999, microsoft-breakup-overturned-2001 |
| bali-bombing-2002 | 54% | 6.8% | 5.4% | 0.17 | yes | sept-11-attacks-2001, afghanistan-campaign-2001, fed-hike-2000-05, enron-bankruptcy-2001, opec-output-cut-1999 |
| sars-global-alert-2003 | 16% | 6.2% | 5.8% | 0.21 |  | afghanistan-campaign-2001, bali-bombing-2002 |
| iraq-war-begins-2003 | 100% | 2.8% | 1.8% | 0.22 |  | afghanistan-campaign-2001, sept-11-attacks-2001, bali-bombing-2002, us-election-contested-2000, fed-hike-2000-05 |
| sars-contained-2003 | 100% | 1.7% | 1.8% | 0.34 |  | fed-post-911-cut-2001, sars-global-alert-2003, bali-bombing-2002, sept-11-attacks-2001, afghanistan-campaign-2001 |
| northeast-blackout-2003 | 96% | 1.8% | 1.6% | 0.24 |  | sept-11-attacks-2001, afghanistan-campaign-2001, opec-output-cut-1999, fed-post-911-cut-2001, microsoft-breakup-overturned-2001 |
| istanbul-bombings-2003 | 17% | 5.9% | 3.2% | -0.25 |  | sept-11-attacks-2001, bali-bombing-2002, fed-post-911-cut-2001 |
| us-steel-tariffs-repealed-2003 | 33% | 5.7% | 3.3% | -0.25 |  | us-china-wto-deal-1999, china-wto-approval-2001, gore-concedes-2000, fed-post-911-cut-2001, microsoft-breakup-overturned-2001 |
| madrid-train-bombings-2004 | 97% | 1.6% | 1.5% | 0.18 |  | bali-bombing-2002, istanbul-bombings-2003, northeast-blackout-2003, sept-11-attacks-2001 |
| fed-first-hike-2004 | 87% | 3.3% | 4.4% | -0.42 |  | fed-hike-2000-05, fed-post-911-cut-2001, fed-intermeeting-cut-2001-01 |
| google-ipo-2004 | 83% | 2.5% | 1.9% | 0.23 |  | enron-bankruptcy-2001 |
| bush-reelected-2004 | 70% | 5.5% | 3.7% | 0.06 |  | gore-concedes-2000, us-steel-tariffs-repealed-2003, fed-post-911-cut-2001, us-china-wto-deal-1999, sars-contained-2003 |
| indian-ocean-tsunami-2004 | 98% | 6.0% | 4.7% | -0.39 |  | bali-bombing-2002, northeast-blackout-2003, sars-global-alert-2003, istanbul-bombings-2003, sept-11-attacks-2001 |
| london-bombings-2005 | 100% | 3.1% | 2.4% | 0.26 |  | istanbul-bombings-2003, sept-11-attacks-2001, madrid-train-bombings-2004, bali-bombing-2002, indian-ocean-tsunami-2004 |
| yuan-revaluation-2005 | 100% | 2.1% | 2.4% | -0.24 |  | us-china-wto-deal-1999, china-wto-approval-2001, us-steel-tariffs-repealed-2003, fed-post-911-cut-2001, argentina-debt-default-2001 |
| hurricane-katrina-2005 | 91% | 3.4% | 1.7% | -0.11 |  | indian-ocean-tsunami-2004, northeast-blackout-2003, sept-11-attacks-2001, bali-bombing-2002 |
| h5n1-turkey-2005 | 97% | 2.9% | 2.3% | 0.40 |  | sars-global-alert-2003, afghanistan-campaign-2001, indian-ocean-tsunami-2004, istanbul-bombings-2003, bali-bombing-2002 |
| israel-lebanon-war-2006 | 57% | 3.7% | 2.6% | -0.14 |  | afghanistan-campaign-2001 |
| uk-airline-plot-2006 | 93% | 1.9% | 1.8% | 0.16 |  | london-bombings-2005, istanbul-bombings-2003, sept-11-attacks-2001, northeast-blackout-2003, afghanistan-campaign-2001 |
| north-korea-nuclear-test-2006 | 100% | 1.6% | 1.5% | 0.07 |  | intel-revenue-warning-2000, sars-global-alert-2003, northeast-blackout-2003, indian-ocean-tsunami-2004, opec-output-cut-1999 |
| iphone-unveiled-2007 | 35% | 4.7% | 1.9% | -0.22 |  | aol-time-warner-merger-2000 |
| bnp-paribas-funds-suspended-2007 | 98% | 2.2% | 4.2% | 0.00 |  | argentina-debt-default-2001, intel-revenue-warning-2000, microsoft-talks-collapse-2000, enron-bankruptcy-2001, opec-output-cut-1999 |
| fed-discount-rate-cut-2007-08 | 69% | 6.0% | 3.1% | -0.04 |  | fed-intermeeting-cut-2001-01, fed-post-911-cut-2001, yuan-revaluation-2005, fed-hike-2000-05, fed-first-hike-2004 |
| fed-emergency-cut-2008-01 | 90% | 3.2% | 2.3% | -0.05 |  | fed-intermeeting-cut-2001-01, fed-post-911-cut-2001, fed-discount-rate-cut-2007-08, yuan-revaluation-2005, fed-hike-2000-05 |
| bear-stearns-rescue-2008 | 94% | 2.2% | 1.5% | -0.02 |  | fed-discount-rate-cut-2007-08, fed-intermeeting-cut-2001-01, google-ipo-2004, fed-post-911-cut-2001, china-wto-approval-2001 |
| russia-georgia-war-2008 | 92% | 2.3% | 2.4% | 0.07 |  | iraq-war-begins-2003, argentina-debt-default-2001, afghanistan-campaign-2001 |
| fannie-freddie-conservatorship-2008 | 0% | 16.4% | 15.3% | 0.03 |  | bear-stearns-rescue-2008, fed-first-hike-2004, fed-hike-2000-05 |
| lehman-bankruptcy-2008 | 24% | 20.6% | 20.2% | -0.27 |  | enron-bankruptcy-2001, worldcom-bankruptcy-2002, bnp-paribas-funds-suspended-2007, argentina-debt-default-2001, opec-output-cut-1999 |
| aig-rescue-loan-2008 | 0% | 28.0% | 26.9% | -0.37 |  | fed-emergency-cut-2008-01, bear-stearns-rescue-2008, fed-intermeeting-cut-2001-01, fed-post-911-cut-2001, fed-discount-rate-cut-2007-08 |
| house-rejects-rescue-plan-2008 | 12% | 28.3% | 31.0% | 0.06 |  | bnp-paribas-funds-suspended-2007, us-election-contested-2000, microsoft-talks-collapse-2000, fed-emergency-cut-2008-01, fed-intermeeting-cut-2001-01 |
| house-passes-rescue-plan-2008 | 3% | 14.4% | 13.6% | -0.15 |  | bear-stearns-rescue-2008, fed-emergency-cut-2008-01, fed-discount-rate-cut-2007-08, microsoft-breakup-overturned-2001, fed-post-911-cut-2001 |
| coordinated-rate-cut-2008-10 | 92% | 6.5% | 5.6% | -0.03 |  | fed-discount-rate-cut-2007-08, fed-intermeeting-cut-2001-01, fed-post-911-cut-2001, fed-emergency-cut-2008-01, yuan-revaluation-2005 |
| fed-mbs-purchases-2008-11 | 70% | 3.5% | 3.5% | 0.20 |  | bear-stearns-rescue-2008, fed-discount-rate-cut-2007-08, fed-post-911-cut-2001, fed-emergency-cut-2008-01, fed-intermeeting-cut-2001-01 |
| fed-zero-rates-2008-12 | 97% | 4.0% | 3.0% | -0.13 |  | fed-emergency-cut-2008-01, fed-intermeeting-cut-2001-01, fed-post-911-cut-2001, fed-discount-rate-cut-2007-08, aig-rescue-loan-2008 |
| fed-treasury-purchases-2009-03 | 71% | 14.1% | 12.7% | -0.41 |  | aig-rescue-loan-2008, fed-mbs-purchases-2008-11, bear-stearns-rescue-2008, fed-discount-rate-cut-2007-08, fed-post-911-cut-2001 |
| swine-flu-emergency-2009 | 99% | 3.5% | 2.0% | -0.11 |  | sars-global-alert-2003, h5n1-turkey-2005, indian-ocean-tsunami-2004, afghanistan-campaign-2001, sars-contained-2003 |
| bank-stress-test-results-2009 | 97% | 5.5% | 2.6% | -0.05 |  | aig-rescue-loan-2008, fed-mbs-purchases-2008-11, coordinated-rate-cut-2008-10, fed-zero-rates-2008-12, bear-stearns-rescue-2008 |
| h1n1-pandemic-declared-2009 | 96% | 8.3% | 6.0% | -0.22 |  | sars-global-alert-2003, h5n1-turkey-2005, indian-ocean-tsunami-2004, afghanistan-campaign-2001, fed-hike-2000-05 |
| us-tyre-tariffs-china-2009 | 96% | 1.8% | 1.7% | -0.02 |  | iraq-war-begins-2003, us-steel-tariffs-repealed-2003, us-china-wto-deal-1999, yuan-revaluation-2005, china-wto-approval-2001 |
| h1n1-vaccines-approved-2009 | 100% | 1.3% | 1.2% | -0.13 |  | sars-contained-2003, us-steel-tariffs-repealed-2003, google-ipo-2004, china-wto-approval-2001, aig-rescue-loan-2008 |
| iceland-ash-cloud-2010 | 72% | 5.2% | 3.7% | -0.16 |  | uk-airline-plot-2006, london-bombings-2005, indian-ocean-tsunami-2004, istanbul-bombings-2003, northeast-blackout-2003 |
| deepwater-horizon-2010 | 42% | 7.7% | 7.2% | -0.27 |  | hurricane-katrina-2005, indian-ocean-tsunami-2004, northeast-blackout-2003, bali-bombing-2002 |
| greece-junk-downgrade-2010 | 23% | 8.4% | 9.2% | 0.34 |  | intel-revenue-warning-2000, bnp-paribas-funds-suspended-2007, argentina-debt-default-2001, opec-output-cut-1999, coordinated-rate-cut-2008-10 |
| greece-first-bailout-2010 | 100% | 6.0% | 7.5% | 0.39 |  | aig-rescue-loan-2008, coordinated-rate-cut-2008-10, house-passes-rescue-plan-2008, china-wto-approval-2001, bear-stearns-rescue-2008 |
| flash-crash-2010 | 54% | 5.7% | 1.4% | 0.19 |  | lehman-bankruptcy-2008, bnp-paribas-funds-suspended-2007, sept-11-attacks-2001, enron-bankruptcy-2001, intel-revenue-warning-2000 |
| uk-hung-parliament-2010 | 100% | 1.7% | 4.9% | 0.27 |  | house-rejects-rescue-plan-2008, us-election-contested-2000, bush-reelected-2004, house-passes-rescue-plan-2008, gore-concedes-2000 |
| eu-750bn-package-2010 | 100% | 1.6% | 2.8% | 0.10 |  | house-passes-rescue-plan-2008, aig-rescue-loan-2008, coordinated-rate-cut-2008-10, fed-mbs-purchases-2008-11, fed-treasury-purchases-2009-03 |
| yuan-flexibility-2010 | 100% | 2.4% | 3.2% | -0.30 |  | yuan-revaluation-2005, coordinated-rate-cut-2008-10, fed-zero-rates-2008-12, fed-treasury-purchases-2009-03, fed-discount-rate-cut-2007-08 |
| fed-qe2-2010-11 | 100% | 3.0% | 1.7% | 0.02 |  | fed-treasury-purchases-2009-03, fed-mbs-purchases-2008-11, aig-rescue-loan-2008, fed-emergency-cut-2008-01, fed-post-911-cut-2001 |
| yeonpyeong-shelling-2010 | 100% | 4.0% | 3.8% | 0.02 |  | indian-ocean-tsunami-2004, north-korea-nuclear-test-2006, london-bombings-2005, israel-lebanon-war-2006, istanbul-bombings-2003 |
| libya-oil-shutdowns-2011 | 100% | 1.9% | 2.1% | 0.45 |  | opec-output-cut-1999, intel-revenue-warning-2000, iceland-ash-cloud-2010, flash-crash-2010, uk-airline-plot-2006 |
| japan-earthquake-tsunami-2011 | 100% | 1.7% | 1.5% | 0.18 |  | indian-ocean-tsunami-2004, northeast-blackout-2003, yeonpyeong-shelling-2010, iceland-ash-cloud-2010, north-korea-nuclear-test-2006 |
| bin-laden-killed-2011 | 100% | 1.9% | 1.3% | -0.39 |  | us-steel-tariffs-repealed-2003, fed-post-911-cut-2001, sars-contained-2003, bush-reelected-2004, gore-concedes-2000 |
| iea-oil-stock-release-2011 | 100% | 4.8% | 1.9% | -0.08 |  | fed-treasury-purchases-2009-03, us-china-wto-deal-1999, greece-first-bailout-2010, house-passes-rescue-plan-2008, fed-post-911-cut-2001 |
| us-debt-ceiling-deal-2011 | 100% | 2.5% | 1.8% | 0.62 |  | house-passes-rescue-plan-2008, coordinated-rate-cut-2008-10, greece-first-bailout-2010, us-china-wto-deal-1999, yuan-flexibility-2010 |
| us-credit-downgrade-2011 | 100% | 4.1% | 2.7% | 0.55 |  | greece-junk-downgrade-2010, flash-crash-2010, bnp-paribas-funds-suspended-2007, fed-discount-rate-cut-2007-08, fed-emergency-cut-2008-01 |
| thailand-floods-2011 | 96% | 4.9% | 1.8% | 0.13 |  | libya-oil-shutdowns-2011, indian-ocean-tsunami-2004, iceland-ash-cloud-2010, japan-earthquake-tsunami-2011, northeast-blackout-2003 |
| eurozone-summit-deal-2011-10 | 98% | 3.0% | 1.2% | 0.22 |  | greece-first-bailout-2010, eu-750bn-package-2010, coordinated-rate-cut-2008-10, fed-intermeeting-cut-2001-01, fed-post-911-cut-2001 |
| eu-iran-oil-embargo-2012 | 85% | 5.3% | 1.8% | -0.18 |  | opec-output-cut-1999, libya-oil-shutdowns-2011, iceland-ash-cloud-2010, argentina-debt-default-2001, eu-750bn-package-2010 |
| greek-election-may-2012 | 100% | 2.0% | 3.1% | 0.73 |  | greece-junk-downgrade-2010, uk-hung-parliament-2010, house-rejects-rescue-plan-2008, flash-crash-2010, greece-first-bailout-2010 |
| greek-election-june-2012 | 97% | 5.2% | 1.5% | 0.30 |  | greece-first-bailout-2010, eu-750bn-package-2010, eurozone-summit-deal-2011-10, uk-hung-parliament-2010 |
| draghi-whatever-it-takes-2012 | 36% | 8.6% | 3.2% | -0.55 |  | greece-first-bailout-2010, eurozone-summit-deal-2011-10, eu-750bn-package-2010, yuan-flexibility-2010, coordinated-rate-cut-2008-10 |
| fed-qe3-2012-09 | 100% | 2.7% | 1.5% | -0.00 |  | fed-treasury-purchases-2009-03, fed-qe2-2010-11, fed-mbs-purchases-2008-11, aig-rescue-loan-2008, bear-stearns-rescue-2008 |
| boston-marathon-bombing-2013 | 95% | 1.9% | 2.0% | 0.25 |  | istanbul-bombings-2003, madrid-train-bombings-2004, london-bombings-2005, bali-bombing-2002, sept-11-attacks-2001 |
| us-shutdown-2013 | 100% | 6.9% | 4.0% | 0.14 |  | house-rejects-rescue-plan-2008, flash-crash-2010, northeast-blackout-2003, microsoft-talks-collapse-2000, thailand-floods-2011 |
| fed-taper-announcement-2013 | 98% | 6.1% | 2.0% | -0.19 |  | fed-hike-2000-05, fed-first-hike-2004, us-credit-downgrade-2011, greece-junk-downgrade-2010, flash-crash-2010 |
| crimea-intervention-2014 | 100% | 2.6% | 1.2% | -0.22 |  | russia-georgia-war-2008, lehman-bankruptcy-2008, eu-iran-oil-embargo-2012, greece-first-bailout-2010, eu-750bn-package-2010 |
| opec-no-cut-2014 | 86% | 2.1% | 1.4% | -0.15 |  | opec-output-cut-1999, us-debt-ceiling-deal-2011, iea-oil-stock-release-2011 |
| greece-bailout-referendum-2015 | 100% | 6.4% | 2.2% | 0.47 |  | greek-election-may-2012, house-rejects-rescue-plan-2008, flash-crash-2010, greece-junk-downgrade-2010, us-election-contested-2000 |
| paris-attacks-2015 | 90% | 2.2% | 1.7% | -0.31 |  | bali-bombing-2002, istanbul-bombings-2003, london-bombings-2005, madrid-train-bombings-2004, boston-marathon-bombing-2013 |
| fed-first-hike-2015 | 99% | 8.4% | 7.8% | 0.32 |  | fed-hike-2000-05, fed-first-hike-2004, fed-taper-announcement-2013, us-shutdown-2013, flash-crash-2010 |
| brussels-bombings-2016 | 100% | 1.3% | 1.2% | 0.23 |  | madrid-train-bombings-2004, london-bombings-2005, istanbul-bombings-2003, uk-airline-plot-2006, boston-marathon-bombing-2013 |
| brexit-referendum-2016 | 45% | 7.4% | 1.9% | 0.28 |  | greece-bailout-referendum-2015, uk-hung-parliament-2010, greek-election-may-2012, us-election-contested-2000, opec-output-cut-1999 |
| manchester-arena-bombing-2017 | 100% | 1.5% | 1.4% | 0.12 |  | boston-marathon-bombing-2013, istanbul-bombings-2003, bali-bombing-2002, deepwater-horizon-2010, uk-airline-plot-2006 |
| hurricane-harvey-2017 | 100% | 2.6% | 2.2% | -0.03 |  | hurricane-katrina-2005, deepwater-horizon-2010, northeast-blackout-2003, japan-earthquake-tsunami-2011, indian-ocean-tsunami-2004 |
| cambridge-analytica-facebook-2018 | 70% | 2.7% | 1.6% | -0.42 |  | uk-airline-plot-2006, bank-stress-test-results-2009 |
| section-301-china-tariffs-2018 | 96% | 2.6% | 1.8% | 0.11 |  | us-tyre-tariffs-china-2009, iraq-war-begins-2003, fed-taper-announcement-2013, house-rejects-rescue-plan-2008, sept-11-attacks-2001 |
| italy-government-crisis-2018 | 99% | 2.1% | 1.5% | 0.47 |  | greece-bailout-referendum-2015, bnp-paribas-funds-suspended-2007, flash-crash-2010, argentina-debt-default-2001, libya-oil-shutdowns-2011 |
| fed-insurance-cut-2019 | 89% | 6.6% | 4.3% | -0.37 |  | fed-emergency-cut-2008-01, fed-zero-rates-2008-12, fed-intermeeting-cut-2001-01, fed-post-911-cut-2001, fed-discount-rate-cut-2007-08 |
| abqaiq-attack-2019 | 100% | 1.6% | 1.9% | 0.02 |  | libya-oil-shutdowns-2011, yeonpyeong-shelling-2010, istanbul-bombings-2003, deepwater-horizon-2010, israel-lebanon-war-2006 |
| us-china-phase-one-2019 | 92% | 4.6% | 2.5% | 0.15 |  | us-china-wto-deal-1999, yuan-flexibility-2010, yuan-revaluation-2005, us-debt-ceiling-deal-2011, china-wto-approval-2001 |
| soleimani-strike-2020 | 90% | 2.4% | 1.8% | 0.19 |  | iraq-war-begins-2003, manchester-arena-bombing-2017, afghanistan-campaign-2001, abqaiq-attack-2019, us-tyre-tariffs-china-2009 |
| covid-italy-lockdown-2020 | 0% | 38.4% | 35.0% | 0.29 |  | sars-global-alert-2003, h5n1-turkey-2005, swine-flu-emergency-2009, h1n1-pandemic-declared-2009, iceland-ash-cloud-2010 |
| fed-emergency-cut-2020-03-03 | 38% | 16.7% | 18.2% | 0.41 |  | fed-insurance-cut-2019, fed-emergency-cut-2008-01, fed-intermeeting-cut-2001-01, fed-post-911-cut-2001, fed-zero-rates-2008-12 |
| who-declares-pandemic-2020 | 83% | 7.4% | 4.3% | 0.14 |  | swine-flu-emergency-2009, h1n1-pandemic-declared-2009, sars-global-alert-2003, h5n1-turkey-2005, afghanistan-campaign-2001 |
| fed-zero-rates-2020-03-16 | 88% | 7.7% | 4.4% | 0.27 |  | fed-insurance-cut-2019, fed-emergency-cut-2008-01, fed-zero-rates-2008-12, fed-post-911-cut-2001, fed-intermeeting-cut-2001-01 |
| opec-plus-record-cut-2020 | 98% | 3.1% | 3.0% | 0.25 |  | iea-oil-stock-release-2011, us-debt-ceiling-deal-2011, eu-750bn-package-2010, us-china-wto-deal-1999, us-china-phase-one-2019 |
| pfizer-vaccine-efficacy-2020 | 54% | 10.5% | 10.4% | -0.51 |  | h1n1-vaccines-approved-2009, sars-contained-2003, fed-zero-rates-2020-03-16, fed-emergency-cut-2020-03-03, aig-rescue-loan-2008 |
| ever-given-suez-2021 | 100% | 2.2% | 3.4% | -0.22 |  | london-bombings-2005, indian-ocean-tsunami-2004, yeonpyeong-shelling-2010, bali-bombing-2002, deepwater-horizon-2010 |
| omicron-variant-2021 | 100% | 2.3% | 1.8% | 0.15 |  | who-declares-pandemic-2020, sars-global-alert-2003, h1n1-pandemic-declared-2009, swine-flu-emergency-2009, h5n1-turkey-2005 |
| russia-invades-ukraine-2022 | 63% | 6.3% | 5.4% | -0.26 |  | crimea-intervention-2014, iraq-war-begins-2003, russia-georgia-war-2008, soleimani-strike-2020, afghanistan-campaign-2001 |
| us-russian-oil-ban-2022 | 96% | 2.5% | 3.1% | 0.04 |  | eu-iran-oil-embargo-2012, section-301-china-tariffs-2018, opec-output-cut-1999, crimea-intervention-2014, us-tyre-tariffs-china-2009 |
| fed-liftoff-hike-2022 | 89% | 4.9% | 2.8% | 0.42 |  | fed-first-hike-2015, fed-first-hike-2004, fed-hike-2000-05, fed-taper-announcement-2013, section-301-china-tariffs-2018 |
| fed-75bp-hike-2022 | 100% | 2.4% | 2.4% | 0.19 |  | fed-liftoff-hike-2022, fed-first-hike-2015, fed-first-hike-2004, fed-hike-2000-05, fed-taper-announcement-2013 |
| uk-mini-budget-2022 | 89% | 2.8% | 2.6% | -0.46 |  | fed-liftoff-hike-2022, fed-taper-announcement-2013, fed-75bp-hike-2022, brexit-referendum-2016, fed-hike-2000-05 |
| boe-gilt-intervention-2022 | 84% | 8.8% | 7.1% | -0.14 |  | fed-treasury-purchases-2009-03, coordinated-rate-cut-2008-10, yuan-flexibility-2010, fed-qe2-2010-11, fed-mbs-purchases-2008-11 |

### Skipped events
- opec-output-cut-1999: only 0 eligible precedents
- us-china-wto-deal-1999: only 1 eligible precedents
- aol-time-warner-merger-2000: only 1 eligible precedents
- microsoft-talks-collapse-2000: only 2 eligible precedents
- fed-hike-2000-05: only 3 eligible precedents
- intel-revenue-warning-2000: only 5 eligible precedents
- us-election-contested-2000: only 5 eligible precedents
- gore-concedes-2000: only 5 eligible precedents
- fed-intermeeting-cut-2001-01: only 6 eligible precedents
- microsoft-breakup-overturned-2001: only 9 eligible precedents
- fed-post-911-cut-2001: only 9 eligible precedents
- sept-11-attacks-2001: only 9 eligible precedents
- afghanistan-campaign-2001: only 10 eligible precedents
- china-wto-approval-2001: only 10 eligible precedents
- enron-bankruptcy-2001: only 10 eligible precedents
- argentina-debt-default-2001: only 12 eligible precedents

### Caveats
- **Survivorship bias:** the stock universe is today's large caps. Stocks that failed or were delisted are missing, which likely makes past portfolios look calmer than real ones.
- **Oracle parse:** the tuned column assumes the parser classifies category and nature correctly. The no-parse column is the lower bound if it never does.
- **In-sample:** settings and q_hat were chosen on these same events. Expect the holdout to be worse.
- **Few events:** about one hundred dev events; the intervals are wide.
- **Not yet measured:** recovery-range coverage and the language-model baseline (holdout, C5).

### Reproducibility
- library.npz: `142e4265564564350be078c53ae880de2df1d16a079124dcb1204a7d1105db0f`
- library.json: `8ed9d1d0a28d08e137c32e6a2fcb4bfd68ce40016a1857f35b386cb1321944d7`
- universe manifest: `0a2723a13bd4518bc767379d612973886bff57df390971f8be3e04fea572a2c4`
