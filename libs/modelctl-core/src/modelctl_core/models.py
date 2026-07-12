"""Data models for the registry."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional

MODEL_TYPES = ("chat", "embedding", "reranker", "vision", "experimental")
FILE_TYPES = ("gguf", "tokenizer", "config",
              "documentation", "adapter", "other")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id() -> str:
    return uuid.uuid4().hex[:12]


@dataclass
class Artifact:
    name: str
    role: str = "primary"
    path: str = ""
    size: int = 0
    file_type: str = "gguf"
    sha256: str = ""

    def __post_init__(self):
        if not self.path:
            self.path = f"files/{self.name}"


@dataclass
class Download:
    url: str
    destination: str
    total_bytes: int = 0
    downloaded_bytes: int = 0
    status: str = "pending"  # pending | downloading | completed | failed
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class Model:
    id: str = ""
    name: str = ""
    type: str = "chat"
    provider: str = "huggingface"
    repo_id: str = ""
    storage_path: str = ""
    status: str = "registered"  # registered | downloading | installed | active | error
    installed_at: Optional[str] = None
    artifacts: list[Artifact] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.id and self.name:
            self.id = self.name.lower().replace(" ", "-")[:64]
            self.id = f"{self.id}-{_id()}"
        if isinstance(self.artifacts, list):
            self.artifacts = [a if isinstance(
                a, Artifact) else Artifact(**a) for a in self.artifacts]
        if not self.storage_path and self.id:
            self.storage_path = f"{self.type}/{self.id}"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["artifacts"] = [asdict(a) for a in self.artifacts]
        return d
