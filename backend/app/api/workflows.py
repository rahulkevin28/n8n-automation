import json
import reprlib
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.workflow import Workflow
from app.engine.executor import WorkflowExecutor
from app.engine.registry import create_default_registry
from app.core.database import get_db
from app.core.security import current_user
from app.core.rate_limit import limit_planning
from app.models.db_models import ExecutionRecord, ExecutionStepRecord, WorkflowRecord, UserRecord
from app.services.workflow_planner import (
    InvalidPlannerResponse,
    InvalidToolSelection,
    WorkflowPlanner,
    WorkflowPlanningError,
)


router = APIRouter()


@router.get("/dashboard/stats")
def dashboard_stats(user: UserRecord = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    total_workflows = db.scalar(select(func.count()).select_from(WorkflowRecord).where(WorkflowRecord.user_id == user.id)) or 0
    total_executions = db.scalar(select(func.count()).select_from(ExecutionRecord).where(ExecutionRecord.user_id == user.id)) or 0
    successful = db.scalar(select(func.count()).select_from(ExecutionRecord).where(ExecutionRecord.user_id == user.id, ExecutionRecord.status == "success")) or 0
    failed = db.scalar(select(func.count()).select_from(ExecutionRecord).where(ExecutionRecord.user_id == user.id, ExecutionRecord.status == "failed")) or 0
    recent_workflows = db.scalars(select(WorkflowRecord).where(WorkflowRecord.user_id == user.id).order_by(WorkflowRecord.created_at.desc()).limit(5)).all()
    recent_executions = db.scalars(select(ExecutionRecord).where(ExecutionRecord.user_id == user.id).order_by(ExecutionRecord.created_at.desc()).limit(8)).all()
    return {
        "total_workflows": total_workflows,
        "total_executions": total_executions,
        "successful_executions": successful,
        "failed_executions": failed,
        "success_rate": round(successful / total_executions * 100, 1) if total_executions else 0,
        "recent_workflows": [{"workflow_id": item.id, "name": item.name, "description": item.description, "created_at": _timestamp(item.created_at)} for item in recent_workflows],
        "recent_executions": [_execution_summary(item) for item in recent_executions],
    }


class WorkflowPlanRequest(BaseModel):
    task_description: str = Field(min_length=1, max_length=4000)


class WorkflowExecutionRequest(BaseModel):
    workflow: Workflow
    approved: bool = False


@router.post("/workflows", response_model=Workflow, status_code=status.HTTP_201_CREATED)
def create_workflow(workflow: Workflow, user: UserRecord = Depends(current_user), db: Session = Depends(get_db)) -> Workflow:
    if db.get(WorkflowRecord, workflow.id) is not None:
        raise HTTPException(status_code=409, detail="A workflow with this ID already exists")
    record = WorkflowRecord(
        id=workflow.id,
        name=workflow.name,
        description=workflow.description,
        definition=workflow.model_dump(mode="json"), user_id=user.id,
    )
    try:
        db.add(record)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="Workflow could not be saved") from exc
    return workflow


@router.get("/workflows", response_model=list[Workflow])
def list_workflows(user: UserRecord = Depends(current_user), db: Session = Depends(get_db)) -> list[Workflow]:
    records = db.scalars(select(WorkflowRecord).where(WorkflowRecord.user_id == user.id).order_by(WorkflowRecord.created_at.desc())).all()
    return [Workflow.model_validate(record.definition) for record in records]


@router.get("/workflows/{workflow_id}", response_model=Workflow)
def get_workflow(workflow_id: str, user: UserRecord = Depends(current_user), db: Session = Depends(get_db)) -> Workflow:
    record = db.scalar(select(WorkflowRecord).where(WorkflowRecord.id == workflow_id, WorkflowRecord.user_id == user.id))
    if record is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return Workflow.model_validate(record.definition)


@router.put("/workflows/{workflow_id}", response_model=Workflow)
def update_workflow(workflow_id: str, workflow: Workflow, user: UserRecord = Depends(current_user), db: Session = Depends(get_db)) -> Workflow:
    if workflow.id != workflow_id:
        raise HTTPException(status_code=422, detail="Workflow ID does not match the URL")
    record = db.scalar(select(WorkflowRecord).where(WorkflowRecord.id == workflow_id, WorkflowRecord.user_id == user.id))
    if record is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    record.name = workflow.name
    record.description = workflow.description
    record.definition = workflow.model_dump(mode="json")
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="Workflow could not be updated") from exc
    return workflow


@router.post("/workflows/plan", response_model=Workflow)
def plan_workflow(request: WorkflowPlanRequest, user: UserRecord = Depends(current_user), _limit: None = Depends(limit_planning)) -> Workflow:
    try:
        return WorkflowPlanner().plan(request.task_description)
    except InvalidToolSelection as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except InvalidPlannerResponse as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except WorkflowPlanningError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/workflows/execute")
def execute_workflow(request: WorkflowExecutionRequest, user: UserRecord = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    if request.approved is not True:
        raise HTTPException(status_code=403, detail="Explicit approval is required to execute a workflow")

    registry = create_default_registry()
    unavailable = [
        f"{step.tool}.{step.action}"
        for step in request.workflow.steps
        if registry.get(step.tool, step.action) is None
    ]
    if unavailable:
        raise HTTPException(
            status_code=422,
            detail={"message": "Workflow contains unavailable tool actions", "actions": unavailable},
        )

    try:
        result = WorkflowExecutor(registry).execute(request.workflow)
    except Exception as exc:
        # Workflow validation errors should be reported as client input errors.
        from pydantic import ValidationError

        if isinstance(exc, (ValidationError, ValueError)):
            raise HTTPException(status_code=422, detail="Workflow validation failed") from exc
        raise HTTPException(status_code=500, detail="Workflow execution failed") from exc
    workflow_data = request.workflow.model_dump(mode="json")
    execution_id = str(uuid4())
    try:
        workflow_record = db.scalar(select(WorkflowRecord).where(WorkflowRecord.id == request.workflow.id, WorkflowRecord.user_id == user.id))
        if workflow_record is None:
            workflow_record = WorkflowRecord(
                id=request.workflow.id,
                name=request.workflow.name,
                description=request.workflow.description,
                definition=workflow_data, user_id=user.id,
            )
            db.add(workflow_record)
        else:
            workflow_record.name = request.workflow.name
            workflow_record.description = request.workflow.description
            workflow_record.definition = workflow_data
        db.flush()

        execution_record = ExecutionRecord(
            id=execution_id,
            workflow_id=request.workflow.id,
            status=result.status,
            user_id=user.id,
        )
        execution_record.steps = [
            ExecutionStepRecord(
                record_id=str(uuid4()),
                step_id=step.id,
                position=index,
                status=step.status,
                attempts=step.attempts,
                output=_json_safe(step.output),
                error=step.error,
            )
            for index, step in enumerate(result.steps)
        ]
        db.add(execution_record)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="Execution completed but could not be saved") from exc

    response = result.to_dict()
    response["execution_id"] = execution_id
    for step in response["steps"]:
        step["output"] = _json_safe(step["output"])
    return response


@router.get("/workflows/{workflow_id}/executions")
def list_workflow_executions(workflow_id: str, user: UserRecord = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    workflow = db.scalar(select(WorkflowRecord).where(WorkflowRecord.id == workflow_id, WorkflowRecord.user_id == user.id))
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    executions = db.scalars(
        select(ExecutionRecord).where(ExecutionRecord.workflow_id == workflow_id)
        .order_by(ExecutionRecord.created_at.desc())
    ).all()
    return {
        "workflow_id": workflow_id,
        "executions": [_execution_summary(item) for item in executions],
    }


@router.get("/executions/{execution_id}")
def get_execution(execution_id: str, user: UserRecord = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    execution = db.scalar(select(ExecutionRecord).where(ExecutionRecord.id == execution_id, ExecutionRecord.user_id == user.id))
    if execution is None:
        raise HTTPException(status_code=404, detail="Execution not found")
    return {
        **_execution_summary(execution),
        "steps": [
            {
                "step_id": step.step_id,
                "status": step.status,
                "attempts": step.attempts,
                "output": step.output,
                "error": step.error,
            }
            for step in execution.steps
        ],
    }


def _execution_summary(execution: ExecutionRecord) -> dict:
    return {
        "execution_id": execution.id,
        "workflow_id": execution.workflow_id,
        "status": execution.status,
        "created_at": _timestamp(execution.created_at),
    }


def _timestamp(value: datetime) -> str:
    return value.isoformat()


def _json_safe(value):
    try:
        return json.loads(json.dumps(value, default=reprlib.repr, allow_nan=False))
    except (TypeError, ValueError, OverflowError):
        return {"serialization_error": "Output could not be represented as JSON", "repr": reprlib.repr(value)}
