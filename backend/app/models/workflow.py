from pydantic import BaseModel, Field
from typing import Any


class WorkflowStep(BaseModel):
    id: str
    tool: str
    action: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    true_next: str | None = None
    false_next: str | None = None
    max_retries: int = Field(default=0, ge=0, le=5)
    timeout_seconds: float | None = Field(default=None, gt=0, le=3600)


class Workflow(BaseModel):
    id: str
    name: str
    description: str
    steps: list[WorkflowStep] = Field(default_factory=list)
