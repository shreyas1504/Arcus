"""
ARCUS — grounding eval tests

The eval's headline number depends on the prompts it compares and on the
deterministic number check, so both are pinned here without any API calls.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest

from backend.routers.chat import PortfolioContext
from backend.evals.grounding_eval import (
    PRE_FIX_RULES,
    QUESTIONS_PATH,
    build_prompts,
    context_block,
    extract_numbers,
    invented_figures,
    known_values,
    load_progress,
    matches_known,
    with_backoff,
    parse_judge,
    strip_thinking,
    summarize,
    unmatched_numbers,
)


@pytest.fixture(scope="module")
def data():
    return json.loads(QUESTIONS_PATH.read_text())


@pytest.fixture(scope="module")
def ctx(data):
    return PortfolioContext(**data["portfolio"])


@pytest.fixture(scope="module")
def prompts(ctx):
    return build_prompts(ctx)


# ── Prompts ───────────────────────────────────────────────────────────────

def test_conditions_differ_only_in_the_rules(prompts):
    before_head = prompts["before"].partition("\n\nRules:")[0]
    after_head = prompts["after"].partition("\n\nRules:")[0]
    assert before_head == after_head
    assert prompts["before"].endswith(PRE_FIX_RULES)


def test_only_the_after_prompt_carries_the_grounding_rule(prompts):
    assert "do not invent missing values" in prompts["after"]
    assert "do not invent" not in prompts["before"]


def test_alpha_is_left_out_of_the_data(prompts):
    # m01 asks for alpha, so the data must not contain it.
    assert "Alpha" not in context_block(prompts["after"])


def test_context_block_holds_only_the_data(prompts):
    block = context_block(prompts["after"])
    assert block.startswith("Holdings: AAPL (30%, $227.50)")
    assert "Rules" not in block and "Arcus AI" not in block


def test_question_ids_are_unique(data):
    ids = [q["id"] for q in data["questions"]]
    assert len(ids) == len(set(ids))


# ── Number check ──────────────────────────────────────────────────────────

def test_extract_numbers_skips_list_markers_and_ticker_digits():
    text = "1. Sharpe is 1.34\n2. VaR −2.1% on $1,250.50\nSee S&P 500 and Q3"
    assert extract_numbers(text) == ["1.34", "\u22122.1", "$1,250.50", "500"]


@pytest.mark.parametrize("token,known,expected", [
    ("1.34", [1.34], True),
    ("1.3", [1.34], True),        # rounded to the reply's precision
    ("1.4", [1.34], False),
    ("2.1", [-2.1], True),        # sign-insensitive: "lose 2.1%" vs VaR -2.1%
    ("$227.50", [227.5], True),
    ("228", [227.5], True),       # half-up, not banker's rounding
    ("17", [16.2], False),
])
def test_matches_known(token, known, expected):
    assert matches_known(token, known) is expected


def test_derived_values_are_not_flagged(ctx, prompts):
    known = known_values(ctx, context_block(prompts["after"]), "What % is in tech?")
    reply = "Tech (AAPL, MSFT, NVDA) is 75% of 5 holdings; the rest is 25%. You beat target by 1.2 points; Calmar 0.88."
    assert unmatched_numbers(reply, known) == []


def test_figures_absent_from_the_data_are_flagged(ctx, prompts):
    known = known_values(ctx, context_block(prompts["after"]), "What's my alpha?")
    reply = "Your alpha is 3.4% and your portfolio is worth $48,200."
    assert unmatched_numbers(reply, known) == ["3.4", "$48,200"]


def test_numbers_from_the_question_are_not_flagged(ctx, prompts):
    question = "Why did my portfolio drop 12% last week?"
    known = known_values(ctx, context_block(prompts["after"]), question)
    assert unmatched_numbers("I can't confirm a 12% drop.", known) == []


# ── Judge parsing and scoring ─────────────────────────────────────────────

def test_parse_judge_tolerates_surrounding_text():
    verdict = parse_judge('Here you go:\n{"figures": [{"figure": "3.4%", "verdict": "invented"}], '
                          '"data_gap_acknowledged": false, "false_premise_accepted": false}\nDone.')
    assert [f["figure"] for f in invented_figures(verdict)] == ["3.4%"]


def test_strip_thinking_drops_reasoning_that_leaks_into_content():
    # Reasoning can contain numbers that would otherwise be scored as the reply's.
    assert strip_thinking("<think>maybe 3.4%?</think>\nAlpha isn't in your data.") == "Alpha isn't in your data."
    assert strip_thinking(None) == ""


def test_parse_judge_rejects_non_json():
    with pytest.raises(ValueError):
        parse_judge("no verdict here")


# ── Surviving rate limits ─────────────────────────────────────────────────

def test_with_backoff_retries_until_success():
    calls, waits = [], []

    def flaky(x):
        calls.append(x)
        if len(calls) < 3:
            raise RuntimeError("429 Too Many Requests")
        return "ok"

    assert with_backoff(flaky, sleep=waits.append)("q") == "ok"
    assert len(calls) == 3
    assert waits[0] < waits[1]          # waits grow between attempts


def test_with_backoff_gives_up_after_the_last_attempt():
    def always_fails():
        raise RuntimeError("429")

    with pytest.raises(RuntimeError):
        with_backoff(always_fails, attempts=3, sleep=lambda s: None)()


def test_load_progress_reads_finished_replies(tmp_path):
    path = tmp_path / "run.jsonl"
    assert load_progress(path) == []
    path.write_text('{"id": "g01", "condition": "before", "repeat": 0}\n\n'
                    '{"id": "g01", "condition": "after", "repeat": 0}\n')
    assert [r["condition"] for r in load_progress(path)] == ["before", "after"]


def test_summarize_counts_replies_not_figures():
    def row(condition, category, n_invented, gap=False, premise=False):
        return {
            "condition": condition, "category": category,
            "invented": [{"verdict": "invented"}] * n_invented,
            "judge": {"data_gap_acknowledged": gap, "false_premise_accepted": premise},
        }

    results = [
        row("before", "missing", 2), row("before", "missing", 0, gap=True), row("before", "trap", 1, premise=True),
        row("after", "missing", 0, gap=True), row("after", "missing", 0, gap=True), row("after", "trap", 0),
    ]
    s = summarize(results)
    assert (s["before"]["replies_with_invented"], s["before"]["invented_figures"]) == (2, 3)
    assert s["after"]["replies_with_invented"] == 0
    assert s["before"]["missing_data_acknowledged"] == 1 and s["after"]["missing_data_acknowledged"] == 2
    assert s["before"]["false_premise_accepted"] == 1 and s["after"]["false_premise_accepted"] == 0
