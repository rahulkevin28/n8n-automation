from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_create_workflow_returns_validated_workflow():
    payload = {
        "id": "workflow_001",
        "name": "Email Assistant",
        "description": "Find urgent emails",
        "steps": [
            {
                "id": "step_1",
                "tool": "email",
                "action": "find_urgent",
                "inputs": {},
            }
        ],
    }

    response = client.post("/workflows", json=payload)

    assert response.status_code == 201
    assert response.json() == payload


def test_create_workflow_rejects_invalid_input():
    payload = {
        "id": "workflow_001",
        "name": "Email Assistant",
        "description": "Find urgent emails",
        "steps": [{"id": "step_1", "action": "find_urgent"}],
    }

    response = client.post("/workflows", json=payload)

    assert response.status_code == 422
