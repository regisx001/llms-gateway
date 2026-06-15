"""File validation — verify downloaded artifacts."""

from __future__ import annotations

import hashlib
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def validate_file(path: Path, expected_size: int = 0) -> list[str]:
    """Validate a downloaded file. Returns list of issues."""
    issues = []
    if not path.exists():
        issues.append(f"File not found: {path}")
        return issues

    actual = path.stat().st_size
    if actual == 0:
        issues.append(f"File is empty: {path}")
    if expected_size and actual != expected_size:
        issues.append(f"Size mismatch: expected {expected_size}, got {actual}")

    # Check GGUF magic bytes
    if path.suffix == ".gguf" and actual >= 4:
        with open(path, "rb") as f:
            magic = f.read(4)
        if magic != b"\x47\x47\x55\x46":
            issues.append(f"Invalid GGUF magic bytes: {magic.hex()}")

    return issues
