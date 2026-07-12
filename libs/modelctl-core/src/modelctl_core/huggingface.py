"""HuggingFace Hub provider — search, inspect, download."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional
from urllib.parse import quote

import requests

from .models import Model, Artifact

HF_API = "https://huggingface.co/api/models"
HF_RESOLVE = "https://huggingface.co/{repo_id}/resolve/main/{filename}"


def _headers() -> dict:
    h = {"User-Agent": "modelctl/0.2"}
    token = os.environ.get("HF_TOKEN")
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _infer_type(repo_info: dict) -> str:
    pipeline = repo_info.get("pipeline_tag", "")
    if pipeline in ("text-generation", "text2text-generation"):
        return "chat"
    if pipeline in ("feature-extraction", "sentence-similarity"):
        return "embedding"
    if pipeline in ("image-to-text", "image-classification", "object-detection"):
        return "vision"
    if "rerank" in repo_info.get("id", "").lower():
        return "reranker"
    return "experimental"


def _filter_gguf_files(siblings: list[dict]) -> list[dict]:
    """Return GGUF files with filename and size, sorted by quantization."""
    files = [
        {"filename": s["rfilename"], "size": s.get("size", 0)}
        for s in siblings
        if s["rfilename"].endswith(".gguf")
    ]

    def sort_key(f):
        m = re.search(r"Q(\d+)", f["filename"], re.IGNORECASE)
        return int(m.group(1)) if m else 99

    files.sort(key=sort_key)
    return files


def search(query: str, limit: int = 15) -> list[dict]:
    """Search HuggingFace for repositories matching query."""
    url = f"{HF_API}?search={quote(query)}&sort=downloads&direction=-1&limit={limit}"
    resp = requests.get(url, headers=_headers(), timeout=15)
    resp.raise_for_status()
    results = []
    for repo in resp.json():
        results.append({
            "repo_id": repo["modelId"],
            "type": _infer_type(repo),
            "downloads": repo.get("downloads", 0),
            "likes": repo.get("likes", 0),
            "tags": [repo.get("pipeline_tag", "")] + repo.get("tags", [])[:3],
            "license": repo.get("cardData", {}).get("license", ""),
        })
    return results


def inspect(repo_id: str) -> Optional[dict]:
    """Get detailed info about a repository including all files."""
    url = f"{HF_API}/{repo_id}?blobs=1"
    resp = requests.get(url, headers=_headers(), timeout=15)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    repo = resp.json()
    siblings = repo.get("siblings", [])
    gguf_files = _filter_gguf_files(siblings)
    all_files = [s["rfilename"] for s in siblings]

    return {
        "repo_id": repo["modelId"],
        "type": _infer_type(repo),
        "description": repo.get("cardData", {}).get("description", ""),
        "downloads": repo.get("downloads", 0),
        "likes": repo.get("likes", 0),
        "license": repo.get("cardData", {}).get("license", ""),
        "pipeline_tag": repo.get("pipeline_tag", ""),
        "library_name": repo.get("library_name", ""),
        "gguf_files": gguf_files,
        "all_files": all_files,
        "siblings": siblings,
    }


def download_file(repo_id: str, filename: str, dest_dir: Path, on_progress=None) -> Path:
    """Download a single file from a HuggingFace repo to dest_dir."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / filename
    # Ensure parent dirs exist for nested paths (e.g., MTP/model.gguf)
    dest.parent.mkdir(parents=True, exist_ok=True)
    url = HF_RESOLVE.format(repo_id=repo_id, filename=filename)

    resp = requests.get(url, headers=_headers(), stream=True, timeout=30)
    resp.raise_for_status()
    total = int(resp.headers.get("content-length", 0))

    downloaded = 0
    with open(dest, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
            downloaded += len(chunk)
            if on_progress and total:
                on_progress(downloaded, total)

    return dest


def build_model_from_repo(
    repo_id: str,
    filename: str,
    model_type: str = "",
    repo_info: Optional[dict] = None,
) -> Model:
    """Build a Model object from repo info ready for installation."""
    if not repo_info:
        info = inspect(repo_id)
    else:
        info = repo_info

    if not info:
        raise ValueError(f"Repository {repo_id} not found")

    model_type = model_type or info["type"]
    model_id = repo_id.split(
        "/")[-1].lower().replace("_", "-").replace(".", "-")
    name = repo_id.split("/")[-1]

    artifact = Artifact(
        name=filename,
        role="primary",
        file_type="gguf",
    )

    return Model(
        id=model_id,
        name=name,
        type=model_type,
        provider="huggingface",
        repo_id=repo_id,
        status="registered",
        artifacts=[artifact],
        metadata={
            "pipeline_tag": info.get("pipeline_tag", ""),
            "library_name": info.get("library_name", ""),
            "siblings": info.get("siblings", []),
        },
    )
