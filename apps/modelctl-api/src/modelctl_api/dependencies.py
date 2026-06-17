"""FastAPI dependency injection — provides service instances."""

from __future__ import annotations

from fastapi import Request

from modelctl_api.services.model_service import ModelService
from modelctl_api.services.search_service import SearchService
from modelctl_api.services.system_service import SystemService


def get_model_service(request: Request) -> ModelService:
    return request.app.state.model_service


def get_search_service(request: Request) -> SearchService:
    return request.app.state.search_service


def get_system_service(request: Request) -> SystemService:
    return request.app.state.system_service
