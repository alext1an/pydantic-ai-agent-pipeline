import asyncio
from myagent.workflow.triage.agent import build_triage_agent
from myagent.core.config import get_settings
import myagent.core.telemetry 


async def cli():
    triage_agent = build_triage_agent()
    while True:
        user_input = input("please input your selection: ")
        if user_input.lower() == 'exit':
            break
        result = await triage_agent.run(user_input)
        print(result)

if __name__ == "__main__":
    settings = get_settings()
    myagent.core.telemetry.init_telemetry(endpoint=settings.PHOENIX_COLLECTOR_ENDPOINT)
    asyncio.run(cli())
