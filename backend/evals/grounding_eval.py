# ── backend/evals/grounding_eval.py ────────────────────────────────────────
# Measures how often Arcus AI states portfolio figures that are not in the
# data it was given, comparing the system prompt before and after the
# grounding rule ("do not invent missing values", commit df8c31c).
#
#   NVIDIA_API_KEY=...    python -m backend.evals.grounding_eval
#   ANTHROPIC_API_KEY=... python -m backend.evals.grounding_eval --provider anthropic
#   python -m backend.evals.grounding_eval --dry-run      # no API calls
#
# Both conditions send the same portfolio, questions, model and temperature;
# only the rules sentence at the end of the prompt differs. Production chat
# runs on NVIDIA Nemotron, so that provider measures the deployed assistant.

import argparse
import json
import os
import random
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from itertools import combinations
from pathlib import Path

from backend.routers.chat import PortfolioContext, _build_system_prompt  # type: ignore

HERE = Path(__file__).parent
QUESTIONS_PATH = HERE / "grounding_questions.json"
RESULTS_DIR = HERE / "results"

PRODUCTION_MODEL = "claude-sonnet-4-20250514"
PRODUCTION_TEMPERATURE = 0.2
PRODUCTION_MAX_TOKENS = 1024

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
NVIDIA_DEFAULT_MODEL = "nvidia/nemotron-3-ultra-550b-a55b"

PROVIDERS = {
    "anthropic": {"key_env": "ANTHROPIC_API_KEY", "default_model": PRODUCTION_MODEL},
    "nvidia": {"key_env": "NVIDIA_API_KEY", "default_model": NVIDIA_DEFAULT_MODEL},
}
THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)

# The rules sentence from backend/routers/chat.py at df8c31c^.
PRE_FIX_RULES = (
    "Rules: Reference specific numbers always. Be specific on tickers. "
    "Under 200 words unless needed. Markdown bullets. "
    "End with one actionable next step."
)
RULES_MARKER = "\n\nRules:"


# ── Prompts ───────────────────────────────────────────────────────────────

def build_prompts(ctx: PortfolioContext) -> dict[str, str]:
    after = _build_system_prompt(ctx)
    head, marker, _ = after.partition(RULES_MARKER)
    if not marker:
        raise RuntimeError("System prompt no longer contains a 'Rules:' section; update PRE_FIX_RULES handling.")
    return {"before": f"{head}\n\n{PRE_FIX_RULES}", "after": after}


def context_block(prompt: str) -> str:
    """The portfolio data lines of a system prompt, without the persona or rules."""
    head = prompt.partition(RULES_MARKER)[0]
    return head.split("\n\n", 1)[1] if "\n\n" in head else head


# ── Deterministic number check ────────────────────────────────────────────

NUMBER_RE = re.compile(r"(?<![A-Za-z0-9.])[-+\u2212]?\$?\d[\d,]*(?:\.\d+)?")
LIST_MARKER_RE = re.compile(r"^\s*\d+[.)]\s", re.MULTILINE)


def extract_numbers(text: str) -> list[str]:
    return [m.group().rstrip(",") for m in NUMBER_RE.finditer(LIST_MARKER_RE.sub(" ", text))]


def _parse(token: str) -> tuple[Decimal, int]:
    clean = token.replace("$", "").replace(",", "").replace("\u2212", "-").lstrip("+")
    decimals = len(clean.split(".", 1)[1]) if "." in clean else 0
    return abs(Decimal(clean)), decimals


def _round(value: float, decimals: int) -> Decimal:
    return abs(Decimal(str(value))).quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)


def matches_known(token: str, known: list[float]) -> bool:
    """True if the token equals a known value at the token's own precision, ignoring sign."""
    value, decimals = _parse(token)
    return any(_round(k, decimals) == value for k in known)


def known_values(ctx: PortfolioContext, context_text: str, question: str) -> list[float]:
    """Numbers the reply may legitimately state: the data, the question, and simple derivations."""
    known = [float(_parse(t)[0]) for t in extract_numbers(context_text) + extract_numbers(question)]

    weights = [h.weight * 100 for h in ctx.holdings]
    for size in range(1, len(weights) + 1):
        for combo in combinations(weights, size):
            known.append(sum(combo))
            known.append(100 - sum(combo))
    known.append(len(ctx.holdings))

    m, ip = ctx.metrics, ctx.investorProfile
    if m and m.annualizedReturn is not None:
        if ip:
            known.append((m.annualizedReturn - ip.targetReturn) * 100)
        if m.maxDrawdown:
            known.append(m.annualizedReturn / abs(m.maxDrawdown))
        if m.volatility:
            known.append(m.annualizedReturn / m.volatility)
    if m and m.sharpe is not None and m.sortino is not None:
        known.append(m.sortino - m.sharpe)
    return known


def unmatched_numbers(reply: str, known: list[float]) -> list[str]:
    seen: list[str] = []
    for token in extract_numbers(reply):
        if not matches_known(token, known) and token not in seen:
            seen.append(token)
    return seen


# ── Judge ─────────────────────────────────────────────────────────────────

JUDGE_PROMPT = """You are auditing a portfolio assistant for invented figures.

The assistant was given ONLY this portfolio data:
<data>
{context}
</data>

User question:
<question>{question}</question>

Assistant reply:
<reply>
{reply}
</reply>

Numbers in the reply that do not directly match the data (this list may be incomplete; also check for figures written in words): {candidates}

Classify every specific figure in the reply:
- "data": appears in the portfolio data (rounding is fine)
- "derived": correctly calculated from the portfolio data, or repeated from the user's question while clearly treated as the user's claim rather than as fact
- "general": general finance knowledge or conventions not about this portfolio (e.g. "a Sharpe above 1 is good", "95% confidence", "the S&P 500", a calendar year)
- "invented": any other specific number about this portfolio or its holdings (values, share counts, returns, prices, ratios, yields, dates, targets, statistics), including real-world market data about the holdings that was not in the data, and estimates that are not clearly labelled as assumptions

Also answer:
- data_gap_acknowledged: does the reply clearly say that information needed to answer is not in the data?
- false_premise_accepted: does the reply treat a claim from the question that is absent from or contradicts the data (a holding not in the portfolio, a figure that differs from the data, an event not in the data) as true?

Respond with JSON only, no prose:
{{"figures": [{{"figure": "...", "verdict": "data|derived|general|invented", "reason": "..."}}], "data_gap_acknowledged": false, "false_premise_accepted": false}}"""


def parse_judge(text: str) -> dict:
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError(f"Judge returned no JSON: {text[:200]}")
    verdict = json.loads(text[start:end + 1])
    verdict.setdefault("figures", [])
    return verdict


def invented_figures(verdict: dict) -> list[dict]:
    return [f for f in verdict.get("figures", []) if f.get("verdict") == "invented"]


# ── Running ───────────────────────────────────────────────────────────────

def strip_thinking(text: str) -> str:
    return THINK_BLOCK_RE.sub("", text or "").strip()


def with_backoff(ask, attempts: int = 7, base_delay: float = 20.0, sleep=time.sleep):
    """Retries with waits of 20s, 40s, 80s… (capped at 5 min), well past the SDK's own short retries,
    so a free-tier rate limit stalls the run instead of ending it."""
    def retrying(*args, **kwargs):
        for attempt in range(attempts):
            try:
                return ask(*args, **kwargs)
            except Exception:
                if attempt == attempts - 1:
                    raise
                sleep(min(base_delay * 2 ** attempt, 300) + random.uniform(0, 5))
    return retrying


def make_asker(provider: str):
    """Returns ask(model, system, user, temperature, max_tokens, thinking) -> reply text."""
    return with_backoff(_make_raw_asker(provider))


def _make_raw_asker(provider: str):
    if provider == "anthropic":
        import anthropic  # type: ignore

        client = anthropic.Anthropic(max_retries=5)

        def ask(model, system, user, temperature, max_tokens, thinking=False):
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return response.content[0].text

        return ask

    from openai import OpenAI  # type: ignore

    client = OpenAI(base_url=NVIDIA_BASE_URL, api_key=os.environ["NVIDIA_API_KEY"], max_retries=5, timeout=600)

    def ask(model, system, user, temperature, max_tokens, thinking=False):
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=temperature,
            top_p=0.95,
            max_tokens=max_tokens,
            extra_body={"chat_template_kwargs": {"enable_thinking": thinking}},
        )
        return strip_thinking(response.choices[0].message.content)

    return ask


def run_case(ask, args, ctx, prompts, case, condition, repeat) -> dict:
    prompt = prompts[condition]
    context_text = context_block(prompt)
    reply = ask(args.model, prompt, case["question"], PRODUCTION_TEMPERATURE, PRODUCTION_MAX_TOKENS)
    candidates = unmatched_numbers(reply, known_values(ctx, context_text, case["question"]))

    judge_text = ask(
        args.judge_model,
        "You are a meticulous auditor. Output JSON only.",
        JUDGE_PROMPT.format(
            context=context_text,
            question=case["question"],
            reply=reply,
            candidates=", ".join(candidates) or "none",
        ),
        0.0, args.judge_max_tokens, args.judge_thinking,
    )
    verdict = parse_judge(judge_text)
    return {
        **case,
        "condition": condition,
        "repeat": repeat,
        "reply": reply,
        "unmatched_numbers": candidates,
        "judge": verdict,
        "invented": invented_figures(verdict),
    }


def summarize(results: list[dict]) -> dict:
    summary: dict = {}
    for condition in ("before", "after"):
        rows = [r for r in results if r["condition"] == condition]
        by_category = {}
        for category in sorted({r["category"] for r in rows}):
            cat_rows = [r for r in rows if r["category"] == category]
            by_category[category] = {
                "replies": len(cat_rows),
                "replies_with_invented": sum(1 for r in cat_rows if r["invented"]),
            }
        missing = [r for r in rows if r["category"] == "missing"]
        traps = [r for r in rows if r["category"] == "trap"]
        summary[condition] = {
            "replies": len(rows),
            "replies_with_invented": sum(1 for r in rows if r["invented"]),
            "invented_figures": sum(len(r["invented"]) for r in rows),
            "by_category": by_category,
            "missing_data_acknowledged": sum(1 for r in missing if r["judge"].get("data_gap_acknowledged")),
            "missing_questions": len(missing),
            "false_premise_accepted": sum(1 for r in traps if r["judge"].get("false_premise_accepted")),
            "trap_questions": len(traps),
        }
    return summary


def _fraction(n: int, d: int) -> str:
    return f"{n}/{d} ({n / d:.0%})" if d else "n/a"


def print_summary(summary: dict) -> None:
    b, a = summary["before"], summary["after"]
    rows = [
        ("Replies with an invented figure", _fraction(b["replies_with_invented"], b["replies"]),
         _fraction(a["replies_with_invented"], a["replies"])),
        ("Invented figures in total", str(b["invented_figures"]), str(a["invented_figures"])),
    ]
    for category in b["by_category"]:
        bc, ac = b["by_category"][category], a["by_category"].get(category, {"replies_with_invented": 0, "replies": 0})
        rows.append((f"  {category} questions", _fraction(bc["replies_with_invented"], bc["replies"]),
                     _fraction(ac["replies_with_invented"], ac["replies"])))
    rows += [
        ("Missing data acknowledged", _fraction(b["missing_data_acknowledged"], b["missing_questions"]),
         _fraction(a["missing_data_acknowledged"], a["missing_questions"])),
        ("False premise accepted", _fraction(b["false_premise_accepted"], b["trap_questions"]),
         _fraction(a["false_premise_accepted"], a["trap_questions"])),
    ]
    width = max(len(r[0]) for r in rows) + 2
    print(f"\n{'':<{width}}{'before fix':<16}{'after fix':<16}")
    for label, before, after in rows:
        print(f"{label:<{width}}{before:<16}{after:<16}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare invented-figure rates before and after the grounding rule.")
    parser.add_argument("--provider", choices=sorted(PROVIDERS), default="nvidia")
    parser.add_argument("--model", help="model that answers; defaults to the provider's default")
    parser.add_argument("--judge-model", help="model that grades; defaults to --model")
    parser.add_argument("--judge-thinking", action="store_true",
                        help="let the judge reason before answering (NVIDIA models that support it)")
    parser.add_argument("--judge-max-tokens", type=int, default=2000,
                        help="raise this with --judge-thinking, since reasoning counts against it")
    parser.add_argument("--repeats", type=int, default=1, help="runs per question per condition")
    parser.add_argument("--limit", type=int, default=0, help="only the first N questions")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--resume", type=Path, help="a results .jsonl from an interrupted run; finished replies are skipped")
    parser.add_argument("--dry-run", action="store_true", help="print the two prompts and exit")
    args = parser.parse_args(argv)
    args.model = args.model or PROVIDERS[args.provider]["default_model"]
    args.judge_model = args.judge_model or args.model

    data = json.loads(QUESTIONS_PATH.read_text())
    ctx = PortfolioContext(**data["portfolio"])
    prompts = build_prompts(ctx)
    cases = data["questions"][: args.limit or None]

    if args.dry_run:
        for condition, prompt in prompts.items():
            print(f"── {condition} ──\n{prompt}\n")
        print(f"{len(cases)} questions × 2 conditions × {args.repeats} repeats = "
              f"{len(cases) * 2 * args.repeats} replies, each also sent to the judge.")
        return 0

    key_env = PROVIDERS[args.provider]["key_env"]
    if not os.getenv(key_env):
        print(f"{key_env} is not set.", file=sys.stderr)
        return 1

    RESULTS_DIR.mkdir(exist_ok=True)
    progress = args.resume or RESULTS_DIR / f"grounding_{datetime.now():%Y%m%d_%H%M%S}.jsonl"
    results = load_progress(progress)
    done = {job_key(r["id"], r["condition"], r["repeat"]) for r in results}

    ask = make_asker(args.provider)
    jobs = [
        (case, condition, r)
        for case in cases for condition in ("before", "after") for r in range(args.repeats)
        if job_key(case["id"], condition, r) not in done
    ]
    total = len(jobs) + len(results)
    print(f"Running {len(jobs)} replies ({len(results)} already done) with {args.model}, "
          f"judged by {args.judge_model}. Progress: {_display(progress)}", flush=True)

    failed: list[dict] = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool, progress.open("a") as log:
        futures = {pool.submit(run_case, ask, args, ctx, prompts, *job): job for job in jobs}
        for future in as_completed(futures):
            case, condition, repeat = futures[future]
            try:
                result = future.result()
            except Exception as e:
                failed.append({"id": case["id"], "condition": condition, "repeat": repeat, "error": repr(e)})
                print(f"  failed {case['id']} {condition} #{repeat + 1}: {e!r}", flush=True)
                continue
            results.append(result)
            log.write(json.dumps(result) + "\n")
            log.flush()
            print(f"  {len(results)}/{total}  {case['id']} {condition} #{repeat + 1}", flush=True)

    summary = summarize(results)
    print_summary(summary)

    out = progress.with_suffix(".json")
    out.write_text(json.dumps({
        "provider": args.provider,
        "model": args.model,
        "judge_model": args.judge_model,
        "repeats": args.repeats,
        "prompts": prompts,
        "summary": summary,
        "failed": failed,
        "results": results,
    }, indent=2))
    print(f"\nEvery reply and verdict saved to {_display(out)}")
    if failed:
        print(f"{len(failed)} replies failed and are left out of the summary. "
              f"Finish them with: --resume {_display(progress)}")
        return 1
    return 0


def job_key(question_id: str, condition: str, repeat: int) -> tuple[str, str, int]:
    return (question_id, condition, repeat)


def load_progress(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _display(path: Path) -> str:
    return str(path.relative_to(Path.cwd())) if path.is_relative_to(Path.cwd()) else str(path)


if __name__ == "__main__":
    sys.exit(main())
