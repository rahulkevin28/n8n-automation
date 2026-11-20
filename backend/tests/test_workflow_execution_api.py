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
    client = TestClient(app)
    try:
        yield client
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()


def request_body(approved=True, steps=None):
    return {
        "approved": approved,
        "workflow": {
            "id": "workflow_api",
            "name": "API workflow",
            "description": "Test execution endpoint",
            "steps": steps if steps is not None else [
                {"id": "step_1", "tool": "text", "action": "uppercase", "inputs": {"text": "hello"}}
            ],
        },
    }


def test_approved_workflow_executes_and_returns_step_output(client_with_database):
    response = client_with_database.post("/workflows/execute", json=request_body())
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["steps"] == [{"id": "step_1", "status": "success", "output": "HELLO", "error": None}]


def test_unapproved_workflow_is_rejected_without_execution(client_with_database):
    response = client_with_database.post("/workflows/execute", json=request_body(approved=False))
    assert response.status_code == 403
    assert response.json()["detail"] == "Explicit approval is required to execute a workflow"


def test_failed_step_is_returned_in_execution_result(client_with_database):
    response = client_with_database.post("/workflows/execute", json=request_body(steps=[
        {"id": "step_1", "tool": "calculator", "action": "divide", "inputs": {"a": 1, "b": 0}},
        {"id": "step_2", "tool": "text", "action": "uppercase", "inputs": {"text": "later"}},
    ]))
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "failed"
    assert result["steps"][0]["status"] == "failed"
    assert result["steps"][0]["error"] == "cannot divide by zero"
    assert result["steps"][1]["status"] == "skipped"


def test_unavailable_tool_is_rejected_before_any_step_runs(client_with_database):
    response = client_with_database.post("/workflows/execute", json=request_body(steps=[
        {"id": "step_1", "tool": "text", "action": "uppercase", "inputs": {"text": "should not run"}},
        {"id": "step_2", "tool": "unknown", "action": "run", "inputs": {}},
    ]))
    assert response.status_code == 422
    assert response.json()["detail"]["actions"] == ["unknown.run"]


def test_invalid_workflow_is_rejected_by_request_validation(client_with_database):
    response = client_with_database.post("/workflows/execute", json={
        "approved": True,
        "workflow": {"id": "bad", "name": "bad", "description": "bad", "steps": [
            {"id": "step_1", "tool": "calculator", "action": "add", "inputs": "invalid"}
        ]},
    })
    assert response.status_code == 422
