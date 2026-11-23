import pytest
import httpx

from app.core.security import current_user
from app.models.db_models import UserRecord
from app.services.workflow_planner import InvalidToolSelection
from main import app


@pytest.fixture
def planning_client(monkeypatch):
    app.dependency_overrides[current_user] = lambda: UserRecord(
        id="planner-user", email="planner@example.com", password_hash="unused"
    )
    try:
        yield
    finally:
        app.dependency_overrides.clear()


def request(path, **kwargs):
    async def send():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return await client.post(path, **kwargs)

    return __import__("asyncio").run(send())


def test_anonymous_planning_is_rejected():
    response = request("/workflows/plan", json={"task_description": "uppercase hello"})
    assert response.status_code == 401


def test_authenticated_planning_works(planning_client, monkeypatch):
    expected = {
        "id": "wf-authenticated",
        "name": "Uppercase",
        "description": "Uppercase text",
        "steps": [{
            "id": "step-1",
            "tool": "text",
            "action": "uppercase",
            "inputs": {"text": "hello"},
            "true_next": None,
            "false_next": None,
            "max_retries": 0,
            "timeout_seconds": None,
        }],
    }
    monkeypatch.setattr("app.api.workflows.WorkflowPlanner.plan", lambda self, task: expected)

    response = request("/workflows/plan", json={"task_description": "uppercase hello"})

    assert response.status_code == 200
    assert response.json() == expected


def test_authenticated_planning_preserves_validation_errors(planning_client, monkeypatch):
    monkeypatch.setattr(
        "app.api.workflows.WorkflowPlanner.plan",
        lambda self, task: (_ for _ in ()).throw(InvalidToolSelection("Unsupported tool action")),
    )

    response = request("/workflows/plan", json={"task_description": "run an unsupported tool"})

    assert response.status_code == 422
    assert response.json()["detail"] == "Unsupported tool action"
