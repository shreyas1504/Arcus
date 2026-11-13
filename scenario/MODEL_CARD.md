# Model card: Arcus Scenario Lab (v2, stress test)

## What it does
Given a plain-English "what if" question and a portfolio, Scenario Lab replays the closest real past market shocks, and a fixed set of seven crises, on the portfolio. For each replay it reports:
- each holding's 21-day move
- the portfolio's move
- the worst fall within 63 trading days
- the recovery time
- which holdings drove the result

**Intended use:** understanding a portfolio's exposure to kinds of shocks, using history.

**Not intended:**
- forecasting returns, timing markets, or deciding whether a shock will happen
- investment advice

The page and narrative say this in plain words, and the narrative never uses advice words.

## How it works
| Part | What | Where |
|---|---|---|
| Question parsing | Nemotron returns only a category, adverse or favorable, regions, sectors and search text, never numbers. It falls back to the raw text on any failure. | `scenario/parse.py` |
| Precedent search | BGE-small embeddings of each event's day-0 trigger, name and category. Cosine similarity minus a 0.3 penalty for the opposite nature. Up to 5 precedents above the threshold 0.523; below it, low confidence and crises only. | `scenario/engine.py` |
| Per-holding replay | The actual 21-day return if the stock traded then. Otherwise ridge factor betas (α 0.1), fitted on the 3 years before the question, × that shock's real factor moves (SPY, sector ETF, SOXX for chips, the 10-year yield, Brent). | `scenario/factors.py`, `scenario/engine.py` |
| Crisis set | S&P fell 10% or more within 21 trading days; events within 63 trading days form one episode, named by its adverse event with the deepest fall. Gives 7 crises. | `engine.crisis_events`, `scenario/eval/crises.md` |
| Narrative | A fixed template filled only with computed numbers | `scenario/narrative.py` |

## Data
- **Events:** 144 shocks from 1999 to 2026. Each has a source URL and a verbatim quote, and each was cross-verified by the tool that didn't write it. One unverifiable event was removed.
- **Market data:** free public sources (Yahoo daily bars, FRED, the Caldara–Iacoviello GPR index, Baker–Bloom–Davis EPU), snapshotted with SHA256. Gaps stay as missing values; only foreign or bond holidays take the previous print, at most 5 days old.
- **Backtest universe:** 125 US large caps listed today, with sectors from Yahoo.

## Evaluation
- **Setup:** each test shock is treated as the scenario. Betas use only prices before it, the estimate uses the shock's real factor moves, and the result is compared with the stocks' real moves. There are 200 random equal-weight portfolios and 6 archetypes per shock.
- **Statistics:** metrics are event-weighted, with 90% bootstrap intervals over events. The baseline is portfolio beta × the S&P path.
- **Pass marks:** fixed in `docs/scenario-lab/PLAN.md` (section v2) before any test.
- **Tuning:** dev (1999–2022, 96 shocks) tuned only ridge strength and stress betas. The holdout (2023+, 32 shocks) was scored once, with the settings and the holdout event list hash-checked first.

| Gate | Dev 1999–2022 | Holdout 2023+ | Pass mark |
|---|---|---|---|
| H1 · 21-day portfolio error vs beta × S&P | 19.0% lower | **24.4% lower** [19.6, 28.9] | ≥ 10% lower |
| H2 · holding ranking (Spearman) | 0.46 | **0.47** [0.42, 0.51] | ≥ 0.30 |
| H3 · 63-day worst fall error | 22.0% lower | **23.2% lower** [19.1, 26.9] | ≥ 10% lower |
| H4 · recovery time, within one bucket (exact) | 94.9% (71.8% vs 64.8%) | **93.1%** (70.5% vs 59.4%) | ≥ 75%, exact ≥ beta |
| H5 · holdout agrees with dev | | ✅ | must match |

The full tables are in `scenario/eval/results.md`, and the raw holdout record is in `scenario/eval/holdout_run.json`.

## Limitations
- **Conditional, not predictive:** accuracy is measured given a scenario's market path. It says nothing about which path will happen. A forecasting version was tested and failed (`scenario/eval/results_forecast_v1.md`).
- **Survivorship bias:** the backtest universe is today's large caps, which likely understates past losses for weaker companies.
- **Small sample:** 128 scored events, so the intervals are wide. Some categories have few events.
- **Lenient bucket measure:** recovery "within one bucket" is lenient because the short buckets are narrow, so the exact-bucket rate is the more telling figure.
- **Stock-specific moves:** actual replays include each stock's own news in that period (for example NVIDIA in 2023–25), by design, because they show what really happened.
- **Weak matches:** the similarity threshold lets 2 of 30 off-topic control questions through. Those answers still show real history, labelled with low similarity.
- **Crisis names:** episode labels come from a fixed rule, so 2008 is named after the House's rejection of the rescue plan, not Lehman.

## Provenance
- **Plan, briefs and decisions:** `docs/scenario-lab/`.
- **Who built what:** Claude Code built the numerical core; Cursor built the parser, narrative, API and page. Each wrote blind tests of the other's modules.
