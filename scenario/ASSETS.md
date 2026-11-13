# Scenario Lab asset layout

`scenario/build_library.py` writes these files to `scenario/assets/`. `scenario/fetch_assets.py` downloads them at deploy time from the GitHub release `scenario-assets-v<N>`, checked by SHA256. `engine.Library` is their in-memory form.

## Conventions
- **Event order:** row `i` of every array is `library.json["events"][i]`, in date order.
- **Factor order:** `FACTOR_NAMES` from `scenario/enums.py`, and `F = len(FACTOR_NAMES)`, which is 13.
- **Path index:** `t = 0` is the close on day -1, with value `0.0`. `t = k` is the close of the k-th trading day starting with day 0. The 21-day move is `[:, 21, :]`.
- **Missing values:** `NaN`, never filled. That covers days not yet observed, factors not yet listed (for example SOXX before 2001-07, which is flagged as `semis_proxy`), and closures.
- **Units:** cumulative simple returns, as fractions. The exception is `DGS10_CHG`, which is a cumulative change in percentage points.
- **Data types:** all arrays are float32 unless stated.

## `library.npz`
| Key | Shape | Meaning |
|---|---|---|
| `embeddings` | (n, 384) | BGE-small embedding of `trigger + " " + name + " " + category`, L2-normalized |
| `factor_paths` | (n, 505, F) | Cumulative factor paths, t = 0..504 |
| `context` | (n, 4) | At the day -1 close: `vix`, `baa10y`, `gpr`, `gpr_rise_5d` |

## `factor_history.npz`
| Key | Shape | Meaning |
|---|---|---|
| `dates` | (T,) int32 | Trading dates as `yyyymmdd`, from 1998-12-01 |
| `returns` | (T, F) | Daily factor returns (`DGS10_CHG` in percentage points) |

## `library.json`
```json
{
  "version": 1,
  "built_from_manifest_sha256": "<sha of scenario/raw/manifest.json>",
  "factor_names": ["SPY", "..."],
  "context_names": ["vix", "baa10y", "gpr", "gpr_rise_5d"],
  "embedding_model": "BAAI/bge-small-en-v1.5",
  "events": ["<Event objects, as in scenario/schemas.py>"],
  "flags": {"<event id>": ["date_check_quiet", "semis_proxy"]}
}
```

## `calibration.json` (from `scenario/eval/`, shipped in the same archive)
```json
{
  "q_hat": 0.0,
  "settings": {"alpha": 0.0, "stress_only": false, "category_bonus": 0.0, "context_weight": 0.0,
               "similarity_threshold": 0.0, "top_k": 5},
  "settings_sha256": "...",
  "holdout_ids_sha256": "...",
  "backtest": "<BacktestSummary>"
}
```

## Size budget
`library.npz` must stay under 15 MB. At 150 events it is about 4 MB: 150 × 505 × 13 × 4 bytes, plus embeddings.
