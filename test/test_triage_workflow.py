import pytest
from pydantic_ai.models.test import TestModel

from myagent.deps.context import AgentDeps
from myagent.schemas.agent_outputs import TriageResult
from myagent.workflow.base import SingleRun
from myagent.workflow.triage.prompts import TRIAGE_SYSTEM_PROMPT


@pytest.fixture
def build_triage_agent():
    def _builder(model: TestModel) -> SingleRun:
        return SingleRun(
            model=model,
            deps_type=AgentDeps,
            result_type=TriageResult,
            system_prompt=TRIAGE_SYSTEM_PROMPT,
            retries=0,
        )
    return _builder


def test_singlerun_returns_structured_triage_result(build_triage_agent):
    model = TestModel(
        custom_output_args={
            "items": [
                {"suggestion": "Revise selected paragraph"},
                {"suggestion": "Clarify key claim"},
                {"suggestion": "Check section consistency"},
            ]
        }
    )
    triage_agent = build_triage_agent(model)

    result = triage_agent.run("Please triage this paragraph.")

    assert isinstance(result, TriageResult)
    assert len(result.items) == 3
    assert [item.suggestion for item in result.items] == [
        "Revise selected paragraph",
        "Clarify key claim",
        "Check section consistency",
    ]


def test_singlerun_allows_explicit_output_type_override():
    agent = SingleRun(
        model=TestModel(custom_output_text="override works"),
        result_type=TriageResult,
        output_type=str,
        system_prompt="Return plain text.",
        retries=0,
    )

    result = agent.run("any input")

    assert isinstance(result, str)
    assert result == "override works"


def test_triage_agent_records_model_request_and_output_schema(build_triage_agent):
    model = TestModel(
        custom_output_args={
            "items": [
                {"suggestion": "Revise selected paragraph"},
                {"suggestion": "Clarify key claim"},
                {"suggestion": "Check section consistency"},
            ]
        }
    )
    triage_agent = build_triage_agent(model)

    _ = triage_agent.run("User selected one sentence.")

    params = model.last_model_request_parameters
    assert params is not None
    assert params.output_tools is not None
    assert len(params.output_tools) >= 1