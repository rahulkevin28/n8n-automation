import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from main import app


@pytest.fixture
def client_with_database():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    # Avoid app lifespan startup here: production startup creates the real local DB.
    client = TestClient(app)
    try:
        yield client
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()


def approved_workflow():
    return {
        "approved": True,
        "workflow": {
            "id": "persisted-workflow",
            "name": "Uppercase",
            "description": "Uppercase text",
            "steps": [{
                "id": "uppercase-step",
                "tool": "text",
                "action": "uppercase",
                "inputs": {"text": "hello"},
            }],
        },
    }


def test_approved_execution_persists_workflow_execution_and_step(client_with_database):
    client = client_with_database
    response = client.post("/workflows/execute", json=approved_workflow())
    assert response.status_code == 200
    executed = response.json()
    assert executed["status"] == "success"
    assert executed["steps"][0]["output"] == "HELLO"

    history = client.get("/workflows/persisted-workflow/executions")
    assert history.status_code == 200
    assert len(history.json()["executions"]) == 1
    entry = history.json()["executions"][0]
    assert entry["execution_id"] == executed["execution_id"]
    assert entry["created_at"]

    detail = client.get(f"/executions/{executed['execution_id']}")
    assert detail.status_code == 200
    assert detail.json()["steps"] == [{
        "step_id": "uppercase-step",
        "status": "success",
        "output": "HELLO",
        "error": None,
    }]


def test_unapproved_execution_is_not_persisted(client_with_database):
    request = approved_workflow()
    request["approved"] = False
    response = client_with_database.post("/workflows/execute", json=request)
    assert response.status_code == 403
    assert client_with_database.get("/workflows/persisted-workflow/executions").status_code == 404


def test_missing_workflow_and_execution_history_return_404(client_with_database):
    assert client_with_database.get("/workflows/missing/executions").status_code == 404
    assert client_with_database.get("/executions/missing").status_code == 404


def test_failed_execution_and_step_statuses_are_persisted(client_with_database):
    request = approved_workflow()
    request["workflow"]["steps"] = [
        {"id": "failed", "tool": "calculator", "action": "divide", "inputs": {"a": 4, "b": 0}},
        {"id": "skipped", "tool": "text", "action": "uppercase", "inputs": {"text": "unused"}},
    ]
    response = client_with_database.post("/workflows/execute", json=request)
    assert response.status_code == 200
    detail = client_with_database.get(f"/executions/{response.json()['execution_id']}")
    assert detail.json()["status"] == "failed"
    assert [step["status"] for step in detail.json()["steps"]] == ["failed", "skipped"]
    assert detail.json()["steps"][0]["error"] == "cannot divide by zero"
