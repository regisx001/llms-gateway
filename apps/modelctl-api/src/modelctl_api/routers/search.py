"""Search and inspect endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from modelctl_api.dependencies import get_search_service
from modelctl_api.models.search import InspectResponse, SearchResult, SearchResults
from modelctl_api.services.search_service import SearchService

router = APIRouter(tags=["Search"])


@router.get("/search", response_model=SearchResults)
async def search(
    q: str = Query(..., description="Search query for HuggingFace models"),
    limit: int = Query(15, ge=1, le=50, description="Maximum results"),
    svc: SearchService = Depends(get_search_service),
):
    """Search HuggingFace for GGUF model repositories."""
    results = svc.search(q, limit=limit)
    return {"results": results, "total": len(results)}


@router.get("/search/inspect", response_model=InspectResponse)
async def inspect(
    repo_id: str = Query(...,
                         description="HuggingFace repository ID, e.g. 'org/model'"),
    svc: SearchService = Depends(get_search_service),
):
    """Get detailed information about a HuggingFace repository."""
    info = svc.inspect(repo_id)
    if info is None:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=404, detail=f"Repository not found: {repo_id}")
    return info
