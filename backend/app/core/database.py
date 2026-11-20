from collections.abc import Generator
import os
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


BACKEND_DIR = Path(__file__).resolve().parents[2]
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{(BACKEND_DIR / 'flowforge.db').as_posix()}")


class Base(DeclarativeBase):
    pass


_is_sqlite = DATABASE_URL.startswith("sqlite")
engine_options = {"connect_args": {"check_same_thread": False}} if _is_sqlite else {"pool_pre_ping": True, "pool_size": 5, "max_overflow": 10}
engine = create_engine(DATABASE_URL, **engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables() -> None:
    from app.models.db_models import ExecutionRecord, ExecutionStepRecord, UserRecord, WorkflowRecord

    Base.metadata.create_all(bind=engine)
    # Lightweight, additive migration for databases created before authentication.
    with engine.begin() as connection:
        for table in ("workflows", "executions"):
            columns = {column["name"] for column in inspect(connection).get_columns(table)}
            if "user_id" not in columns:
                connection.execute(text(f"ALTER TABLE {table} ADD COLUMN user_id VARCHAR REFERENCES users(id)"))
