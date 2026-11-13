# Scenario Lab dev diagnostics

Dev events: 96 (33 with an S&P move above 5% in 21 days). Event-weighted means, 90% bootstrap CI over events. Forecast settings: `{"alpha": 1.0, "category_bonus": 0.0, "nature_penalty": 0.3, "similarity_threshold": 0.5, "stress_only": false, "top_k": 5, "use_actual": false}`.

- **Forecast** = the engine's question as designed: what happens next, from past precedents.
- **Conditional** = given the event's own real 21-day factor moves ("if it plays out like this"), how well the portfolio impact is estimated. Not a forecast: it shows what the factor model does once a path is assumed.

| Measure | All dev events | S&P moved > 5% |
|---|---|---|
| forecast_engine | 0.0560 [0.0465, 0.0664] | 0.0976 [0.0757, 0.1239] |
| forecast_random5 | 0.0558 [0.0474, 0.0657] | 0.1023 [0.0830, 0.1236] |
| forecast_zero | 0.0554 [0.0467, 0.0657] | 0.1018 [0.0813, 0.1252] |
| rank_forecast | 0.0281 [-0.0156, 0.0744] | 0.0220 [-0.0713, 0.1072] |
| conditional_beta_spx | 0.0204 [0.0189, 0.0220] | 0.0252 [0.0215, 0.0292] |
| rank_beta_spx | 0.1969 [0.1503, 0.2447] | 0.3048 [0.2184, 0.3863] |
| conditional_factor_a0.1 | 0.0165 [0.0155, 0.0175] | 0.0192 [0.0173, 0.0213] |
| rank_factor_a0.1 | 0.4645 [0.4356, 0.4918] | 0.4820 [0.4169, 0.5403] |
| conditional_factor_a1.0 | 0.0236 [0.0208, 0.0266] | 0.0342 [0.0275, 0.0415] |
| rank_factor_a1.0 | 0.4399 [0.4088, 0.4709] | 0.4475 [0.3756, 0.5134] |

MAE rows are 21-day portfolio return errors; rank rows are Spearman correlations across stocks.
