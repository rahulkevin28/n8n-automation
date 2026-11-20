"""Copy FlowForge records from SQLite to another SQLAlchemy database.

Usage: python scripts/migrate_sqlite_to_postgres.py --source sqlite:///./flowforge.db --target postgresql+psycopg://...
"""
import argparse
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.core.database import Base
from app.models.db_models import ExecutionRecord, ExecutionStepRecord, UserRecord, WorkflowRecord

def copy_records(source_url: str, target_url: str) -> tuple[int, int, int, int]:
    source = create_engine(source_url, connect_args={"check_same_thread": False} if source_url.startswith("sqlite") else {})
    target = create_engine(target_url, pool_pre_ping=True)
    Base.metadata.create_all(target)
    counts = [0, 0, 0, 0]
    with Session(source) as src, Session(target) as dst:
        for model, index in ((UserRecord, 0), (WorkflowRecord, 1), (ExecutionRecord, 2), (ExecutionStepRecord, 3)):
            for record in src.scalars(select(model)):
                if dst.get(model, record.id if model is not ExecutionStepRecord else record.record_id) is None:
                    dst.add(model(**{column.name: getattr(record, column.name) for column in model.__table__.columns}))
                    counts[index] += 1
        dst.commit()
    source.dispose(); target.dispose()
    return tuple(counts)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate FlowForge SQLite data to PostgreSQL")
    parser.add_argument("--source", required=True)
    parser.add_argument("--target", required=True)
    args = parser.parse_args()
    print("Migrating records without exposing credentials...")
    print("Copied users, workflows, executions, steps:", copy_records(args.source, args.target))
