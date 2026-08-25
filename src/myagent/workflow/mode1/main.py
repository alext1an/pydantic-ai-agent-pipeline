from pydantic_ai import Agent
from myagent.core.config import settings
from myagent.deps.context import AppDeps
from myagent.schemas.agent_outputs import TriageResult
from myagent.workflow.mode1
from myagent.workflow.base import SingleRun

triage_agent = SingleRun(
    model=settings.DEFAULT_LLM_MODEL,
    deps_type=AppDeps,
    result_type=TriageResult,
    system_prompt=TRIAGE_SYSTEM_PROMPT,
    retries=2,
)

if __name__ == '__main__':
    print("Hello World")