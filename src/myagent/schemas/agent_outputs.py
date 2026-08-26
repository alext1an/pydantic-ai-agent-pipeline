from pydantic import BaseModel, Field

class TriageItem(BaseModel):
    suggestion: str = Field(description="suggested next action", min_length=1, max_length=50)

class TriageResult(BaseModel):
    items: list[TriageItem] = Field(
        default_factory=list,
        min_length=3,
        max_length=3,
        description="list of triage items, descending order by relevance"
    )

