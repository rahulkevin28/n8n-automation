import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from main import app


@pytest.fixture
def client_with_database():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
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


def workflow(workflow_id="saved-1", name="Saved workflow"):
    return {"id": workflow_id, "name": name, "description": "Persisted description", "steps": [
        {"id": "step-1", "tool": "text", "action": "uppercase", "inputs": {"text": "hello"}}
    ]}


def test_create_list_and_retrieve_workflow(client_with_database):
    client = client_with_database
    payload = workflow()
    created = client.post("/workflows", json=payload)
    assert created.status_code == 201
    assert created.json() == payload
    assert client.get("/workflows").json() == [payload]
    assert client.get("/workflows/saved-1").json() == payload


def test_update_workflow_persists_new_definition(client_with_database):
    client = client_with_database
    client.post("/workflows", json=workflow())
    updated = workflow(name="Updated workflow")
    updated["steps"][0]["inputs"]["text"] = "updated"
    response = client.put("/workflows/saved-1", json=updated)
    assert response.status_code == 200
    assert client.get("/workflows/saved-1").json() == updated


def test_missing_and_duplicate_workflows_have_clear_errors(client_with_database):
    client = client_with_database
    assert client.get("/workflows/missing").status_code == 404
    assert client.put("/workflows/missing", json=workflow("missing")).status_code == 404
    client.post("/workflows", json=workflow())
    assert client.post("/workflows", json=workflow()).status_code == 409
