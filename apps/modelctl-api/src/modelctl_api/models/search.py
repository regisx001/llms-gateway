"""Pydantic schemas for search/inspect endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    repo_id: str
    type: str
    downloads: int
    likes: int
    tags: list[str]
    license: str


class SearchResults(BaseModel):
    results: list[SearchResult]
    total: int


class GGUFFile(BaseModel):
    filename: str
    size: int = 0


class InspectResponse(BaseModel):
    repo_id: str
    type: str
    description: str
    downloads: int
    likes: int
    license: str
    pipeline_tag: str
    library_name: str
    gguf_files: list[GGUFFile]
    total_files: int
