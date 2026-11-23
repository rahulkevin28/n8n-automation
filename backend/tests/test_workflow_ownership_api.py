import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import current_user
from app.models.db_models import UserRecord
from main import app


@pytest.fixture
def ownership_api():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    sessions = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    db = sessions()
    owner = UserRecord(id="owner", email="owner@example.com", password_hash="unused")
    other = UserRecord(id="other", email="other@example.com", password_hash="unused")
    db.add_all([owner, other])
    db.commit()
    db.close()
    active_user = {"value": owner}

    def override_get_db():
        session = sessions()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[current_user] = lambda: active_user["value"]
    try:
        with TestClient(app) as client:
            yield client, active_user, owner, other
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()


def workflow_payload(workflow_id="owned-workflow"):
    return {
        "id": workflow_id,
        "name": "Owned workflow",
        "description": "Private workflow",
        "steps": [{"id": "step", "tool": "text", "action": "uppercase", "inputs": {"text": "hello"}}],
    }


def test_cross_user_workflow_and_execution_access_is_denied(ownership_api):
    client, active_user, _owner, other = ownership_api
    created = client.post("/workflows", json=workflow_payload())
    assert created.status_code == 201
    executed = client.post("/workflows/execute", json={"workflow": workflow_payload(), "approved": True})
    assert executed.status_code == 200
    execution_id = executed.json()["execution_id"]

    active_user["value"] = other
    headers = {"Authorization": "Bearer test-overridden-user"}

    for response in (
        client.get("/workflows/owned-workflow", headers=headers),
        client.put("/workflows/owned-workflow", json=workflow_payload(), headers=headers),
        client.get("/workflows/owned-workflow/executions", headers=headers),
        client.get(f"/executions/{execution_id}", headers=headers),
    ):
        assert response.status_code == 404
        assert response.json()["error"]["code"] in {"WORKFLOW_NOT_FOUND", "EXECUTION_NOT_FOUND"}

    assert client.get("/workflows", headers=headers).json() == []


def test_cross_user_execution_by_existing_workflow_id_is_not_run_or_saved(ownership_api):
    client, active_user, _owner, other = ownership_api
    assert client.post("/workflows", json=workflow_payload()).status_code == 201
    active_user["value"] = other

    response = client.post("/workflows/execute", json={"workflow": workflow_payload(), "approved": True})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "WORKFLOW_NOT_FOUND"


def test_workflow_endpoints_require_authentication():
    app.dependency_overrides.clear()
    response = TestClient(app).get("/workflows")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"
