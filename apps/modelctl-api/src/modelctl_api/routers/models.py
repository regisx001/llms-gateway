"""Model CRUD and lifecycle endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from modelctl_api.dependencies import get_model_service
from modelctl_api.models.model import (
    InstallRequest,
    ModelListResponse,
    ModelResponse,
)
from modelctl_api.services.model_service import ModelService

router = APIRouter(tags=["Models"])


@router.get("/models", response_model=ModelListResponse)
async def list_models(
    type: str | None = Query(
        None, description="Filter by model type (chat, embedding, etc.)"),
    status: str | None = Query(
        None, description="Filter by status (installed, downloading, etc.)"),
    svc: ModelService = Depends(get_model_service),
):
    """List all registered models, with optional type/status filters."""
    models = svc.list_models(type_filter=type, status_filter=status)
    return {"models": models, "total": len(models)}


@router.get("/models/{model_id}", response_model=ModelResponse)
async def get_model(
    model_id: str,
    svc: ModelService = Depends(get_model_service),
):
    """Get detailed information about a specific model."""
    return svc.get_model(model_id)


@router.post("/models/install", response_model=ModelResponse, status_code=202)
async def install_model(
    body: InstallRequest,
    svc: ModelService = Depends(get_model_service),
):
    """Install a model from HuggingFace — download, validate, and register."""
    return svc.install_model(
        repo_id=body.repo_id,
        filename=body.filename,
        model_type=body.model_type,
    )


@router.delete("/models/{model_id}", response_model=ModelResponse)
async def remove_model(
    model_id: str,
    svc: ModelService = Depends(get_model_service),
):
    """Remove a model: delete files, clear active state, remove from registry."""
    return svc.remove_model(model_id)


@router.post("/models/{model_id}/activate", response_model=ModelResponse)
async def activate_model(
    model_id: str,
    svc: ModelService = Depends(get_model_service),
):
    """Activate a model for serving — create symlink and update active state."""
    return svc.activate_model(model_id)


@router.post("/models/{model_id}/deactivate", response_model=ModelResponse)
async def deactivate_model(
    model_id: str,
    svc: ModelService = Depends(get_model_service),
):
    """Deactivate a model — remove symlink and clear active state."""
    return svc.deactivate_model(model_id)
