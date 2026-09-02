import asyncio
from myagent.core.config import get_settings
from myagent.deps.context import AgentDeps
from myagent.schemas.agent_outputs import TriageResult
from myagent.workflow.triage.prompts import TRIAGE_SYSTEM_PROMPT
from myagent.workflow.base import SingleRun
from myagent.core.provider import build_model

def build_triage_agent() -> SingleRun:
  settings = get_settings()
  return  SingleRun(
    model=build_model(settings),
    deps_type=AgentDeps,
    output_type=TriageResult,
    system_prompt=TRIAGE_SYSTEM_PROMPT,
    retries=2,
    name="triage",
    model_settings={
        'extra_body': {
            'reasoning': {
                'enabled': False
                }
                }
    },
    instrument=True,
)