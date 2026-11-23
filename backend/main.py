import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.workflows import router as workflows_router
from app.api.auth import router as auth_router
from app.core.database import DATABASE_URL, create_tables


# SQLite remains convenient for local development. PostgreSQL schema changes
# are applied only by the deployment's Alembic command.
if DATABASE_URL.startswith("sqlite:"):
    create_tables()

app = FastAPI(
    title="FlowForge AI",
    description="AI-powered workflow automation platform",
    version="0.1.0",
)


@app.middleware("http")
async def request_size_limit(request: Request, call_next):
    if request.method in {"POST", "PUT", "PATCH"}:
        if request.url.path == "/workflows/plan":
            limit = 8 * 1024
        elif request.url.path == "/workflows" or (request.url.path.startswith("/workflows/") and request.method == "PUT"):
            limit = 64 * 1024
        else:
            limit = None
        if limit is not None:
            content_length = request.headers.get("content-length")
            try:
                if content_length is not None and int(content_length) > limit:
                    return JSONResponse(status_code=413, content={"detail": "Request body is too large"})
            except ValueError:
                # An invalid length is not trusted; enforce the limit from the body stream.
                pass

            body_chunks = []
            body_size = 0
            async for chunk in request.stream():
                body_size += len(chunk)
                if body_size > limit:
                    return JSONResponse(status_code=413, content={"detail": "Request body is too large"})
                body_chunks.append(chunk)

            body = b"".join(body_chunks)
            # BaseHTTPMiddleware replays this cached body to the downstream app.
            request._body = body
    return await call_next(request)

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

