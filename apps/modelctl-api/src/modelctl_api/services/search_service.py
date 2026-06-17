"""Search service — delegates to modelctl_core HuggingFace client."""

from __future__ import annotations

from modelctl_core import huggingface as hf


class SearchService:
    """Business logic for HuggingFace search and inspect."""

    def search(self, query: str, limit: int = 15) -> list[dict]:
        """Search HuggingFace for GGUF repositories."""
        if not query.strip():
            return []
        return hf.search(query.strip(), limit=limit)

    def inspect(self, repo_id: str) -> dict | None:
        """Get detailed information about a HuggingFace repository."""
        if not repo_id.strip():
            return None
        info = hf.inspect(repo_id.strip())
        if not info:
            return None
        return {
            "repo_id": info["repo_id"],
            "type": info["type"],
            "description": info.get("description", ""),
            "downloads": info["downloads"],
            "likes": info["likes"],
            "license": info.get("license", ""),
            "pipeline_tag": info.get("pipeline_tag", ""),
            "library_name": info.get("library_name", ""),
            "gguf_files": info["gguf_files"],
            "total_files": len(info.get("all_files", [])),
        }
