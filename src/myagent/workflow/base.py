from typing import Any

from pydantic_ai import Agent


class SingleRun:
    def __init__(
        self,
        *args: Any,
        output_type: Any = str,
        instrument: bool = False,
        **kwargs: Any,
    ) -> None:
        if "output_type" not in kwargs:
            kwargs["output_type"] = output_type
        if kwargs.get("tools") or kwargs.get("toolsets"):
            raise ValueError("SingleRun does not support tools")
        self.agent = Agent(*args, **kwargs)
        self.agent.instrument = instrument

    async def run(self, input: str, **kwargs: Any):
        result = await self.agent.run(input, **kwargs)
        return result.output