from pydantic_ai import Agent

class SingleRun:
    agent: Agent

    def run(self, input):
        if 'tool' in input:
            raise ValueError("input should not contain tool")
        result = self.agent.run_sync(input)
        return result.output