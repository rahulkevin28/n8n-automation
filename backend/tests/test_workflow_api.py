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
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[current_user] = lambda: UserRecord(
        id="workflow-api-user", email="workflow-api@example.com", password_hash="unused"
    )

    client = TestClient(app)
    try:
        yield client
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_create_workflow_returns_validated_workflow(client):
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
    assert response.json() == {
        **payload,
        "steps": [
            {
                **payload["steps"][0],
                "true_next": None,
                "false_next": None,
                "max_retries": 0,
                "timeout_seconds": None,
            }
        ],
    }


def test_create_workflow_rejects_invalid_input(client):
    payload = {
        "id": "workflow_001",
        "name": "Email Assistant",
        "description": "Find urgent emails",
        "steps": [{"id": "step_1", "action": "find_urgent"}],
    }

    response = client.post("/workflows", json=payload)

    assert response.status_code == 422
