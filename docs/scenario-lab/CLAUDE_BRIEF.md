# Claude Code brief: Scenario Lab Phase 1

You are building the **numerical core** of Arcus Scenario Lab: contracts, data, library build, factor model, engine and backtest, plus the deploy. Cursor builds the parser, narrative, API, frontend and CI in parallel. `PLAN.md` in this folder is the spec. This brief tells you what to do and in what order.

## Before every session
1. Read `docs/scenario-lab/PLAN.md` in full, and `/Users/shreyas/Desktop/portfolio-risk-tracker/docs/scenario-lab/STATUS.md`.
2. Find the first task below that isn't checked off in `STATUS.md` and whose "Needs" are met.
3. In `STATUS.md`, set that task to `in progress (claude)` before writing any code.

## Workspace
- Work in a git worktree on branch `scenario/core`. Create it once:
  `git worktree add ../arcus-scenario-core -b scenario/core main`
- Cursor works in the main folder on `scenario/app`. **Never edit files in the main folder except `STATUS.md`**, and always edit it by its absolute path above. It is untracked on purpose, so both tools see the same copy.
- Only edit the files listed as owned by Claude in PLAN section 4. Never edit Cursor's blind tests (`test_scenario_factors.py`, `test_scenario_engine.py`).
- Don't merge into `main` or push without the user approving. When a gate passes, write "ready to merge: scenario/core @ <sha>" in `STATUS.md` and tell the user.
- PR descriptions do not get a "Generated with Claude Code" footer.

## Hard rules
- **No fabricated data.** If a download fails, the build fails loudly, or the event is marked missing. Never fill gaps with substitutes, constants or interpolated prices.
- **No event fact from memory.** Follow the event-writing rules in PLAN Step 1 exactly. Every URL and quote must come from a page you opened in that session.
- **Point-in-time everywhere.** Every function in factors, engine and backtest takes `as_of` and must not read data on or after it.
- **The holdout runs once**, and only after the user writes "run holdout" in `STATUS.md`.
- **If downloads fail locally with SSL errors**, set `SSL_CERT_FILE` (the same fix as the RSS feeds).
- **Finish every task with its gate:** run the listed tests, paste the pass and fail summary into `STATUS.md`, and only then check the task off.

## Tasks

### C0 · Step 0: contracts
**Needs:** nothing. **Cursor waits on this.**
- `scenario/__init__.py`
- `scenario/enums.py`
- `scenario/schemas.py`: the models listed in PLAN Step 0
- `scenario/ASSETS.md`
- Stubs with final signatures and docstrings:
  - `scenario/factors.py`: `fit_betas(stock_returns, factor_returns, as_of, *, alpha, stress_only, window_years=3) -> dict[str, BetaFit]`
  - `scenario/parse.py`: `parse_scenario(text, *, client=None) -> ParsedScenario`
  - `scenario/engine.py`: `WhatIfEngine.run(request, *, as_of=None) -> WhatIfResponse`, `FakeEngine`, `get_engine()`
  - `scenario/narrative.py`: `render(response) -> str`
- You may adjust these signatures while you write them. Once C0 is merged they are frozen.
- `scripts/gen_nyse_holidays.py` → `scenario/nyse_holidays.json`
- `scripts/gen_fixture.py` → `frontend/src/lib/__fixtures__/whatif-response.json`. Clearly synthetic: tickers `DEMO1` and `DEMO2`, event names prefixed "Example".
- `backend/tests/test_scenario_contracts.py`

**Gate:** contract tests pass and the full `pytest backend/tests -v` stays green. Commit `docs/scenario-lab/{PLAN,CLAUDE_BRIEF,CURSOR_BRIEF}.md` in the same branch. Then ask the user to merge into `main`, and write "C0 merged, Cursor unblocked" in `STATUS.md`.

### C1 · Events 2013–2026, data download, shared embedder
**Needs:** C0 merged.
- `scenario/events/2013_2026.jsonl`:
  - About 60 events, roughly half in the holdout (2023 onward)
  - Spread across all 11 categories, with at least 12 `favorable`
  - `drafted_by: "claude"`, `verified_by: null`
- `backend/tests/test_scenario_events.py`: every test in PLAN Step 1
- `scenario/data.py`: downloads to `scenario/raw/` (add it to `.gitignore`) and writes `manifest.json`
- `shared_embedder()` in `research/embedder.py`, used from `research/qa.py`

**Gate:**
- Events tests pass on your file.
- The research tests still pass.
- `python -m scenario.data` completes and `manifest.json` lists every series.

### C2 · Verify Cursor's events, build the library, factor model, blind tests for parse
**Needs:** C1 and Cursor's U1 events merged.
- Verify every event in `scenario/events/1999_2012.jsonl` against PLAN Step 1:
  - Open each source and confirm the quote is verbatim and the date is right.
  - Set `verified_by: "claude"`, or fix the event, or remove it.
  - Log every fix or removal, with the reason, under "Event changes" in `STATUS.md`.
- `scenario/build_library.py`, plus the Step 2 tests in `test_scenario_build.py`. They use a small committed fixture under `backend/tests/fixtures/scenario/`, so no network is needed.
- `scenario/factors.py`. Implement against the stub signature. **Don't read Cursor's factor tests until your implementation is done.**
- `backend/tests/test_scenario_parse.py`, written blind from PLAN 3b and the `parse.py` stub. Don't open Cursor's `parse.py`.

**Gate:**
- Build tests pass, and two builds have the same hash.
- `build_report.md` is written and its flagged events are listed in `STATUS.md` for the user.
- Cursor's factor tests pass against your code. A failure is either fixed in your code or logged as a spec dispute.

### C3 · Engine, blind tests for narrative
**Needs:** C2, the verification on both sides done (`SCENARIO_REQUIRE_VERIFIED=1` passes), and Cursor's U3 engine tests committed. **Don't read those tests until your engine is done.**
- `scenario/engine.py` (`WhatIfEngine`), following PLAN 3c. Keep `FakeEngine`. `get_engine()` returns the real engine when assets are loaded and `SCENARIO_FAKE` is not set.
- `backend/tests/test_scenario_narrative.py`, written blind from PLAN 3d.

**Gate:** all of Cursor's engine tests pass, or each failure is resolved as a spec dispute. Nothing is skipped or marked xfail without the user agreeing.

### C4 · Backtest on dev
**Needs:** C3.
- `scenario/backtest.py`, exactly as in PLAN Step 4 and section 2b
- `backend/tests/test_scenario_backtest.py`, with all tests except `test_ship_gate`
- A dev-only run: tune the settings and write `results.md` (dev section) and the draft `calibration.json`
- Freeze the settings and write the settings hash to `STATUS.md`
- Ask Cursor for the leakage review (task U4) in `STATUS.md`

**Gate:** backtest tests pass, and dev metrics and confidence intervals are in `STATUS.md`.

### C5 · Holdout, run once
**Needs:** Cursor's U4 review checked off **and** the user has written "run holdout" in `STATUS.md`.
- Run the holdout once and write the final `results.md` and `calibration.json`.
- Run `test_ship_gate`.
- **Stop.** Paste the gate table (G1–G5 with their confidence intervals) into `STATUS.md` and ask the user to decide (see PLAN 2b, "If the gate fails"). Do not change any setting after this run.

### C6 · Deploy
**Needs:** the user approved shipping.
- Pack the assets. **Ask the user before publishing** the GitHub release `scenario-assets-v1`.
- Pin the URL and SHA in `scenario/fetch_assets.py`. Cursor owns that file, so give the values in `STATUS.md` for Cursor to set, or get the user's OK to edit that one constant yourself.
- `test_scenario_assets.py`
- `render.yaml` changes
- `scripts/measure_memory.py`: peak memory must be under 450 MB with both features warm after 20 mixed requests
- `scenario/MODEL_CARD.md`
- README section

**Gate:** asset tests pass, the memory number is in `STATUS.md`, and the production smoke test in PLAN Step 7 passes after the user deploys.

## When to stop and ask the user
- Any gate fails in a way you can't fix inside your own files.
- A spec dispute that the plan doesn't settle.
- Before the holdout run, before publishing a release, before pushing or merging.
- Fewer than 6 verifiable events in any category.
