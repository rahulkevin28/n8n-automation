from __future__ import annotations

from collections import deque
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request, status
from app.models.db_models import UserRecord
from fastapi import Depends
from app.core.security import current_user


class InMemoryRateLimiter:
    """Small single-process fixed-window limiter for the Render free service."""

    def __init__(self) -> None:
        self._attempts: dict[tuple[str, str], deque[float]] = {}
        self._lock = Lock()

    def check(self, scope: str, key: str, limit: int, window_seconds: int = 60) -> None:
        now = monotonic()
        cutoff = now - window_seconds
        bucket_key = (scope, key)
        with self._lock:
            bucket = self._attempts.setdefault(bucket_key, deque())
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                retry_after = max(1, int(window_seconds - (now - bucket[0])))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please try again later.",
                    headers={"Retry-After": str(retry_after)},
                )
            bucket.append(now)

    @staticmethod
    def client_key(request: Request) -> str:
        return request.client.host if request.client else "unknown"


rate_limiter = InMemoryRateLimiter()


def limit_auth_requests(request: Request) -> None:
    rate_limiter.check("auth", rate_limiter.client_key(request), limit=10)


def limit_registration(request: Request) -> None:
    rate_limiter.check("register", rate_limiter.client_key(request), limit=5)


def limit_planning(request: Request, user: UserRecord = Depends(current_user)) -> None:
    rate_limiter.check("plan", user.id, limit=5)

