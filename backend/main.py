import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.workflows import router as workflows_router
from app.api.auth import router as auth_router
from app.core.database import create_tables


create_tables()

app = FastAPI(
    title="FlowForge AI",
    description="AI-powered workflow automation platform",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("FRONTEND_ORIGIN", "http://localhost:5173").split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(auth_router)
app.include_router(workflows_router)


@app.get("/")
def home():
    return {
        "message": "Welcome to FlowForge AI!",
        "status": "running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }
import os

