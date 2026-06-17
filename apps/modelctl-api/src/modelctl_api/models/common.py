"""Common/shared Pydantic schemas."""

from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    version: str


class ErrorResponse(BaseModel):
    detail: str
    error_code: str | None = None


class SystemInfoResponse(BaseModel):
    version: str
    storage_used: str
    storage_free: str
    models_count: int
    active_models: list[str]
