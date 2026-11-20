import pytest
from pydantic import ValidationError

from app.models.workflow import Workflow


def test_valid_workflow():
    workflow = Workflow(
        id="workflow_001",
        name="Email Assistant",
        description="Find and summarise urgent emails",
        steps=[
            {
                "id": "step_1",
                "tool": "email",
                "action": "find_urgent",
                "inputs": {}
            }
        ]
    )

    assert workflow.name == "Email Assistant"
    assert len(workflow.steps) == 1


def test_invalid_workflow():
    with pytest.raises(ValidationError):
        Workflow(
            id="workflow_001",
            name="Email Assistant",
            description="Find urgent emails",
            steps=[
                {
                    "id": "step_1",
                    "action": "find_urgent"
                }
            ]
        )