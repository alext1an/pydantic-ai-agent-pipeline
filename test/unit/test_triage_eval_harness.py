"""Checks the eval harness with stub tasks (no LLM calls, no judge calls).

Locks in: golden loading, verb-set extraction, and stability (mean per-case
Jaccard across repeated runs). The LLM-judge accuracy side is pydantic_evals'
own logic and is not unit-tested here.
"""
from dataclasses import dataclass

from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import Evaluator, EvaluatorContext

from evals.eval_triage_agent import load_cases, stability_summary, verb_set
from myagent.schemas.agent_outputs import TriageItem, TriageResult


@dataclass
class AlwaysPass(Evaluator):
    def evaluate(self, ctx: EvaluatorContext) -> bool:
        return True


def _result(verbs):
    return TriageResult(items=[TriageItem(suggestion=f"{v} some words") for v in verbs])


def _run(verbs_for_run):
    seen = {}

    def task(_inputs):
        n = seen.get(_inputs, 0) + 1
        seen[_inputs] = n
        return _result(verbs_for_run[n] if n in verbs_for_run else verbs_for_run[1])

    return Dataset(name="t", cases=load_cases(), evaluators=[AlwaysPass()]).evaluate_sync(
        task=task, repeat=3, progress=False
    )


def test_load_cases_has_intent_fields():
    cases = load_cases()
    assert len(cases) == 6
    assert all(c.name and c.inputs and c.expected_output for c in cases)


def test_stability_is_1_when_identical_across_runs():
    report = _run({1: ["shorten", "fix", "expand"]})  # runs 2,3 reuse run1's verbs
    stab, per_case = stability_summary(report)
    assert stab == 1.0
    assert all(s == 1.0 for s in per_case.values())


def test_stability_drops_when_verbs_differ_between_runs():
    report = _run({1: ["shorten", "fix", "expand"], 2: ["shorten", "fix", "expand"], 3: ["xyz", "fix", "expand"]})
    stab, per_case = stability_summary(report)
    assert 0.0 < stab < 1.0
    assert all(0.0 < s < 1.0 for s in per_case.values())  # one run drifts for every case