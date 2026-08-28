"""Triage agent eval: LLM-judge accuracy + run-to-run stability.

Usage:
    uv run python -m evals.eval_triage_agent [--repeat N] [--min-accuracy F] [--min-stability F]

- accuracy: an LLM judge (same model as the triage agent) grades each run's
  three suggestions against the case's stated intent; ordering is ignored.
- stability: mean per-case Jaccard of suggestion verb-sets across repeated
  runs -- measures whether the agent returns consistent suggestions.
- After the run, every graded example is dumped to evals/reviews/ so a human
  can audit (or override) the judge's verdicts.

Exits non-zero if either metric falls below its threshold (CI-gate friendly).
"""
import argparse
import json
from datetime import datetime
from pathlib import Path

from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import LLMJudge

from myagent.workflow.triage.main import model, triage_agent

GOLDEN = Path(__file__).parent / "datasets" / "triage_golden.jsonl"
REVIEWS = Path(__file__).parent / "reviews"

RUBRIC = (
    "Do the output's three suggestions each accurately address the user's stated intent for the input? "
    "Ignore the ordering of the suggestions. A suggestion is a 3-5 word actionable action, not content. "
    "Answer yes only if at least two suggestions are on-target for the intent; otherwise no."
)


def build_suite() -> Dataset:
    return Dataset(
        name="triage-golden",
        cases=load_cases(),
        evaluators=[LLMJudge(rubric=RUBRIC, model=model, include_input=True, include_expected_output=True)],
    )


def load_cases() -> list[Case]:
    cases = []
    for line in GOLDEN.read_text().splitlines():
        row = json.loads(line)
        cases.append(Case(name=row["name"], inputs=row["input"], expected_output=row["intent"]))
    return cases


def verb_set(output) -> set[str]:
    return {item.suggestion.split()[0].lower() for item in output.items}


def stability_summary(report) -> tuple[float, dict[str, float]]:
    """Per-case Jaccard of verb-sets across repeated runs: intersection / union."""
    per_case = {}
    for group in report.case_groups():
        sets = [verb_set(run.output) for run in group.runs]
        if not sets:
            per_case[group.name] = 0.0
            continue
        union = set.union(*sets)
        per_case[group.name] = len(set.intersection(*sets)) / len(union) if union else 1.0
    mean = sum(per_case.values()) / len(per_case) if per_case else 0.0
    return mean, per_case


def dump_for_human_review(report) -> Path:
    """Write one line per run: input, intent, suggestions, judge verdict + reason."""
    REVIEWS.mkdir(parents=True, exist_ok=True)
    path = REVIEWS / f"triage_review_{datetime.now():%Y%m%d_%H%M%S}.jsonl"
    rows = []
    for case in report.cases:
        verdict = case.assertions.get("LLMJudge")
        rows.append(
            {
                "name": case.name,
                "input": case.inputs,
                "intent": case.expected_output,
                "suggestions": [s.suggestion for s in case.output.items],
                "judge_pass": verdict.value if verdict else None,
                "judge_reason": verdict.reason if verdict else None,
            }
        )
    for failure in report.failures:
        rows.append(
            {
                "name": failure.name,
                "input": failure.inputs,
                "intent": failure.expected_output,
                "error": failure.error_message.split(":")[-1].strip()[:200],
            }
        )
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
    return path


def main(repeat: int = 3, min_accuracy: float = 0.8, min_stability: float = 0.7) -> int:
    report = build_suite().evaluate_sync(
        task=triage_agent.run, name="eval-triage", repeat=repeat, metadata={"suite": "triage-golden"}
    )
    report.print()

    averages = report.averages() if report.averages() else None
    acc = averages.assertions if averages else 0.0
    stab, per_case = stability_summary(report)
    review_path = dump_for_human_review(report)

    print(f"\naccuracy   (LLM-judge pass rate across {repeat} runs): {acc:.3f}")
    print(f"stability  (mean verb-set Jaccard):                {stab:.3f}")
    for name, s in sorted(per_case.items()):
        print(f"  - {name}: {s:.3f}")
    print(f"human-review dump: {review_path}")

    ok = acc >= min_accuracy and stab >= min_stability
    print(f"\nthresholds: accuracy>={min_accuracy} stability>={min_stability} -> {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--min-accuracy", type=float, default=0.8)
    parser.add_argument("--min-stability", type=float, default=0.7)
    args = parser.parse_args()
    raise SystemExit(main(args.repeat, args.min_accuracy, args.min_stability))