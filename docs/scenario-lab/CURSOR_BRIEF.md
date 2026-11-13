# Cursor brief: Scenario Lab Phase 1

You are building the **application side** of Arcus Scenario Lab: the question parser, the narrative template, the API router, asset fetching, the frontend page and CI. You also write **blind tests** for Claude's factor model and engine, and review Claude's backtest for leakage. Claude Code builds the numerical core in parallel. `PLAN.md` in this folder is the spec. This brief tells you what to do and in what order.

> ## ⚠️ v2 UPDATE (2026-11-13): read this first; it overrides the task list below where they differ
> The user chose **plan v2: a stress test, not a forecast** (PLAN.md section "v2"). The C4 dev backtest proved forecasts were no better than guessing, while conditional replays are accurate. Tasks U4, U5 and C5 below are **redefined**, and the new tasks C4b and U4b come first. Pass marks H1–H5 and their fallbacks are fixed in PLAN v2 and **must not be changed** by either tool.
>
> **Staged hand-off.** CI stays green at every merge because v1 stays in place until the switch:
> 1. **Stage 1: C4b-contract (Claude).** Adds the v2 models **next to** v1 in `scenario/schemas.py`:
>    - `ScenarioHolding`, `ScenarioReplay`, `ExposureRank`, `Resilience`, `BacktestSummaryV2`, `WhatIfResponseV2`
>    - stubs with exact docstrings: `WhatIfEngine.run_v2`, `crisis_events`, `recovery_bucket`, `exposure_ranking`, `resilience_summary` in `engine.py`, and `render_v2` in `narrative.py`
>    - `FakeEngine.run_v2`, serving `frontend/src/lib/__fixtures__/whatif-response-v2.json`
>    - contract tests
>    
>    Merged, then STATUS says **"C4b contract merged"**.
> 2. **Stage 2, in parallel:**
>    - **Claude (C4b-engine):** implements engine v2, the crisis set (`scenario/eval/crises.md`), the off-topic threshold (from `scenario/eval/controls.txt`), and the conditional backtest H1–H4 with recovery buckets. Then a dev run, `results.md` v2 and `calibration_dev.json` v2. **Doesn't read Cursor's v2 tests** until done.
>    - **Cursor (U4b):**
>      1. blind tests `backend/tests/test_scenario_engine_v2.py`, written from PLAN v2 and the stubs before the engine lands, marked `xfail(raises=NotImplementedError)`
>      2. `render_v2` and its tests
>      3. router: `POST /api/scenario/whatif` returns `WhatIfResponseV2` from `engine.run_v2` (FakeEngine with `SCENARIO_FAKE=1` until the real engine lands)
>      4. page v2 + types + page tests against the v2 fixture
> 3. **Stage 3:**
>    - **U4 (Cursor):** the leakage review of the conditional backtest (PLAN v2 checklist).
>    - **C5 (Claude):** the one-time holdout, only after the user writes "run holdout". It applies the pre-registered fallbacks, and writes `calibration.json`, the only file that makes the engine available.
>    - **Then** U5, C6, U6.
>    
>    v1 `run()` and its tests stay until C6 cleanup; the page and router use v2 only.
>
> **Rules that still hold:**
> - **Files:** own files only; blind tests are never edited by the implementer; disputes go in STATUS.md.
> - **Release:** local merges only; nothing is pushed; `scripts/local_ci.sh` before every "ready to merge".
> - **Data:** no fabricated data; no event facts from memory.

## Before every session
1. Read `docs/scenario-lab/PLAN.md` in full, and `docs/scenario-lab/STATUS.md`.
2. Find the first task below that isn't checked off in `STATUS.md` and whose "Needs" are met.
3. In `STATUS.md`, set that task to `in progress (cursor)` before writing any code.

## Workspace
- Work in the main folder (`~/Desktop/portfolio-risk-tracker`) on branch `scenario/app`. Create it once:
  `git checkout -b scenario/app main`
  After each of Claude's merges, run `git rebase main`.
- Claude works in `../arcus-scenario-core` on `scenario/core`. Never edit files there.
- `STATUS.md` is untracked on purpose. It is the one board both tools share, so never commit it.
- Only edit the files listed as owned by Cursor in PLAN section 4. Never edit Claude's blind tests (`test_scenario_parse.py`, `test_scenario_narrative.py`). Never edit `scenario/engine.py`, `factors.py`, `backtest.py` or `schemas.py`. If one of them needs changing, log it in `STATUS.md`.
- Don't merge into `main` or push without the user approving. When a gate passes, write "ready to merge: scenario/app @ <sha>" in `STATUS.md`.

## Hard rules
- **No fabricated data.** A failed price source returns 503 or an empty state, never a substituted number. The UI shows an error, not zeros.
- **No event fact from memory.** Follow the event-writing rules in PLAN Step 1 exactly. Every URL and quote must come from a page you opened in that session.
- **The language model never produces numbers.** `parse.py` returns only `ParsedScenario` fields. `narrative.py` only formats numbers that are already in the response.
- **Blind tests:** write them from PLAN and the stub signatures **before** Claude's implementation is merged. Don't open Claude's implementation while writing them. After they are committed, change them only through a spec dispute in `STATUS.md`.
- **Keep the feature hidden until the ship gate passes:** `VITE_ENABLE_SCENARIOS=false` in `frontend/.env.production`.
- **Finish every task with its gate:** run the listed tests, paste the pass and fail summary into `STATUS.md`, and only then check the task off.

## Tasks

### U0 · Frontend skeleton
**Needs:** nothing, so start now.
- Add a route at `/dashboard/scenarios` in `frontend/src/App.tsx` and a sidebar item in `frontend/src/components/Sidebar.tsx`, both behind `VITE_ENABLE_SCENARIOS`. Copy how `VITE_ENABLE_RESEARCH` is handled.
- A placeholder `frontend/src/pages/ScenarioLab.tsx`.
- `VITE_ENABLE_SCENARIOS=false` in `frontend/.env.production`.
- `VITE_ENABLE_SCENARIOS: ${{ vars.VITE_ENABLE_SCENARIOS || 'false' }}` in the build step of `.github/workflows/ci.yml`.

**Gate:** `npm test` and `npm run build` pass. With the flag off, the route and sidebar item don't appear.

### U1 · Events 1999–2012, parser, router, page
**Needs:** Claude's C0 merged into `main` (check `STATUS.md`), then rebase.
- `scenario/events/1999_2012.jsonl`:
  - About 60 events covering all 11 categories, with at least 13 `favorable`
  - Must include 9/11, the dot-com bust milestones, Lehman and other 2008 events, the 2010 flash crash, the 2011 US downgrade, the 2011 Japan earthquake and the 2011 Thailand floods, **each only if you can open a source for it**
  - `drafted_by: "cursor"`, `verified_by: null`
  - Claude's `test_scenario_events.py` must pass on your file.
- `scenario/parse.py`, against the stub signature:
  - Calls Nemotron through the same client setup as `research/qa.py`
  - Temperature 0, 15-second timeout
  - Validates the result as `ParsedScenario`
  - Caches by SHA256 of the normalized text
  - Falls back to raw text with no category on any failure
- `backend/routers/scenario.py`, as in PLAN Step 5:
  - `GET /api/scenario/status` and `POST /api/scenario/whatif`
  - Engine supplied by `Depends(get_engine)`
  - Reuses `DailyQuota` and `_is_automation` from `backend/routers/research.py`, with a separate `scenario_rate_limits.sqlite3` and a limit of 20 per day
  - `SCENARIO_ENABLED` flag
  - Registered in `backend/main.py`
- `frontend/src/lib/scenario.ts`: the API client, with types matching `schemas.py`
- `frontend/src/pages/ScenarioLab.tsx`, the full page from PLAN Step 6, built against `whatif-response.json` and against the backend with `SCENARIO_FAKE=1`
  - Holdings come from `buildChatPortfolioContext()`.
  - Charts use recharts.
  - Every number on screen comes from the response, and the UI never computes new figures except formatting.

**Gate:**
- The events tests pass on your file.
- The `test_scenario_api.py` tests from PLAN Step 5 pass with `SCENARIO_FAKE=1`.
- `npm test` passes.

### U2 · Verify Claude's events, narrative, assets fetch, blind tests for factors
**Needs:** C1 and U1 merged.
- Verify every event in `scenario/events/2013_2026.jsonl`:
  - Open each source and confirm the quote is verbatim and the date is right.
  - Set `verified_by: "cursor"`, or fix the event, or remove it.
  - Log every change, with the reason, under "Event changes" in `STATUS.md`.
- `scenario/narrative.py`: a fixed template with slots for computed values only, no model call. It includes the low-confidence sentence and no advice words.
- `scenario/fetch_assets.py`: reuses `research.fetch_assets.fetch`. Extend that function to take a `members` argument, which is the one allowed edit to a research file. The URL and SHA are placeholders until Claude gives the real values in C6.
- `backend/tests/test_scenario_factors.py`, written **blind** from PLAN 3a and the `factors.py` stub, before Claude's `factors.py` lands.

**Gate:** your factor tests run and fail only with `NotImplementedError` against the stub, which proves they test the contract. Narrative and fetch tests pass.

### U3 · Blind engine tests, API and frontend tests
**Needs:** U2. Must be done **before** C3 is merged.
- `backend/tests/test_scenario_engine.py`: every test in PLAN 3c, written blind from the spec and the stub, with small hand-built libraries and hand-computed expected values.
- Finish `test_scenario_api.py` (every test in PLAN Step 5).
- `frontend/src/pages/__tests__/ScenarioLab.test.tsx` (every test in PLAN Step 6).

**Gate:** the API and frontend tests pass. The engine tests fail only with `NotImplementedError` against the stub.

### U4 · Leakage review of `backtest.py`
**Needs:** Claude has asked for it in `STATUS.md` (after C4).

Read `scenario/backtest.py` and `scenario/engine.py` and check each item. Write pass or fail, with file:line evidence, in `STATUS.md`:
1. Every precedent used for an event is dated before it, with 63-day windows that overlap it purged.
2. The beta window ends before the event date.
3. Context features (VIX, credit spread, GPR) are read at day -1.
4. Tuning functions reject holdout events.
5. The conformal residuals come only from dev.
6. Random portfolios use only stocks with prices on day -1.
7. All baselines are scored on exactly the same cases.
8. The event-weighted means and the bootstrap resample events, not cases.
9. No hindsight text from `name` reaches the retrieval query. Only `trigger`, `name` and `category` are embedded, and the backtest query is the `trigger` only.
10. The settings hash is written before the holdout code path runs.

**Gate:** all 10 items pass, or each failure is fixed by Claude and re-checked.

### U5 · Accuracy panel and UI polish
**Needs:** C5 done and the user's ship decision.
- The "How accurate is this?" panel shows G1–G5 with confidence intervals, from `backtest_summary` in the response. It shows misses honestly.
- Polish the loading, error and low-confidence states.
- Flip `VITE_ENABLE_SCENARIOS=true` **only when the user says to**.

**Gate:** `npm test` passes and the user has reviewed the page.

### U6 · Phase 1b groundwork
**Needs:** U5.
- Shareable `/dashboard/scenarios?q=` links
- `CONTRIBUTING.md`
- `.github/ISSUE_TEMPLATE/`: "Add an event", "Verify an event", "Submit a ScenarioBench model"
- A CI job that runs `test_scenario_events.py` on PRs that touch `scenario/events/`

**Gate:** CI passes on a test PR that adds a deliberately bad event: the job must fail.

## When to stop and ask the user
- Any gate fails in a way you can't fix inside your own files.
- A blind test disagrees with Claude's code and the plan doesn't settle which is right.
- Before pushing, merging, or turning the feature flag on.
