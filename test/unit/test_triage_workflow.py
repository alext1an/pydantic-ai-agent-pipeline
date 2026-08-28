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

async def test_singlerun_returns_structured_triage_result(build_triage_agent):
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

    result = await triage_agent.run("Please triage this paragraph.")

    assert isinstance(result, TriageResult)
    assert len(result.items) == 3
    assert [item.suggestion for item in result.items] == [
        "Revise selected paragraph",
        "Clarify key claim",
        "Check section consistency",
    ]


async def test_singlerun_allows_explicit_output_type_override():
    agent = SingleRun(
        model=TestModel(custom_output_text="override works"),
        result_type=TriageResult,
        output_type=str,
        system_prompt="Return plain text.",
        retries=0,
    )

    result = await agent.run("any input")

    assert isinstance(result, str)
    assert result == "override works"


async def test_triage_agent_records_model_request_and_output_schema(build_triage_agent):
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

    _ = await triage_agent.run("User selected one sentence.")

    params = model.last_model_request_parameters
    assert params is not None
    assert params.output_tools is not None
    assert len(params.output_tools) >= 1

@pytest.mark.parametrize("unsupported_argument", ["tools", "toolsets"])
def test_singlerun_rejects_tools(unsupported_argument):
    with pytest.raises(ValueError, match="SingleRun does not support tools"):
        SingleRun(model=TestModel(), **{unsupported_argument: [object()]})