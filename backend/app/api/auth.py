from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from pydantic.functional_validators import AfterValidator
from typing import Annotated
import re
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import limit_auth_requests, limit_registration
from app.core.security import create_access_token, current_user, hash_password, verify_password
from app.models.db_models import UserRecord

router = APIRouter(prefix="/auth")


def valid_email(value: str) -> str:
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
        raise ValueError("Invalid email address")
    return value.lower()


class Credentials(BaseModel):
    email: Annotated[str, AfterValidator(valid_email)]
    password: str = Field(min_length=8, max_length=128)


@router.post("/register", status_code=201, dependencies=[Depends(limit_registration)])
def register(credentials: Credentials, db: Session = Depends(get_db)):
    if db.scalar(select(UserRecord).where(UserRecord.email == credentials.email)):
        raise HTTPException(status_code=409, detail="An account with that email already exists")
    user = UserRecord(id=str(uuid4()), email=credentials.email, password_hash=hash_password(credentials.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with that email already exists") from exc
    return {"access_token": create_access_token(user.id), "token_type": "bearer"}


@router.post("/login", dependencies=[Depends(limit_auth_requests)])
def login(credentials: Credentials, db: Session = Depends(get_db)):
    user = db.scalar(select(UserRecord).where(UserRecord.email == credentials.email))
    if user is None or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"access_token": create_access_token(user.id), "token_type": "bearer"}


@router.get("/me")
def me(user: UserRecord = Depends(current_user)):
    return {"id": user.id, "email": user.email, "created_at": user.created_at.isoformat()}
