"""Pydantic schemas for model CRUD endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ArtifactResponse(BaseModel):
    name: str
    role: str
    path: str
    size: int
    file_type: str
    sha256: str


class ModelResponse(BaseModel):
    id: str
    name: str
    type: str
    provider: str
    repo_id: str
    status: str
    installed_at: str | None = None
    storage_path: str
    artifacts: list[ArtifactResponse]
    metadata: dict = Field(default_factory=dict)


class ModelListResponse(BaseModel):
    models: list[ModelResponse]
    total: int


class InstallRequest(BaseModel):
    repo_id: str = Field(...,
                         description="HuggingFace repository ID, e.g. 'org/model'")
    filename: str = Field(..., description="GGUF filename to download")
    model_type: str | None = Field(
        None, description="Override model type (chat, embedding, reranker, vision, experimental)"
    )


class DownloadProgressResponse(BaseModel):
    model_id: str
    repo_id: str = ""
    filename: str = ""
    status: str
    downloaded_bytes: int = 0
    total_bytes: int = 0
    progress_pct: int = 0
    error: str | None = None
