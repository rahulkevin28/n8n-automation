from collections.abc import Mapping
from typing import Any

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def error_response(
    status_code: int,
    code: str,
    message: str,
    details: Any = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details}},
        headers=dict(headers or {}),
    )


def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict) and detail.get("actions"):
        return error_response(
            exc.status_code,
            "WORKFLOW_ACTION_UNAVAILABLE",
            "The workflow contains unavailable actions.",
            {"actions": detail["actions"]},
            exc.headers,
        )

    code, message = _http_error_info(exc.status_code, detail)
    return error_response(exc.status_code, code, message, None, exc.headers)


def validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        {"location": list(error.get("loc", ())), "message": error.get("msg", "Invalid value")}
        for error in exc.errors()
    ]
    return error_response(422, "VALIDATION_ERROR", "The request could not be validated.", details)


def unexpected_exception_handler(_request: Request, _exc: Exception) -> JSONResponse:
    return error_response(500, "INTERNAL_SERVER_ERROR", "An unexpected server error occurred.")


def _http_error_info(status_code: int, detail: Any) -> tuple[str, str]:
    if status_code == 401:
        if detail == "Invalid email or password":
            return "INVALID_CREDENTIALS", "The email or password is incorrect."
        if detail == "Authentication required":
            return "AUTHENTICATION_REQUIRED", "Authentication is required."
        return "INVALID_TOKEN", "The authentication token is invalid or expired."
    if status_code == 403:
        return "EXECUTION_NOT_APPROVED", "Explicit approval is required to execute a workflow."
    if status_code == 404:
        if detail == "Execution not found":
            return "EXECUTION_NOT_FOUND", "The requested execution was not found."
        return "WORKFLOW_NOT_FOUND", "The requested workflow was not found."
    if status_code == 409:
        return "ACCOUNT_ALREADY_EXISTS", "An account with that email already exists."
    if status_code == 413:
        return "REQUEST_BODY_TOO_LARGE", "Request body is too large."
    if status_code == 429:
        return "RATE_LIMITED", "Too many requests. Please try again later."
    if status_code == 502:
        return "PLANNER_INVALID_RESPONSE", "The workflow planner returned an invalid response."
    if status_code == 503:
        if detail == "Authentication is not configured":
            return "AUTHENTICATION_NOT_CONFIGURED", "Authentication is not configured."
        if detail == "Workflow could not be saved":
            return "WORKFLOW_SAVE_FAILED", "The workflow could not be saved."
        if detail == "Workflow could not be updated":
            return "WORKFLOW_UPDATE_FAILED", "The workflow could not be updated."
        if detail == "Execution completed but could not be saved":
            return "EXECUTION_SAVE_FAILED", "The execution completed but could not be saved."
        return "SERVICE_UNAVAILABLE", "The service is temporarily unavailable."
    if status_code == 422:
        if isinstance(detail, str) and ("unavailable tool action" in detail.lower() or "unsupported tool action" in detail.lower()):
            return "WORKFLOW_ACTION_UNAVAILABLE", "The workflow contains an unavailable action."
        if detail == "Workflow ID does not match the URL":
            return "WORKFLOW_ID_MISMATCH", "The workflow ID does not match the URL."
        return "WORKFLOW_VALIDATION_FAILED", "The workflow request could not be validated."
    if status_code == 500:
        return "INTERNAL_SERVER_ERROR", "An unexpected server error occurred."
    return f"HTTP_{status_code}", "The request could not be completed."
