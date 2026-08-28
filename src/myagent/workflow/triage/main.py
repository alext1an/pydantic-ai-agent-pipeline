from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
import asyncio
from myagent.core.config import settings
from myagent.deps.context import AgentDeps
from myagent.schemas.agent_outputs import TriageResult
from myagent.workflow.triage.prompts import TRIAGE_SYSTEM_PROMPT
from myagent.workflow.base import SingleRun

provider = OpenAIProvider(
    base_url=settings.BASE_URL,
    api_key=settings.API_KEY.get_secret_value(),
)

model = OpenAIChatModel(settings.DEFAULT_LLM_MODEL, provider=provider)

triage_agent = SingleRun(
    model=model,
    deps_type=AgentDeps,
    result_type=TriageResult,
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
)
triage_agent.agent.instrument = True

if __name__ == '__main__':
  WORKSPACE_CONTEXT = """
workspace_context:

  rules:
    - "Preserve the user's existing writing style unless explicitly asked otherwise."
    - "Do not modify content outside the current selection unless the requested action requires it."
    - "Preserve the original meaning unless the user explicitly requests a substantive change."
    - "Do not invent facts, citations, or document context."
    - "Keep inline suggestions concise and actionable."

  workspace:
    description: >
      A collaborative document-editing workspace for writing technical
      documents, research notes, and product documentation.
    application: "Google Docs"
    mode: "editing"
    user_role: "document editor"

  capabilities:
    tools:
      - name: "read_document"
        description: "Read document content and surrounding context."

      - name: "edit_document"
        description: "Insert, replace, delete, or modify document content."

      - name: "search_document"
        description: "Search for text or concepts within the current document."

      - name: "search_workspace"
        description: "Search across documents available in the workspace."

      - name: "web_search"
        description: "Search the web for external information."

      - name: "get_document_metadata"
        description: "Retrieve document metadata such as title, section, and language."

  document:
    title: "Reliable Skill Execution in LLM Agents"
    type: "technical article"
    language: "English"
    writing_style: "technical, concise, research-oriented"

    outline:
      - "1. Introduction"
      - "2. Skill Documents"
      - "3. Instruction Following"
      - "4. Failure Modes"
      - "5. Improving Reliability"
      - "6. Evaluation"

    current_section:
      title: "3. Instruction Following"
      level: 2

    surrounding_context:
      Skill documents are essential for LLMs to function as agents, yet models frequently violate the very instructions they are given. We ask whether such violations are predictable from the model's internal state before generation begins. To test this, we extract residual-stream activations after the full context is read but before any tokens are generated, and train linear probes to predict which rules the forthcoming output will violate. Our study targets ten checkable rules from a spreadsheet skill document, evaluated on Qwen3.5-4B trajectories. Several probes clear permutation-based significance thresholds, but none surpass what simple input features already achieve. Whether a genuine compliance direction exists remains open; what we can establish is that the apparent signal is not separable from task-level confounds in this conditional setting.

  real_time_info:
    timestamp: "2026-08-26T18:31:00+08:00"
    cursor_position: "after paragraph 4"
    recent_action: "selected a paragraph"
    unsaved_changes: false

    collaborators:
      - name: "Alex"
        status: "active"

  selection:
    text: >

    """
  async def main():
    while True:
      user_input = input("please input your selection: ")
      if user_input.lower() == 'exit':
        break
      result = await triage_agent.run(WORKSPACE_CONTEXT + user_input)
      print(result)
  asyncio.run(main())