from typing import Any

from pydantic_ai import Agent


class SingleRun:
    def __init__(self, *args: Any, result_type: Any = str, **kwargs: Any) -> None:
        if "output_type" not in kwargs:
            kwargs["output_type"] = result_type
        if kwargs.get("tools") or kwargs.get("toolsets"):
            raise ValueError("SingleRun does not support tools")
        self.agent = Agent(*args, **kwargs)

    def run(self, input: str, **kwargs: Any):
        result = self.agent.run_sync(input, **kwargs)
        return result.output