import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.rate_limit import rate_limiter
from app.core.security import create_access_token, current_user, hash_password
from app.models.db_models import UserRecord
from app.services.workflow_planner import (
    InvalidPlannerResponse,
    InvalidToolSelection,
    WorkflowPlanningError,
)
from main import app


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    with rate_limiter._lock:
        rate_limiter._attempts.clear()
    yield
    with rate_limiter._lock:
        rate_limiter._attempts.clear()


@pytest.fixture
def security_api(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "http-security-test-secret-key-at-least-32-bytes")
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    db = testing_session()
    user = UserRecord(
        id="security-test-user",
        email="security-test@example.com",
        password_hash=hash_password("correct-horse-battery"),
    )
    db.add(user)
    db.commit()
    db.close()

    def override_get_db():
        session = testing_session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = override_get_db
    token = create_access_token(user.id)
    try:
        with TestClient(app) as client:
            yield client, token, testing_session
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()


def planner_result():
    return {
        "id": "http-planned-workflow",
        "name": "Uppercase",
        "description": "Uppercase text",
        "steps": [{
            "id": "step-1",
            "tool": "text",
            "action": "uppercase",
            "inputs": {"text": "hello"},
        }],
    }


def plan(client, token, description="uppercase hello"):
    return client.post(
        "/workflows/plan",
        json={"task_description": description},
        headers={"Authorization": f"Bearer {token}"},
    )


def assert_retry_after(response):
    assert response.status_code == 429
    assert int(response.headers["Retry-After"]) > 0


def test_planner_requires_auth_and_valid_token_reaches_mocked_planner(security_api, monkeypatch):
    client, token, _ = security_api
    calls = []

    def mocked_plan(self, description):
        calls.append(description)
        return planner_result()

    monkeypatch.setattr("app.api.workflows.WorkflowPlanner.plan", mocked_plan)

    anonymous = client.post("/workflows/plan", json={"task_description": "uppercase hello"})
    assert anonymous.status_code == 401

    authenticated = plan(client, token)
    assert authenticated.status_code == 200
    assert authenticated.json()["id"] == "http-planned-workflow"
    assert calls == ["uppercase hello"]


@pytest.mark.parametrize(
    ("error", "status_code", "detail"),
    [
        (InvalidToolSelection("Unsupported tool action"), 422, "Unsupported tool action"),
        (InvalidPlannerResponse("Invalid planner JSON"), 502, "Invalid planner JSON"),
        (WorkflowPlanningError("Planner unavailable"), 503, "Planner unavailable"),
    ],
)
def test_planner_errors_keep_http_status_and_detail(security_api, monkeypatch, error, status_code, detail):
    client, token, _ = security_api
    monkeypatch.setattr(
        "app.api.workflows.WorkflowPlanner.plan",
        lambda self, description: (_ for _ in ()).throw(error),
    )

    response = plan(client, token)

    assert response.status_code == status_code
    assert response.json()["detail"] == detail


def test_register_allows_five_requests_then_returns_429(security_api):
    client, _, _ = security_api
    responses = [
        client.post("/auth/register", json={"email": f"user-{index}@example.com", "password": "password-123"})
        for index in range(5)
    ]

    assert all(response.status_code == 201 for response in responses)
    limited = client.post(
        "/auth/register",
        json={"email": "user-over-limit@example.com", "password": "password-123"},
    )
    assert_retry_after(limited)
    with security_api[2]() as db:
        assert db.query(UserRecord).count() == 6  # seed user plus five successful registrations


def test_login_allows_ten_requests_then_returns_429(security_api):
    client, _, _ = security_api
    payload = {"email": "security-test@example.com", "password": "correct-horse-battery"}
    responses = [client.post("/auth/login", json=payload) for _ in range(10)]

    assert all(response.status_code == 200 for response in responses)
    assert_retry_after(client.post("/auth/login", json=payload))


def test_planning_allows_five_requests_per_user_then_returns_429(security_api, monkeypatch):
    client, token, testing_session = security_api
    monkeypatch.setattr("app.api.workflows.WorkflowPlanner.plan", lambda self, description: planner_result())
    responses = [plan(client, token) for _ in range(5)]

    assert all(response.status_code == 200 for response in responses)
    assert_retry_after(plan(client, token))

    with testing_session() as db:
        second_user = UserRecord(
            id="another-security-user",
            email="another-security-user@example.com",
            password_hash="unused",
        )
        db.add(second_user)
        db.commit()
    second_token = create_access_token("another-security-user")
    assert plan(client, second_token).status_code == 200


def test_planning_body_limit_rejects_over_8_kib_and_allows_normal_request(security_api, monkeypatch):
    client, token, _ = security_api
    monkeypatch.setattr("app.api.workflows.WorkflowPlanner.plan", lambda self, description: planner_result())

    oversized = plan(client, token, "x" * (8 * 1024))
    assert oversized.status_code == 413
    assert plan(client, token).status_code == 200


def test_workflow_body_limit_rejects_over_64_kib_and_allows_create_update(security_api):
    client, token, _ = security_api
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "id": "size-limited-workflow",
        "name": "Small workflow",
        "description": "small",
        "steps": [],
    }

    created = client.post("/workflows", json=payload, headers=headers)
    assert created.status_code == 201
    updated = {**payload, "name": "Updated workflow"}
    assert client.put(f"/workflows/{payload['id']}", json=updated, headers=headers).status_code == 200

    oversized_create = {**payload, "id": "too-large-create", "description": "x" * (64 * 1024)}
    assert client.post("/workflows", json=oversized_create, headers=headers).status_code == 413
    oversized_update = {**updated, "description": "x" * (64 * 1024)}
    assert client.put(
        f"/workflows/{payload['id']}", json=oversized_update, headers=headers
    ).status_code == 413
